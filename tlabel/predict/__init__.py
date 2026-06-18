"""
tlabel.predict — AI辅助预标注模块

从"纯手动标注" → "人机协作标注"，用规则+统计推断+ML自动预测标注维度。

两种引擎:
  - PredictEngine: 纯规则引擎，无需训练数据，零配置即可用
  - MLEngine: ML引擎 (需 pip install tlabel[ml])，使用梯度提升+校准，更高准确率
"""

from tlabel.predict.engine import PredictEngine, PredictConfig, PredictResult

# MLEngine 需要额外依赖 (scikit-learn, joblib)
# 如果未安装，导入时会给出友好提示
try:
    from tlabel.predict.ml_engine import MLEngine, MLEngineConfig
except ImportError:
    MLEngine = None
    MLEngineConfig = None

__all__ = ["PredictEngine", "PredictConfig", "PredictResult", "MLEngine", "MLEngineConfig"]
