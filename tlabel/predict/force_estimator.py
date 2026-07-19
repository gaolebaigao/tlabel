"""
Force Estimator — v0.14.0 新增

从视触觉传感器数据（形变、图像）推断力的大小。
让只有 GelSight / DIGIT / PaXini 等视触觉传感器（无F/T传感器）的用户也能进行 primitive 标注。

核心物理模型:
  - F = k × δ  (弹性体刚度 × 形变量)
  - 形变来源: deformation_magnitude 字段 / 图像帧差异

不引入外部ML依赖（无PyTorch/TensorFlow），纯物理模型+简单图像处理。
"""

import math
from typing import List, Dict, Optional, Any

from tlabel.core.types import TLabelData, TLabelFrame


# ============================================================
# 传感器默认弹性体刚度 (N/m)
# ============================================================

DEFAULT_ELASTOMER_STIFFNESS = {
    "gelsight_mini": 800.0,      # GelSight Mini: 中等刚度弹性体
    "gelsight": 600.0,           # GelSight (标准版)
    "digit": 1200.0,             # DIGIT: 较硬弹性体
    "paxini": 500.0,             # PaXini: 软弹性体
    "daimon": 700.0,             # Daimon
    "touchd": 450.0,             # ToucHD
    "contactile": 350.0,         # Contactile
}


def get_default_stiffness(sensor_type: str) -> float:
    """获取传感器默认刚度值"""
    sensor_type_lower = sensor_type.lower().replace(" ", "_")
    for key, val in DEFAULT_ELASTOMER_STIFFNESS.items():
        if key in sensor_type_lower:
            return val
    # 未知传感器使用保守的中等刚度
    return 500.0


# ============================================================
# 推断结果容器
# ============================================================

class ForceEstimate:
    """单帧力推断结果"""
    __slots__ = ['frame_idx', 'estimated_force_n', 'confidence',
                 'method', 'deformation_used', 'stiffness_used']

    def __init__(self, frame_idx: int, estimated_force_n: float,
                 confidence: float, method: str,
                 deformation_used: float, stiffness_used: float):
        self.frame_idx = frame_idx
        self.estimated_force_n = estimated_force_n
        self.confidence = confidence
        self.method = method
        self.deformation_used = deformation_used
        self.stiffness_used = stiffness_used

    def to_dict(self) -> Dict:
        return {
            "frame_idx": self.frame_idx,
            "estimated_force_n": round(self.estimated_force_n, 4),
            "confidence": round(self.confidence, 4),
            "method": self.method,
            "source": "estimated_force",
            "deformation_used": round(self.deformation_used, 4),
            "stiffness_used": round(self.stiffness_used, 2),
        }


# ============================================================
# 基类
# ============================================================

class ForceEstimator:
    """力推断器基类"""

    def can_estimate(self, data: TLabelData) -> bool:
        """判断是否能从当前数据推断力"""
        raise NotImplementedError

    def estimate(self, data: TLabelData) -> List[ForceEstimate]:
        """逐帧推断力，返回ForceEstimate列表"""
        raise NotImplementedError

    def integrate(self, data: TLabelData) -> TLabelData:
        """将推断结果写入TLabelData的frames中，并标记source"""
        estimates = self.estimate(data)
        est_by_frame = {e.frame_idx: e for e in estimates}

        for frame in data.frames:
            est = est_by_frame.get(frame.frame_idx)
            if est is None:
                continue
            # 写入力估计值到tlabel_v2
            frame.tlabel_v2["force_magnitude"] = est.estimated_force_n
            # 在sensor_specific中记录推断信息
            frame.sensor_specific["force_source"] = "estimated_force"
            frame.sensor_specific["force_estimate_method"] = est.method
            frame.sensor_specific["force_estimate_confidence"] = est.confidence
            frame.sensor_specific["force_estimate_stiffness"] = est.stiffness_used

        # 在TLabelData级别标记
        data._force_estimates = estimates
        data._force_estimate_summary = {
            "method": self.__class__.__name__,
            "total_estimates": len(estimates),
            "avg_confidence": (
                sum(e.confidence for e in estimates) / len(estimates)
                if estimates else 0.0
            ),
        }
        return data


# ============================================================
# 基于形变 + 弹性体刚度的推断
# ============================================================

class DeformationForceEstimator(ForceEstimator):
    """
    利用已有 deformation_magnitude 字段 + sensor_profile中的弹性体刚度参数
    通过物理模型 F = k × δ 推断力

    置信度规则:
    - 有标定刚度参数 → confidence=0.75
    - 仅有默认刚度 → confidence=0.55
    - 无deformation_magnitude数据 → confidence=0.0 (can_estimate=False)
    """

    def can_estimate(self, data: TLabelData) -> bool:
        if not data.frames:
            return False
        # 检查是否有非零的deformation_magnitude
        for f in data.frames:
            if f.tlabel_v2.get("deformation_magnitude", 0.0) > 0.01:
                return True
        return False

    def _get_stiffness(self, data: TLabelData):
        """获取弹性体刚度，返回 (stiffness_n_m, is_default)"""
        sp = data.sensor_profile or {}
        elastomer = sp.get("elastomer", {})
        stiffness = elastomer.get("stiffness_n_m")
        if stiffness is not None and stiffness > 0:
            return float(stiffness), False
        # 回退到传感器类型默认刚度
        sensor_type = data.sensor_info.get("type", "")
        default_k = get_default_stiffness(sensor_type)
        return default_k, True

    def estimate(self, data: TLabelData) -> List[ForceEstimate]:
        stiffness, is_default = self._get_stiffness(data)
        # 形变→力的映射：将 deformation_magnitude (0-1 arbitrary units) 映射到
        # 归一化力值范围 (0-1)，使推断结果兼容现有的规则引擎阈值。
        # 物理含义：F_normalized = deform * (k / k_reference)
        # 其中 k_reference = 1000 N/m 是归一化参考刚度
        k_reference = 1000.0
        scale = stiffness / k_reference

        results = []
        for frame in data.frames:
            deform = frame.tlabel_v2.get("deformation_magnitude", 0.0)
            if deform < 0.001:
                results.append(ForceEstimate(
                    frame_idx=frame.frame_idx,
                    estimated_force_n=0.0,
                    confidence=0.9 if is_default else 0.95,
                    method="deformation_model",
                    deformation_used=deform,
                    stiffness_used=stiffness,
                ))
                continue

            # 归一化力估计：deformation * scale_factor
            # 保证输出值在合理范围 (0-1+)，兼容现有predict_primitives阈值
            force_n = deform * scale

            # 置信度
            conf = 0.75 if not is_default else 0.55

            results.append(ForceEstimate(
                frame_idx=frame.frame_idx,
                estimated_force_n=force_n,
                confidence=conf,
                method="deformation_model",
                deformation_used=deform,
                stiffness_used=stiffness,
            ))
        return results


# ============================================================
# 基于图像帧差异的推断
# ============================================================

class ImageForceEstimator(ForceEstimator):
    """
    利用图像帧差异（pixel intensity change）推断变形量→映射为力估计

    流程:
    1. 计算相邻帧的像素差异均值（作为变形代理）
    2. 归一化为0-1范围的"pseudo_deformation"
    3. 应用 F = k × δ 物理模型

    置信度: 0.35-0.45 (图像推断不如形变字段直接)
    """

    def can_estimate(self, data: TLabelData) -> bool:
        if not data.frames:
            return False
        # 检查是否有图像数据
        images = data.get_images(max_frames=5)
        return any(img is not None for img in images)

    def estimate(self, data: TLabelData) -> List[ForceEstimate]:
        stiffness = get_default_stiffness(data.sensor_info.get("type", ""))
        images = data.get_images()

        # 计算帧间差异
        intensity_diffs = []
        for i in range(len(images)):
            if i == 0 or images[i] is None or images[i - 1] is None:
                intensity_diffs.append(0.0)
            else:
                try:
                    img_curr = images[i].astype(float)
                    img_prev = images[i - 1].astype(float)
                    diff = abs(img_curr - img_prev).mean()
                    intensity_diffs.append(float(diff))
                except Exception:
                    intensity_diffs.append(0.0)

        # 归一化到0-1
        max_diff = max(intensity_diffs) if intensity_diffs else 1.0
        if max_diff < 0.01:
            max_diff = 1.0

        results = []
        for i, frame in enumerate(data.frames):
            pseudo_deform = intensity_diffs[i] / max_diff if max_diff > 0 else 0.0

            # F = k × δ，但图像推断的形变-力关系较弱
            # 使用归一化系数：pseudo_deform 已经是 0-1 范围
            # 乘以刚度比作为缩放，但图像推断本身置信度低
            k_reference = 1000.0
            force_n = pseudo_deform * (stiffness / k_reference) * 0.5  # 0.5衰减因子（图像推断不可靠）

            # 置信度较低
            conf = 0.45 if pseudo_deform > 0.1 else 0.35

            results.append(ForceEstimate(
                frame_idx=frame.frame_idx,
                estimated_force_n=force_n,
                confidence=conf,
                method="image_difference",
                deformation_used=pseudo_deform,
                stiffness_used=stiffness,
            ))
        return results


# ============================================================
# 组合推断器 + 自动推断入口
# ============================================================

class CompositeForceEstimator(ForceEstimator):
    """
    组合推断器 — 自动选择最佳推断策略

    优先级:
    1. DeformationForceEstimator (有deformation_magnitude字段时)
    2. ImageForceEstimator (有图像数据时)
    """

    def __init__(self):
        self._deformation_estimator = DeformationForceEstimator()
        self._image_estimator = ImageForceEstimator()
        self._chosen_method = None

    def can_estimate(self, data: TLabelData) -> bool:
        return (self._deformation_estimator.can_estimate(data) or
                self._image_estimator.can_estimate(data))

    def estimate(self, data: TLabelData) -> List[ForceEstimate]:
        if self._deformation_estimator.can_estimate(data):
            self._chosen_method = "deformation"
            return self._deformation_estimator.estimate(data)
        elif self._image_estimator.can_estimate(data):
            self._chosen_method = "image"
            return self._image_estimator.estimate(data)
        else:
            return []

    def integrate(self, data: TLabelData) -> TLabelData:
        if self._deformation_estimator.can_estimate(data):
            self._chosen_method = "deformation"
            return self._deformation_estimator.integrate(data)
        elif self._image_estimator.can_estimate(data):
            self._chosen_method = "image"
            return self._image_estimator.integrate(data)
        else:
            data._force_estimate_summary = {
                "method": "none",
                "reason": "No usable data for force estimation",
                "total_estimates": 0,
            }
            return data


def auto_force_estimate(data: TLabelData) -> TLabelData:
    """
    自动力推断入口函数

    检测可用数据，选择最佳推断策略，将推断结果写入TLabelData。

    Args:
        data: TLabelData实例

    Returns:
        修改后的TLabelData（原地修改，推断结果写入frames）

    用法:
        data = auto_force_estimate(data)
        # data._force_estimate_summary 包含推断摘要
        # data.frames[i].sensor_specific["force_source"] == "estimated_force"
    """
    estimator = CompositeForceEstimator()
    return estimator.integrate(data)


def has_real_force_data(data: TLabelData) -> bool:
    """
    判断TLabelData是否包含真实的力/力矩数据（而非形变别名）

    用于判断是否需要force estimation。
    当force_magnitude全为0或等于deformation_magnitude时，视为无力数据。
    """
    if not data.frames:
        return False

    has_nonzero_force = False
    for f in data.frames:
        tv2 = f.tlabel_v2
        force = tv2.get("force_magnitude", 0.0)
        deform = tv2.get("deformation_magnitude", 0.0)
        # 如果有传感器明确提供了力数据（如delta_force, normal_field_magnitude > 0）
        # 或者force_magnitude与deformation_magnitude不同
        normal_field = tv2.get("normal_field_magnitude", 0.0)
        delta_force = tv2.get("delta_force_normal", 0.0)

        if normal_field > 0.01 or delta_force > 0.01:
            return True
        if force > 0.01 and abs(force - deform) > 0.001:
            return True
        if force > 0.01:
            has_nonzero_force = True

    # force_magnitude 等于 deformation_magnitude（未标定别名）→ 视为无力数据
    # force_magnitude 全0 → 无力数据
    return False
