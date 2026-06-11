"""
适配器抽象基类 — 所有传感器适配器的统一接口

适配器的职责：在load阶段消化格式差异，输出统一的TLabelData。
review阶段全是TLabel格式，交互完全统一。
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

from tlabel.core.types import TLabelData, TLabelFrame


class BaseAdapter(ABC):
    """传感器适配器基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """适配器名称"""
        pass

    @property
    @abstractmethod
    def supported_extensions(self) -> list:
        """支持的文件扩展名"""
        pass

    @abstractmethod
    def load(self, file_path: str,
             trajectory_id: Optional[int] = None,
             **kwargs) -> TLabelData:
        """
        加载数据文件，转换为TLabelData
        
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
