"""
触觉数据增强变换 / Tactile data augmentation transforms

提供5种增强方法，每种方法接收 (T, D) numpy array，返回同形状 array。
所有方法支持 seed 参数保证可复现性。

v0.17 Breaking Change: 移除 LEGACY_V2_FEATURE_NAMES (22维)，只使用 Schema V2 (16列展开)。
"""

import numpy as np
from typing import Tuple, Optional


# v0.17: Schema V2 14维展开后的特征名称（向量展开为多列）= 16列
FEATURE_NAMES = [
    "contact",              # 0
    "centroid_x",           # 1
    "centroid_y",           # 2
    "force_magnitude",      # 3
    "force_x",              # 4
    "force_y",              # 5
    "force_z",              # 6
    "torque_x",             # 7
    "torque_y",             # 8
    "torque_z",             # 9
    "slip_event",           # 10
    "slip_vx",              # 11
    "slip_vy",              # 12
    "object_deformation",   # 13
    "temperature",          # 14
    "confidence",           # 15
]

# 力相关维度索引（Schema V2 only）
FORCE_DIM_INDICES = [3, 4, 5, 6]  # force_magnitude, force_x, force_y, force_z


def _validate_features(data: np.ndarray) -> None:
    """验证输入特征矩阵维度 / Validate input feature matrix dimensions"""
    if data.ndim != 2:
        raise ValueError(f"Expected 2D array (T, D), got {data.ndim}D array with shape {data.shape}")
    if data.shape[0] < 2:
        raise ValueError(f"Need at least 2 time steps, got {data.shape[0]}")


def time_warp(data: np.ndarray, sigma: float = 0.1, seed: Optional[int] = None) -> np.ndarray:
    """
    时序弹性扭曲 / Temporal elastic warping

    对时间轴做随机弹性形变，模拟不同速度的接触过程。
    """
    _validate_features(data)
    rng = np.random.RandomState(seed)
    T, D = data.shape

    if T < 4:
        return data.copy()

    original_times = np.linspace(0, 1, T)
    perturbations = rng.normal(0, sigma, T)
    perturbations[0] = 0.0
    perturbations[-1] = 0.0

    kernel_size = max(3, T // 5)
    if kernel_size % 2 == 0:
        kernel_size += 1
    kernel = np.ones(kernel_size) / kernel_size
    smooth_perturbations = np.convolve(perturbations, kernel, mode='same')

    warped_times = original_times + smooth_perturbations
    warped_times[0] = 0.0
    warped_times[-1] = 1.0
    warped_times = np.clip(warped_times, 0, 1)
    for i in range(1, T):
        if warped_times[i] <= warped_times[i - 1]:
            warped_times[i] = warped_times[i - 1] + 1e-8

    warped_data = np.zeros_like(data)
    for d in range(D):
        warped_data[:, d] = np.interp(original_times, warped_times, data[:, d])

    return warped_data


def noise_inject(data: np.ndarray, sigma: float = 0.05, seed: Optional[int] = None) -> np.ndarray:
    """高斯噪声注入 / Gaussian noise injection"""
    _validate_features(data)
    rng = np.random.RandomState(seed)
    noise = rng.normal(0, sigma, data.shape)
    return data + noise


def random_crop(data: np.ndarray, ratio: float = 0.8, seed: Optional[int] = None) -> np.ndarray:
    """随机时间窗口裁剪 / Random temporal window cropping"""
    _validate_features(data)
    rng = np.random.RandomState(seed)
    T, D = data.shape

    ratio = np.clip(ratio, 0.1, 1.0)
    crop_len = max(2, int(T * ratio))

    if crop_len >= T:
        return data.copy()

    max_start = T - crop_len
    start = rng.randint(0, max_start + 1)
    cropped = data[start:start + crop_len]

    result = np.zeros_like(data)
    result[:crop_len] = cropped

    return result


def force_scale(data: np.ndarray, factor_range: Tuple[float, float] = (0.8, 1.2),
                seed: Optional[int] = None) -> np.ndarray:
    """
    力 magnitude 缩放 / Force magnitude scaling

    随机缩放力相关维度，模拟不同接触力度。
    v0.17: 只使用 Schema V2 force indices。
    """
    _validate_features(data)
    rng = np.random.RandomState(seed)
    result = data.copy()

    factor = rng.uniform(factor_range[0], factor_range[1])

    for dim_idx in FORCE_DIM_INDICES:
        if dim_idx < result.shape[1]:
            result[:, dim_idx] *= factor

    return result


def frame_dropout(data: np.ndarray, drop_rate: float = 0.1,
                  seed: Optional[int] = None) -> np.ndarray:
    """随机帧丢弃 / Random frame dropout"""
    _validate_features(data)
    rng = np.random.RandomState(seed)
    result = data.copy()

    T = data.shape[0]
    drop_mask = rng.random(T) < drop_rate
    drop_mask[0] = False
    drop_mask[-1] = False
    result[drop_mask] = 0.0

    return result
