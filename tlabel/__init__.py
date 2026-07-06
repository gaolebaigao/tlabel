"""TouchLabel AI - Tactile Data Annotation Toolkit"""

from tlabel._version import __version__

from tlabel.core.loader import load
from tlabel.core.types import TLabelData, TLabelFrame, EpisodeLabel
from tlabel.core.primitive import PrimitiveAnnotation, PRIMITIVE_PRESETS, PRIMITIVE_COLORS
from tlabel.demo import demo, list_demos
from tlabel.predict.engine import PredictEngine
from tlabel.quality.scorer import QualityScorer
from tlabel.batch.processor import BatchProcessor
from tlabel.viewer.batch_panel import TLabelBatchPanel

from tlabel.augment.engine import AugmentEngine

def augment(data, methods, params=None, seed=None):
    """
    便捷增强API / Convenience augmentation API

    对 TLabelData 实例应用数据增强，等价于 data.augment(methods, params, seed)。

    Args:
        data: TLabelData 实例
        methods: 增强方法名列表
        params: 各方法的参数覆盖
        seed: 主随机种子

    Returns:
        增强后的新 TLabelData 实例
    """
    return data.augment(methods, params, seed=seed)

__all__ = [
    "load", "TLabelData", "TLabelFrame", "EpisodeLabel",
    "PrimitiveAnnotation", "PRIMITIVE_PRESETS", "PRIMITIVE_COLORS",
    "demo", "list_demos", "PredictEngine",
    "QualityScorer", "BatchProcessor", "TLabelBatchPanel", "AugmentEngine", "augment", "__version__",
]
