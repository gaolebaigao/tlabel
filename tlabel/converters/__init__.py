"""
TLabel 格式转换器

支持与其他机器人学习框架的数据交换：
- LeRobot (Parquet + meta/info.json)
- HDF5 (科学计算标准)
- FTP-1/MTTS (Zarr格式，触觉基础模型)
- 未来支持: RLDS, ROS2, TFRecord
"""

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

# LeRobot converter requires pyarrow (optional dependency)
try:
    from tlabel.converters.lerobot import lerobot_to_tlabel, tlabel_to_lerobot, detect_image_shape_for_lerobot
    _HAS_LEROBOT = True
except ImportError:
    _HAS_LEROBOT = False

__all__ = [
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

# Only add lerobot functions if available
if _HAS_LEROBOT:
    __all__.extend(["lerobot_to_tlabel", "tlabel_to_lerobot", "detect_image_shape_for_lerobot"])

# v0.19.0-dev: 统一转换器接口
from tlabel.converters.base import (
    BaseConverter,
    FTP1Converter,
    LeRobotConverter,
    CONVERTERS,
    get_converter,
    list_converters,
    list_available_converters,
)

__all__.extend([
    "BaseConverter",
    "FTP1Converter",
    "LeRobotConverter",
    "CONVERTERS",
    "get_converter",
    "list_converters",
    "list_available_converters",
])
