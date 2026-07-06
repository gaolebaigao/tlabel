"""
Taxonomy 系统 — v0.14.0 新增

管理可用的 Motor Primitive 子集，支持内置默认 + 用户自定义扩展。

设计原则：
- 内置默认 7 种 primitive（从 T-Rex 22 种中选取物理含义明确、力信号特征清晰的子集）
- 支持用户自定义扩展（PrimitiveRule）
- 规则引擎定位为"辅助预标注"，不是权威分类器
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class PrimitiveRule:
    """单个 primitive 的判定规则（用于自定义扩展）"""
    name: str                          # primitive 名称
    description: str                   # 物理含义描述
    physical_definition: str           # 物理定义（文字）

    # 判定条件（基于 tlabel_v2 字段）
    # 格式: {"field_name": {"op": ">", "threshold": 0.2}}
    # 支持的 op: ">", "<", ">=", "<=", "==", "between"
    # "between" 使用 "range": (low, high) 代替 "threshold"
    conditions: Dict[str, dict] = field(default_factory=dict)

    # 置信度基线
    base_confidence: float = 0.6       # 满足所有条件时的基线置信度

    # 参考来源
    reference: str = ""                # 论文/标准引用


# ─────────────────────────────────────────────
# 默认 7 种 Primitive（从 T-Rex 22 种中选取）
# ─────────────────────────────────────────────

DEFAULT_PRIMITIVE_RULES: Dict[str, PrimitiveRule] = {
    'reach': PrimitiveRule(
        name='reach',
        description='伸达 — 无接触的自由运动',
        physical_definition='无接触(contact<0.3) + 低力(force<0.1)',
        conditions={
            'contact': {'op': '<', 'threshold': 0.3},
            'force_magnitude': {'op': '<', 'threshold': 0.1},
        },
        base_confidence=0.65,
        reference='T-Rex (2024)',
    ),
    'grasp': PrimitiveRule(
        name='grasp',
        description='抓握 — 力上升 + 接触建立 + 形变增大',
        physical_definition='contact>0.5 + force上升(avg_delta>0.05) + 形变>0.2',
        conditions={
            'contact': {'op': '>', 'threshold': 0.5},
            'force_magnitude': {'op': '>', 'threshold': 0.2},
            'deformation_magnitude': {'op': '>', 'threshold': 0.2},
        },
        base_confidence=0.6,
        reference='Cutkosky (1992) Power Grasp',
    ),
    'press': PrimitiveRule(
        name='press',
        description='按压 — 力上升 + 接触 + 低形变',
        physical_definition='contact>0.5 + force上升 + 形变<0.2（垂直按压）',
        conditions={
            'contact': {'op': '>', 'threshold': 0.5},
            'force_magnitude': {'op': '>', 'threshold': 0.15},
            'deformation_magnitude': {'op': '<', 'threshold': 0.2},
        },
        base_confidence=0.55,
        reference='T-Rex (2024)',
    ),
    'squeeze': PrimitiveRule(
        name='squeeze',
        description='挤压 — 力持续变化（上升或波动）+ 接触保持',
        physical_definition='contact>0.5 + force变化(avg_delta<-0.05或持续增大)',
        conditions={
            'contact': {'op': '>', 'threshold': 0.5},
        },
        base_confidence=0.45,
        reference='T-Rex (2024)',
    ),
    'wrap': PrimitiveRule(
        name='wrap',
        description='包裹 — 力稳定 + 接触保持 + 无显著剪切力',
        physical_definition='contact>0.5 + force稳定(|delta|<0.02) + 低剪切力(shear<0.1)',
        conditions={
            'contact': {'op': '>', 'threshold': 0.5},
            'force_magnitude': {'op': '>', 'threshold': 0.1},
            'shear_field_magnitude': {'op': '<', 'threshold': 0.1},
        },
        base_confidence=0.5,
        reference='T-Rex (2024)',
    ),
    'wipe': PrimitiveRule(
        name='wipe',
        description='擦拭 — 剪切力显著 + 力稳定 + 接触保持',
        physical_definition='contact>0.5 + 高剪切力(shear>0.1) + force稳定',
        conditions={
            'contact': {'op': '>', 'threshold': 0.5},
            'shear_field_magnitude': {'op': '>', 'threshold': 0.1},
            'force_magnitude': {'op': '>', 'threshold': 0.1},
        },
        base_confidence=0.5,
        reference='T-Rex (2024)',
    ),
    'lift': PrimitiveRule(
        name='lift',
        description='提起 — 力先升后降 + 有位移趋势',
        physical_definition='contact>0.3 + force变化(|delta|>0.03) + 中等力范围',
        conditions={
            'contact': {'op': '>', 'threshold': 0.3},
            'force_magnitude': {'op': '>', 'threshold': 0.1},
        },
        base_confidence=0.45,
        reference='T-Rex (2024)',
    ),
}

# 默认启用的 primitive 列表（有序）
DEFAULT_PRIMITIVE_NAMES = list(DEFAULT_PRIMITIVE_RULES.keys())

# grasp 子分类（参考 Cutkosky 1992）— 用于高级用户扩展
GRASP_SUBTYPES = {
    'power_grasp': PrimitiveRule(
        name='power_grasp',
        description='力量抓握 — 全手指接触，大力',
        physical_definition='contact_area大 + 力大 + 多指接触',
        conditions={
            'contact_area': {'op': '>', 'threshold': 0.4},
            'force_magnitude': {'op': '>', 'threshold': 0.5},
            'contact': {'op': '>', 'threshold': 0.8},
        },
        base_confidence=0.55,
        reference='Cutkosky (1992) Power Grasp',
    ),
    'precision_grasp': PrimitiveRule(
        name='precision_grasp',
        description='精确抓握 — 指尖接触，精细力',
        physical_definition='contact_area小 + 精细力控制',
        conditions={
            'contact_area': {'op': '<', 'threshold': 0.15},
            'force_magnitude': {'op': '>', 'threshold': 0.05},
            'contact': {'op': '>', 'threshold': 0.5},
        },
        base_confidence=0.5,
        reference='Cutkosky (1992) Precision Grasp',
    ),
    'lateral_grasp': PrimitiveRule(
        name='lateral_grasp',
        description='侧向抓握 — 拇指侧面，如捏钥匙',
        physical_definition='侧向力为主 + 接触面积中等',
        conditions={
            'shear_field_magnitude': {'op': '>', 'threshold': 0.15},
            'force_magnitude': {'op': '>', 'threshold': 0.1},
            'contact': {'op': '>', 'threshold': 0.5},
        },
        base_confidence=0.45,
        reference='Cutkosky (1992) Lateral Grasp',
    ),
}


class TaxonomyConfig:
    """
    Taxonomy 配置 — 管理可用的 primitive 列表

    用法:
        # 1. 使用默认 taxonomy
        taxonomy = get_default_taxonomy()
        print(taxonomy.get_primitives())  # ['reach', 'grasp', 'press', ...]

        # 2. 自定义扩展
        taxonomy.register(PrimitiveRule(
            name="pinch",
            description="捏取",
            physical_definition="双点接触 + 法向力",
            conditions={"contact_area": {"op": "<", "threshold": 0.15}},
        ))

        # 3. 序列化
        config_dict = taxonomy.to_dict()
        loaded = TaxonomyConfig.from_dict(config_dict)
    """

    def __init__(self, name: str = "default"):
        self.name = name
        self._rules: Dict[str, PrimitiveRule] = {}

    @property
    def primitives(self) -> Dict[str, PrimitiveRule]:
        return dict(self._rules)

    def get_primitives(self) -> List[str]:
        """返回可用 primitive 名称列表"""
        return list(self._rules.keys())

    def get_rule(self, name: str) -> Optional[PrimitiveRule]:
        """获取指定 primitive 的判定规则"""
        return self._rules.get(name)

    def register(self, rule: PrimitiveRule) -> None:
        """
        注册自定义 primitive

        Args:
            rule: PrimitiveRule 实例

        Raises:
            ValueError: 如果同名 primitive 已存在
        """
        if rule.name in self._rules:
            raise ValueError(
                f"Primitive '{rule.name}' already registered. "
                f"Use unregister() first or choose a different name."
            )
        self._rules[rule.name] = rule
        # 同步到全局扩展注册表，使 PrimitiveAnnotation 验证通过
        from tlabel.core.primitive import register_custom_primitive
        register_custom_primitive(rule.name)

    def unregister(self, name: str) -> None:
        """移除已注册的 primitive"""
        if name not in self._rules:
            raise ValueError(f"Primitive '{name}' not found in taxonomy '{self.name}'")
        del self._rules[name]

    def has(self, name: str) -> bool:
        """检查 primitive 是否在 taxonomy 中"""
        return name in self._rules

    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            'name': self.name,
            'primitives': {
                name: {
                    'name': rule.name,
                    'description': rule.description,
                    'physical_definition': rule.physical_definition,
                    'conditions': rule.conditions,
                    'base_confidence': rule.base_confidence,
                    'reference': rule.reference,
                }
                for name, rule in self._rules.items()
            },
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TaxonomyConfig":
        """从字典反序列化"""
        config = cls(name=d.get('name', 'custom'))
        for name, rule_dict in d.get('primitives', {}).items():
            rule = PrimitiveRule(
                name=rule_dict['name'],
                description=rule_dict['description'],
                physical_definition=rule_dict['physical_definition'],
                conditions=rule_dict.get('conditions', {}),
                base_confidence=rule_dict.get('base_confidence', 0.6),
                reference=rule_dict.get('reference', ''),
            )
            config._rules[name] = rule
        return config

    def __repr__(self):
        return f"TaxonomyConfig(name='{self.name}', primitives={self.get_primitives()})"

    def __len__(self):
        return len(self._rules)


def get_default_taxonomy() -> TaxonomyConfig:
    """
    获取内置默认 taxonomy（7种 primitive）

    Returns:
        TaxonomyConfig 实例，包含 reach, grasp, press, squeeze, wrap, wipe, lift
    """
    config = TaxonomyConfig(name="default")
    for name, rule in DEFAULT_PRIMITIVE_RULES.items():
        config._rules[name] = rule
    return config


def get_full_taxonomy() -> TaxonomyConfig:
    """
    获取完整 taxonomy（T-Rex 22种 primitive，无自定义规则）

    注意：这 22 种中部分无法通过力数据可靠区分（如 twist vs rotate），
    使用完整 taxonomy 时，规则引擎只能输出有足够信号支撑的 primitive。

    Returns:
        TaxonomyConfig 实例，包含全部 22 种 T-Rex primitive
    """
    from tlabel.core.primitive import PRIMITIVE_PRESETS
    config = TaxonomyConfig(name="full_trex")

    # 先用默认规则填充
    for name, rule in DEFAULT_PRIMITIVE_RULES.items():
        config._rules[name] = rule

    # 再为其余 primitive 创建宽松规则（低基线置信度）
    for name in PRIMITIVE_PRESETS:
        if name not in config._rules:
            config._rules[name] = PrimitiveRule(
                name=name,
                description=f'{name} (generic rule)',
                physical_definition='Generic rule — requires manual verification',
                conditions={
                    'contact': {'op': '>', 'threshold': 0.3},
                },
                base_confidence=0.3,  # 低基线，需要人工验证
                reference='T-Rex (2024) generic',
            )

    return config


# 预创建实例（避免重复创建）
_DEFAULT_TAXONOMY_CACHE: Optional[TaxonomyConfig] = None


def default_taxonomy() -> TaxonomyConfig:
    """获取默认 taxonomy 的缓存实例（只读使用，不要修改）"""
    global _DEFAULT_TAXONOMY_CACHE
    if _DEFAULT_TAXONOMY_CACHE is None:
        _DEFAULT_TAXONOMY_CACHE = get_default_taxonomy()
    return _DEFAULT_TAXONOMY_CACHE
