"""
TLabel 格式转换器

支持与其他机器人学习框架的数据交换：
- LeRobot (Parquet + meta/info.json)
- HDF5 (科学计算标准)
- 未来支持: RLDS, ROS2, TFRecord
"""

from tlabel.converters.lerobot import lerobot_to_tlabel, tlabel_to_lerobot

__all__ = [
    "lerobot_to_tlabel",
    "tlabel_to_lerobot",
]
