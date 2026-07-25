"""TouchLabel AI - Tactile Data Annotation Toolkit"""

from tlabel._version import __version__

from tlabel.core.loader import load
from tlabel.core.types import TLabelData, TLabelFrame, EpisodeLabel
from tlabel.core.primitive import (
    PrimitiveAnnotation, PRIMITIVE_PRESETS, PRIMITIVE_COLORS,
    DEFAULT_PRIMITIVE_SUBSET, GRASP_SUBTYPES, is_valid_primitive,
)
from tlabel.core.taxonomy import (
    TaxonomyConfig, PrimitiveRule, get_default_taxonomy, get_full_taxonomy,
)
from tlabel.core.events import TactileEvent, EVENT_PRESETS
from tlabel.demo import demo, list_demos

# Lazy imports for predict module (avoids eager sklearn/joblib load)
def __getattr__(name):
    if name == "PredictEngine":
        from tlabel.predict.engine import PredictEngine
        return PredictEngine
    if name == "PredictConfig":
        from tlabel.predict.engine import PredictConfig
        return PredictConfig
    if name == "PredictResult":
        from tlabel.predict.engine import PredictResult
        return PredictResult
    if name == "QualityScorer":
        from tlabel.quality.scorer import QualityScorer
        return QualityScorer
    if name == "BatchProcessor":
        from tlabel.batch.processor import BatchProcessor
        return BatchProcessor
    if name == "TLabelBatchPanel":
        from tlabel.viewer.batch_panel import TLabelBatchPanel
        return TLabelBatchPanel
    if name == "AugmentEngine":
        from tlabel.augment.engine import AugmentEngine
        return AugmentEngine
    raise AttributeError(f"module 'tlabel' has no attribute {name!r}")

from tlabel.core.loader import load
from tlabel.core.types import TLabelData, TLabelFrame, EpisodeLabel

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
    "DEFAULT_PRIMITIVE_SUBSET", "GRASP_SUBTYPES", "is_valid_primitive",
    "TaxonomyConfig", "PrimitiveRule", "get_default_taxonomy", "get_full_taxonomy",
    "TactileEvent", "EVENT_PRESETS",
    "PredictEngine", "PredictConfig", "PredictResult",
    "QualityScorer", "BatchProcessor", "TLabelBatchPanel", "AugmentEngine", "augment", "__version__",
]
