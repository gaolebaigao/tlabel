"""
时序后处理 — 消除单帧跳变，强制物理一致性

核心功能:
  1. TemporalSmoother: 连续字段(contact/force等)移动平均+中值滤波
  2. PhaseHMM: manipulation_phase的HMM建模+Viterbi解码
  3. PostProcessor: 统一后处理管线，对PredictEngine/MLEngine的结果做时序修正

设计原则:
  - 不修改原始预测值，只做后处理修正
  - 物理约束硬编码：contact归零时所有依赖字段必须归零
  - Phase转移只允许合法路径，禁止跳跃(如 idle→slip)
"""

import math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import Counter

from tlabel.predict.engine import PredictResult


# ============================================================
# Phase HMM 定义
# ============================================================

PHASE_STATES = ["idle", "initial_contact", "stable_contact", "slip", "grasp", "hold"]
PHASE_TO_IDX = {s: i for i, s in enumerate(PHASE_STATES)}
IDX_TO_PHASE = {i: s for i, s in enumerate(PHASE_STATES)}

# 合法的Phase转移（物理约束）
LEGAL_TRANSITIONS = {
    "idle": {"idle", "initial_contact"},
    "initial_contact": {"initial_contact", "stable_contact", "grasp", "idle"},
    "stable_contact": {"stable_contact", "slip", "hold", "grasp", "initial_contact"},
    "grasp": {"grasp", "hold", "stable_contact", "slip", "idle"},
    "hold": {"hold", "slip", "stable_contact", "grasp", "idle"},
    "slip": {"slip", "stable_contact", "grasp", "idle"},
}

# 默认转移概率
def _build_default_transition():
    n = len(PHASE_STATES)
    trans = [[0.0] * n for _ in range(n)]
    for i, phase in enumerate(PHASE_STATES):
        legal = LEGAL_TRANSITIONS[phase]
        legal_indices = [PHASE_TO_IDX[s] for s in legal]
        trans[i][i] = 0.4
        other_count = len(legal_indices) - 1
        if other_count > 0:
            for j in legal_indices:
                if j != i:
                    trans[i][j] = 0.6 / other_count
        else:
            trans[i][i] = 1.0
    return trans

DEFAULT_TRANSITION = _build_default_transition()

EMISSION_SIGNALS = ["contact", "force_magnitude", "slip_event", "deformation_magnitude"]

PHASE_EMISSIONS = {
    "idle":             (0.05, 0.05, 0.05, 0.05),
    "initial_contact":  (0.60, 0.30, 0.05, 0.40),
    "stable_contact":   (0.90, 0.60, 0.10, 0.50),
    "slip":             (0.90, 0.50, 0.80, 0.40),
    "grasp":            (0.95, 0.80, 0.10, 0.60),
    "hold":             (0.95, 0.70, 0.05, 0.50),
}


def _log_emission_prob(phase, contact, force, slip, deform):
    expected = PHASE_EMISSIONS.get(phase, (0.5, 0.5, 0.5, 0.5))
    sigma = 0.25
    log_prob = 0.0
    for obs, exp in zip([contact, force, slip, deform], expected):
        diff = obs - exp
        log_prob -= (diff * diff) / (2 * sigma * sigma)
    return log_prob


# ============================================================
# TemporalSmoother
# ============================================================

class TemporalSmoother:
    """时序平滑器 — 消除单帧跳变"""

    def __init__(self, window_size=5, min_contact_run=3, edge_threshold=0.3):
        self.window_size = max(3, window_size | 1)
        self.min_contact_run = min_contact_run
        self.edge_threshold = edge_threshold

    def smooth_field(self, values):
        n = len(values)
        if n < 3:
            return values[:]
        result = values[:]
        half_w = self.window_size // 2
        for i in range(half_w, n - half_w):
            left = values[i - 1]
            right = values[i + 1]
            curr = values[i]
            if abs(curr - left) > self.edge_threshold and abs(curr - right) > self.edge_threshold:
                continue
            window = values[i - half_w:i + half_w + 1]
            result[i] = sum(window) / len(window)
        return result

    def median_filter(self, values, window=3):
        n = len(values)
        if n < window:
            return values[:]
        half_w = window // 2
        result = values[:]
        for i in range(half_w, n - half_w):
            segment = sorted(values[i - half_w:i + half_w + 1])
            result[i] = segment[len(segment) // 2]
        return result

    def denoise_contact(self, contact_values, threshold=0.5):
        n = len(contact_values)
        if n < self.min_contact_run:
            return contact_values[:]
        binary = [1.0 if v > threshold else 0.0 for v in contact_values]
        result = binary[:]

        # 消除短时脉冲
        i = 0
        while i < n:
            if result[i] > 0.5:
                run_start = i
                while i < n and result[i] > 0.5:
                    i += 1
                run_len = i - run_start
                if run_len < self.min_contact_run:
                    for j in range(run_start, i):
                        result[j] = 0.0
            else:
                i += 1

        # 消除短时间隙
        i = 0
        while i < n:
            if result[i] < 0.5:
                gap_start = i
                while i < n and result[i] < 0.5:
                    i += 1
                gap_len = i - gap_start
                before = gap_start > 0 and result[gap_start - 1] > 0.5
                after = i < n and result[i] > 0.5
                if gap_len < self.min_contact_run and before and after:
                    for j in range(gap_start, i):
                        result[j] = 1.0
            else:
                i += 1

        final = []
        for i in range(n):
            if result[i] > 0.5:
                final.append(max(contact_values[i], threshold * 1.02))
            else:
                final.append(min(contact_values[i], threshold * 0.5))
        return final

    def smooth_results(self, results, smooth_fields=None):
        if not results:
            return results
        if smooth_fields is None:
            smooth_fields = ["contact", "force_magnitude", "deformation_magnitude",
                             "slip_event", "contact_area"]

        field_series = {}
        for f in smooth_fields:
            field_series[f] = [r.predictions.get(f, 0.0) for r in results]

        for f in smooth_fields:
            series = field_series[f]
            if not series:
                continue
            if f == "contact":
                series = self.denoise_contact(series)
                series = self.smooth_field(series)
            elif f in ("slip_event",):
                series = self.median_filter(series, window=5)
            else:
                series = self.median_filter(series, window=3)
                series = self.smooth_field(series)
            field_series[f] = series

        new_results = []
        for i, r in enumerate(results):
            new_preds = dict(r.predictions)
            new_conf = dict(r.confidence)
            new_method = dict(r.method)
            for f in smooth_fields:
                if f in new_preds and f in field_series:
                    old_val = new_preds[f]
                    new_val = field_series[f][i]
                    if abs(new_val - old_val) > 0.1:
                        new_method[f] = new_method.get(f, "rule") + "+smooth"
                        new_conf[f] = min(1.0, new_conf.get(f, 0.5) + 0.1)
                    new_preds[f] = round(new_val, 4)

            new_results.append(PredictResult(
                frame_idx=r.frame_idx,
                predictions=new_preds,
                confidence=new_conf,
                method=new_method,
            ))
        return new_results


# ============================================================
# PhaseHMM
# ============================================================

class PhaseHMM:
    """Manipulation Phase HMM — Viterbi解码最优状态序列"""

    def __init__(self, transition=None, min_phase_run=3):
        self.transition = transition or DEFAULT_TRANSITION
        self.min_phase_run = min_phase_run
        self._trained = False
        self._trained_trans = None

    def fit(self, phases):
        n = len(PHASE_STATES)
        counts = [[0] * n for _ in range(n)]
        for i in range(len(phases) - 1):
            src = PHASE_TO_IDX.get(phases[i])
            dst = PHASE_TO_IDX.get(phases[i + 1])
            if src is not None and dst is not None:
                counts[src][dst] += 1

        trans = [[0.0] * n for _ in range(n)]
        for i in range(n):
            total = sum(counts[i]) + n
            for j in range(n):
                base = DEFAULT_TRANSITION[i][j]
                observed = (counts[i][j] + 1) / total if total > 0 else 0
                trans[i][j] = 0.7 * observed + 0.3 * base
            row_sum = sum(trans[i])
            if row_sum > 0:
                trans[i] = [v / row_sum for v in trans[i]]

        self._trained_trans = trans
        self._trained = True
        return self

    def decode(self, frames_data):
        n = len(frames_data)
        if n == 0:
            return []

        num_states = len(PHASE_STATES)
        trans = self._trained_trans if self._trained else self.transition

        dp = [[-math.inf] * num_states for _ in range(n)]
        backptr = [[0] * num_states for _ in range(n)]

        for s in range(num_states):
            dp[0][s] = math.log(1.0 / num_states) + self._emission_log_prob(s, frames_data[0])

        # Enforce legal phase transitions
        for t in range(1, n):
            for s in range(num_states):
                phase_s = IDX_TO_PHASE[s]
                best_prev = 0
                best_score = -math.inf
                for ps in range(num_states):
                    phase_ps = IDX_TO_PHASE[ps]
                    # Only allow legal transitions
                    if phase_s not in LEGAL_TRANSITIONS.get(phase_ps, set()):
                        continue
                    score = dp[t - 1][ps] + math.log(max(trans[ps][s], 1e-10))
                    if score > best_score:
                        best_score = score
                        best_prev = ps
                dp[t][s] = best_score + self._emission_log_prob(s, frames_data[t])
                backptr[t][s] = best_prev

        best_last = max(range(num_states), key=lambda s: dp[n - 1][s])
        path = [0] * n
        path[n - 1] = best_last
        for t in range(n - 2, -1, -1):
            path[t] = backptr[t + 1][path[t + 1]]

        phases = [IDX_TO_PHASE[idx] for idx in path]
        phases = self._remove_short_runs(phases)
        return phases

    def _emission_log_prob(self, state_idx, frame_data):
        phase = IDX_TO_PHASE[state_idx]
        contact = frame_data.get("contact", 0.0)
        force = frame_data.get("force_magnitude", 0.0)
        slip = frame_data.get("slip_event", 0.0)
        deform = frame_data.get("deformation_magnitude", 0.0)
        return _log_emission_prob(phase, contact, force, slip, deform)

    def _remove_short_runs(self, phases):
        if not phases:
            return phases
        result = phases[:]
        n = len(result)
        changed = True
        max_iter = 5
        iteration = 0
        while changed and iteration < max_iter:
            changed = False
            iteration += 1
            i = 0
            while i < n:
                run_start = i
                while i < n and result[i] == result[run_start]:
                    i += 1
                run_len = i - run_start
                if run_len < self.min_phase_run and run_start > 0 and i < n:
                    prev_phase = result[run_start - 1]
                    next_phase = result[i]
                    # Choose fill phase that maintains legal transitions
                    # Prefer the previous phase if transition from prev→prev is legal
                    # and transition from prev→next is legal
                    fill_phase = prev_phase  # default
                    if next_phase not in LEGAL_TRANSITIONS.get(fill_phase, set()):
                        # prev→next is illegal, try filling with a bridge phase
                        # Find a phase that is legal from prev AND legal to next
                        for bridge in PHASE_STATES:
                            if (bridge in LEGAL_TRANSITIONS.get(prev_phase, set()) and
                                next_phase in LEGAL_TRANSITIONS.get(bridge, set())):
                                fill_phase = bridge
                                break
                    for j in range(run_start, i):
                        result[j] = fill_phase
                    changed = True
            if n > 1 and result[0] != result[1]:
                # First frame: use legal phase from frame 1
                if result[1] in LEGAL_TRANSITIONS.get("idle", set()):
                    result[0] = result[1]
                else:
                    result[0] = "idle"
                changed = True
        return result


# ============================================================
# PostProcessor
# ============================================================

@dataclass
class PostProcessConfig:
    smooth_window: int = 5
    min_contact_run: int = 3
    edge_threshold: float = 0.3
    min_phase_run: int = 3
    enable_smoothing: bool = True
    enable_hmm: bool = True
    enable_cascade_fix: bool = True


class PostProcessor:
    """预标注后处理器"""

    def __init__(self, config=None):
        self.config = config or PostProcessConfig()
        self._smoother = TemporalSmoother(
            window_size=self.config.smooth_window,
            min_contact_run=self.config.min_contact_run,
            edge_threshold=self.config.edge_threshold,
        )
        self._hmm = PhaseHMM(min_phase_run=self.config.min_phase_run)

    def process(self, results, frames_data=None, existing_phases=None):
        if not results:
            return results
        processed = results
        if self.config.enable_smoothing:
            processed = self._smoother.smooth_results(processed)
        if self.config.enable_hmm:
            processed = self._decode_phases(processed, frames_data, existing_phases)
        if self.config.enable_cascade_fix:
            processed = self._fix_cascade(processed)
        return processed

    def _decode_phases(self, results, frames_data, existing_phases):
        if frames_data is None:
            frames_data = []
            for r in results:
                frames_data.append({
                    "contact": r.predictions.get("contact", 0.0),
                    "force_magnitude": r.predictions.get("force_magnitude", 0.0),
                    "slip_event": r.predictions.get("slip_event", 0.0),
                    "deformation_magnitude": r.predictions.get("deformation_magnitude", 0.0),
                })
        if existing_phases:
            self._hmm.fit(existing_phases)
        decoded_phases = self._hmm.decode(frames_data)

        new_results = []
        for i, r in enumerate(results):
            if i < len(decoded_phases):
                new_preds = dict(r.predictions)
                new_conf = dict(r.confidence)
                new_method = dict(r.method)
                new_preds["manipulation_phase"] = decoded_phases[i]
                new_conf["manipulation_phase"] = 0.8
                new_method["manipulation_phase"] = "hmm"
                new_results.append(PredictResult(
                    frame_idx=r.frame_idx,
                    predictions=new_preds,
                    confidence=new_conf,
                    method=new_method,
                ))
            else:
                new_results.append(r)
        return new_results

    def _fix_cascade(self, results):
        new_results = []
        for r in results:
            new_preds = dict(r.predictions)
            new_conf = dict(r.confidence)
            new_method = dict(r.method)
            contact = new_preds.get("contact", 0.0)

            # Step 1: Force/slip implies contact (UPGRADE contact first)
            force = new_preds.get("force_magnitude", 0.0)
            if force >= 0.2 and contact < 0.3:
                new_preds["contact"] = max(contact, 0.8)  # Boost contact
                new_method["contact"] = "cascade_fix"
                contact = new_preds["contact"]

            slip = new_preds.get("slip_event", 0.0)
            if slip >= 0.5 and contact < 0.3:
                new_preds["contact"] = max(contact, 0.8)
                new_method["contact"] = "cascade_fix"
                contact = new_preds["contact"]

            # Step 2: No contact zeros dependent fields (AFTER upgrade check)
            if contact < 0.15:
                zero_fields = ["force_magnitude", "force_peak", "slip_event",
                               "delta_force_normal", "delta_force_shear",
                               "contact_area", "contact_transition"]
                for zf in zero_fields:
                    if zf in new_preds and new_preds[zf] > 0.05:
                        new_preds[zf] = 0.0
                        new_method[zf] = new_method.get(zf, "rule") + "+cascade"

            new_results.append(PredictResult(
                frame_idx=r.frame_idx,
                predictions=new_preds,
                confidence=new_conf,
                method=new_method,
            ))
        return new_results

    def summary(self, before, after):
        total = len(before)
        changed = 0
        field_changed = {}
        for b, a in zip(before, after):
            for k in set(list(b.predictions.keys()) + list(a.predictions.keys())):
                bv = b.predictions.get(k, 0.0)
                av = a.predictions.get(k, 0.0)
                if abs(bv - av) > 0.01:
                    changed += 1
                    field_changed[k] = field_changed.get(k, 0) + 1
        return {
            "total_frames": total,
            "total_changes": changed,
            "field_changes": field_changed,
            "change_rate": round(changed / max(total * max(len(field_changed), 1), 1), 4),
        }
