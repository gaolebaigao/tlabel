"""
Tactile Event Annotation System — v0.14.0 新增

在力/形变时间曲线上标注关键事件点或区间，为VQ-VAE训练提供数据基础设施。
"""

from typing import Optional, List, Dict, Any
from copy import deepcopy


# ============================================================
# 6种预设事件类型
# ============================================================

EVENT_PRESETS = {
    "contact_onset": {
        "description": "接触开始 — contact从0→1的跳变帧",
        "is_interval": False,
        "color": "#4CAF50",
        "icon": "▶",
    },
    "contact_loss": {
        "description": "接触丢失 — contact从1→0的跳变帧",
        "is_interval": False,
        "color": "#F44336",
        "icon": "◀",
    },
    "slip": {
        "description": "滑移事件 — slip_event > 阈值 且 contact > 0.5",
        "is_interval": True,
        "color": "#FF9800",
        "icon": "〜",
    },
    "force_spike": {
        "description": "力值突变 — 力值变化超过2σ",
        "is_interval": False,
        "color": "#E91E63",
        "icon": "⚡",
    },
    "deformation_anomaly": {
        "description": "形变异常 — 超出正常范围的形变",
        "is_interval": True,
        "color": "#9C27B0",
        "icon": "⚠",
    },
    "stable_grip": {
        "description": "稳定抓握 — 连续N帧contact稳定 + 力波动小",
        "is_interval": True,
        "color": "#2196F3",
        "icon": "■",
    },
}


class TactileEvent:
    """
    触觉事件标注

    支持点事件（如contact_onset）和区间事件（如slip、stable_grip）。

    Attributes:
        event_type: 事件类型（必须是EVENT_PRESETS中的键）
        frame_idx: 事件帧（点事件）
        start_frame: 起始帧（区间事件，可选）
        end_frame: 结束帧（区间事件，可选）
        confidence: 置信度 0-1
        source: 标注来源 "manual" / "ai_predicted"
        metadata: 附加信息（如slip方向、force_spike幅值）
    """

    __slots__ = [
        'event_type', 'frame_idx', 'start_frame', 'end_frame',
        'confidence', 'source', 'metadata',
    ]

    def __init__(self,
                 event_type: str,
                 frame_idx: int,
                 confidence: float = 1.0,
                 source: str = "manual",
                 start_frame: Optional[int] = None,
                 end_frame: Optional[int] = None,
                 metadata: Optional[Dict] = None):
        if event_type not in EVENT_PRESETS:
            raise ValueError(
                f"Unknown event_type: '{event_type}'. "
                f"Must be one of {list(EVENT_PRESETS.keys())}"
            )
        if not 0.0 <= confidence <= 1.0:
            raise ValueError(
                f"Invalid confidence: {confidence}. Must be in [0.0, 1.0]."
            )
        if source not in ("manual", "ai_predicted"):
            raise ValueError(
                f"Invalid source: '{source}'. Must be 'manual' or 'ai_predicted'."
            )

        self.event_type = event_type
        self.frame_idx = frame_idx
        self.start_frame = start_frame if start_frame is not None else frame_idx
        self.end_frame = end_frame if end_frame is not None else frame_idx
        self.confidence = confidence
        self.source = source
        self.metadata = metadata or {}

    @property
    def is_point_event(self) -> bool:
        """是否为点事件"""
        return not EVENT_PRESETS[self.event_type]["is_interval"]

    @property
    def is_interval_event(self) -> bool:
        """是否为区间事件"""
        return EVENT_PRESETS[self.event_type]["is_interval"]

    @property
    def duration_frames(self) -> int:
        """持续帧数"""
        return self.end_frame - self.start_frame + 1

    def contains_frame(self, frame_idx: int) -> bool:
        """判断某帧是否在此事件区间内"""
        return self.start_frame <= frame_idx <= self.end_frame

    def to_dict(self) -> Dict:
        """序列化为字典"""
        d = {
            "event_type": self.event_type,
            "frame_idx": self.frame_idx,
            "confidence": round(self.confidence, 4),
            "source": self.source,
        }
        if EVENT_PRESETS[self.event_type]["is_interval"]:
            d["start_frame"] = self.start_frame
            d["end_frame"] = self.end_frame
        if self.metadata:
            d["metadata"] = self.metadata
        return d

    @classmethod
    def from_dict(cls, d: Dict) -> "TactileEvent":
        """从字典反序列化"""
        return cls(
            event_type=d["event_type"],
            frame_idx=d["frame_idx"],
            confidence=d.get("confidence", 1.0),
            source=d.get("source", "manual"),
            start_frame=d.get("start_frame"),
            end_frame=d.get("end_frame"),
            metadata=d.get("metadata"),
        )

    def __repr__(self):
        if self.is_point_event:
            return (f"TactileEvent('{self.event_type}', "
                    f"frame={self.frame_idx}, "
                    f"conf={self.confidence:.2f}, src={self.source})")
        else:
            return (f"TactileEvent('{self.event_type}', "
                    f"frames={self.start_frame}-{self.end_frame}, "
                    f"conf={self.confidence:.2f}, src={self.source})")

    def __eq__(self, other):
        if not isinstance(other, TactileEvent):
            return False
        return (self.event_type == other.event_type and
                self.frame_idx == other.frame_idx and
                self.start_frame == other.start_frame and
                self.end_frame == other.end_frame)
