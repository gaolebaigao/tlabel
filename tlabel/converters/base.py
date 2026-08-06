"""
统一格式转换器基类 — v0.19.0-dev

提供统一的 export() 接口，封装不同转换器的调用差异，
使 CLI 层无需关心底层转换器函数签名的区别。

已注册转换器:
    - ftp1:    FTP-1/MTTS Zarr 格式（触觉基础模型训练格式）
    - lerobot: LeRobot Parquet 格式（机器人学习框架）

用法:
    from tlabel.converters.base import get_converter

    converter = get_converter("ftp1")
    stats = converter.export(tlabel_data, "output.zarr")

    converter = get_converter("lerobot")
    stats = converter.export(tlabel_data, "output_dir/", adapter=adapter_instance)
"""

import json
import tempfile
from pathlib import Path
from typing import Dict, Optional, Any, Type

from tlabel.core.types import TLabelData


# =============================================================================
# BaseConverter — 统一转换器接口
# =============================================================================

class BaseConverter:
    """格式转换器基类

    子类需实现:
        - name: 转换器名称（唯一标识符）
        - description: 人类可读描述
        - export(): 将 TLabelData 导出为目标格式
        - is_available(): 检查依赖是否可用
    """

    name: str = ""
    description: str = ""
    file_extension: str = ""  # 输出文件/目录的扩展名提示

    @staticmethod
    def export(tlabel_data: TLabelData, output_path: str,
               **kwargs) -> Dict[str, Any]:
        """将 TLabelData 导出为目标格式

        参数:
            tlabel_data: TLabelData 实例（由 adapter.load() 产生）
            output_path: 输出路径
            **kwargs: 转换器特有参数

        返回:
            导出统计信息 dict
        """
        raise NotImplementedError

    @staticmethod
    def is_available() -> bool:
        """检查该转换器的依赖是否可用"""
        return True

    @staticmethod
    def required_dependencies() -> list:
        """返回所需依赖列表（用于错误提示）"""
        return []


# =============================================================================
# FTP1Converter — FTP-1/MTTS Zarr 格式
# =============================================================================

class FTP1Converter(BaseConverter):
    """FTP-1/MTTS Zarr 格式转换器

    将 TLabelData 导出为 FTP-1 兼容的 Zarr 格式，
    可直接用于 FTP-1 触觉基础模型微调或推理。

    底层调用: tlabel.converters.ftp1.tlabel_to_ftp1()
    """

    name = "ftp1"
    description = "FTP-1/MTTS Zarr format — tactile foundation model training format"
    file_extension = ".zarr"

    @staticmethod
    def export(tlabel_data: TLabelData, output_path: str,
               sensor_name: str = "GelSightMini",
               functional_areas: Optional[list] = None,
               side: str = "right",
               group: str = "gripper",
               **kwargs) -> Dict[str, Any]:
        """导出为 FTP-1 MTTS Zarr 格式

        参数:
            tlabel_data: TLabelData 实例
            output_path: 输出 .zarr 路径
            sensor_name: FTP-1 注册的传感器名
            functional_areas: 功能区 ID 列表
            side: "left" 或 "right"
            group: 组名（如 "gripper", "dexterous"）

        返回:
            导出统计 dict（包含 output_path, time_steps, data_shape 等）
        """
        from tlabel.converters.ftp1 import tlabel_to_ftp1

        return tlabel_to_ftp1(
            tlabel_data,
            output_path,
            sensor_name=sensor_name,
            functional_areas=functional_areas,
            side=side,
            group=group,
        )

    @staticmethod
    def is_available() -> bool:
        try:
            import zarr  # noqa: F401
            return True
        except ImportError:
            return False

    @staticmethod
    def required_dependencies() -> list:
        return ["zarr>=2.16"]


# =============================================================================
# LeRobotConverter — LeRobot Parquet 格式
# =============================================================================

class LeRobotConverter(BaseConverter):
    """LeRobot Parquet 格式转换器

    将 TLabelData 导出为 LeRobot 兼容的 Parquet 格式，
    包含 meta/info.json 和 data/chunk-0000.parquet 结构。

    底层调用: tlabel.converters.lerobot.tlabel_to_lerobot()
    由于该函数需要 (1) JSON 文件路径 (2) 已有 Parquet 文件，
    本转换器会自动创建最小 LeRobot 骨架再合并标注。
    """

    name = "lerobot"
    description = "LeRobot Parquet format — robot learning framework integration"
    file_extension = ""  # 输出为目录

    @staticmethod
    def export(tlabel_data: TLabelData, output_path: str,
               adapter: Optional[object] = None,
               tactile_field: str = "observation.tactile",
               action_dim: int = 6,
               **kwargs) -> Dict[str, Any]:
        """导出为 LeRobot Parquet 格式

        参数:
            tlabel_data: TLabelData 实例
            output_path: 输出目录路径
            adapter: 可选，适配器实例（用于自动检测图像形状）
            tactile_field: 触觉字段名
            action_dim: 占位 action 向量维度（默认 6）

        返回:
            导出统计 dict
        """
        from tlabel.converters.lerobot import tlabel_to_lerobot

        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)

        num_frames = tlabel_data.num_frames
        if num_frames == 0:
            raise ValueError("TLabelData has 0 frames — nothing to export")

        # 1. 将 TLabelData 序列化为临时 JSON（tlabel_to_lerobot 需要 JSON 路径）
        data_dict = tlabel_data.to_dict()
        # 保留 feature_names_v2 供 tlabel_to_lerobot 使用
        if "feature_names_v2" not in data_dict:
            from tlabel.core.schema import SCHEMA_V2_FIELD_NAMES
            data_dict["feature_names_v2"] = list(SCHEMA_V2_FIELD_NAMES)

        temp_json = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False, encoding="utf-8"
            ) as f:
                json.dump(data_dict, f, ensure_ascii=False)
                temp_json = f.name

            # 2. 创建最小 LeRobot 骨架（parquet + meta/info.json）
            data_dir = output_path / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            meta_dir = output_path / "meta"
            meta_dir.mkdir(parents=True, exist_ok=True)

            try:
                import pyarrow as pa
                import pyarrow.parquet as pq
                import pandas as pd
            except ImportError as e:
                raise ImportError(
                    f"LeRobot export requires pyarrow. Install with: pip install pyarrow\n{e}"
                )

            # 创建占位 DataFrame（frame_index + action）
            df = pd.DataFrame({
                "frame_index": list(range(num_frames)),
                "action": [[0.0] * action_dim for _ in range(num_frames)],
            })
            table = pa.Table.from_pandas(df)
            pq.write_table(table, data_dir / "chunk-0000.parquet")

            # 创建最小 meta/info.json
            meta_info = {
                "codebase_version": "v2.0",
                "robot_type": "unknown",
                "total_episodes": 1,
                "total_frames": num_frames,
                "fps": 30,
                "features": {
                    "action": {
                        "dtype": "float32",
                        "shape": [action_dim],
                        "type": "vector",
                        "names": None,
                    },
                    "frame_index": {
                        "dtype": "int64",
                        "shape": [1],
                        "type": "int",
                    },
                },
            }
            with open(meta_dir / "info.json", "w", encoding="utf-8") as f:
                json.dump(meta_info, f, indent=2)

            # 3. 调用 tlabel_to_lerobot 合并触觉标注
            tlabel_to_lerobot(
                temp_json,
                str(output_path),
                tactile_field=tactile_field,
                adapter=adapter,
            )

            return {
                "output_path": str(output_path),
                "frames": num_frames,
                "format": "lerobot",
                "tactile_field": tactile_field,
            }

        finally:
            if temp_json:
                Path(temp_json).unlink(missing_ok=True)

    @staticmethod
    def is_available() -> bool:
        try:
            import pyarrow  # noqa: F401
            return True
        except ImportError:
            return False

    @staticmethod
    def required_dependencies() -> list:
        return ["pyarrow>=10.0"]


# =============================================================================
# 转换器注册表
# =============================================================================

CONVERTERS: Dict[str, Type[BaseConverter]] = {
    "ftp1": FTP1Converter,
    "lerobot": LeRobotConverter,
}


def get_converter(name: str) -> Optional[Type[BaseConverter]]:
    """获取转换器类

    参数:
        name: 转换器名称（"ftp1" 或 "lerobot"）

    返回:
        转换器类，或 None
    """
    return CONVERTERS.get(name)


def list_converters() -> Dict[str, Type[BaseConverter]]:
    """列出所有已注册的转换器"""
    return dict(CONVERTERS)


def list_available_converters() -> Dict[str, Type[BaseConverter]]:
    """列出所有依赖可用的转换器"""
    return {k: v for k, v in CONVERTERS.items() if v.is_available()}
