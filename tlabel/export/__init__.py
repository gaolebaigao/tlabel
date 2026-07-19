"""
TLabel 导出模块

提供两种使用方式：

1. 简单导出（向后兼容）:
    from tlabel.export import export_data
    export_data(data, "output.json")

2. 插件注册表（推荐）:
    from tlabel.export import get_registry
    registry = get_registry()
    for fmt in registry.list_formats():
        print(fmt.name, fmt.fields)
    result = registry.export("ftp1", data, "output.zarr", sensor_name="GelSightMini")
"""

from tlabel.export.writer import export_data
from tlabel.export.registry import (
    FieldType,
    ExportField,
    ExporterSpec,
    ExporterResult,
    ExporterBase,
    ExporterRegistry,
    get_registry,
)

__all__ = [
    # legacy
    "export_data",
    # registry API
    "FieldType",
    "ExportField",
    "ExporterSpec",
    "ExporterResult",
    "ExporterBase",
    "ExporterRegistry",
    "get_registry",
]
