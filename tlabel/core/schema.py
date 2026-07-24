"""
TLabel Schema V2.1 — 14维结构化语义空间

基于设计文档 v2.1 §3.1 定义，支持 Compliance Level (L1-L4) 分层。
"""

import math
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple


# 枚举值定义（字符串类型，方便JSON序列化）
VALID_CONTACT_REGIONS = ("palmar", "digital", "lateral", "proximal", "distal", "dorsal", "other")
VALID_MANIPULATION_PHASES = ("pre_contact", "approach", "grasp", "lift", "hold", "place")
VALID_TEXTURE_CLASSES = ("smooth", "rough", "granular", "fibrous", "sticky", "slippery")
VALID_COMPLIANCE_LEVELS = ("L1", "L2", "L3", "L4")

# 14维字段名列表（有序）
SCHEMA_V2_FIELD_NAMES = [
    "contact",
    "contact_centroid",
    "contact_region",
    "force_magnitude",
    "force_vector",
    "torque_vector",
    "slip_event",
    "slip_velocity",
    "manipulation_phase",
    "texture_class",
    "object_deformation",
    "temperature",
    "confidence",
    "compliance_level",
]


@dataclass
class TLabelSchemaV2:
    """
    TLabel Schema V2.1 — 14维结构化触觉语义标注
    
    Compliance Level 分层（§3.3）：
      L1 Basic:        contact, contact_centroid, slip_event, confidence
      L2 Force-Aware:  L1 + force_magnitude (约定必填)
      L3 Full-Vector:  L2 + force_vector [Fx,Fy,Fz]
      L4 Rich-Semantic: L3 + 所有 Optional 字段
    """

    # --- Required (无条件) ---
    contact: bool = False
    slip_event: bool = False
    confidence: float = 1.0
    compliance_level: str = "L1"

    # --- 条件 Required ---
    contact_centroid: Optional[List[float]] = None  # Required when contact=true

    # --- Optional ---
    contact_region: Optional[str] = None
    force_magnitude: Optional[float] = None          # L2+ 约定必填, 法向力(N)
    force_vector: Optional[List[float]] = None        # L3+ Optional, [Fx,Fy,Fz] (N)
    torque_vector: Optional[List[float]] = None       # Optional, [Mx,My,Mz] (N·m)
    slip_velocity: Optional[List[float]] = None       # Optional when slip_event=true, [vx,vy] (mm/s)
    manipulation_phase: Optional[str] = None          # enum: pre_contact/approach/grasp/lift/hold/place
    texture_class: Optional[str] = None               # enum: smooth/rough/granular/fibrous/sticky/slippery
    object_deformation: Optional[float] = None        # mm or ratio
    temperature: Optional[float] = None               # °C

    # ================================================================
    # 序列化
    # ================================================================

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "contact": self.contact,
            "contact_centroid": self.contact_centroid,
            "contact_region": self.contact_region,
            "force_magnitude": self.force_magnitude,
            "force_vector": self.force_vector,
            "torque_vector": self.torque_vector,
            "slip_event": self.slip_event,
            "slip_velocity": self.slip_velocity,
            "manipulation_phase": self.manipulation_phase,
            "texture_class": self.texture_class,
            "object_deformation": self.object_deformation,
            "temperature": self.temperature,
            "confidence": self.confidence,
            "compliance_level": self.compliance_level,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TLabelSchemaV2":
        """从字典构建 TLabelSchemaV2"""
        return cls(
            contact=bool(data.get("contact", False)),
            contact_centroid=data.get("contact_centroid"),
            contact_region=data.get("contact_region"),
            force_magnitude=data.get("force_magnitude"),
            force_vector=data.get("force_vector"),
            torque_vector=data.get("torque_vector"),
            slip_event=bool(data.get("slip_event", False)),
            slip_velocity=data.get("slip_velocity"),
            manipulation_phase=data.get("manipulation_phase"),
            texture_class=data.get("texture_class"),
            object_deformation=data.get("object_deformation"),
            temperature=data.get("temperature"),
            confidence=float(data.get("confidence", 1.0)),
            compliance_level=str(data.get("compliance_level", "L1")),
        )

    # ================================================================
    # 从 v1 (22维 flat dict) 转换
    # ================================================================

    @classmethod
    def from_tlabel_v1(cls, v1_dict: Dict[str, float]) -> "TLabelSchemaV2":
        """
        从旧版22维 tlabel_v2 flat dict 转换为新14维 Schema V2。
        
        映射规则：
          contact → contact (bool: >0.5 为 True)
          centroid_x → contact_centroid[0]  (需与 centroid_y 配对)
          force_magnitude → force_magnitude
          force_magnitude + force_direction → force_vector [Fx, Fy, Fz]
          slip_event → slip_event (bool: >0.5 为 True)
          slip_direction → slip_velocity [vx, vy] (方向→单位速度向量)
          manipulation_phase → manipulation_phase (映射枚举值)
          deformation_magnitude → object_deformation
          confidence → confidence
          无法导出的字段填 None
          compliance_level 默认 "L1"
        """
        # contact: v1 是 float 0/1, v2 是 bool
        contact_val = float(v1_dict.get("contact", 0.0)) > 0.5

        # contact_centroid: v1 有 centroid_x (归一化), 无 centroid_y → 填 None 或 [centroid_x, 0]
        centroid_x = v1_dict.get("centroid_x")
        if centroid_x is not None:
            contact_centroid = [float(centroid_x), 0.0]
        else:
            contact_centroid = None

        # force_magnitude
        force_mag = v1_dict.get("force_magnitude")
        if force_mag is not None:
            force_mag = float(force_mag)
            if force_mag == 0.0:
                force_mag = None  # 0可能是"传感器不支持"的占位

        # force_vector: 从 force_magnitude + force_direction 合成
        force_vector = None
        if force_mag is not None:
            force_dir = v1_dict.get("force_direction")
            if force_dir is not None:
                force_dir_rad = math.radians(float(force_dir))
                # v1 的 force_direction 是变形场梯度方向(degree)
                # 近似映射: [Fx, Fy, Fz] = [mag*sin(dir), 0, mag*cos(dir)]
                # Fz 为法向分量(主), Fx 为剪切分量
                fx = force_mag * math.sin(force_dir_rad)
                fy = 0.0
                fz = force_mag * math.cos(force_dir_rad)
                force_vector = [round(fx, 4), round(fy, 4), round(fz, 4)]

        # slip_event
        slip_val = float(v1_dict.get("slip_event", 0.0)) > 0.5

        # slip_velocity: v1 的 slip_direction 是角度 → 转单位速度向量
        slip_velocity = None
        if slip_val:
            slip_dir = v1_dict.get("slip_direction")
            if slip_dir is not None:
                slip_dir_rad = math.radians(float(slip_dir))
                vx = math.cos(slip_dir_rad)
                vy = math.sin(slip_dir_rad)
                slip_velocity = [round(vx, 4), round(vy, 4)]

        # manipulation_phase: v1 枚举 → v2 枚举映射
        v1_phase = v1_dict.get("manipulation_phase", "")
        phase_map = {
            "idle": "pre_contact",
            "initial_contact": "approach",
            "stable_contact": "grasp",
            "slip": "grasp",
            "release": "place",
            "re_contact": "approach",
            "approach": "approach",
            "retract": "place",
            "grasp": "grasp",
            "transport": "lift",
            "hold": "hold",
        }
        manipulation_phase = phase_map.get(str(v1_phase))

        # object_deformation
        deformation = v1_dict.get("deformation_magnitude")
        if deformation is not None:
            deformation = float(deformation)

        # confidence: v1 中 confidence 是帧级别字段，不在 tlabel_v2 dict 里
        # 但 v1_dict 可能已经包含（从 TLabelFrame.confidence 传入）
        confidence = float(v1_dict.get("confidence", 1.0))

        return cls(
            contact=contact_val,
            contact_centroid=contact_centroid,
            contact_region=None,
            force_magnitude=force_mag,
            force_vector=force_vector,
            torque_vector=None,
            slip_event=slip_val,
            slip_velocity=slip_velocity,
            manipulation_phase=manipulation_phase,
            texture_class=None,
            object_deformation=deformation,
            temperature=None,
            confidence=confidence,
            compliance_level="L1",
        )

    # ================================================================
    # 验证
    # ================================================================

    def validate(self) -> Tuple[bool, List[str]]:
        """
        验证 Schema 完整性与 compliance_level 一致性。
        
        Returns:
            (is_valid, errors): is_valid=True 表示通过；errors 是错误消息列表。
        """
        errors: List[str] = []

        # 1. Required 字段检查
        if not isinstance(self.contact, bool):
            errors.append("contact must be bool")
        if not isinstance(self.slip_event, bool):
            errors.append("slip_event must be bool")

        # 2. confidence 范围
        if not (0.0 <= self.confidence <= 1.0):
            errors.append(f"confidence must be in [0.0, 1.0], got {self.confidence}")

        # 3. compliance_level 枚举
        if self.compliance_level not in VALID_COMPLIANCE_LEVELS:
            errors.append(
                f"compliance_level must be one of {VALID_COMPLIANCE_LEVELS}, got '{self.compliance_level}'"
            )

        # 4. contact=true 时 contact_centroid 不能为 null
        if self.contact and self.contact_centroid is None:
            errors.append("contact_centroid is required when contact=true")

        # 5. contact_centroid 维度检查
        if self.contact_centroid is not None:
            if not isinstance(self.contact_centroid, (list, tuple)) or len(self.contact_centroid) != 2:
                errors.append("contact_centroid must be [x, y] (2 floats)")

        # 6. compliance_level 条件必填
        level_order = {"L1": 1, "L2": 2, "L3": 3, "L4": 4}
        level_num = level_order.get(self.compliance_level, 0)

        if level_num >= 2 and self.force_magnitude is None:
            errors.append("force_magnitude is required for compliance_level >= L2")

        if level_num >= 3 and self.force_vector is None:
            errors.append("force_vector is required for compliance_level >= L3")

        # 7. 枚举值合法性检查
        if self.contact_region is not None and self.contact_region not in VALID_CONTACT_REGIONS:
            errors.append(
                f"contact_region must be one of {VALID_CONTACT_REGIONS}, got '{self.contact_region}'"
            )

        if self.manipulation_phase is not None and self.manipulation_phase not in VALID_MANIPULATION_PHASES:
            errors.append(
                f"manipulation_phase must be one of {VALID_MANIPULATION_PHASES}, got '{self.manipulation_phase}'"
            )

        if self.texture_class is not None and self.texture_class not in VALID_TEXTURE_CLASSES:
            errors.append(
                f"texture_class must be one of {VALID_TEXTURE_CLASSES}, got '{self.texture_class}'"
            )

        # 8. 向量维度检查
        if self.force_vector is not None:
            if not isinstance(self.force_vector, (list, tuple)) or len(self.force_vector) != 3:
                errors.append("force_vector must be [Fx, Fy, Fz] (3 floats)")

        if self.torque_vector is not None:
            if not isinstance(self.torque_vector, (list, tuple)) or len(self.torque_vector) != 3:
                errors.append("torque_vector must be [Mx, My, Mz] (3 floats)")

        if self.slip_velocity is not None:
            if not isinstance(self.slip_velocity, (list, tuple)) or len(self.slip_velocity) != 2:
                errors.append("slip_velocity must be [vx, vy] (2 floats)")

        return (len(errors) == 0, errors)
