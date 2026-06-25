"""
TLabel v0.7 Feature Metadata Registry

每个22维特征的静态元数据：类别、计算公式、物理语义、单位、力相关度、标定依赖。
用于 to_dict() 输出和文档自动生成。
"""

from typing import Dict, Any, Optional, List


# 特征4类重分类（RFC §3.3）
FEATURE_CATEGORIES = ["deformation", "gradient", "force_semantic", "temporal"]

# 力相关度级别
FORCE_CORRELATION_LEVELS = ["direct", "high", "moderate", "low", "indirect"]


FEATURE_REGISTRY: Dict[str, Dict[str, Any]] = {
    # ── deformation (1-5): RGB差图像素级变形描述 ──
    "contact": {
        "feature_id": 1,
        "category": "deformation",
        "computation": "Binary: 1.0 if sensor contact detected (from ground-truth label or threshold), else 0.0",
        "physical_semantics": "Binary contact indicator. Derived from external label or deformation threshold, not from force measurement.",
        "si_unit": None,
        "raw_unit": "dimensionless",
        "force_correlation": "direct",
        "requires_calibration": False,
        "calibration_depends_on": [],
        "deprecated": False,
    },
    "deformation_magnitude": {
        "feature_id": 2,
        "category": "deformation",
        "computation": "sqrt(mean(R² + G² + B²)) of background-subtracted differential image",
        "physical_semantics": "RMS of RGB differential image. Measures overall pixel-level deformation intensity. Proportional to normal deformation when elastomer properties are known, but without calibration the unit is pixel intensity (arbitrary_unit).",
        "si_unit": None,
        "raw_unit": "arbitrary_unit",
        "force_correlation": "direct",
        "requires_calibration": True,
        "calibration_depends_on": ["sensor_profile.elastomer.modulus_pa", "sensor_profile.elastomer.thickness_mm"],
        "deprecated": False,
    },
    "force_magnitude": {
        "feature_id": 3,
        "category": "deformation",
        "computation": "Direct alias of deformation_magnitude (force_magnitude = deformation_magnitude)",
        "physical_semantics": "DEPRECATED: This is an uncalibrated copy of deformation_magnitude. The name implies a force measurement in Newtons, but the value has NOT undergone force-deformation calibration. Use deformation_magnitude_peak instead for transparency, or apply calibration via sensor_profile.",
        "si_unit": None,
        "raw_unit": "arbitrary_unit",
        "force_correlation": "direct",
        "requires_calibration": True,
        "calibration_depends_on": ["sensor_profile.elastomer.modulus_pa", "sensor_profile.elastomer.thickness_mm"],
        "deprecated": True,
        "deprecated_since": "0.7.0",
        "replacement": "deformation_magnitude_peak",
    },
    "force_peak": {
        "feature_id": 4,
        "category": "deformation",
        "computation": "max(|gray|) where gray = mean(R, G, B) of differential image",
        "physical_semantics": "Peak pixel intensity in the grayscale differential image. Represents the maximum single-pixel deformation. Without calibration, unit is pixel intensity.",
        "si_unit": None,
        "raw_unit": "arbitrary_unit",
        "force_correlation": "high",
        "requires_calibration": True,
        "calibration_depends_on": ["sensor_profile.elastomer.modulus_pa", "sensor_profile.elastomer.thickness_mm"],
        "deprecated": False,
    },
    "force_direction": {
        "feature_id": 5,
        "category": "deformation",
        "computation": "arctan2(weighted_mean_gy, weighted_mean_gx) where weights = |gray|, gx/gy = gradient of grayscale differential",
        "physical_semantics": "Intensity-weighted gradient direction of the deformation field. Indicates the dominant direction of surface displacement in image coordinates (not world coordinates without extrinsic calibration).",
        "si_unit": None,
        "raw_unit": "degree",
        "force_correlation": "high",
        "requires_calibration": True,
        "calibration_depends_on": ["sensor_profile.elastomer.modulus_pa"],
        "deprecated": False,
    },

    # ── gradient (6-9): 变形梯度（位移/应变近似） ──
    "slip_entropy": {
        "feature_id": 6,
        "category": "gradient",
        "computation": "-sum(p * log(p)) where p = histogram(grayscale_diff, bins=32, density=True) + 1e-10",
        "physical_semantics": "Shannon entropy of the grayscale deformation distribution. Higher entropy indicates more complex or distributed contact patterns. Indirectly related to slip propensity.",
        "si_unit": None,
        "raw_unit": "dimensionless",
        "force_correlation": "moderate",
        "requires_calibration": False,
        "calibration_depends_on": [],
        "deprecated": False,
    },
    "slip_event": {
        "feature_id": 7,
        "category": "gradient",
        "computation": "min(var(gradient_angle) / 100, 1.0) where gradient_angle = arctan2(gy, gx) of grayscale differential",
        "physical_semantics": "Variance of gradient angles in the deformation field, normalized to [0, 1]. High angular variance suggests multi-directional displacement patterns consistent with slip. This is a pixel-space heuristic, not a calibrated slip detector.",
        "si_unit": None,
        "raw_unit": "dimensionless",
        "force_correlation": "high",
        "requires_calibration": False,
        "calibration_depends_on": [],
        "deprecated": False,
    },
    "texture_energy": {
        "feature_id": 8,
        "category": "gradient",
        "computation": "mean(gray²) where gray = mean(R, G, B) of differential image",
        "physical_semantics": "Mean squared intensity of the grayscale differential. A simple texture energy measure. Related to deformation magnitude (squared) rather than surface texture per se.",
        "si_unit": None,
        "raw_unit": "arbitrary_unit",
        "force_correlation": "low",
        "requires_calibration": False,
        "calibration_depends_on": [],
        "deprecated": False,
    },
    "edge_density": {
        "feature_id": 9,
        "category": "gradient",
        "computation": "mean(|gradient(gray)| > percentile_90) where gradient is spatial gradient of grayscale differential",
        "physical_semantics": "Fraction of pixels with gradient magnitude above the 90th percentile. Indicates how much of the deformation field has sharp edges. Related to contact geometry rather than force.",
        "si_unit": None,
        "raw_unit": "dimensionless",
        "force_correlation": "low",
        "requires_calibration": False,
        "calibration_depends_on": [],
        "deprecated": False,
    },

    # ── force_semantic (10-18): 与力高度相关的像素空间计算 ──
    "contact_area": {
        "feature_id": 10,
        "category": "force_semantic",
        "computation": "mean(|gray| > 2 * std(gray)) where gray = mean(R, G, B) of differential image",
        "physical_semantics": "Fraction of pixels exceeding 2 standard deviations above the mean in the grayscale differential. Approximates the contact region area in pixel space. Proportional to contact area when sensor geometry is known.",
        "si_unit": None,
        "raw_unit": "dimensionless",
        "force_correlation": "high",
        "requires_calibration": True,
        "calibration_depends_on": ["sensor_profile.elastomer.modulus_pa", "sensor_profile.elastomer.thickness_mm"],
        "deprecated": False,
    },
    "centroid_x": {
        "feature_id": 11,
        "category": "force_semantic",
        "computation": "weighted_average(col_index, weights=col_sums(|gray|)) / image_width",
        "physical_semantics": "Column-wise center of mass of the deformation field, normalized to [0, 1]. Indicates the lateral position of the contact centroid.",
        "si_unit": None,
        "raw_unit": "dimensionless",
        "force_correlation": "indirect",
        "requires_calibration": False,
        "calibration_depends_on": [],
        "deprecated": False,
    },
    "normal_field_magnitude": {
        "feature_id": 12,
        "category": "force_semantic",
        "computation": "sqrt(mean(R² + G² + B²)) of contact differential image (RMS of 3-channel differential)",
        "physical_semantics": "RMS of the RGB differential image. Despite the name suggesting 'normal force', this is purely a pixel-space computation. Highly correlated with normal force when elastomer properties are known, but without calibration the unit is pixel intensity (arbitrary_unit).",
        "si_unit": None,
        "raw_unit": "arbitrary_unit",
        "force_correlation": "high",
        "requires_calibration": True,
        "calibration_depends_on": ["sensor_profile.elastomer.modulus_pa", "sensor_profile.elastomer.thickness_mm"],
        "deprecated": False,
    },
    "normal_field_variance": {
        "feature_id": 13,
        "category": "force_semantic",
        "computation": "var(sqrt(gx² + gy²)) where gx, gy = gradient of mean(R, G, B) of differential image",
        "physical_semantics": "Spatial variance of the gradient magnitude in the grayscale differential. Captures the non-uniformity of the deformation field. Moderate correlation with contact geometry changes.",
        "si_unit": None,
        "raw_unit": "arbitrary_unit",
        "force_correlation": "moderate",
        "requires_calibration": False,
        "calibration_depends_on": [],
        "deprecated": False,
    },
    "shear_field_magnitude": {
        "feature_id": 14,
        "category": "force_semantic",
        "computation": "sqrt(mean(|R_gx|)² + mean(|G_gy|)²) where R_gx = spatial gradient of R channel (x-direction), G_gy = spatial gradient of G channel (y-direction)",
        "physical_semantics": "Magnitude of the shear deformation estimated from channel-separated spatial gradients. R channel horizontal gradient approximates x-shear, G channel vertical gradient approximates y-shear. Despite the name suggesting 'shear force', this is a pixel-space computation without force calibration.",
        "si_unit": None,
        "raw_unit": "arbitrary_unit",
        "force_correlation": "high",
        "requires_calibration": True,
        "calibration_depends_on": ["sensor_profile.elastomer.modulus_pa", "sensor_profile.elastomer.thickness_mm", "sensor_profile.elastomer.friction_coefficient"],
        "deprecated": False,
    },
    "shear_field_direction": {
        "feature_id": 15,
        "category": "force_semantic",
        "computation": "degrees(arctan2(mean(|G_gy|), mean(|R_gx|))) where R_gx, G_gy are channel-separated spatial gradients",
        "physical_semantics": "Direction of the shear deformation in image coordinates. Derived from the ratio of vertical to horizontal gradient components. Not calibrated to world coordinates.",
        "si_unit": None,
        "raw_unit": "degree",
        "force_correlation": "moderate",
        "requires_calibration": True,
        "calibration_depends_on": ["sensor_profile.elastomer.friction_coefficient"],
        "deprecated": False,
    },
    "delta_force_normal": {
        "feature_id": 16,
        "category": "force_semantic",
        "computation": "Frame-to-frame change in normal_field_magnitude: sqrt(mean((gray_t - gray_{t-1})²)) or |normal_field_t - normal_field_{t-1}|",
        "physical_semantics": "Temporal derivative of the normal deformation field. Represents the rate of change of normal deformation between consecutive frames. Despite the name suggesting 'force change', this is computed in pixel space without force calibration.",
        "si_unit": None,
        "raw_unit": "arbitrary_unit",
        "force_correlation": "high",
        "requires_calibration": True,
        "calibration_depends_on": ["sensor_profile.elastomer.modulus_pa", "sensor_profile.elastomer.thickness_mm"],
        "deprecated": False,
    },
    "delta_force_shear": {
        "feature_id": 17,
        "category": "force_semantic",
        "computation": "Frame-to-frame change in shear_field_magnitude: |shear_field_t - shear_field_{t-1}|",
        "physical_semantics": "Temporal derivative of the shear deformation field. Represents the rate of change of shear between consecutive frames. Pixel-space computation without force calibration.",
        "si_unit": None,
        "raw_unit": "arbitrary_unit",
        "force_correlation": "high",
        "requires_calibration": True,
        "calibration_depends_on": ["sensor_profile.elastomer.modulus_pa", "sensor_profile.elastomer.friction_coefficient"],
        "deprecated": False,
    },
    "friction_cone_ratio": {
        "feature_id": 18,
        "category": "force_semantic",
        "computation": "shear_field_magnitude / normal_field_magnitude (clamped to max 10.0)",
        "physical_semantics": "Ratio of shear to normal deformation magnitude. Analogous to the friction cone concept in contact mechanics (τ/σ < μ for no-slip), but computed from uncalibrated pixel values. Exceeding the physical friction coefficient would indicate slip, but without calibration this threshold is unknown.",
        "si_unit": None,
        "raw_unit": "dimensionless",
        "force_correlation": "high",
        "requires_calibration": True,
        "calibration_depends_on": ["sensor_profile.elastomer.friction_coefficient"],
        "deprecated": False,
    },

    # ── temporal (19-22): 帧间时序变化 ──
    "optical_flow_magnitude": {
        "feature_id": 19,
        "category": "temporal",
        "computation": "mean(magnitude) of Farneback optical flow between consecutive frames",
        "physical_semantics": "Average pixel displacement magnitude between consecutive frames, computed via dense optical flow. Captures global surface motion. Requires OpenCV.",
        "si_unit": None,
        "raw_unit": "pixel/frame",
        "force_correlation": "indirect",
        "requires_calibration": False,
        "calibration_depends_on": [],
        "deprecated": False,
    },
    "optical_flow_direction": {
        "feature_id": 20,
        "category": "temporal",
        "computation": "degrees(mean(angle)) of Farneback optical flow between consecutive frames",
        "physical_semantics": "Average pixel displacement direction between consecutive frames, computed via dense optical flow. Indicates the dominant motion direction in image coordinates.",
        "si_unit": None,
        "raw_unit": "degree",
        "force_correlation": "indirect",
        "requires_calibration": False,
        "calibration_depends_on": [],
        "deprecated": False,
    },
    "temporal_deformation_rate": {
        "feature_id": 21,
        "category": "temporal",
        "computation": "|deformation_magnitude_t - deformation_magnitude_{t-1}| / dt where dt = 1/sampling_rate",
        "physical_semantics": "Rate of change of deformation magnitude over time. Represents how quickly the contact intensity is changing. Higher values indicate dynamic loading or unloading.",
        "si_unit": None,
        "raw_unit": "arbitrary_unit/s",
        "force_correlation": "high",
        "requires_calibration": True,
        "calibration_depends_on": ["sensor_profile.elastomer.modulus_pa"],
        "deprecated": False,
    },
    "contact_transition": {
        "feature_id": 22,
        "category": "temporal",
        "computation": "min(1.0, |contact_t - contact_{t-1}| + |contact_area_change| * 5.0)",
        "physical_semantics": "Contact state transition intensity. Combines binary contact change with contact area change rate. Values near 1.0 indicate a contact onset or release event.",
        "si_unit": None,
        "raw_unit": "dimensionless",
        "force_correlation": "high",
        "requires_calibration": False,
        "calibration_depends_on": [],
        "deprecated": False,
    },
}

# 新增：deformation_magnitude_peak（force_magnitude的诚实替代）
FEATURE_REGISTRY["deformation_magnitude_peak"] = {
    "feature_id": 3,
    "category": "deformation",
    "computation": "Direct alias of deformation_magnitude (same value, honest naming)",
    "physical_semantics": "Peak deformation magnitude. Identical to deformation_magnitude in computation, but named transparently to avoid implying a force measurement. Use this instead of the deprecated force_magnitude.",
    "si_unit": None,
    "raw_unit": "arbitrary_unit",
    "force_correlation": "direct",
    "requires_calibration": True,
    "calibration_depends_on": ["sensor_profile.elastomer.modulus_pa", "sensor_profile.elastomer.thickness_mm"],
    "deprecated": False,
}


def get_feature_metadata(feature_name: str) -> Optional[Dict[str, Any]]:
    """获取单个特征的元数据"""
    return FEATURE_REGISTRY.get(feature_name)


def get_features_by_category(category: str) -> List[str]:
    """按类别获取特征名列表"""
    return [name for name, meta in FEATURE_REGISTRY.items()
            if meta["category"] == category and not meta.get("deprecated", False)]


def get_features_requiring_calibration() -> List[str]:
    """获取需要标定的特征名列表"""
    return [name for name, meta in FEATURE_REGISTRY.items()
            if meta["requires_calibration"] and not meta.get("deprecated", False)]


def get_deprecated_features() -> List[str]:
    """获取已废弃的特征名列表"""
    return [name for name, meta in FEATURE_REGISTRY.items()
            if meta.get("deprecated", False)]


def get_feature_metadata_summary() -> Dict[str, Dict[str, Any]]:
    """获取全部特征元数据（用于to_dict输出）"""
    return FEATURE_REGISTRY
