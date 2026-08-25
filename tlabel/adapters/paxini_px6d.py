"""
PaXini PX6D 六维力/触觉传感器适配器 — placeholder（开发中）

PX6D 是 PaXini 新一代六维力触觉传感器，集成高精度力觉与触觉感知。
该适配器为占位符，目前尚未实现，后续版本将提供完整支持。

所有方法均抛出 NotImplementedError，仅供注册占位使用。
"""

from typing import Optional, Dict, Any, Iterator, List

from tlabel.adapters.base import SensorAdapterBase
from tlabel.core.types import TLabelData, TLabelFrame
from tlabel.core.schema import TLabelSchemaV2


class PaxiniPX6DAdapter(SensorAdapterBase):
    """PaXini PX6D 六维力触觉传感器 → TLabelData (placeholder)

    **占位符适配器 — 正在开发中**

    PX6D 是 PaXini 新一代六维力/触觉一体化传感器，支持：
      - 6 轴力/力矩测量（Fx/Fy/Fz/Mx/My/Mz）
      - 高分辨率触觉阵列（待公布规格）
      - 集成温度补偿与实时标定

    本类为注册占位符，所有方法均抛出 NotImplementedError。
    完整实现将在后续版本中提供。

    依赖: paxini-px6d-sdk（厂商 SDK，待发布）
    """

    def __init__(self):
        raise NotImplementedError("PaXini PX6D adapter is under development")

    @property
    def name(self) -> str:
        return "paxini_px6d"

    @property
    def supported_extensions(self) -> List[str]:
        return []

    def get_capabilities(self) -> Dict[str, bool]:
        raise NotImplementedError("PaXini PX6D adapter is under development")

    def get_sensor_info(self) -> Dict[str, Any]:
        raise NotImplementedError("PaXini PX6D adapter is under development")

    def extract_schema(self, raw_frame_data) -> TLabelSchemaV2:
        raise NotImplementedError("PaXini PX6D adapter is under development")

    def load(self, file_path: str,
             trajectory_id: Optional[int] = None,
             **kwargs) -> TLabelData:
        raise NotImplementedError("PaXini PX6D adapter is under development")

    def connect(self, device_id: str = "auto", **kwargs) -> bool:
        raise NotImplementedError("PaXini PX6D adapter is under development")

    def disconnect(self) -> None:
        raise NotImplementedError("PaXini PX6D adapter is under development")

    def is_connected(self) -> bool:
        raise NotImplementedError("PaXini PX6D adapter is under development")

    def stream_frames(self, num_frames: int = -1,
                      **kwargs) -> Iterator[TLabelFrame]:
        raise NotImplementedError("PaXini PX6D adapter is under development")
