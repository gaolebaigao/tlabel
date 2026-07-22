"""
TLabel CLI — 命令行工具

提供以下命令:
  tlabel validate <path>    校验数据文件是否符合 tlabel_v2 schema
  tlabel list               列出所有已注册的适配器
  tlabel info <adapter>     查看适配器详细信息
  tlabel version            显示版本号

v0.16.0 新增: validate 命令支持 22 维 tlabel_v2 特征空间校验
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Optional, List, Dict, Any


# 22 维 tlabel_v2 特征空间完整列表
TLABEL_V2_DIMENSIONS = [
    "contact",
    "deformation_magnitude",
    "force_magnitude",  # deprecated, alias of deformation_magnitude
    "force_peak",
    "force_direction",
    "slip_entropy",
    "slip_event",
    "texture_energy",
    "edge_density",
    "contact_area",
    "centroid_x",
    "normal_field_magnitude",
    "normal_field_variance",
    "shear_field_magnitude",
    "shear_field_direction",
    "delta_force_normal",
    "delta_force_shear",
    "friction_cone_ratio",
    "optical_flow_magnitude",
    "optical_flow_direction",
    "temporal_deformation_rate",
    "contact_transition",
]


class ValidationResult:
    """单条校验结果"""
    def __init__(self, level: str, message: str, field: str = ""):
        self.level = level  # "error", "warning", "info"
        self.message = message
        self.field = field

    def __repr__(self):
        prefix = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}.get(self.level, "?")
        field_str = f" [{self.field}]" if self.field else ""
        return f"{prefix}{field_str} {self.message}"


def validate_tlabel_file(file_path: str) -> List[ValidationResult]:
    """校验单个文件是否符合 tlabel_v2 schema"""
    results = []
    path = Path(file_path)

    if not path.exists():
        results.append(ValidationResult("error", f"文件不存在: {file_path}"))
        return results

    # 1. 尝试作为 JSON 格式校验
    if path.suffix == ".json":
        results.extend(_validate_json_file(path))
    elif path.suffix in (".h5", ".hdf5"):
        results.extend(_validate_hdf5_file(path))
    elif path.suffix == ".parquet":
        results.extend(_validate_parquet_file(path))
    elif path.is_dir():
        results.extend(_validate_directory(path))
    else:
        results.append(ValidationResult("warning",
            f"不支持的文件格式: {path.suffix}，尝试自动检测..."))
        results.extend(_validate_auto_detect(path))

    return results


def _validate_json_file(path: Path) -> List[ValidationResult]:
    """校验 JSON 格式的 tlabel 文件"""
    results = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        results.append(ValidationResult("error", f"JSON 解析失败: {e}"))
        return results

    # 检查顶层字段
    if "schema_version" not in data:
        results.append(ValidationResult("error", "缺少 schema_version 字段", "schema_version"))
    else:
        sv = data["schema_version"]
        if not isinstance(sv, str) or not sv.replace(".", "").replace("-", "").isalnum():
            results.append(ValidationResult("error", f"schema_version 格式异常: {sv}", "schema_version"))

    if "format" not in data:
        results.append(ValidationResult("error", "缺少 format 字段", "format"))
    elif data["format"] != "tlabel_v2":
        results.append(ValidationResult("warning",
            f"format 为 '{data['format']}'，预期 'tlabel_v2'", "format"))

    # 检查 frames
    if "frames" not in data:
        results.append(ValidationResult("error", "缺少 frames 字段", "frames"))
    elif not isinstance(data["frames"], list):
        results.append(ValidationResult("error", "frames 应为数组", "frames"))
    else:
        frames = data["frames"]
        results.append(ValidationResult("info", f"共 {len(frames)} 帧"))

        if len(frames) == 0:
            results.append(ValidationResult("warning", "frames 为空数组", "frames"))
        else:
            # 校验第一帧的 tlabel_v2 维度
            frame0 = frames[0]
            if "tlabel_v2" not in frame0:
                results.append(ValidationResult("error", "帧缺少 tlabel_v2 字段", "frames[0].tlabel_v2"))
            else:
                results.extend(_validate_tlabel_v2_dict(frame0["tlabel_v2"], "frames[0]"))

            # 抽样校验（最多检查 10 帧）
            sample_indices = [0]
            if len(frames) > 10:
                step = max(1, len(frames) // 10)
                sample_indices = list(range(0, len(frames), step))
            
            error_count = 0
            for idx in sample_indices[1:]:
                frame = frames[idx]
                if "tlabel_v2" not in frame:
                    error_count += 1
                    continue
                errs = _validate_tlabel_v2_dict(frame["tlabel_v2"], f"frames[{idx}]")
                error_count += sum(1 for e in errs if e.level == "error")
            
            if error_count > 0:
                results.append(ValidationResult("warning",
                    f"抽样 {len(sample_indices)} 帧中有 {error_count} 帧存在维度错误"))

    # 检查 capabilities（可选但推荐）
    if "capabilities" in data:
        caps = data["capabilities"]
        if isinstance(caps, dict):
            found_dims = sum(1 for d in TLABEL_V2_DIMENSIONS if caps.get(d, False))
            results.append(ValidationResult("info",
                f"capabilities 声明 {found_dims}/22 维特征"))

    # 检查 sensor 信息
    if "sensor" not in data:
        results.append(ValidationResult("warning", "缺少 sensor 字段（推荐提供）", "sensor"))

    return results


def _validate_tlabel_v2_dict(tlabel_v2: Dict, prefix: str) -> List[ValidationResult]:
    """校验单个 tlabel_v2 字典的维度完整性"""
    results = []
    
    if not isinstance(tlabel_v2, dict):
        results.append(ValidationResult("error", f"{prefix}.tlabel_v2 不是字典", f"{prefix}.tlabel_v2"))
        return results

    # 检查核心维度是否存在
    core_dims = ["contact", "deformation_magnitude"]
    for dim in core_dims:
        if dim not in tlabel_v2:
            results.append(ValidationResult("error",
                f"缺少核心维度 '{dim}'", f"{prefix}.tlabel_v2.{dim}"))

    # 检查维度值类型
    for key, value in tlabel_v2.items():
        if key in TLABEL_V2_DIMENSIONS or key.startswith(tuple(TLABEL_V2_DIMENSIONS)):
            if value is not None and not isinstance(value, (int, float)):
                results.append(ValidationResult("warning",
                    f"维度 '{key}' 值类型异常: {type(value).__name__}（应为 float）",
                    f"{prefix}.tlabel_v2.{key}"))

    # 统计覆盖维度数
    covered = sum(1 for d in TLABEL_V2_DIMENSIONS if d in tlabel_v2)
    total = len(TLABEL_V2_DIMENSIONS)
    if covered < total:
        missing = [d for d in TLABEL_V2_DIMENSIONS if d not in tlabel_v2]
        results.append(ValidationResult("info",
            f"覆盖 {covered}/{total} 维，缺少: {', '.join(missing[:5])}{'...' if len(missing) > 5 else ''}",
            f"{prefix}.tlabel_v2"))

    return results


def _validate_hdf5_file(path: Path) -> List[ValidationResult]:
    """校验 HDF5 格式文件"""
    results = []
    try:
        import h5py
        with h5py.File(path, "r") as f:
            results.append(ValidationResult("info", f"HDF5 文件，顶层 keys: {list(f.keys())}"))
            
            # 检查是否有 tactile 数据组
            if "tactile" in f:
                tactile_keys = list(f["tactile"].keys())
                results.append(ValidationResult("info", f"tactile 组包含 {len(tactile_keys)} 个数据通道"))
            else:
                results.append(ValidationResult("warning", "未找到 'tactile' 数据组"))
    except ImportError:
        results.append(ValidationResult("error", "需要安装 h5py: pip install h5py"))
    except Exception as e:
        results.append(ValidationResult("error", f"HDF5 读取失败: {e}"))
    return results


def _validate_parquet_file(path: Path) -> List[ValidationResult]:
    """校验 Parquet 格式文件"""
    results = []
    try:
        import pyarrow.parquet as pq
        table = pq.read_table(path)
        results.append(ValidationResult("info", f"Parquet 文件，{table.num_rows} 行 × {table.num_columns} 列"))
        results.append(ValidationResult("info", f"列名: {table.column_names[:10]}{'...' if len(table.column_names) > 10 else ''}"))
    except ImportError:
        results.append(ValidationResult("error", "需要安装 pyarrow: pip install pyarrow"))
    except Exception as e:
        results.append(ValidationResult("error", f"Parquet 读取失败: {e}"))
    return results


def _validate_directory(path: Path) -> List[ValidationResult]:
    """校验目录格式"""
    results = []
    files = list(path.iterdir())
    results.append(ValidationResult("info", f"目录包含 {len(files)} 个文件/子目录"))
    
    # 尝试自动检测格式
    from tlabel.core.registry import auto_detect_format
    fmt = auto_detect_format(str(path))
    if fmt:
        results.append(ValidationResult("info", f"自动检测到格式: {fmt}"))
    else:
        results.append(ValidationResult("warning", "无法自动检测数据格式"))

    # 检查常见的元数据文件
    meta_files = ["meta/info.json", "README.md", "info.json"]
    for mf in meta_files:
        if (path / mf).exists():
            results.append(ValidationResult("info", f"找到元数据: {mf}"))

    return results


def _validate_auto_detect(path: Path) -> List[ValidationResult]:
    """尝试用 tlabel loader 加载并校验"""
    results = []
    try:
        from tlabel.core.loader import load
        data = load(str(path))
        if data and hasattr(data, "frames"):
            results.append(ValidationResult("info", f"成功加载，共 {len(data.frames)} 帧"))
            if data.frames:
                frame0 = data.frames[0]
                if hasattr(frame0, "tlabel_v2"):
                    results.extend(_validate_tlabel_v2_dict(frame0.tlabel_v2, "frame[0]"))
        else:
            results.append(ValidationResult("warning", "加载成功但数据为空"))
    except Exception as e:
        results.append(ValidationResult("error", f"加载失败: {e}"))
    return results


def cmd_validate(args):
    """执行 validate 子命令"""
    path = args.path
    print(f"🔍 校验中: {path}")
    print("=" * 60)

    results = validate_tlabel_file(path)

    # 统计
    errors = [r for r in results if r.level == "error"]
    warnings = [r for r in results if r.level == "warning"]
    infos = [r for r in results if r.level == "info"]

    # 输出结果
    for r in results:
        print(r)

    print("=" * 60)
    print(f"结果: {len(errors)} 错误, {len(warnings)} 警告, {len(infos)} 信息")

    if errors:
        print("\n❌ 校验未通过")
        return 1
    elif warnings:
        print("\n⚠️ 校验通过（有警告）")
        return 0
    else:
        print("\n✅ 校验通过")
        return 0


def cmd_list(args):
    """执行 list 子命令"""
    from tlabel.core.registry import list_adapters, list_builtin_adapters, list_external_adapters, _ensure_adapters
    
    # 触发懒加载
    _ensure_adapters()

    builtin = list_builtin_adapters()
    external = list_external_adapters()

    print("📦 TLabel 已注册适配器")
    print("=" * 60)

    if builtin:
        print(f"\n内置适配器 ({len(builtin)}):")
        for name, cls in sorted(builtin.items()):
            # 判断类型
            from tlabel.adapters.base import SensorAdapterBase
            adapter_type = "🔌 传感器" if issubclass(cls, SensorAdapterBase) else "📁 数据集"
            doc = (cls.__doc__ or "").strip().split("\n")[0][:50]
            print(f"  {adapter_type} {name:20s} {doc}")

    if external:
        print(f"\n社区适配器 ({len(external)}):")
        for name, cls in sorted(external.items()):
            doc = (cls.__doc__ or "").strip().split("\n")[0][:50]
            print(f"  🌐 {name:20s} {doc}")
    else:
        print("\n社区适配器: 暂无（欢迎贡献！详见 CONTRIBUTING.md）")

    print(f"\n总计: {len(builtin) + len(external)} 个适配器")
    return 0


def cmd_info(args):
    """执行 info 子命令"""
    from tlabel.core.registry import get_adapter, _ensure_adapters

    _ensure_adapters()
    adapter_cls = get_adapter(args.name)
    if adapter_cls is None:
        print(f"❌ 未找到适配器: {args.name}")
        print("使用 'tlabel list' 查看所有可用适配器")
        return 1

    try:
        adapter = adapter_cls()
        info = {
            "名称": adapter.name,
            "类型": adapter_cls.__bases__[0].__name__,
            "支持格式": adapter.supported_extensions,
        }
        
        try:
            caps = adapter.get_capabilities()
            active_dims = [k for k, v in caps.items() if v and k in TLABEL_V2_DIMENSIONS]
            info["活跃维度"] = f"{len(active_dims)}/22"
        except Exception:
            pass

        try:
            sensor_info = adapter.get_sensor_info()
            info["传感器类型"] = sensor_info.get("type", "unknown")
            info["制造商"] = sensor_info.get("manufacturer", "unknown")
        except Exception:
            pass

        print(f"📋 适配器详情: {args.name}")
        print("=" * 40)
        for k, v in info.items():
            print(f"  {k}: {v}")

    except Exception as e:
        print(f"⚠️ 无法实例化适配器: {e}")
        print(f"  类名: {adapter_cls.__name__}")
        print(f"  模块: {adapter_cls.__module__}")

    return 0


def cmd_version(args):
    """执行 version 子命令"""
    from tlabel._version import __version__
    print(f"tlabel {__version__}")
    return 0


def main():
    parser = argparse.ArgumentParser(
        prog="tlabel",
        description="TLabel — 触觉数据标注工具包 CLI",
    )
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # validate
    p_validate = subparsers.add_parser("validate", help="校验数据文件是否符合 tlabel_v2 schema")
    p_validate.add_argument("path", help="数据文件或目录路径")
    p_validate.set_defaults(func=cmd_validate)

    # list
    p_list = subparsers.add_parser("list", help="列出所有已注册的适配器")
    p_list.set_defaults(func=cmd_list)

    # info
    p_info = subparsers.add_parser("info", help="查看适配器详细信息")
    p_info.add_argument("name", help="适配器名称")
    p_info.set_defaults(func=cmd_info)

    # version
    p_version = subparsers.add_parser("version", help="显示版本号")
    p_version.set_defaults(func=cmd_version)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main() or 0)
