"""
QualityScorer — 数据质量评分引擎

对标国标《具身智能数据质量规范》TC28/SC42

4个评分维度：
1. physical_consistency (30%): 物理一致性 — 联动规则是否满足
2. temporal_smoothness (25%): 时序平滑度 — 相邻帧是否突变
3. completeness (25%): 完整性 — 字段缺失/全零比例
4. coverage (20%): 标注覆盖率 — 有意义的标注占比

综合评分 = 加权平均，映射到 0-100
等级: A(≥90) / B(≥75) / C(≥60) / D(≥40) / F(<40)
"""

import math
from typing import Dict, List, Optional

from tlabel.core.types import TLabelData, TLabelFrame


# 22维特征完整列表
TLABEL_DIMS = [
    "contact", "deformation_magnitude", "force_magnitude", "force_peak",
    "force_direction", "slip_entropy", "slip_event", "texture_energy",
    "edge_density", "contact_area", "centroid_x",
    "normal_field_magnitude", "normal_field_variance",
    "shear_field_magnitude", "shear_field_direction",
    "delta_force_normal", "delta_force_shear", "friction_cone_ratio",
    "optical_flow_magnitude", "optical_flow_direction",
    "temporal_deformation_rate", "contact_transition",
]


class QualityScorer:
    """数据质量评分器"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def score(self, data: TLabelData) -> Dict:
        """
        计算数据质量评分

        Returns:
            {
                "overall": float,          # 0-100
                "physical_consistency": float,
                "temporal_smoothness": float,
                "completeness": float,
                "coverage": float,
                "warnings": List[str],
                "grade": str,
            }
        """
        if not data.frames:
            return {
                "overall": 0.0,
                "physical_consistency": 0.0,
                "temporal_smoothness": 0.0,
                "completeness": 0.0,
                "coverage": 0.0,
                "warnings": ["数据为空"],
                "grade": "F",
            }

        warnings = []

        # 1. 物理一致性
        phys_score, phys_warnings = self._physical_consistency(data)
        warnings.extend(phys_warnings)

        # 2. 时序平滑度
        temporal_score, temporal_warnings = self._temporal_smoothness(data)
        warnings.extend(temporal_warnings)

        # 3. 完整性
        comp_score, comp_warnings = self._completeness(data)
        warnings.extend(comp_warnings)

        # 4. 覆盖率
        cov_score, cov_warnings = self._coverage(data)
        warnings.extend(cov_warnings)

        # 加权综合
        overall = (
            phys_score * 0.30 +
            temporal_score * 0.25 +
            comp_score * 0.25 +
            cov_score * 0.20
        )
        overall = round(overall, 1)

        grade = self._grade(overall)

        return {
            "overall": overall,
            "physical_consistency": round(phys_score, 1),
            "temporal_smoothness": round(temporal_score, 1),
            "completeness": round(comp_score, 1),
            "coverage": round(cov_score, 1),
            "warnings": warnings,
            "grade": grade,
        }

    def _physical_consistency(self, data: TLabelData) -> tuple:
        """
        物理一致性检查：
        - contact=0 时，force_magnitude应为0
        - contact=0 时，slip_event应为0
        - slip_event>0 时，contact应>0
        - force_magnitude>0 时，contact应>0
        - contact_area>0 时，contact应>0
        """
        violations = 0
        total_checks = 0
        warnings = []

        for frame in data.frames:
            tv2 = frame.tlabel_v2
            contact = tv2.get("contact", 0)
            force = tv2.get("force_magnitude", 0)
            slip = tv2.get("slip_event", 0)
            area = tv2.get("contact_area", 0)

            # Rule 1: contact=0 → force should be ~0
            if contact < 0.1:
                total_checks += 1
                if force > 0.15:
                    violations += 1
                    if self.verbose:
                        warnings.append(f"Frame {frame.frame_idx}: contact={contact:.2f} but force={force:.2f}")

            # Rule 2: contact=0 → slip should be 0
            if contact < 0.1:
                total_checks += 1
                if slip > 0.5:
                    violations += 1
                    if self.verbose:
                        warnings.append(f"Frame {frame.frame_idx}: contact={contact:.2f} but slip_event={slip:.2f}")

            # Rule 3: slip>0 → contact should be >0
            if slip > 0.5:
                total_checks += 1
                if contact < 0.1:
                    violations += 1
                    if self.verbose:
                        warnings.append(f"Frame {frame.frame_idx}: slip_event={slip:.2f} but contact={contact:.2f}")

            # Rule 4: force>0 → contact should be >0
            if force > 0.15:
                total_checks += 1
                if contact < 0.1:
                    violations += 1

            # Rule 5: area>0 → contact should be >0
            if area > 0.1:
                total_checks += 1
                if contact < 0.1:
                    violations += 1

        if total_checks == 0:
            return 100.0, []

        consistency = (1 - violations / total_checks) * 100

        if violations > 0:
            warnings.insert(0, f"物理一致性违规: {violations}/{total_checks} 次检查未通过")

        return consistency, warnings

    def _temporal_smoothness(self, data: TLabelData) -> tuple:
        """
        时序平滑度：检查相邻帧之间的突变

        对每个维度，计算相邻帧差值，超过3倍标准差视为突变
        """
        warnings = []
        if len(data.frames) < 2:
            return 100.0, []

        # 计算每个维度的差值
        keys = data.dimension_keys
        total_jumps = 0
        total_pairs = 0

        for key in keys:
            values = [f.tlabel_v2.get(key, 0.0) for f in data.frames]
            diffs = [abs(values[i+1] - values[i]) for i in range(len(values) - 1)]

            if not diffs:
                continue

            mean_diff = sum(diffs) / len(diffs)
            var_diff = sum((d - mean_diff) ** 2 for d in diffs) / len(diffs)
            std_diff = math.sqrt(var_diff) if var_diff > 0 else 0

            threshold = mean_diff + 3 * std_diff if std_diff > 0 else mean_diff * 5

            for i, d in enumerate(diffs):
                total_pairs += 1
                if threshold > 0 and d > threshold:
                    total_jumps += 1

        if total_pairs == 0:
            return 100.0, []

        smoothness = (1 - total_jumps / total_pairs) * 100

        if total_jumps > total_pairs * 0.05:
            warnings.append(f"时序突变较多: {total_jumps}/{total_pairs} 帧对存在突变")

        return smoothness, warnings

    def _completeness(self, data: TLabelData) -> tuple:
        """
        完整性：检查字段缺失和全零比例

        - 期望22维特征都存在
        - 全零帧比例不应过高
        """
        warnings = []

        # Check dimension count
        keys = data.dimension_keys
        expected_dims = 22
        dim_ratio = min(len(keys) / expected_dims, 1.0)

        if len(keys) < expected_dims:
            warnings.append(f"维度不完整: {len(keys)}/{expected_dims}")

        # Check all-zero frames
        all_zero_count = 0
        for frame in data.frames:
            non_zero = sum(1 for v in frame.tlabel_v2.values() if v != 0)
            # centroid_x and force_direction can be non-zero in idle, so use contact-related dims
            if frame.contact < 0.1:
                contact_related = [
                    frame.tlabel_v2.get("force_magnitude", 0),
                    frame.tlabel_v2.get("slip_event", 0),
                    frame.tlabel_v2.get("contact_area", 0),
                    frame.tlabel_v2.get("deformation_magnitude", 0),
                ]
                if all(v == 0 for v in contact_related):
                    all_zero_count += 1

        # all-zero frames in non-contact regions are OK
        # But check if contact frames have meaningful data
        contact_frames = [f for f in data.frames if f.contact > 0.5]
        empty_contact = 0
        for f in contact_frames:
            has_force = f.tlabel_v2.get("force_magnitude", 0) > 0
            has_deform = f.tlabel_v2.get("deformation_magnitude", 0) > 0
            has_area = f.tlabel_v2.get("contact_area", 0) > 0
            if not (has_force or has_deform or has_area):
                empty_contact += 1

        if contact_frames and empty_contact > 0:
            empty_ratio = empty_contact / len(contact_frames)
            warnings.append(f"接触帧中{empty_ratio:.0%}缺少力度/形变/面积数据")
            contact_quality = (1 - empty_ratio) * 100
        else:
            contact_quality = 100.0

        completeness = dim_ratio * 0.3 + contact_quality * 0.7

        return completeness, warnings

    def _coverage(self, data: TLabelData) -> tuple:
        """
        覆盖率：有意义的标注占比

        - 接触帧占比不应为0
        - 置信度>0.5的帧占比
        - 至少有一些slip事件（如果数据足够长）
        """
        warnings = []

        total = len(data.frames)
        if total == 0:
            return 0.0, ["无帧数据"]

        # Contact coverage
        contact_count = sum(1 for f in data.frames if f.contact > 0.5)
        contact_ratio = contact_count / total

        # Confidence coverage
        high_conf = sum(1 for f in data.frames if f.confidence > 0.5)
        conf_ratio = high_conf / total

        # Phase diversity
        phases = set(f.manipulation_phase for f in data.frames)
        phase_diversity = min(len(phases) / 5, 1.0)  # 5 phases = good diversity

        # Slip coverage (for long episodes)
        slip_count = sum(1 for f in data.frames if f.slip_event > 0.5)
        has_slip = 1.0 if slip_count > 0 else (0.5 if total < 50 else 0.0)

        if contact_ratio < 0.05:
            warnings.append("接触帧占比极低 ({:.1%})，数据可能无实际交互".format(contact_ratio))
        if conf_ratio < 0.8:
            warnings.append("高置信度帧占比低 ({:.1%})".format(conf_ratio))
        if not has_slip and total >= 50:
            warnings.append("无滑移事件标注，建议补充slip_event")

        coverage = (
            min(contact_ratio * 5, 1.0) * 0.3 +  # 接触比例，20%以上即满分
            conf_ratio * 0.3 +
            phase_diversity * 0.2 +
            has_slip * 0.2
        ) * 100

        return coverage, warnings

    @staticmethod
    def _grade(score: float) -> str:
        """将分数映射为等级"""
        if score >= 90:
            return "A"
        elif score >= 75:
            return "B"
        elif score >= 60:
            return "C"
        elif score >= 40:
            return "D"
        else:
            return "F"
