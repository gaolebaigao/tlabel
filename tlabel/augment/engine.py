"""
触觉数据增强引擎 / Tactile data augmentation engine

提供 AugmentEngine 类，支持链式调用多种增强方法。
"""

import inspect
import numpy as np
from typing import List, Dict, Optional

from tlabel.augment.transforms import (
    time_warp, noise_inject, random_crop, force_scale, frame_dropout,
)


class AugmentEngine:
    """
    触觉数据增强引擎 / Tactile data augmentation engine

    支持对 (T, 22) 特征矩阵链式应用多种增强方法。

    Attributes:
        AVAILABLE_METHODS: 可用的增强方法注册表

    用法:
        augmented = AugmentEngine.augment(features, ['time_warp', 'noise_inject'])
        augmented = AugmentEngine.augment(
            features,
            methods=['force_scale', 'frame_dropout'],
            params={'force_scale': {'factor_range': (0.5, 1.5)}},
        )
    """

    AVAILABLE_METHODS: Dict[str, callable] = {
        'time_warp': time_warp,
        'noise_inject': noise_inject,
        'random_crop': random_crop,
        'force_scale': force_scale,
        'frame_dropout': frame_dropout,
    }

    @staticmethod
    def augment(features: np.ndarray, methods: List[str],
                params: Optional[Dict[str, dict]] = None,
                seed: Optional[int] = None) -> np.ndarray:
        """
        对22维特征序列应用增强 / Apply augmentation to 22-dim feature sequence

        Args:
            features: shape (T, 22) 的特征矩阵
            methods: 增强方法名列表，如 ['time_warp', 'noise_inject']
            params: 各方法的参数覆盖，如 {'time_warp': {'sigma': 0.2}}
            seed: 主随机种子。若提供，将为每个方法派生确定性子种子以保证可复现。
                  若不提供，各方法使用各自 params 中的 seed 或自行生成随机种子。

        Returns:
            增强后的 (T, 22) 特征矩阵

        Raises:
            ValueError: 特征矩阵维度不正确或方法名无效
        """
        if features.ndim != 2:
            raise ValueError(
                f"Expected 2D features array (T, D), got {features.ndim}D with shape {features.shape}"
            )

        if not methods:
            return features.copy()

        params = params or {}
        result = features.copy()
        master_rng = np.random.RandomState(seed)

        for method_name in methods:
            if method_name not in AugmentEngine.AVAILABLE_METHODS:
                available = list(AugmentEngine.AVAILABLE_METHODS.keys())
                raise ValueError(
                    f"Unknown augmentation method '{method_name}'. "
                    f"Available methods: {available}"
                )

            func = AugmentEngine.AVAILABLE_METHODS[method_name]
            method_params = params.get(method_name, {})

            # 如果提供了主种子，为每个方法派生确定性子种子
            if seed is not None and 'seed' not in method_params:
                method_params = {**method_params, 'seed': int(master_rng.randint(0, 2**31))}

            # 检查函数是否接受 seed 参数，安全传入
            sig = inspect.signature(func)
            if 'seed' in sig.parameters and 'seed' not in method_params:
                method_params = {**method_params, 'seed': int(master_rng.randint(0, 2**31))}

            result = func(result, **method_params)

        return result
