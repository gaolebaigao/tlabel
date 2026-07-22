"""
适配器抽象基类 — v0.16.0 架构分离

两个基类：
- DataAdapterBase: 数据集适配器，解析离线数据文件
- SensorAdapterBase: 传感器适配器，通过SDK实时读取传感器数据

v0.15及之前版本使用统一的BaseAdapter，v0.16起拆分为两个专用基类，
为第三方贡献机制提供更清晰的接口契约。
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Iterator, List

from tlabel.core.types import TLabelData, TLabelFrame


# =============================================================================
# DataAdapterBase — 数据集适配器基类
# =============================================================================

class DataAdapterBase(ABC):
    """数据集适配器基类 — 用于解析离线数据文件

    适用于：公开数据集、本地存储的传感器数据文件
    特点：不需要传感器硬件，只需要数据文件即可工作

    实现步骤：
    1. 继承DataAdapterBase
    2. 实现name、supported_extensions、load()、get_capabilities()、get_sensor_info()
    3. 在load()中将原始数据转换为TLabelData（22维tlabel_v2格式）
    4. 使用@register_adapter注册到适配器表
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """适配器名称（唯一标识符，小写+下划线）"""
        pass

    @property
    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """支持的文件扩展名列表，如['.h5', '.pkl']"""
        pass

    @abstractmethod
    def load(self, file_path: str,
             trajectory_id: Optional[int] = None,
             **kwargs) -> TLabelData:
        """
        加载数据文件，转换为TLabelData

        参数:
            file_path: 数据文件路径
            trajectory_id: 轨迹ID（可选，用于多轨迹数据集）
            **kwargs: 适配器特有参数

        返回:
            TLabelData — 统一标注容器，包含22维tlabel_v2特征
        """
        pass

    @abstractmethod
    def get_capabilities(self) -> Dict[str, bool]:
        """返回该数据源的22维能力声明

        返回格式示例:
            {
                "contact": True,
                "deformation_magnitude": True,
                "force_magnitude": False,
                ...
            }
        """
        pass

    @abstractmethod
    def get_sensor_info(self) -> Dict[str, Any]:
        """返回数据源元信息

        返回格式示例:
            {
                "type": "vision-based_tactile",
                "manufacturer": "gelsight",
                "model": "GelSight Mini",
                "dataset_name": "example_dataset",
                ...
            }
        """
        pass


# =============================================================================
# SensorAdapterBase — 传感器适配器基类
# =============================================================================

class SensorAdapterBase(ABC):
    """传感器适配器基类 — 用于实时对接传感器SDK

    适用于：通过SDK/硬件接口实时读取传感器数据
    特点：需要传感器硬件 + 厂商SDK，支持实时数据流

    实现步骤：
    1. 继承SensorAdapterBase
    2. 实现name、supported_extensions、load()、get_capabilities()、get_sensor_info()
    3. 实现connect()、stream_frames()、disconnect()实时数据流接口
    4. 使用@register_adapter注册到适配器表

    注意：传感器适配器需要额外的依赖（厂商SDK），建议在pyproject.toml中
    使用optional dependencies声明，如：tlabel[sensor-paxini]
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """适配器名称（唯一标识符，小写+下划线）"""
        pass

    @property
    def supported_extensions(self) -> List[str]:
        """支持的文件扩展名列表（传感器适配器通常为空或特定录制格式）

        对于实时传感器，这个方法返回录制文件的格式（如.avi, .bag），
        用于支持"先录制后处理"的工作流。
        """
        return []

    @abstractmethod
    def load(self, file_path: str,
             trajectory_id: Optional[int] = None,
             **kwargs) -> TLabelData:
        """
        加载数据文件，转换为TLabelData

        对于传感器适配器，这个方法用于处理录制好的数据文件。
        实时采集请使用stream_frames()接口。

        参数:
            file_path: 数据文件路径
            trajectory_id: 轨迹ID（可选）
            **kwargs: 适配器特有参数

        返回:
            TLabelData — 统一标注容器
        """
        pass

    @abstractmethod
    def get_capabilities(self) -> Dict[str, bool]:
        """返回该传感器的22维能力声明"""
        pass

    @abstractmethod
    def get_sensor_info(self) -> Dict[str, Any]:
        """返回传感器元信息"""
        pass

    # ─── 实时数据流接口（SensorAdapterBase特有）────────────────────────────

    @abstractmethod
    def connect(self, device_id: str = "auto", **kwargs) -> bool:
        """
        连接到传感器

        参数:
            device_id: 设备标识符
                - "auto": 自动检测第一个可用设备
                - 数字字符串: 设备索引（如"0"表示/dev/video0）
                - 序列号: 设备序列号
            **kwargs: 传感器特有的连接参数
                - 采样率、分辨率、通信协议等

        返回:
            bool — 连接是否成功

        异常:
            ConnectionError: 连接失败时抛出
            ImportError: 缺少SDK依赖时抛出
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """
        断开传感器连接，释放资源

        必须确保：
        - 设备句柄正确关闭
        - 内存/文件句柄释放
        - 可安全再次调用connect()
        """
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """
        检查当前连接状态

        返回:
            bool — 是否已连接到传感器
        """
        pass

    @abstractmethod
    def stream_frames(self, num_frames: int = -1,
                      **kwargs) -> Iterator[TLabelFrame]:
        """
        实时数据流生成器

        参数:
            num_frames: 采集帧数，-1表示无限采集直到手动停止
            **kwargs: 采集参数
                - timeout_ms: 单帧超时时间
                - skip_frames: 跳帧数（降采样）

        返回:
            Iterator[TLabelFrame] — 逐帧产出TLabelFrame

        用法示例:
            adapter.connect("auto")
            for frame in adapter.stream_frames(num_frames=100):
                process(frame)
            adapter.disconnect()
        """
        pass

    def collect(self, num_frames: int, **kwargs) -> TLabelData:
        """
        便捷方法：采集指定帧数并返回TLabelData

        参数:
            num_frames: 采集帧数
            **kwargs: 传递给stream_frames()的参数

        返回:
            TLabelData — 包含所有采集帧的统一标注容器

        异常:
            RuntimeError: 未连接时调用
        """
        if not self.is_connected():
            raise RuntimeError(
                f"传感器 {self.name} 未连接，请先调用 connect()"
            )

        frames: List[TLabelFrame] = []
        for frame in self.stream_frames(num_frames=num_frames, **kwargs):
            frames.append(frame)

        # 组装为TLabelData
        from tlabel.core.types import TLabelData
        return TLabelData(
            sensor_name=self.name,
            frames=frames,
            metadata=self.get_sensor_info(),
        )


# =============================================================================
# 向后兼容：BaseAdapter 作为 DataAdapterBase 的别名
# =============================================================================

# v0.15及之前版本使用BaseAdapter，v0.16起拆分为DataAdapterBase和SensorAdapterBase
# 为保持向后兼容，BaseAdapter作为DataAdapterBase的别名
BaseAdapter = DataAdapterBase
