"""
Motor Primitive 标注系统 — v0.13.0 新增, v0.14.0 扩展

基于 T-Rex 论文定义的 22 个标准 Motor Primitive，
为触觉数据提供 primitive 级别的时间区间标注。

v0.14.0: 新增 DEFAULT_PRIMITIVE_SUBSET（7种默认启用）、
         GRASP_SUBTYPES（Cutkosky 1992 抓握子分类）、
         运行时自定义扩展注册表 _custom_registry。

Paper: T-Rex — Primitive × Object composition for tactile data organization.
"""

from typing import Optional, List, Dict, Set


# 22 个标准 Motor Primitive（T-Rex 论文定义，不可随意增删）
PRIMITIVE_PRESETS = [
    'wrap', 'lift', 'grasp', 'fold', 'cut', 'insert', 'press',
    'wipe', 'peel', 'assemble', 'extract', 'twist', 'shake',
    'dispense', 'disassemble', 'squeeze', 'pour', 'open',
    'close', 'screw', 'unscrew', 'reach'
]

# v0.14.0: 默认启用的 7 种 primitive（从 T-Rex 22 种中选取）
# 选取标准：物理含义明确 + 力信号特征清晰 + 视触觉可区分
DEFAULT_PRIMITIVE_SUBSET = [
    'reach',     # 无接触的自由运动
    'grasp',     # 抓握（力上升+接触+形变）
    'press',     # 按压（力上升+低形变）
    'squeeze',   # 挤压（力持续变化+接触保持）
    'wrap',      # 包裹（力稳定+接触+无剪切）
    'wipe',      # 擦拭（剪切力+横向运动）
    'lift',      # 提起（力先升后降）
]

# v0.14.0: Cutkosky 1992 抓握子分类（供高级用户扩展）
GRASP_SUBTYPES = {
    'power_grasp': '力量抓握 — 全手指接触，大力',
    'precision_grasp': '精确抓握 — 指尖接触，精细力',
    'lateral_grasp': '侧向抓握 — 拇指侧面，如捏钥匙',
}

# 运行时自定义扩展注册表（通过 taxonomy.register() 添加）
_custom_registry: Set[str] = set()


def register_custom_primitive(name: str) -> None:
    """注册自定义 primitive 名称到全局扩展注册表（供 PrimitiveAnnotation 验证用）"""
    _custom_registry.add(name)


def is_valid_primitive(name: str) -> bool:
    """检查 primitive 名称是否有效（内置 22 种 + 自定义扩展）"""
    return name in PRIMITIVE_PRESETS or name in _custom_registry


# Primitive 颜色映射（用于 UI 可视化）
PRIMITIVE_COLORS = {
    'wrap': '#FF6B6B', 'lift': '#4ECDC4', 'grasp': '#45B7D1',
    'fold': '#FFA07A', 'cut': '#98D8C8', 'insert': '#F7DC6F',
    'press': '#BB8FCE', 'wipe': '#85C1E2', 'peel': '#F8B739',
    'assemble': '#82E0AA', 'extract': '#F1948A', 'twist': '#D7BDE2',
    'shake': '#AED6F1', 'dispense': '#A3E4D7', 'disassemble': '#F9E79F',
    'squeeze': '#F5B7B1', 'pour': '#D5F5E3', 'open': '#FADBD8',
    'close': '#D4E6F1', 'screw': '#FCF3CF', 'unscrew': '#E8DAEF',
    'reach': '#D5D8DC',
    # v0.14: 自定义 primitive 的默认颜色池
    'power_grasp': '#E74C3C', 'precision_grasp': '#3498DB', 'lateral_grasp': '#2ECC71',
}


class PrimitiveAnnotation:
    """
    Primitive 时间区间标注

    每个 PrimitiveAnnotation 表示一个 motor primitive 在一段时间帧区间内的出现。

    Attributes:
        primitive_name: primitive 名称（必须在 PRIMITIVE_PRESETS 中）
        start_frame: 起始帧索引
        end_frame: 结束帧索引
        confidence: 置信度 0.0-1.0（AI 预标注时使用）
        source: 标注来源 'manual' | 'ai_predicted'
    """
    __slots__ = ['primitive_name', 'start_frame', 'end_frame', 'confidence', 'source']

    def __init__(self, name: str, start: int, end: int,
                 confidence: float = 1.0, source: str = 'manual'):
        if not is_valid_primitive(name):
            raise ValueError(
                f"Unknown primitive: '{name}'. Must be one of {PRIMITIVE_PRESETS} "
                f"or registered via taxonomy.register()."
            )
        if start < 0 or end < start:
            raise ValueError(
                f"Invalid frame range: start={start}, end={end}. "
                f"Must satisfy 0 <= start <= end."
            )
        if not 0.0 <= confidence <= 1.0:
            raise ValueError(
                f"Invalid confidence: {confidence}. Must be in [0.0, 1.0]."
            )
        if source not in ('manual', 'ai_predicted', 'ai_predicted_estimated'):
            raise ValueError(
                f"Invalid source: '{source}'. Must be 'manual', 'ai_predicted', "
                f"or 'ai_predicted_estimated' (v0.14)."
            )

        self.primitive_name = name
        self.start_frame = start
        self.end_frame = end
        self.confidence = confidence
        self.source = source

    def to_dict(self) -> Dict:
        """序列化为字典"""
        return {
            'primitive_name': self.primitive_name,
            'start_frame': self.start_frame,
            'end_frame': self.end_frame,
            'confidence': round(self.confidence, 4),
            'source': self.source,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> 'PrimitiveAnnotation':
        """从字典反序列化"""
        return cls(
            name=d['primitive_name'],
            start=d['start_frame'],
            end=d['end_frame'],
            confidence=d.get('confidence', 1.0),
            source=d.get('source', 'manual'),
        )

    def duration_frames(self) -> int:
        """持续帧数"""
        return self.end_frame - self.start_frame + 1

    def contains_frame(self, frame_idx: int) -> bool:
        """判断某帧是否在此 primitive 区间内"""
        return self.start_frame <= frame_idx <= self.end_frame

    def __repr__(self):
        return (f"PrimitiveAnnotation('{self.primitive_name}', "
                f"frames={self.start_frame}-{self.end_frame}, "
                f"conf={self.confidence:.2f}, src={self.source})")

    def __eq__(self, other):
        if not isinstance(other, PrimitiveAnnotation):
            return False
        return (self.primitive_name == other.primitive_name and
                self.start_frame == other.start_frame and
                self.end_frame == other.end_frame)
