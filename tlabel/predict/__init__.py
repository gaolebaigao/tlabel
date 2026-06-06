"""
tlabel.predict — AI辅助预标注模块

从"纯手动标注" → "人机协作标注"，用规则+统计推断自动预测标注维度。
"""

from tlabel.predict.engine import PredictEngine

__all__ = ["PredictEngine"]
