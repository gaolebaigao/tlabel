"""
TLabel 格式转换器

支持与其他机器人学习框架的数据交换：
- LeRobot (Parquet + meta/info.json)
- HDF5 (科学计算标准)
- FTP-1/MTTS (Zarr格式，触觉基础模型)
- 未来支持: RLDS, ROS2, TFRecord
"""

from tlabel.converters.lerobot import lerobot_to_tlabel, tlabel_to_lerobot
from tlabel.converters.ftp1 import (
    tlabel_to_ftp1,
    batch_to_ftp1,
    list_functional_areas,
    list_known_sensors,
    HAND_FUNCTIONAL_AREAS,
    TORQUE_AREAS,
    ALL_FUNCTIONAL_AREAS,
    FTP1_KNOWN_SENSORS,
    DEFAULT_AREA_MAPPINGS,
)

__all__ = [
    "lerobot_to_tlabel",
    "tlabel_to_lerobot",
    "tlabel_to_ftp1",
    "batch_to_ftp1",
    "list_functional_areas",
    "list_known_sensors",
    "HAND_FUNCTIONAL_AREAS",
    "TORQUE_AREAS",
    "ALL_FUNCTIONAL_AREAS",
    "FTP1_KNOWN_SENSORS",
    "DEFAULT_AREA_MAPPINGS",
]
