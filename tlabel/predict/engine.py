"""
预标注引擎 — 规则+统计推断

Pipeline:
  1. 从已有标注中提取统计特征（均值/方差/阈值）
  2. 对未标注帧，用规则推断关键维度（contact / slip_event / force_magnitude）
  3. 联动规则自动填充依赖维度
  4. 置信度评分，低置信度高亮供人工校正
"""

import math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from tlabel.core.types import TLabelData, TLabelFrame


@dataclass
class PredictResult:
    """单帧预标注结果"""
    frame_idx: int
    predictions: Dict[str, float]
    confidence: Dict[str, float]  # 0-1, 越高越可信
    method: Dict[str, str]  # "rule" / "stat" / "cascade"


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


class PredictEngine:
    """
    AI辅助预标注引擎
    
    用法:
        engine = PredictEngine()
        results = engine.predict(data)
        engine.apply(data, results, min_confidence=0.7)  # 只应用高置信预测
    """

    def __init__(self, config: Optional[PredictConfig] = None):
        self.config = config or PredictConfig()
        self._stats: Dict = {}  # 从已有数据提取的统计特征

    def fit(self, data: TLabelData) -> "PredictEngine":
        """
        从已有标注数据中学习统计特征
        
        对部分已标注的数据，先fit再predict可提升准确率
        """
        if not data.frames:
            return self

        # 提取每个维度的统计量
        all_keys = data.dimension_keys
        self._stats = {}

        for key in all_keys:
            values = [f.tlabel_v2.get(key, 0.0) for f in data.frames]
            if not values:
                continue
            mean = sum(values) / len(values)
            var = sum((v - mean) ** 2 for v in values) / len(values)
            std = math.sqrt(var)
            sorted_vals = sorted(values)
            q25 = sorted_vals[len(sorted_vals) // 4]
            q75 = sorted_vals[3 * len(sorted_vals) // 4]
            self._stats[key] = {
                "mean": mean,
                "std": std,
                "min": min(values),
                "max": max(values),
                "q25": q25,
                "q75": q75,
                "iqr": q75 - q25,
                "contact_mean": sum(v for v, f in zip(values, data.frames) if f.contact > 0.5) / max(1, sum(1 for f in data.frames if f.contact > 0.5)),
                "no_contact_mean": sum(v for v, f in zip(values, data.frames) if f.contact <= 0.5) / max(1, sum(1 for f in data.frames if f.contact <= 0.5)),
            }
        return self

    def predict(self, data: TLabelData,
                target_fields: Optional[List[str]] = None) -> List[PredictResult]:
        """
        对TLabelData进行预标注
        
        Args:
            data: 待预标注数据
            target_fields: 只预测指定维度，None则预测所有可推断维度
        
        Returns:
            每帧一个PredictResult
        """
        results = []
        for i, frame in enumerate(data.frames):
            result = self._predict_frame(frame, i, data)
            if target_fields:
                result.predictions = {k: v for k, v in result.predictions.items() if k in target_fields}
                result.confidence = {k: v for k, v in result.confidence.items() if k in target_fields}
                result.method = {k: v for k, v in result.method.items() if k in target_fields}
            results.append(result)
        return results

    def apply(self, data: TLabelData, results: List[PredictResult],
              min_confidence: float = 0.0, cascade: bool = True) -> int:
        """
        将预标注结果应用到TLabelData（修改原数据）
        
        Args:
            data: 目标数据
            results: predict()的输出
            min_confidence: 最低置信度阈值，低于此值不应用
            cascade: 是否触发联动规则
        
        Returns:
            成功应用的字段数
        """
        applied = 0
        for result in results:
            frame = data.get_frame(result.frame_idx)
            if frame is None:
                continue
            for field, value in result.predictions.items():
                conf = result.confidence.get(field, 0.0)
                if conf >= min_confidence:
                    old = frame.tlabel_v2.get(field)
                    if old != value:
                        frame.patch(field, value, cascade=cascade)
                        applied += 1
        return applied

    def _predict_frame(self, frame: TLabelFrame, idx: int,
                       data: TLabelData) -> PredictResult:
        """对单帧进行预标注推断"""
        predictions = {}
        confidence = {}
        method = {}

        tv2 = frame.tlabel_v2

        # === 1. contact推断 ===
        # 规则：deformation/force/area任一显著非零→contact
        if "contact" in tv2:
            force_mag = tv2.get("force_magnitude", 0)
            deform_mag = tv2.get("deformation_magnitude", 0)
            contact_area = tv2.get("contact_area", 0)

            # 统计辅助：如果fit过，用contact_mean做参考
            force_threshold = self.config.force_contact_threshold
            deform_threshold = self.config.deformation_contact_threshold

            if self._stats:
                force_stat = self._stats.get("force_magnitude", {})
                deform_stat = self._stats.get("deformation_magnitude", {})
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

            # 只有当原始contact为0或缺失时才预测
            if tv2.get("contact", 0) < 0.01:
                predictions["contact"] = predicted_contact
                confidence["contact"] = conf
                method["contact"] = "rule"

        # === 2. slip_event推断 ===
        if "slip_event" in tv2:
            shear_mag = tv2.get("shear_field_magnitude", 0)
            delta_shear = tv2.get("delta_force_shear", 0)
            slip_entropy = tv2.get("slip_entropy", 0)
            is_contact = tv2.get("contact", 0) > 0.5

            slip_signals = 0
            if shear_mag > self.config.slip_shear_threshold:
                slip_signals += 1
            if delta_shear > self.config.slip_force_delta_threshold:
                slip_signals += 1
            if slip_entropy > 0.3:
                slip_signals += 1

            if is_contact and slip_signals >= 2:
                predictions["slip_event"] = 1.0
                confidence["slip_event"] = 0.75 if slip_signals >= 3 else 0.55
            else:
                predictions["slip_event"] = 0.0
                confidence["slip_event"] = 0.8
            method["slip_event"] = "rule"

        # === 3. manipulation_phase推断 ===
        if frame.manipulation_phase == "idle" or not frame.manipulation_phase:
            contact_val = predictions.get("contact", tv2.get("contact", 0))
            slip_val = predictions.get("slip_event", tv2.get("slip_event", 0))
            force_val = tv2.get("force_magnitude", 0)

            if contact_val > 0.5:
                if slip_val > 0.5:
                    predictions["manipulation_phase"] = "slip"
                    confidence["manipulation_phase"] = 0.6
                elif force_val > 0.5:
                    predictions["manipulation_phase"] = "stable_contact"
                    confidence["manipulation_phase"] = 0.65
                else:
                    predictions["manipulation_phase"] = "initial_contact"
                    confidence["manipulation_phase"] = 0.55
                method["manipulation_phase"] = "rule"

        # === 4. 统计推断：缺失维度 ===
        for key in tv2:
            if tv2[key] == 0.0 and key not in predictions and self._stats:
                stat = self._stats.get(key, {})
                # 如果该帧有contact但该维度为0，可能是缺失
                if tv2.get("contact", 0) > 0.5 and stat.get("contact_mean", 0) > 0:
                    predictions[key] = round(stat["contact_mean"], 4)
                    confidence[key] = 0.4  # 统计推断置信度较低
                    method[key] = "stat"

        return PredictResult(
            frame_idx=frame.frame_idx,
            predictions=predictions,
            confidence=confidence,
            method=method,
        )

    def summary(self, results: List[PredictResult]) -> Dict:
        """汇总预标注结果统计"""
        total = len(results)
        field_counts: Dict[str, int] = {}
        field_conf: Dict[str, List[float]] = {}
        method_counts: Dict[str, int] = {"rule": 0, "stat": 0, "cascade": 0}

        for r in results:
            for field in r.predictions:
                field_counts[field] = field_counts.get(field, 0) + 1
                if field not in field_conf:
                    field_conf[field] = []
                field_conf[field].append(r.confidence.get(field, 0))
            for m in r.method.values():
                method_counts[m] = method_counts.get(m, 0) + 1

        avg_conf = {}
        for field, confs in field_conf.items():
            avg_conf[field] = round(sum(confs) / len(confs), 3) if confs else 0

        low_conf_count = sum(
            1 for r in results
            for c in r.confidence.values()
            if c < self.config.low_confidence_threshold
        )

        return {
            "total_frames": total,
            "predicted_fields": field_counts,
            "avg_confidence": avg_conf,
            "method_distribution": method_counts,
            "low_confidence_count": low_conf_count,
            "coverage": {k: round(v / total, 3) for k, v in field_counts.items()},
        }
