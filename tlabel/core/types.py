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
        """联动规则 — 从tlabel-web移植"""
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
                   fit_first: bool = True) -> Dict:
        """
        AI辅助预标注 — 自动推断未标注/低置信帧的关键维度
        
        Args:
            min_confidence: 最低置信度阈值，低于此值的预测不应用
            target_fields: 只预测指定维度（如["contact", "slip_event"]）
            fit_first: 是否先用当前数据做统计拟合
        
        Returns:
            预标注统计摘要
        """
        from tlabel.predict.engine import PredictEngine
        engine = PredictEngine()
        if fit_first:
            engine.fit(self)
        results = engine.predict(self, target_fields=target_fields)
        applied = engine.apply(self, results, min_confidence=min_confidence)
        summary = engine.summary(results)
        summary["applied_count"] = applied
        return summary

    def export(self, output_path: str, format: str = "auto"):
        """导出标注数据"""
        from tlabel.export.writer import export_data
        return export_data(self, output_path, format=format)

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
