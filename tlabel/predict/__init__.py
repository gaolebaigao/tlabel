"""
tlabel.predict — AI辅助预标注模块

从"纯手动标注" → "人机协作标注"，用规则+统计推断+ML自动预测标注维度。

三种引擎:
  - PredictEngine: 纯规则引擎，无需训练数据，零配置即可用
  - MLEngine: ML引擎 (需 pip install tlabel[ml])，使用梯度提升+校准，更高准确率
  - PostProcessor: [v0.5.0] 时序后处理器，平滑+HMM Phase+联动修正

v0.5.0 改进:
  - Phase用HMM+Viterbi解码替代简单规则/hash编码
  - 时序平滑消除单帧跳变
  - 预测后自动联动修正确保物理一致性
"""

from tlabel.predict.engine import PredictEngine, PredictConfig, PredictResult

try:
    from tlabel.predict.ml_engine import MLEngine, MLEngineConfig
except ImportError:
    MLEngine = None
    MLEngineConfig = None

def _check_ml_deps():
    """Check if ML dependencies are available, raise helpful error if not."""
    if MLEngine is None:
        raise ImportError(
            "MLEngine requires scikit-learn and joblib. "
            "Install with: pip install tlabel[ml]"
        )

from tlabel.predict.postprocess import (
    PostProcessor, PostProcessConfig,
    TemporalSmoother, PhaseHMM,
    PHASE_STATES, PHASE_TO_IDX,
)

__all__ = [
    "PredictEngine", "PredictConfig", "PredictResult",
    "MLEngine", "MLEngineConfig",
    "PostProcessor", "PostProcessConfig",
    "TemporalSmoother", "PhaseHMM",
    "PHASE_STATES", "PHASE_TO_IDX",
]
