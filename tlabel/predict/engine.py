"""
预标注引擎 — 规则+统计推断 + 时序后处理

Pipeline:
  1. 从已有标注中提取统计特征（均值/方差/阈值）
  2. 对未标注帧，用规则推断关键维度（contact / slip_event / force_magnitude）
  3. 联动规则自动填充依赖维度
  4. 置信度评分，低置信度高亮供人工校正
  5. [v0.5.0] 时序后处理：平滑+HMM Phase解码+联动修正

v0.17 Breaking Change:
  - 彻底移除 _compat 兼容层，所有字段通过 frame.schema_v2 直接访问
  - deformation_magnitude → object_deformation
  - shear_field_magnitude → 从 force_vector 计算
  - contact_area → 从 sensor_specific 获取
"""

import math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from tlabel.core.types import TLabelData, TLabelFrame, _sv2_scalar


# ─────────────────────────────────────────────
# Schema V2 字段访问辅助函数
# ─────────────────────────────────────────────

def _get_shear_magnitude(frame: TLabelFrame) -> float:
    """从 force_vector 水平分量计算剪切力模长"""
    sv2 = frame.schema_v2
    if sv2 is not None and sv2.force_vector is not None:
        fv = sv2.force_vector
        if len(fv) >= 2:
            return math.sqrt(fv[0] ** 2 + fv[1] ** 2)
    return 0.0


def _get_contact_area(frame: TLabelFrame) -> float:
    """获取接触面积（从 sensor_specific）"""
    ss = frame.sensor_specific
    if ss and "contact_area" in ss:
        return float(ss["contact_area"])
    return 0.0


def _get_centroid_x(frame: TLabelFrame) -> float:
    """获取接触质心 X 坐标"""
    sv2 = frame.schema_v2
    if sv2 is not None and sv2.contact_centroid is not None:
        return float(sv2.contact_centroid[0])
    return 0.0


@dataclass
class PredictResult:
    """单帧预标注结果"""
    frame_idx: int
    predictions: Dict[str, float]
    confidence: Dict[str, float]  # 0-1, 越高越可信
    method: Dict[str, str]  # "rule" / "stat" / "cascade" / "hmm" / "smooth"


@dataclass
class PredictConfig:
    """预标注配置"""
    # contact检测阈值
    force_contact_threshold: float = 0.15
    deformation_contact_threshold: float = 0.10
    # slip检测参数
    slip_force_delta_threshold: float = 0.08
    slip_shear_threshold: float = 0.12
    # 时序窗口
    temporal_window: int = 3
    # 置信度阈值（低于此值标为低置信）
    low_confidence_threshold: float = 0.6
    # [v0.5.0] 时序后处理开关
    enable_postprocess: bool = True
    # [v0.5.0] Phase HMM开关
    enable_hmm_phase: bool = True


class PredictEngine:
    """
    AI辅助预标注引擎

    用法:
        engine = PredictEngine()
        results = engine.predict(data)
        engine.apply(data, results, min_confidence=0.7)  # 只应用高置信预测
    """

    # Schema V2 标量数值字段（用于 fit 统计）
    _STAT_FIELDS = [
        "contact", "force_magnitude", "slip_event",
        "object_deformation", "temperature", "confidence",
    ]

    def __init__(self, config: Optional[PredictConfig] = None):
        self.config = config or PredictConfig()
        self._stats: Dict = {}

    def fit(self, data: TLabelData) -> "PredictEngine":
        if not data.frames:
            return self
        self._stats = {}
        for key in self._STAT_FIELDS:
            values = [_sv2_scalar(f, key) for f in data.frames]
            if not values:
                continue
            mean = sum(values) / len(values)
            var = sum((v - mean) ** 2 for v in values) / len(values)
            std = math.sqrt(var)
            sorted_vals = sorted(values)
            q25 = sorted_vals[len(sorted_vals) // 4]
            q75 = sorted_vals[3 * len(sorted_vals) // 4]
            contact_count = max(1, sum(1 for f in data.frames if f.contact > 0.5))
            no_contact_count = max(1, sum(1 for f in data.frames if f.contact <= 0.5))
            self._stats[key] = {
                "mean": mean,
                "std": std,
                "min": min(values),
                "max": max(values),
                "q25": q25,
                "q75": q75,
                "iqr": q75 - q25,
                "contact_mean": sum(v for v, f in zip(values, data.frames) if f.contact > 0.5) / contact_count,
                "no_contact_mean": sum(v for v, f in zip(values, data.frames) if f.contact <= 0.5) / no_contact_count,
            }
        return self

    def predict(self, data: TLabelData,
                target_fields: Optional[List[str]] = None) -> List[PredictResult]:
        # Step 1: 逐帧规则推断
        raw_results = []
        for i, frame in enumerate(data.frames):
            result = self._predict_frame(frame, i, data)
            if target_fields:
                result.predictions = {k: v for k, v in result.predictions.items() if k in target_fields}
                result.confidence = {k: v for k, v in result.confidence.items() if k in target_fields}
                result.method = {k: v for k, v in result.method.items() if k in target_fields}
            raw_results.append(result)

        # Step 2: [v0.5.0] 时序后处理
        if self.config.enable_postprocess and raw_results:
            from tlabel.predict.postprocess import PostProcessor, PostProcessConfig
            pp_config = PostProcessConfig(
                enable_smoothing=True,
                enable_hmm=self.config.enable_hmm_phase,
                enable_cascade_fix=True,
            )
            processor = PostProcessor(pp_config)

            frames_data = []
            for frame in data.frames:
                frames_data.append({
                    "contact": _sv2_scalar(frame, "contact"),
                    "force_magnitude": _sv2_scalar(frame, "force_magnitude"),
                    "slip_event": _sv2_scalar(frame, "slip_event"),
                    "object_deformation": _sv2_scalar(frame, "object_deformation"),
                })

            existing_phases = [f.manipulation_phase for f in data.frames]
            raw_results = processor.process(raw_results, frames_data, existing_phases)

        return raw_results

    def apply(self, data: TLabelData, results: List[PredictResult],
              min_confidence: float = 0.0, cascade: bool = True) -> int:
        applied = 0
        for result in results:
            frame = data.get_frame(result.frame_idx)
            if frame is None:
                continue
            for field, value in result.predictions.items():
                conf = result.confidence.get(field, 0.0)
                if conf >= min_confidence:
                    if field == "manipulation_phase":
                        if frame.manipulation_phase != value:
                            frame.manipulation_phase = str(value)
                            applied += 1
                    else:
                        old = _sv2_scalar(frame, field)
                        if old != value:
                            frame.patch(field, value, cascade=cascade)
                            applied += 1
        return applied

    def _predict_frame(self, frame: TLabelFrame, idx: int,
                       data: TLabelData) -> PredictResult:
        predictions = {}
        confidence = {}
        method = {}
        sv2 = frame.schema_v2

        # === 1. contact推断 ===
        force_mag = sv2.force_magnitude if sv2.force_magnitude is not None else 0.0
        deform_mag = sv2.object_deformation if sv2.object_deformation is not None else 0.0
        contact_area = _get_contact_area(frame)

        force_threshold = self.config.force_contact_threshold
        deform_threshold = self.config.deformation_contact_threshold

        if self._stats:
            force_stat = self._stats.get("force_magnitude", {})
            deform_stat = self._stats.get("object_deformation", {})
            if force_stat.get("no_contact_mean", 0) > 0:
                force_threshold = force_stat["no_contact_mean"] * 2
            if deform_stat.get("no_contact_mean", 0) > 0:
                deform_threshold = deform_stat["no_contact_mean"] * 2

        contact_score = 0.0
        signals = 0
        if force_mag > force_threshold:
            contact_score += 1.0
            signals += 1
        if deform_mag > deform_threshold:
            contact_score += 1.0
            signals += 1
        if contact_area > 0.1:
            contact_score += 1.0
            signals += 1

        if signals > 0:
            predicted_contact = 1.0 if contact_score >= 2.0 else round(contact_score / 3, 2)
            conf = 0.9 if contact_score >= 3.0 else (0.7 if contact_score >= 2.0 else 0.4)
        else:
            predicted_contact = 0.0
            conf = 0.85

        if not sv2.contact:
            predictions["contact"] = predicted_contact
            confidence["contact"] = conf
            method["contact"] = "rule"

        # === 2. slip_event推断 ===
        shear_mag = _get_shear_magnitude(frame)
        delta_force = self._delta_force(frame, idx, data)
        delta_shear = self._delta_shear(frame, idx, data)

        slip_score = 0.0
        slip_signals = 0
        if shear_mag > self.config.slip_shear_threshold:
            slip_score += 1.0
            slip_signals += 1
        if delta_force > self.config.slip_force_delta_threshold:
            slip_score += 0.5
            slip_signals += 1
        if delta_shear > self.config.slip_shear_threshold * 0.5:
            slip_score += 0.5
            slip_signals += 1

        if slip_signals > 0:
            predicted_slip = 1.0 if slip_score >= 1.5 else round(slip_score / 2, 2)
            slip_conf = 0.8 if slip_score >= 2.0 else (0.6 if slip_score >= 1.0 else 0.3)
        else:
            predicted_slip = 0.0
            slip_conf = 0.85

        if not sv2.slip_event:
            predictions["slip_event"] = predicted_slip
            confidence["slip_event"] = slip_conf
            method["slip_event"] = "rule"

        # === 3. force_magnitude推断（从形变+剪切力） ===
        if sv2.force_magnitude is None or sv2.force_magnitude == 0:
            if sv2.contact:
                est_force = max(force_mag, deform_mag, shear_mag * 0.5)
                if est_force > 0.01:
                    predictions["force_magnitude"] = round(est_force, 3)
                    confidence["force_magnitude"] = 0.5
                    method["force_magnitude"] = "stat"

        # === 4. object_deformation推断 ===
        if sv2.object_deformation is None or sv2.object_deformation == 0:
            if sv2.contact:
                # 简单推断：如果有力但没有形变，从力反推
                if force_mag > 0.01:
                    predictions["object_deformation"] = round(force_mag * 0.8, 3)
                    confidence["object_deformation"] = 0.4
                    method["object_deformation"] = "stat"

        return PredictResult(
            frame_idx=frame.frame_idx,
            predictions=predictions,
            confidence=confidence,
            method=method,
        )

    def _delta_force(self, frame: TLabelFrame, idx: int, data: TLabelData) -> float:
        """计算与前帧的力变化量"""
        if idx == 0:
            return 0.0
        prev_frame = data.frames[idx - 1]
        curr = frame.schema_v2.force_magnitude if frame.schema_v2.force_magnitude is not None else 0.0
        prev = prev_frame.schema_v2.force_magnitude if prev_frame.schema_v2.force_magnitude is not None else 0.0
        return abs(curr - prev)

    def _delta_shear(self, frame: TLabelFrame, idx: int, data: TLabelData) -> float:
        """计算与前帧的剪切力变化量"""
        if idx == 0:
            return 0.0
        prev_frame = data.frames[idx - 1]
        return abs(_get_shear_magnitude(frame) - _get_shear_magnitude(prev_frame))

    def summary(self, results: List[PredictResult]) -> Dict:
        """预标注结果摘要"""
        total = len(results)
        field_counts = {}
        field_conf = {}
        method_counts = {"rule": 0, "stat": 0, "cascade": 0, "hmm": 0, "smooth": 0}

        for r in results:
            for f in r.predictions:
                field_counts[f] = field_counts.get(f, 0) + 1
                if f not in field_conf:
                    field_conf[f] = []
                field_conf[f].append(r.confidence.get(f, 0))
            for m in r.method.values():
                for base_m in m.split("+"):
                    if base_m in method_counts:
                        method_counts[base_m] += 1

        avg_conf = {f: round(sum(c) / len(c), 3) for f, c in field_conf.items() if c}

        return {
            "total_frames": total,
            "predicted_fields": field_counts,
            "avg_confidence": avg_conf,
            "method_distribution": method_counts,
        }

    # ============================================================
    # v0.14.0: Motor Primitive 预标注
    # ============================================================

    def predict_primitives(self, data: TLabelData, taxonomy=None) -> List[Dict]:
        """
        基于 taxonomy 规则引擎自动检测 primitive 区间

        Args:
            data: TLabelData 实例
            taxonomy: TaxonomyConfig 实例，None 则使用默认 7 种

        Returns:
            List of primitive annotation dicts
        """
        from tlabel.core.taxonomy import default_taxonomy, evaluate_rule

        tax = taxonomy or default_taxonomy()
        primitives = tax.get_primitives()
        if not primitives:
            return []

        # 逐帧评估每个 primitive
        frame_scores = []
        for frame in data.frames:
            scores = {}
            for name in primitives:
                rule = tax.get_rule(name)
                if rule:
                    matched, conf = evaluate_rule(rule, frame)
                    scores[name] = conf if matched else 0.0
            frame_scores.append(scores)

        # 区间合并：连续帧同一 primitive → 合并为一个标注
        annotations = []
        for name in primitives:
            start = None
            for i, scores in enumerate(frame_scores):
                if scores.get(name, 0) > 0:
                    if start is None:
                        start = i
                else:
                    if start is not None:
                        end = i - 1
                        avg_conf = sum(frame_scores[j].get(name, 0) for j in range(start, end + 1)) / (end - start + 1)
                        annotations.append({
                            'primitive_name': name,
                            'start_frame': data.frames[start].frame_idx,
                            'end_frame': data.frames[end].frame_idx,
                            'confidence': round(avg_conf, 4),
                            'source': 'ai_predicted',
                        })
                        start = None
            if start is not None:
                end = len(frame_scores) - 1
                avg_conf = sum(frame_scores[j].get(name, 0) for j in range(start, end + 1)) / (end - start + 1)
                annotations.append({
                    'primitive_name': name,
                    'start_frame': data.frames[start].frame_idx,
                    'end_frame': data.frames[end].frame_idx,
                    'confidence': round(avg_conf, 4),
                    'source': 'ai_predicted',
                })

        return annotations

    def apply_primitives(self, data: TLabelData, min_confidence: float = 0.4) -> int:
        """应用 primitive 预标注到 TLabelData"""
        from tlabel.core.primitive import PrimitiveAnnotation
        annotations = self.predict_primitives(data)
        count = 0
        for ann in annotations:
            if ann['confidence'] >= min_confidence:
                try:
                    source = ann.get('source', 'ai_predicted')
                    if source == 'ai_predicted_estimated':
                        source = 'ai_predicted'
                    pa = PrimitiveAnnotation(
                        name=ann['primitive_name'],
                        start=ann['start_frame'],
                        end=ann['end_frame'],
                        confidence=ann['confidence'],
                        source=source,
                    )
                    data.primitive_annotations.append(pa)
                    count += 1
                except ValueError:
                    pass
        return count

    # ============================================================
    # v0.14.0: Tactile Event 预测
    # ============================================================

    def predict_events(self, data: TLabelData) -> List[Dict]:
        """
        基于阈值+统计的自动事件检测

        检测6种事件类型:
        - contact_onset: contact从0→1的跳变帧
        - contact_loss: contact从1→0的跳变帧
        - slip: slip_event > 阈值 且 contact > 0.5
        - force_spike: 力值突变（delta > 2σ）
        - deformation_anomaly: 形变异常（超出正常范围）
        - stable_grip: 连续N帧contact稳定 + 力波动小
        """
        from tlabel.core.events import TactileEvent, EVENT_PRESETS

        if not data.frames or len(data.frames) < 3:
            return []

        events = []
        n = len(data.frames)

        # 提取时序信号
        contacts = [_sv2_scalar(f, "contact") for f in data.frames]
        slips = [_sv2_scalar(f, "slip_event") for f in data.frames]
        forces = [_sv2_scalar(f, "force_magnitude") for f in data.frames]
        deformations = [_sv2_scalar(f, "object_deformation") for f in data.frames]

        # 计算力的统计量
        force_mean = sum(forces) / n if n > 0 else 0.0
        force_var = sum((f - force_mean) ** 2 for f in forces) / n if n > 0 else 0.0
        force_std = math.sqrt(force_var) if force_var > 0 else 0.01

        # 形变统计量
        deform_mean = sum(deformations) / n if n > 0 else 0.0
        deform_var = sum((d - deform_mean) ** 2 for d in deformations) / n if n > 0 else 0.0
        deform_std = math.sqrt(deform_var) if deform_var > 0 else 0.01

        # ── 1. contact_onset & contact_loss ──
        for i in range(1, n):
            prev_contact = contacts[i - 1]
            curr_contact = contacts[i]
            frame_idx = data.frames[i].frame_idx

            if prev_contact <= 0.3 and curr_contact > 0.5:
                events.append({
                    "event_type": "contact_onset",
                    "frame_idx": frame_idx,
                    "confidence": 0.9,
                    "source": "ai_predicted",
                    "metadata": {"prev_contact": prev_contact, "curr_contact": curr_contact},
                })
            elif prev_contact > 0.5 and curr_contact <= 0.3:
                events.append({
                    "event_type": "contact_loss",
                    "frame_idx": frame_idx,
                    "confidence": 0.9,
                    "source": "ai_predicted",
                    "metadata": {"prev_contact": prev_contact, "curr_contact": curr_contact},
                })

        # ── 2. slip (区间事件) ──
        slip_start = None
        slip_threshold = 0.3
        for i in range(n):
            if slips[i] > slip_threshold and contacts[i] > 0.5:
                if slip_start is None:
                    slip_start = i
            else:
                if slip_start is not None:
                    end_i = i - 1
                    if end_i - slip_start >= 1:
                        events.append({
                            "event_type": "slip",
                            "frame_idx": data.frames[slip_start].frame_idx,
                            "start_frame": data.frames[slip_start].frame_idx,
                            "end_frame": data.frames[end_i].frame_idx,
                            "confidence": 0.7,
                            "source": "ai_predicted",
                            "metadata": {
                                "max_slip": max(slips[slip_start:end_i + 1]),
                                "duration_frames": end_i - slip_start + 1,
                            },
                        })
                    slip_start = None
        if slip_start is not None:
            end_i = n - 1
            if end_i - slip_start >= 1:
                events.append({
                    "event_type": "slip",
                    "frame_idx": data.frames[slip_start].frame_idx,
                    "start_frame": data.frames[slip_start].frame_idx,
                    "end_frame": data.frames[end_i].frame_idx,
                    "confidence": 0.7,
                    "source": "ai_predicted",
                    "metadata": {
                        "max_slip": max(slips[slip_start:end_i + 1]),
                        "duration_frames": end_i - slip_start + 1,
                    },
                })

        # ── 3. force_spike ──
        force_spike_threshold = 2.0 * force_std
        for i in range(1, n):
            delta = abs(forces[i] - forces[i - 1])
            if delta > force_spike_threshold and delta > 0.01:
                events.append({
                    "event_type": "force_spike",
                    "frame_idx": data.frames[i].frame_idx,
                    "confidence": min(0.9, 0.5 + delta / (4 * force_std + 0.01)),
                    "source": "ai_predicted",
                    "metadata": {"delta": round(delta, 4), "threshold": round(force_spike_threshold, 4)},
                })

        # ── 4. deformation_anomaly (区间事件) ──
        anomaly_threshold = deform_mean + 2.5 * deform_std
        if anomaly_threshold > 0.01:
            anomaly_start = None
            for i in range(n):
                if deformations[i] > anomaly_threshold:
                    if anomaly_start is None:
                        anomaly_start = i
                else:
                    if anomaly_start is not None:
                        end_i = i - 1
                        if end_i - anomaly_start >= 0:
                            events.append({
                                "event_type": "deformation_anomaly",
                                "frame_idx": data.frames[anomaly_start].frame_idx,
                                "start_frame": data.frames[anomaly_start].frame_idx,
                                "end_frame": data.frames[end_i].frame_idx,
                                "confidence": 0.6,
                                "source": "ai_predicted",
                                "metadata": {
                                    "max_deformation": round(max(deformations[anomaly_start:end_i + 1]), 4),
                                    "threshold": round(anomaly_threshold, 4),
                                },
                            })
                        anomaly_start = None
            if anomaly_start is not None:
                end_i = n - 1
                events.append({
                    "event_type": "deformation_anomaly",
                    "frame_idx": data.frames[anomaly_start].frame_idx,
                    "start_frame": data.frames[anomaly_start].frame_idx,
                    "end_frame": data.frames[end_i].frame_idx,
                    "confidence": 0.6,
                    "source": "ai_predicted",
                    "metadata": {
                        "max_deformation": round(max(deformations[anomaly_start:end_i + 1]), 4),
                        "threshold": round(anomaly_threshold, 4),
                    },
                })

        # ── 5. stable_grip (区间事件) ──
        stable_threshold = 8
        force_variation_threshold = 0.05 * force_mean if force_mean > 0 else 0.01
        stable_start = None
        for i in range(n):
            is_stable = (contacts[i] > 0.8 and forces[i] > 0.1)
            if is_stable:
                if stable_start is None:
                    stable_start = i
            else:
                if stable_start is not None:
                    end_i = i - 1
                    duration = end_i - stable_start + 1
                    if duration >= stable_threshold:
                        seg_forces = forces[stable_start:end_i + 1]
                        seg_mean = sum(seg_forces) / len(seg_forces)
                        seg_var = sum((f - seg_mean) ** 2 for f in seg_forces) / len(seg_forces)
                        seg_std = math.sqrt(seg_var)
                        if seg_std < force_variation_threshold:
                            events.append({
                                "event_type": "stable_grip",
                                "frame_idx": data.frames[stable_start].frame_idx,
                                "start_frame": data.frames[stable_start].frame_idx,
                                "end_frame": data.frames[end_i].frame_idx,
                                "confidence": 0.75,
                                "source": "ai_predicted",
                                "metadata": {
                                    "duration_frames": duration,
                                    "mean_force": round(seg_mean, 4),
                                    "force_std": round(seg_std, 6),
                                },
                            })
                    stable_start = None
        if stable_start is not None:
            end_i = n - 1
            duration = end_i - stable_start + 1
            if duration >= stable_threshold:
                seg_forces = forces[stable_start:end_i + 1]
                seg_mean = sum(seg_forces) / len(seg_forces)
                seg_var = sum((f - seg_mean) ** 2 for f in seg_forces) / len(seg_forces)
                seg_std = math.sqrt(seg_var)
                if seg_std < force_variation_threshold:
                    events.append({
                        "event_type": "stable_grip",
                        "frame_idx": data.frames[stable_start].frame_idx,
                        "start_frame": data.frames[stable_start].frame_idx,
                        "end_frame": data.frames[end_i].frame_idx,
                        "confidence": 0.75,
                        "source": "ai_predicted",
                        "metadata": {
                            "duration_frames": duration,
                            "mean_force": round(seg_mean, 4),
                            "force_std": round(seg_std, 6),
                        },
                    })

        return events

    def apply_events(self, data: TLabelData,
                     min_confidence: float = 0.5) -> int:
        """将预测的触觉事件应用到TLabelData"""
        from tlabel.core.events import TactileEvent

        events = self.predict_events(data)
        count = 0
        for ev_dict in events:
            if ev_dict['confidence'] >= min_confidence:
                try:
                    te = TactileEvent(
                        event_type=ev_dict['event_type'],
                        frame_idx=ev_dict['frame_idx'],
                        confidence=ev_dict['confidence'],
                        source=ev_dict['source'],
                        start_frame=ev_dict.get('start_frame'),
                        end_frame=ev_dict.get('end_frame'),
                        metadata=ev_dict.get('metadata'),
                    )
                    data.tactile_events.append(te)
                    count += 1
                except (ValueError, KeyError):
                    pass
        return count
