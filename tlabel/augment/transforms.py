"""
触觉数据增强变换 / Tactile data augmentation transforms

提供5种增强方法，每种方法接收 (T, D) numpy array，返回同形状 array。
所有方法支持 seed 参数保证可复现性。
"""

import numpy as np
from typing import Tuple, Optional


# 22维特征名称（与 TLabelData.to_dict 中 FEATURE_NAMES 保持一致）
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

# 力相关维度索引: normal_field_magnitude(11), shear_field_magnitude(13), shear_field_direction(14)
FORCE_DIM_INDICES = [11, 13, 14]


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
    通过在均匀时间网格上施加平滑随机偏移，再用样条插值重采样实现。

    Args:
        data: shape (T, D) 的特征矩阵
        sigma: 扭曲强度，控制时间偏移的标准差（越大形变越剧烈）
        seed: 随机种子，用于复现

    Returns:
        扭曲后的 (T, D) 特征矩阵
    """
    _validate_features(data)
    rng = np.random.RandomState(seed)
    T, D = data.shape

    if T < 4:
        return data.copy()

    # 原始均匀时间网格
    original_times = np.linspace(0, 1, T)

    # 在内部节点施加高斯随机偏移，边界保持不动
    perturbations = rng.normal(0, sigma, T)
    perturbations[0] = 0.0
    perturbations[-1] = 0.0

    # 平滑扰动（简单移动平均）以保持时序单调性
    kernel_size = max(3, T // 5)
    if kernel_size % 2 == 0:
        kernel_size += 1
    kernel = np.ones(kernel_size) / kernel_size
    smooth_perturbations = np.convolve(perturbations, kernel, mode='same')

    # 归一化平滑扰动到 [0, 1] 范围，确保时间单调递增
    warped_times = original_times + smooth_perturbations
    warped_times[0] = 0.0
    warped_times[-1] = 1.0
    warped_times = np.clip(warped_times, 0, 1)
    # 确保严格单调递增
    for i in range(1, T):
        if warped_times[i] <= warped_times[i - 1]:
            warped_times[i] = warped_times[i - 1] + 1e-8

    # 对每个维度独立做线性插值重采样
    warped_data = np.zeros_like(data)
    for d in range(D):
        warped_data[:, d] = np.interp(original_times, warped_times, data[:, d])

    return warped_data


def noise_inject(data: np.ndarray, sigma: float = 0.05, seed: Optional[int] = None) -> np.ndarray:
    """
    高斯噪声注入 / Gaussian noise injection

    添加小幅高斯噪声，模拟传感器固有测量噪声。

    Args:
        data: shape (T, D) 的特征矩阵
        sigma: 噪声标准差（相对于数据幅值）
        seed: 随机种子，用于复现

    Returns:
        注入噪声后的 (T, D) 特征矩阵
    """
    _validate_features(data)
    rng = np.random.RandomState(seed)
    noise = rng.normal(0, sigma, data.shape)
    return data + noise


def random_crop(data: np.ndarray, ratio: float = 0.8, seed: Optional[int] = None) -> np.ndarray:
    """
    随机时间窗口裁剪 / Random temporal window cropping

    从时间序列中随机截取一个子窗口，然后用零填充（zero-padding）回原始长度。
    模拟传感器采集中断或有效接触窗口截取。

    Args:
        data: shape (T, D) 的特征矩阵
        ratio: 裁剪窗口占原始长度的比例，范围 (0, 1]
        seed: 随机种子，用于复现

    Returns:
        裁剪并填充后的 (T, D) 特征矩阵
    """
    _validate_features(data)
    rng = np.random.RandomState(seed)
    T, D = data.shape

    ratio = np.clip(ratio, 0.1, 1.0)
    crop_len = max(2, int(T * ratio))

    if crop_len >= T:
        return data.copy()

    # 随机选择裁剪起点
    max_start = T - crop_len
    start = rng.randint(0, max_start + 1)
    cropped = data[start:start + crop_len]

    # 零填充回原长度
    result = np.zeros_like(data)
    result[:crop_len] = cropped

    return result


def force_scale(data: np.ndarray, factor_range: Tuple[float, float] = (0.8, 1.2),
                seed: Optional[int] = None) -> np.ndarray:
    """
    力 magnitude 缩放 / Force magnitude scaling

    随机缩放力相关维度（normal_field_magnitude, shear_field_magnitude,
    shear_field_direction），模拟不同接触力度。

    Args:
        data: shape (T, D) 的特征矩阵
        factor_range: 缩放因子范围 (min, max)
        seed: 随机种子，用于复现

    Returns:
        缩放后的 (T, D) 特征矩阵
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
    """
    随机帧丢弃 / Random frame dropout

    随机将某些帧的所有特征置零，模拟数据包丢失或传感器瞬断。

    Args:
        data: shape (T, D) 的特征矩阵
        drop_rate: 每帧被丢弃（置零）的概率
        seed: 随机种子，用于复现

    Returns:
        丢弃帧后的 (T, D) 特征矩阵
    """
    _validate_features(data)
    rng = np.random.RandomState(seed)
    result = data.copy()

    T = data.shape[0]
    drop_mask = rng.random(T) < drop_rate
    # 至少保留第一帧和最后一帧，避免完全丢失时序锚点
    drop_mask[0] = False
    drop_mask[-1] = False
    result[drop_mask] = 0.0

    return result
