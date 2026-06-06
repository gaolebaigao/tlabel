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
                # 接触归零 → 力度和滑移也归零
                if self.tlabel_v2.get("force_magnitude", 0) > 0:
                    cascades.append({"field": "force_magnitude", "old_value": self.tlabel_v2["force_magnitude"], "new_value": 0.0})
                    self.tlabel_v2["force_magnitude"] = 0.0
                if self.tlabel_v2.get("force_peak", 0) > 0:
                    cascades.append({"field": "force_peak", "old_value": self.tlabel_v2["force_peak"], "new_value": 0.0})
                    self.tlabel_v2["force_peak"] = 0.0
                if self.tlabel_v2.get("slip_event", 0) > 0:
                    cascades.append({"field": "slip_event", "old_value": self.tlabel_v2["slip_event"], "new_value": 0.0})
                    self.tlabel_v2["slip_event"] = 0.0
                if self.tlabel_v2.get("contact_area", 0) > 0:
                    cascades.append({"field": "contact_area", "old_value": self.tlabel_v2["contact_area"], "new_value": 0.0})
                    self.tlabel_v2["contact_area"] = 0.0
                # HACK: contact归零时contact_transition也应归零
                if self.tlabel_v2.get("contact_transition", 0) > 0.5:
                    cascades.append({"field": "contact_transition", "old_value": self.tlabel_v2["contact_transition"], "new_value": 0.0})
                    self.tlabel_v2["contact_transition"] = 0.0
                if self.manipulation_phase in ("initial_contact", "stable_contact", "slip", "grasp", "hold"):
                    old_phase = self.manipulation_phase
                    self.manipulation_phase = "idle"
                    cascades.append({"field": "manipulation_phase", "old_value": old_phase, "new_value": "idle"})
        return cascades

    def to_dict(self) -> Dict:
        d = {
            "frame_idx": self.frame_idx,
            "timestamp_s": round(self.timestamp_s, 4),
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
                 schema_version: str = "0.4.0"):
        self.frames = frames
        self.sensor_info = sensor_info
        self.episode_info = episode_info
        self.capabilities = capabilities
        self.schema_version = schema_version

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
    def modified_count(self) -> int:
        return sum(1 for f in self.frames if f.is_modified)

    def get_frame(self, frame_idx: int) -> Optional[TLabelFrame]:
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

    def export(self, output_path: str, format: str = "json"):
        """导出标注数据"""
        from tlabel.export.writer import export_data
        return export_data(self, output_path, format=format)

    def to_dict(self) -> Dict:
        """转换为字典"""
        contact_count = sum(1 for f in self.frames if f.contact > 0.5)
        slip_count = sum(1 for f in self.frames if f.slip_event > 0.5)

        return {
            "schema_version": self.schema_version,
            "format": "tlabel_v2",
            "tlabel_dimensions": 22,
            "sensor": self.sensor_info,
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
            "frames": [f.to_dict() for f in self.frames],
        }

    def _repr_html_(self):
        """Jupyter自动渲染面板"""
        panel = self.review()
        return panel._repr_html_()

    def __len__(self):
        return self.num_frames

    def __repr__(self):
        return (f"TLabelData(sensor={self.sensor_type}, "
                f"frames={self.num_frames}, "
                f"duration={self.duration_s:.1f}s, "
                f"modified={self.modified_count})")
