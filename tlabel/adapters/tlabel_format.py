"""
TLabel Format 适配器

用于直接加载 TLabel Format v2 JSON 文件，绕过原始传感器格式转换。
"""

import json
from pathlib import Path
from typing import Optional, Union, Dict, List

from tlabel.adapters.base import BaseAdapter
from tlabel.core.types import TLabelData, TLabelFrame


class TLabelAdapter(BaseAdapter):
    """TLabel Format JSON 适配器"""

    @property
    def name(self) -> str:
        return "tlabel"
    
    @property
    def supported_extensions(self) -> List[str]:
        return [".json"]
    
    def get_sensor_info(self, file_path: Union[str, Path]) -> Dict:
        """获取传感器信息"""
        path = Path(file_path)
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return raw.get("sensor", {})
    
    def get_capabilities(self, file_path: Union[str, Path]) -> Dict:
        """获取能力信息"""
        path = Path(file_path)
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return raw.get("capabilities", {})

    def load(self, file_path: Union[str, Path], **kwargs) -> TLabelData:
        """
        从 TLabel Format JSON 文件加载数据
        
        参数:
            file_path: JSON 文件路径
            **kwargs: 额外参数（未使用）
        
        返回:
            TLabelData 对象
        """
        path = Path(file_path)
        
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        
        # 解析 frames
        frames = []
        for fd in raw.get("frames", []):
            frame = TLabelFrame(
                frame_idx=fd["frame_idx"],
                timestamp_s=fd["timestamp_s"],
                tlabel_v2=fd["tlabel_v2"],
                manipulation_phase=fd.get("manipulation_phase", "idle"),
                confidence=fd.get("confidence", 1.0),
                sensor_specific=fd.get("sensor_specific"),
            )
            frames.append(frame)
        
        # 构建 TLabelData
        data = TLabelData(
            frames=frames,
            sensor_info=raw.get("sensor", {}),
            episode_info=raw.get("episode", {}),
            capabilities=raw.get("capabilities", {}),
            schema_version=raw.get("schema_version", "0.4.0"),
        )
        
        # v0.13: 加载 primitive_annotations（向后兼容：旧JSON没有此字段也能正常加载）
        if "primitive_annotations" in raw:
            from tlabel.core.primitive import PrimitiveAnnotation
            for pa_dict in raw["primitive_annotations"]:
                try:
                    pa = PrimitiveAnnotation(
                        name=pa_dict["primitive_name"],
                        start=pa_dict["start_frame"],
                        end=pa_dict["end_frame"],
                        confidence=pa_dict.get("confidence", 1.0),
                        source=pa_dict.get("source", "manual"),
                    )
                    data.primitive_annotations.append(pa)
                except (ValueError, KeyError):
                    pass
        
        return data
