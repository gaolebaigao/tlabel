"""
TLabel Format v2 数据结构 — 统一触觉标注容器

所有适配器输出此格式，review阶段交互完全统一。
"""

import json
import copy
from pathlib import Path
from typing import Optional, List, Dict, Any


class TLabelFrame:
    """单帧标注数据"""
    __slots__ = [
        "frame_idx", "timestamp_s", "tlabel_v2", "manipulation_phase",
        "confidence", "sensor_specific", "patches", "_original_tlabel"
    ]

    def __init__(self, frame_idx: int, timestamp_s: float,
                 tlabel_v2: Dict[str, float],
                 manipulation_phase: str = "idle",
                 confidence: float = 1.0,
                 sensor_specific: Optional[Dict] = None):
        self.frame_idx = frame_idx
        self.timestamp_s = timestamp_s
        self.tlabel_v2 = tlabel_v2
        self.manipulation_phase = manipulation_phase
        self.confidence = confidence
        self.sensor_specific = sensor_specific or {}
        self.patches = []
        self._original_tlabel = copy.deepcopy(tlabel_v2)

    @property
    def contact(self) -> float:
        return self.tlabel_v2.get("contact", 0.0)

    @property
    def slip_event(self) -> float:
        return self.tlabel_v2.get("slip_event", 0.0)

    @property
    def force_magnitude(self) -> float:
        return self.tlabel_v2.get("force_magnitude", 0.0)

    @property
    def is_modified(self) -> bool:
        return len(self.patches) > 0

    def patch(self, field: str, new_value: Any, cascade: bool = True):
        """修正单帧标注，支持联动"""
        old_value = self.tlabel_v2.get(field)
        patch_record = {
            "field": field,
            "old_value": old_value,
            "new_value": new_value,
        }
        self.tlabel_v2[field] = new_value
        cascades = []

        if cascade:
            cascades = self._apply_cascade(field, new_value)

        patch_record["cascade"] = cascades
        self.patches.append(patch_record)
        return patch_record

    def _apply_cascade(self, field: str, new_value: Any) -> List[Dict]:
        """联动规则 — 物理一致性约束"""
        cascades = []

        if field == "contact":
            if new_value == 0:
                # 接触归零 → 力度/滑移/力变化/面积/接触过渡全部归零
                zero_fields = [
                    "force_magnitude", "force_peak", "slip_event",
                    "delta_force_normal", "delta_force_shear",
                    "contact_area", "contact_transition",
                ]
                for zf in zero_fields:
                    if self.tlabel_v2.get(zf, 0) != 0:
                        # contact_transition阈值0.5以上才归零
                        if zf == "contact_transition" and self.tlabel_v2.get(zf, 0) <= 0.5:
                            continue
                        cascades.append({"field": zf, "old_value": self.tlabel_v2[zf], "new_value": 0.0})
                        self.tlabel_v2[zf] = 0.0
                if self.manipulation_phase in ("initial_contact", "stable_contact", "slip", "grasp", "hold"):
                    old_phase = self.manipulation_phase
                    self.manipulation_phase = "idle"
                    cascades.append({"field": "manipulation_phase", "old_value": old_phase, "new_value": "idle"})

        elif field == "slip_event":
            if new_value > 0.5 and self.tlabel_v2.get("contact", 0) < 0.5:
                # 滑移必须发生在接触状态 → 联动设置contact
                old_contact = self.tlabel_v2.get("contact", 0)
                cascades.append({"field": "contact", "old_value": old_contact, "new_value": 1.0})
                self.tlabel_v2["contact"] = 1.0
                # 如果当前phase是idle，升级为slip
                if self.manipulation_phase == "idle":
                    old_phase = self.manipulation_phase
                    self.manipulation_phase = "slip"
                    cascades.append({"field": "manipulation_phase", "old_value": old_phase, "new_value": "slip"})

        elif field == "force_magnitude":
            if new_value > 0 and self.tlabel_v2.get("contact", 0) < 0.5:
                # 有力必须有接触 → 联动设置contact
                old_contact = self.tlabel_v2.get("contact", 0)
                cascades.append({"field": "contact", "old_value": old_contact, "new_value": 1.0})
                self.tlabel_v2["contact"] = 1.0

        return cascades

    def to_dict(self, is_first: bool = False, is_last: bool = False) -> Dict:
        d = {
            "frame_idx": self.frame_idx,
            "timestamp_s": round(self.timestamp_s, 4),
            "is_first": is_first,
            "is_last": is_last,
            "tlabel_v2": {k: round(v, 4) if isinstance(v, float) else v for k, v in self.tlabel_v2.items()},
            "manipulation_phase": self.manipulation_phase,
            "confidence": round(self.confidence, 2),
        }
        if self.sensor_specific:
            d["sensor_specific"] = self.sensor_specific
        if self.patches:
            d["patches"] = self.patches
        return d


class TLabelData:
    """
    统一触觉标注容器 — 所有适配器的输出
    
    用法:
        data = tlabel.load("file.pkl")
        data.review()        # Jupyter彩色面板
        data.export("out")   # 导出
    """

    def __init__(self, frames: List[TLabelFrame],
                 sensor_info: Dict,
                 episode_info: Dict,
                 capabilities: Dict,
                 schema_version: str = "0.4.0",
                 sensor_id: Optional[str] = None,
                 calibration_params: Optional[Dict] = None):
        self.frames = frames
        self.sensor_info = sensor_info
        self.episode_info = episode_info
        self.capabilities = capabilities
        self.schema_version = schema_version
        self.sensor_id = sensor_id  # 新增：传感器标识（如 "left_gripper"）
        self.calibration_params = calibration_params or {}  # 新增：标定参数
        self._predict_results = None  # v0.5.0: 预标注结果缓存（供UI高亮）

    @property
    def num_frames(self) -> int:
        return len(self.frames)

    @property
    def duration_s(self) -> float:
        if not self.frames:
            return 0.0
        return self.frames[-1].timestamp_s - self.frames[0].timestamp_s

    @property
    def sensor_type(self) -> str:
        return self.sensor_info.get("type", "unknown")

    @property
    def dimension_keys(self) -> List[str]:
        """返回当前传感器支持的所有标注维度键名"""
        if not self.frames:
            return []
        return list(self.frames[0].tlabel_v2.keys())

    @property
    def modified_count(self) -> int:
        return sum(1 for f in self.frames if f.is_modified)

    def get_frame(self, frame_idx: int, logical: bool = False) -> Optional[TLabelFrame]:
        """按帧索引获取帧数据
        
        Args:
            frame_idx: logical=False时为全局frame_idx(原始编号)；logical=True时为位置索引(0=第一帧)
        """
        if logical:
            if 0 <= frame_idx < len(self.frames):
                return self.frames[frame_idx]
            return None
        for f in self.frames:
            if f.frame_idx == frame_idx:
                return f
        return None

    def batch_patch(self, start_frame: int, end_frame: int,
                    field: str, new_value: Any, cascade: bool = True) -> int:
        """批量修正帧区间"""
        count = 0
        for f in self.frames:
            if start_frame <= f.frame_idx <= end_frame:
                old = f.tlabel_v2.get(field)
                if old != new_value:
                    f.patch(field, new_value, cascade=cascade)
                    count += 1
        return count

    def review(self, lang: str = "auto", **kwargs):
        """弹出Jupyter彩色标注面板"""
        from tlabel.viewer.panel import TLabelPanel
        panel = TLabelPanel(self, lang=lang, **kwargs)
        return panel

    def auto_label(self, min_confidence: float = 0.6,
                   target_fields: Optional[List[str]] = None,
                   fit_first: bool = True,
                   engine: str = "auto",
                   enabled_fields: Optional[List[str]] = None,
                   enable_postprocess: bool = True,
                   enable_hmm_phase: bool = True) -> Dict:
        """
        AI辅助预标注 — 自动推断未标注/低置信帧的关键维度

        v0.5.0: 新增时序后处理（平滑+HMM Phase+联动修正）

        Args:
            min_confidence: 最低置信度阈值，低于此值的预测不应用
            target_fields: 只预测指定维度（如["contact", "slip_event"]）
            fit_first: 是否先用当前数据做统计拟合
            engine: 引擎选择 "auto"(优先ML,回退规则) / "ml" / "rule"
            enabled_fields: ML引擎启用的字段列表
            enable_postprocess: [v0.5.0] 是否启用时序后处理
            enable_hmm_phase: [v0.5.0] 是否启用HMM Phase解码

        Returns:
            预标注统计摘要（含predict_results供UI高亮）
        """
        use_ml = False
        predict_results = None

        if engine in ("auto", "ml"):
            try:
                from tlabel.predict.ml_engine import MLEngine, MLEngineConfig
                config = MLEngineConfig(
                    enabled_fields=enabled_fields,
                    enable_postprocess=enable_postprocess,
                    enable_hmm_phase=enable_hmm_phase,
                )
                ml_engine = MLEngine(config)
                if fit_first:
                    ml_engine.fit(self)
                if ml_engine._is_fitted:
                    results = ml_engine.predict(self, target_fields=target_fields)
                    predict_results = results
                    applied = ml_engine.apply(self, results, min_confidence=min_confidence)
                    summary = ml_engine.summary(results)
                    summary["applied_count"] = applied
                    summary["engine"] = "ml"
                    use_ml = True
                elif engine == "ml":
                    return {"error": "ML engine failed to fit", "fit_report": ml_engine.fit_report(), "engine": "ml"}
            except ImportError:
                if engine == "ml":
                    return {"error": "ML engine requires: pip install tlabel[ml]", "engine": "ml"}

        if not use_ml:
            from tlabel.predict.engine import PredictEngine, PredictConfig
            config = PredictConfig(
                enable_postprocess=enable_postprocess,
                enable_hmm_phase=enable_hmm_phase,
            )
            rule_engine = PredictEngine(config)
            if fit_first:
                rule_engine.fit(self)
            results = rule_engine.predict(self, target_fields=target_fields)
            predict_results = results
            applied = rule_engine.apply(self, results, min_confidence=min_confidence)
            summary = rule_engine.summary(results)
            summary["applied_count"] = applied
            summary["engine"] = "rule"

        # v0.5.0: 存储预测结果供UI高亮
        self._predict_results = predict_results
        summary["low_confidence_frames"] = [
            r.frame_idx for r in (predict_results or [])
            if any(c < min_confidence for c in r.confidence.values())
        ]

        return summary

    def export(self, output_path: str, format: str = "auto"):
        """导出标注数据"""
        from tlabel.export.writer import export_data
        return export_data(self, output_path, format=format)


    # ============================================================
    # v0.4.0: Episode级标注
    # ============================================================

    def label_episode(self,
                      outcome: str = "inconclusive",
                      manipulation_type: str = "other",
                      difficulty: str = "medium",
                      notes: str = "",
                      annotator: str = "",
                      verified: bool = False) -> "EpisodeLabel":
        """
        Episode级标注 — 从帧级提升到任务级

        对整个Episode打上任务级标签：操作结果、操作类型、难度等。

        Args:
            outcome: 操作结果 (success/partial/failure/inconclusive)
            manipulation_type: 操作类型 (grasp/pinch/poke/slide/push/pull/tap/lift/place/other)
            difficulty: 难度 (easy/medium/hard)
            notes: 标注备注
            annotator: 标注人
            verified: 是否已审核

        Returns:
            EpisodeLabel实例

        用法:
            data.label_episode(outcome="success", manipulation_type="grasp", difficulty="medium")
            data.label_episode(outcome="failure", notes="物体滑落")
        """
        valid_outcomes = {"success", "partial", "failure", "inconclusive"}
        valid_types = {"grasp", "pinch", "poke", "slide", "push", "pull", "tap", "lift", "place", "other"}
        valid_diffs = {"easy", "medium", "hard"}

        if outcome not in valid_outcomes:
            raise ValueError(f"Invalid outcome '{outcome}', must be one of {valid_outcomes}")
        if manipulation_type not in valid_types:
            raise ValueError(f"Invalid manipulation_type '{manipulation_type}', must be one of {valid_types}")
        if difficulty not in valid_diffs:
            raise ValueError(f"Invalid difficulty '{difficulty}', must be one of {valid_diffs}")

        label = EpisodeLabel(
            outcome=outcome,
            manipulation_type=manipulation_type,
            difficulty=difficulty,
            notes=notes,
            annotator=annotator,
            verified=verified,
        )
        self.episode_info["episode_label"] = label.to_dict()
        return label

    @property
    def episode_label(self) -> Optional["EpisodeLabel"]:
        """获取当前Episode级标注"""
        raw = self.episode_info.get("episode_label")
        if raw is None:
            return None
        if isinstance(raw, EpisodeLabel):
            return raw
        return EpisodeLabel.from_dict(raw)

    # ============================================================
    # v0.4.0: 数据质量评分
    # ============================================================

    def quality_score(self, verbose: bool = False) -> Dict:
        """
        数据质量评分 — 对标国标《具身智能数据质量规范》

        从4个维度评估标注数据质量：
        1. physical_consistency: 物理一致性（联动规则是否满足）
        2. temporal_smoothness: 时序平滑度（相邻帧是否突变）
        3. completeness: 完整性（字段缺失/全零比例）
        4. coverage: 标注覆盖率（有意义的标注占比）

        Args:
            verbose: 是否输出详细warnings

        Returns:
            {
                "overall": float,          # 综合评分 0-100
                "physical_consistency": float,
                "temporal_smoothness": float,
                "completeness": float,
                "coverage": float,
                "warnings": List[str],
                "grade": str,              # A/B/C/D/F
            }

        用法:
            score = data.quality_score()
            print(f"质量评分: {score['overall']}/100 ({score['grade']})")
        """
        from tlabel.quality.scorer import QualityScorer
        scorer = QualityScorer(verbose=verbose)
        return scorer.score(self)

    # ============================================================
    # v0.4.0: describe统计摘要
    # ============================================================

    def describe(self, fields: Optional[List[str]] = None) -> Dict:
        """
        统计摘要 — 类pandas describe

        对每个标注维度计算统计量：count, mean, std, min, 25%, 50%, 75%, max

        Args:
            fields: 只统计指定维度，None则统计全部22维

        Returns:
            Dict[str, Dict[str, float]] — 每个维度的统计摘要

        用法:
            stats = data.describe()
            stats = data.describe(fields=["contact", "force_magnitude", "slip_event"])
        """
        import math

        if not self.frames:
            return {}

        keys = fields if fields else self.dimension_keys
        result = {}

        for key in keys:
            values = [f.tlabel_v2.get(key, 0.0) for f in self.frames]
            if not values:
                continue

            n = len(values)
            mean = sum(values) / n
            var = sum((v - mean) ** 2 for v in values) / n
            std = math.sqrt(var)
            sorted_vals = sorted(values)
            q25 = sorted_vals[n // 4] if n >= 4 else sorted_vals[0]
            q50 = sorted_vals[n // 2]
            q75 = sorted_vals[3 * n // 4] if n >= 4 else sorted_vals[-1]

            result[key] = {
                "count": n,
                "mean": round(mean, 4),
                "std": round(std, 4),
                "min": round(min(values), 4),
                "25%": round(q25, 4),
                "50%": round(q50, 4),
                "75%": round(q75, 4),
                "max": round(max(values), 4),
            }

        return result

    def to_dict(self) -> Dict:
        """转换为字典"""
        contact_count = sum(1 for f in self.frames if f.contact > 0.5)
        slip_count = sum(1 for f in self.frames if f.slip_event > 0.5)

        # 22维特征名称列表
        FEATURE_NAMES = [
            "contact", "deformation_magnitude", "force_magnitude", "force_peak",
            "force_direction", "slip_entropy", "slip_event", "texture_energy",
            "edge_density", "contact_area", "centroid_x",
            "normal_field_magnitude", "normal_field_variance",
            "shear_field_magnitude", "shear_field_direction",
            "delta_force_normal", "delta_force_shear", "friction_cone_ratio",
            "optical_flow_magnitude", "optical_flow_direction",
            "temporal_deformation_rate", "contact_transition",
        ]

        return {
            "schema_version": self.schema_version,
            "format": "tlabel_v2",
            "tlabel_dimensions": 22,
            "feature_names": FEATURE_NAMES,
            "sensor": self.sensor_info,
            "sensor_id": self.sensor_id,
            "calibration": self.calibration_params if self.calibration_params else None,
            "episode": {
                **self.episode_info,
                "episode_label": self.episode_label.to_dict() if self.episode_label else None,
                "num_frames": self.num_frames,
                "duration_s": round(self.duration_s, 2),
                "stats": {
                    "contact_frames": contact_count,
                    "contact_ratio": round(contact_count / max(self.num_frames, 1), 4),
                    "slip_frames": slip_count,
                    "slip_ratio": round(slip_count / max(self.num_frames, 1), 4),
                    "modified_frames": self.modified_count,
                }
            },
            "capabilities": self.capabilities,
            "frames": [f.to_dict(is_first=(i == 0), is_last=(i == len(self.frames) - 1)) 
                      for i, f in enumerate(self.frames)],
        }

    def _repr_html_(self):
        """Jupyter自动渲染面板"""
        panel = self.review()
        return panel._repr_html_()

    def __len__(self):
        return self.num_frames

    def __getitem__(self, index):
        """支持 data[0] 按索引访问帧"""
        return self.frames[index]

    def __repr__(self):
        return (f"TLabelData(sensor={self.sensor_type}, "
                f"frames={self.num_frames}, "
                f"duration={self.duration_s:.1f}s, "
                f"modified={self.modified_count})")

# ============================================================
# v0.4.0 新增：Episode级标注
# ============================================================

from dataclasses import dataclass, field as dc_field
from enum import Enum


class ManipulationType(str, Enum):
    """操作类型枚举"""
    GRASP = "grasp"
    PINCH = "pinch"
    POKE = "poke"
    SLIDE = "slide"
    PUSH = "push"
    PULL = "pull"
    TAP = "tap"
    LIFT = "lift"
    PLACE = "place"
    OTHER = "other"


class EpisodeOutcome(str, Enum):
    """Episode结果枚举"""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"
    INCONCLUSIVE = "inconclusive"


class Difficulty(str, Enum):
    """难度等级"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


@dataclass
class EpisodeLabel:
    """Episode级标注 — 从帧级提升到任务级"""
    outcome: str = "inconclusive"
    manipulation_type: str = "other"
    difficulty: str = "medium"
    notes: str = ""
    annotator: str = ""
    verified: bool = False


    # ============================================================
    # v0.4.0: Episode级标注
    # ============================================================

    def label_episode(self,
                      outcome: str = "inconclusive",
                      manipulation_type: str = "other",
                      difficulty: str = "medium",
                      notes: str = "",
                      annotator: str = "",
                      verified: bool = False) -> "EpisodeLabel":
        """
        Episode级标注 — 从帧级提升到任务级

        对整个Episode打上任务级标签：操作结果、操作类型、难度等。

        Args:
            outcome: 操作结果 (success/partial/failure/inconclusive)
            manipulation_type: 操作类型 (grasp/pinch/poke/slide/push/pull/tap/lift/place/other)
            difficulty: 难度 (easy/medium/hard)
            notes: 标注备注
            annotator: 标注人
            verified: 是否已审核

        Returns:
            EpisodeLabel实例

        用法:
            data.label_episode(outcome="success", manipulation_type="grasp", difficulty="medium")
            data.label_episode(outcome="failure", notes="物体滑落")
        """
        valid_outcomes = {"success", "partial", "failure", "inconclusive"}
        valid_types = {"grasp", "pinch", "poke", "slide", "push", "pull", "tap", "lift", "place", "other"}
        valid_diffs = {"easy", "medium", "hard"}

        if outcome not in valid_outcomes:
            raise ValueError(f"Invalid outcome '{outcome}', must be one of {valid_outcomes}")
        if manipulation_type not in valid_types:
            raise ValueError(f"Invalid manipulation_type '{manipulation_type}', must be one of {valid_types}")
        if difficulty not in valid_diffs:
            raise ValueError(f"Invalid difficulty '{difficulty}', must be one of {valid_diffs}")

        label = EpisodeLabel(
            outcome=outcome,
            manipulation_type=manipulation_type,
            difficulty=difficulty,
            notes=notes,
            annotator=annotator,
            verified=verified,
        )
        self.episode_info["episode_label"] = label.to_dict()
        return label

    @property
    def episode_label(self) -> Optional["EpisodeLabel"]:
        """获取当前Episode级标注"""
        raw = self.episode_info.get("episode_label")
        if raw is None:
            return None
        if isinstance(raw, EpisodeLabel):
            return raw
        return EpisodeLabel.from_dict(raw)

    # ============================================================
    # v0.4.0: 数据质量评分
    # ============================================================

    def quality_score(self, verbose: bool = False) -> Dict:
        """
        数据质量评分 — 对标国标《具身智能数据质量规范》

        从4个维度评估标注数据质量：
        1. physical_consistency: 物理一致性（联动规则是否满足）
        2. temporal_smoothness: 时序平滑度（相邻帧是否突变）
        3. completeness: 完整性（字段缺失/全零比例）
        4. coverage: 标注覆盖率（有意义的标注占比）

        Args:
            verbose: 是否输出详细warnings

        Returns:
            {
                "overall": float,          # 综合评分 0-100
                "physical_consistency": float,
                "temporal_smoothness": float,
                "completeness": float,
                "coverage": float,
                "warnings": List[str],
                "grade": str,              # A/B/C/D/F
            }

        用法:
            score = data.quality_score()
            print(f"质量评分: {score['overall']}/100 ({score['grade']})")
        """
        from tlabel.quality.scorer import QualityScorer
        scorer = QualityScorer(verbose=verbose)
        return scorer.score(self)

    # ============================================================
    # v0.4.0: describe统计摘要
    # ============================================================

    def describe(self, fields: Optional[List[str]] = None) -> Dict:
        """
        统计摘要 — 类pandas describe

        对每个标注维度计算统计量：count, mean, std, min, 25%, 50%, 75%, max

        Args:
            fields: 只统计指定维度，None则统计全部22维

        Returns:
            Dict[str, Dict[str, float]] — 每个维度的统计摘要

        用法:
            stats = data.describe()
            stats = data.describe(fields=["contact", "force_magnitude", "slip_event"])
        """
        import math

        if not self.frames:
            return {}

        keys = fields if fields else self.dimension_keys
        result = {}

        for key in keys:
            values = [f.tlabel_v2.get(key, 0.0) for f in self.frames]
            if not values:
                continue

            n = len(values)
            mean = sum(values) / n
            var = sum((v - mean) ** 2 for v in values) / n
            std = math.sqrt(var)
            sorted_vals = sorted(values)
            q25 = sorted_vals[n // 4] if n >= 4 else sorted_vals[0]
            q50 = sorted_vals[n // 2]
            q75 = sorted_vals[3 * n // 4] if n >= 4 else sorted_vals[-1]

            result[key] = {
                "count": n,
                "mean": round(mean, 4),
                "std": round(std, 4),
                "min": round(min(values), 4),
                "25%": round(q25, 4),
                "50%": round(q50, 4),
                "75%": round(q75, 4),
                "max": round(max(values), 4),
            }

        return result

    def to_dict(self) -> Dict:
        return {
            "outcome": self.outcome,
            "manipulation_type": self.manipulation_type,
            "difficulty": self.difficulty,
            "notes": self.notes,
            "annotator": self.annotator,
            "verified": self.verified,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "EpisodeLabel":
        return cls(
            outcome=d.get("outcome", "inconclusive"),
            manipulation_type=d.get("manipulation_type", "other"),
            difficulty=d.get("difficulty", "medium"),
            notes=d.get("notes", ""),
            annotator=d.get("annotator", ""),
            verified=d.get("verified", False),
        )
