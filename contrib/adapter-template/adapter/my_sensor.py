"""
<SENSOR_NAME> 适配器 — <简要描述>

传感器类型: <视触觉/阵列式/霍尔效应/...>
制造商: <厂商名称>
型号: <型号>
数据来源: <公开数据集名称 + URL 或 SDK>

数据映射:
  原始字段                    →  TLabel v2 字段
  ──────────────────────        ────────────────────────────
  <原始字段1>                  →  <tlabel维度>
  <原始字段2>                  →  <tlabel维度>

依赖: <如有特殊依赖在此列出，如 pip install xxx>
"""

from typing import Optional, Dict, Any, List

from tlabel.adapters.base import DataAdapterBase  # 数据集适配器用 DataAdapterBase
# from tlabel.adapters.base import SensorAdapterBase  # 实时传感器用 SensorAdapterBase
from tlabel.core.types import TLabelData, TLabelFrame


# TODO: 重命名类名为你的适配器名称，如 GelSightAdapter, PaxiniAdapter
class MySensorAdapter(DataAdapterBase):
    """<传感器名称> → TLabelData

    <一段话描述该适配器的功能和支持的型号>
    """

    @property
    def name(self) -> str:
        # TODO: 改为你的适配器名称（小写+下划线，与注册名一致）
        return "my_sensor"

    @property
    def supported_extensions(self) -> List[str]:
        # TODO: 改为你的数据文件扩展名
        return [".csv", ".dat"]

    def load(self, file_path: str,
             trajectory_id: Optional[int] = None,
             **kwargs) -> TLabelData:
        """加载数据文件，转换为 TLabelData

        参数:
            file_path: 数据文件路径
            trajectory_id: 轨迹ID（可选，用于多轨迹数据集）
            **kwargs: 适配器特有参数

        返回:
            TLabelData — 统一标注容器
        """
        import numpy as np

        # TODO: 实现你的数据加载逻辑
        # 1. 读取原始数据文件
        # 2. 遍历每一帧/时间步
        # 3. 将原始数据映射到 22 维 tlabel_v2 特征
        # 4. 组装 TLabelFrame 列表
        # 5. 返回 TLabelData

        frames = []

        # === 示例代码 ===
        # raw_data = np.load(file_path)
        # for i, frame_raw in enumerate(raw_data):
        #     tlabel_v2 = {
        #         "contact": 1.0 if frame_raw.pressure > 0 else 0.0,
        #         "deformation_magnitude": float(frame_raw.pressure / MAX_PRESSURE),
        #         "force_magnitude": 0.0,  # deprecated
        #         "force_peak": 0.0,
        #         "force_direction": 0.0,
        #         "slip_entropy": 0.0,
        #         "slip_event": 0.0,
        #         "texture_energy": 0.0,
        #         "edge_density": 0.0,
        #         "contact_area": float(frame_raw.contact_area_ratio),
        #         "centroid_x": 0.5,
        #         "normal_field_magnitude": 0.0,
        #         "normal_field_variance": 0.0,
        #         "shear_field_magnitude": 0.0,
        #         "shear_field_direction": 0.0,
        #         "delta_force_normal": 0.0,
        #         "delta_force_shear": 0.0,
        #         "friction_cone_ratio": 0.0,
        #         "optical_flow_magnitude": 0.0,
        #         "optical_flow_direction": 0.0,
        #         "temporal_deformation_rate": 0.0,
        #         "contact_transition": 0.0,
        #     }
        #     frame = TLabelFrame(
        #         frame_idx=i,
        #         timestamp_s=round(i / SAMPLE_RATE, 4),
        #         tlabel_v2=tlabel_v2,
        #         manipulation_phase="unknown",
        #         confidence=0.8,
        #         sensor_specific={"source": "my_sensor"},
        #     )
        #     frames.append(frame)

        sensor_info = self.get_sensor_info()
        episode_info = {
            "source": self.name,
            "file_path": str(file_path),
        }

        return TLabelData(
            frames=frames,
            sensor_info=sensor_info,
            episode_info=episode_info,
            capabilities=self.get_capabilities(),
            sensor_id=self.name,
        )

    def get_capabilities(self) -> Dict[str, bool]:
        """声明该传感器支持的 22 维特征

        TODO: 根据你的传感器实际能力修改。
        支持的维度设为 True，不支持的设为 False。
        """
        return {
            "contact": True,
            "deformation_magnitude": True,
            "force_magnitude": False,       # deprecated
            "force_peak": False,
            "force_direction": False,
            "slip_entropy": False,
            "slip_event": False,
            "texture_energy": False,
            "edge_density": False,
            "contact_area": True,
            "centroid_x": True,
            "normal_field_magnitude": False,
            "normal_field_variance": False,
            "shear_field_magnitude": False,
            "shear_field_direction": False,
            "delta_force_normal": False,
            "delta_force_shear": False,
            "friction_cone_ratio": False,
            "optical_flow_magnitude": False,
            "optical_flow_direction": False,
            "temporal_deformation_rate": False,
            "contact_transition": False,
        }

    def get_sensor_info(self) -> Dict[str, Any]:
        """传感器元信息

        TODO: 填写你的传感器信息
        """
        return {
            "type": "unknown",           # vision-based_tactile / distributed_taxel_array / piezoresistive / ...
            "manufacturer": "unknown",   # 厂商名称
            "model": "unknown",          # 型号
            "modality": "unknown",       # 模态描述
        }


# =============================================================================
# 传感器适配器模板（如需实时对接 SDK，取消注释以下代码）
# =============================================================================

# class MySensorRealtimeAdapter(SensorAdapterBase):
#     """<传感器名称> 实时 SDK 适配器"""
#
#     def __init__(self):
#         self._device = None
#         self._connected = False
#
#     @property
#     def name(self) -> str:
#         return "my_sensor_realtime"
#
#     def connect(self, device_id: str = "auto", **kwargs) -> bool:
#         # TODO: 实现连接逻辑
#         self._connected = True
#         return True
#
#     def disconnect(self) -> None:
#         # TODO: 实现断开逻辑
#         self._connected = False
#
#     def is_connected(self) -> bool:
#         return self._connected
#
#     def stream_frames(self, num_frames: int = -1, **kwargs) -> Iterator[TLabelFrame]:
#         # TODO: 实现实时数据流
#         frame_idx = 0
#         max_frames = num_frames if num_frames > 0 else float('inf')
#         while frame_idx < max_frames:
#             # raw_data = self._device.read()
#             # tlabel_v2 = self._convert(raw_data)
#             # yield TLabelFrame(...)
#             frame_idx += 1
#
#     def load(self, file_path: str, trajectory_id=None, **kwargs) -> TLabelData:
#         # 可选：支持录制文件回放
#         ...
#
#     def get_capabilities(self) -> Dict[str, bool]:
#         # 同 DataAdapterBase
#         ...
#
#     def get_sensor_info(self) -> Dict[str, Any]:
#         # 同 DataAdapterBase
#         ...
