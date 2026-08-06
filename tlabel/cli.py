"""
TLabel CLI — 命令行工具

提供以下命令:
  tlabel validate <path>           校验数据文件是否符合 tlabel_v2 schema
  tlabel list                      列出所有已注册的适配器
  tlabel info <adapter>            查看适配器详细信息
  tlabel version                   显示版本号
  tlabel convert                   单文件格式转换（adapter → target format）
  tlabel batch-convert             批量目录格式转换
  tlabel list-adapters             列出所有适配器（含类型/格式/描述）
  tlabel adapter-info <name>       查看适配器详情（字段映射/合规等级）

v0.17.0 更新: validate 命令支持 14 维 Schema V2 校验，向后兼容 22 维旧格式
v0.19.0-dev: 新增 convert / batch-convert / list-adapters / adapter-info 命令
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Optional, List, Dict, Any

from tlabel.core.schema import SCHEMA_V2_FIELD_NAMES


# 14 维 Schema V2 特征空间字段列表
SCHEMA_V2_DIMENSIONS = list(SCHEMA_V2_FIELD_NAMES)

# 旧 22 维 tlabel_v2 特征空间（向后兼容）
LEGACY_V2_DIMENSIONS = [
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

# 保持旧名兼容
TLABEL_V2_DIMENSIONS = LEGACY_V2_DIMENSIONS


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
            # 校验第一帧的维度数据
            frame0 = frames[0]
            if "schema_v2" in frame0:
                # v0.17+: Schema V2 格式（14维）
                results.extend(_validate_schema_v2_dict(frame0["schema_v2"], "frames[0]"))
            elif "tlabel_v2" in frame0:
                # 旧格式（22维），向后兼容
                results.extend(_validate_tlabel_v2_dict(frame0["tlabel_v2"], "frames[0]"))
            else:
                results.append(ValidationResult("error", "帧缺少 schema_v2 或 tlabel_v2 字段", "frames[0]"))

            # 抽样校验（最多检查 10 帧）
            sample_indices = [0]
            if len(frames) > 10:
                step = max(1, len(frames) // 10)
                sample_indices = list(range(0, len(frames), step))
            
            error_count = 0
            for idx in sample_indices[1:]:
                frame = frames[idx]
                if "schema_v2" in frame:
                    errs = _validate_schema_v2_dict(frame["schema_v2"], f"frames[{idx}]")
                elif "tlabel_v2" in frame:
                    errs = _validate_tlabel_v2_dict(frame["tlabel_v2"], f"frames[{idx}]")
                else:
                    error_count += 1
                    continue
                error_count += sum(1 for e in errs if e.level == "error")
            
            if error_count > 0:
                results.append(ValidationResult("warning",
                    f"抽样 {len(sample_indices)} 帧中有 {error_count} 帧存在维度错误"))

    # 检查 capabilities（可选但推荐）
    if "capabilities" in data:
        caps = data["capabilities"]
        if isinstance(caps, dict):
            # v0.17: 检查 Schema V2 字段
            found_v2 = sum(1 for d in SCHEMA_V2_DIMENSIONS if caps.get(d, False))
            # 旧 22 维字段兼容检查
            found_legacy = sum(1 for d in LEGACY_V2_DIMENSIONS if caps.get(d, False))
            if found_v2 > 0:
                results.append(ValidationResult("info",
                    f"capabilities 声明 {found_v2}/14 维 (Schema V2)"))
            if found_legacy > 0:
                results.append(ValidationResult("info",
                    f"capabilities 旧字段声明 {found_legacy}/22 维 (legacy)"))

    # 检查 sensor 信息
    if "sensor" not in data:
        results.append(ValidationResult("warning", "缺少 sensor 字段（推荐提供）", "sensor"))

    return results


def _validate_tlabel_v2_dict(tlabel_v2: Dict, prefix: str) -> List[ValidationResult]:
    """
    校验单个 tlabel_v2 字典的维度完整性（旧 22 维格式）。
    
    自动检测：如果 dict 包含 Schema V2 特征字段（如 contact_centroid, compliance_level），
    则使用 14 维 Schema V2 校验；否则使用旧 22 维校验。
    """
    results = []
    
    if not isinstance(tlabel_v2, dict):
        results.append(ValidationResult("error", f"{prefix} 不是字典", f"{prefix}"))
        return results

    # 自动检测 Schema 版本
    v2_indicators = ["contact_centroid", "contact_region", "compliance_level",
                     "force_vector", "torque_vector", "slip_velocity",
                     "manipulation_phase", "texture_class", "object_deformation", "temperature"]
    is_schema_v2 = any(k in tlabel_v2 for k in v2_indicators)

    if is_schema_v2:
        return _validate_schema_v2_dict(tlabel_v2, prefix)

    # --- 旧 22 维校验 ---
    # 检查核心维度是否存在
    core_dims = ["contact", "deformation_magnitude"]
    for dim in core_dims:
        if dim not in tlabel_v2:
            results.append(ValidationResult("error",
                f"缺少核心维度 '{dim}'", f"{prefix}.{dim}"))

    # 检查维度值类型
    for key, value in tlabel_v2.items():
        if key in LEGACY_V2_DIMENSIONS or key.startswith(tuple(LEGACY_V2_DIMENSIONS)):
            if value is not None and not isinstance(value, (int, float)):
                results.append(ValidationResult("warning",
                    f"维度 '{key}' 值类型异常: {type(value).__name__}（应为 float）",
                    f"{prefix}.{key}"))

    # 统计覆盖维度数
    covered = sum(1 for d in LEGACY_V2_DIMENSIONS if d in tlabel_v2)
    total = len(LEGACY_V2_DIMENSIONS)
    if covered < total:
        missing = [d for d in LEGACY_V2_DIMENSIONS if d not in tlabel_v2]
        results.append(ValidationResult("info",
            f"覆盖 {covered}/{total} 维 (legacy)，缺少: {', '.join(missing[:5])}{'...' if len(missing) > 5 else ''}",
            f"{prefix}"))

    return results


def _validate_schema_v2_dict(schema_v2: Dict, prefix: str) -> List[ValidationResult]:
    """校验 Schema V2 (14维) 字典的完整性和类型合法性"""
    results = []

    if not isinstance(schema_v2, dict):
        results.append(ValidationResult("error", f"{prefix} 不是字典", f"{prefix}"))
        return results

    # 必填字段检查
    required_fields = ["contact", "confidence", "compliance_level"]
    for field in required_fields:
        if field not in schema_v2:
            results.append(ValidationResult("error",
                f"缺少必填字段 '{field}'", f"{prefix}.{field}"))

    # contact 类型检查（Schema V2 中应为 bool 或 0/1）
    if "contact" in schema_v2:
        val = schema_v2["contact"]
        if val is not None and not isinstance(val, (bool, int, float)):
            results.append(ValidationResult("warning",
                f"contact 值类型异常: {type(val).__name__}（应为 bool/float）",
                f"{prefix}.contact"))

    # compliance_level 枚举检查
    if "compliance_level" in schema_v2:
        valid_levels = ("L1", "L2", "L3", "L4")
        if schema_v2["compliance_level"] not in valid_levels:
            results.append(ValidationResult("error",
                f"compliance_level 值 '{schema_v2['compliance_level']}' 不合法，应为 {valid_levels}",
                f"{prefix}.compliance_level"))

    # confidence 范围检查
    if "confidence" in schema_v2:
        conf = schema_v2["confidence"]
        if isinstance(conf, (int, float)) and not (0.0 <= conf <= 1.0):
            results.append(ValidationResult("warning",
                f"confidence 超出范围: {conf}（应为 0.0-1.0）",
                f"{prefix}.confidence"))

    # 向量维度检查
    vector_specs = {
        "contact_centroid": 2,
        "force_vector": 3,
        "torque_vector": 3,
        "slip_velocity": 2,
    }
    for vec_field, expected_len in vector_specs.items():
        if vec_field in schema_v2 and schema_v2[vec_field] is not None:
            vec = schema_v2[vec_field]
            if isinstance(vec, list) and len(vec) != expected_len:
                results.append(ValidationResult("warning",
                    f"{vec_field} 维度异常: {len(vec)}（应为 {expected_len}）",
                    f"{prefix}.{vec_field}"))

    # 枚举字段检查
    from tlabel.core.schema import (
        VALID_CONTACT_REGIONS, VALID_MANIPULATION_PHASES,
        VALID_TEXTURE_CLASSES, VALID_COMPLIANCE_LEVELS,
    )
    enum_specs = {
        "contact_region": VALID_CONTACT_REGIONS,
        "manipulation_phase": VALID_MANIPULATION_PHASES,
        "texture_class": VALID_TEXTURE_CLASSES,
    }
    for enum_field, valid_vals in enum_specs.items():
        if enum_field in schema_v2 and schema_v2[enum_field] is not None:
            if schema_v2[enum_field] not in valid_vals:
                results.append(ValidationResult("warning",
                    f"{enum_field} 值 '{schema_v2[enum_field]}' 不合法",
                    f"{prefix}.{enum_field}"))

    # 统计覆盖维度数
    covered = sum(1 for d in SCHEMA_V2_DIMENSIONS if d in schema_v2)
    total = len(SCHEMA_V2_DIMENSIONS)
    if covered < total:
        missing = [d for d in SCHEMA_V2_DIMENSIONS if d not in schema_v2]
        results.append(ValidationResult("info",
            f"覆盖 {covered}/{total} 维 (Schema V2)，缺少: {', '.join(missing[:5])}{'...' if len(missing) > 5 else ''}",
            f"{prefix}"))

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
                # v0.17: Schema V2 only
                if hasattr(frame0, "schema_v2") and frame0.schema_v2 is not None:
                    results.extend(_validate_schema_v2_dict(frame0.schema_v2.to_dict(), "frame[0]"))
                else:
                    results.append(ValidationResult("error", "frame[0] 缺少 schema_v2 字段", "frame[0]"))
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
            # v0.17: 支持 Schema V2 (14维) 和旧 (22维) 两种口径
            active_v2 = [k for k, v in caps.items() if v and k in SCHEMA_V2_DIMENSIONS]
            active_legacy = [k for k, v in caps.items() if v and k in LEGACY_V2_DIMENSIONS]
            if active_v2:
                info["活跃维度 (Schema V2)"] = f"{len(active_v2)}/14"
            if active_legacy:
                info["活跃维度 (legacy)"] = f"{len(active_legacy)}/22"
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


# =============================================================================
# v0.19.0-dev: 格式转换命令
# =============================================================================

# 可用于 convert/batch-convert 的数据集适配器名称
_CONVERTIBLE_ADAPTERS = [
    "gelsight", "paxini", "daimon", "tlabel",
    "touchd", "univtac", "vtouch", "ycb_slide", "tacquad",
]

# 可用于 convert/batch-convert 的目标格式
_TARGET_FORMATS = ["lerobot", "ftp1"]


def cmd_convert(args):
    """执行 convert 子命令 — 单文件格式转换

    流程: adapter.load(input) → TLabelData → converter.export(output)
    """
    from tlabel.core.registry import get_adapter, _ensure_adapters
    from tlabel.converters.base import get_converter

    _ensure_adapters()

    # 1. 验证源适配器
    adapter_cls = get_adapter(args.from_format)
    if adapter_cls is None:
        print(f"❌ 未找到适配器: {args.from_format}")
        print(f"   可用适配器: {', '.join(_CONVERTIBLE_ADAPTERS)}")
        print("   使用 'tlabel list-adapters' 查看完整列表")
        return 1

    # 2. 验证目标转换器
    converter_cls = get_converter(args.to_format)
    if converter_cls is None:
        print(f"❌ 未找到目标格式: {args.to_format}")
        print(f"   可用格式: {', '.join(_TARGET_FORMATS)}")
        return 1

    # 3. 检查转换器依赖
    if not converter_cls.is_available():
        deps = converter_cls.required_dependencies()
        print(f"❌ 目标格式 '{args.to_format}' 缺少依赖: {', '.join(deps)}")
        print(f"   安装命令: pip install {' '.join(deps)}")
        return 1

    # 4. 验证输入路径
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ 输入路径不存在: {args.input}")
        return 1

    # 5. 加载数据
    print(f"🔄 转换中: {args.from_format} → {args.to_format}")
    print(f"   输入: {args.input}")
    print(f"   输出: {args.output}")
    print("-" * 50)

    try:
        adapter = adapter_cls()
        print(f"   [1/3] 加载数据 ({adapter.name})...")
        tlabel_data = adapter.load(str(input_path))
        print(f"         ✅ 加载成功，共 {tlabel_data.num_frames} 帧")
    except ImportError as e:
        print(f"   ❌ 适配器依赖缺失: {e}")
        print(f"       请安装所需依赖后重试")
        return 1
    except FileNotFoundError as e:
        print(f"   ❌ 文件未找到: {e}")
        return 1
    except Exception as e:
        print(f"   ❌ 加载失败: {e}")
        return 1

    # 6. 转换并导出
    try:
        print(f"   [2/3] 转换为 {args.to_format} 格式...")
        # 传递适配器实例（用于 LeRobot 图像形状检测）
        stats = converter_cls.export(
            tlabel_data,
            args.output,
            adapter=adapter,
        )
        print(f"   [3/3] ✅ 导出完成")
        print("-" * 50)
        print(f"📊 转换结果:")
        for k, v in stats.items():
            print(f"   {k}: {v}")
        return 0
    except ImportError as e:
        print(f"   ❌ 转换器依赖缺失: {e}")
        return 1
    except Exception as e:
        print(f"   ❌ 转换失败: {e}")
        return 1


def cmd_batch_convert(args):
    """执行 batch-convert 子命令 — 批量目录格式转换

    遍历 input-dir，自动发现符合 adapter 格式的文件，批量转换
    """
    from tlabel.core.registry import get_adapter, _ensure_adapters
    from tlabel.converters.base import get_converter

    _ensure_adapters()

    # 1. 验证源适配器
    adapter_cls = get_adapter(args.from_format)
    if adapter_cls is None:
        print(f"❌ 未找到适配器: {args.from_format}")
        print(f"   可用适配器: {', '.join(_CONVERTIBLE_ADAPTERS)}")
        return 1

    # 2. 验证目标转换器
    converter_cls = get_converter(args.to_format)
    if converter_cls is None:
        print(f"❌ 未找到目标格式: {args.to_format}")
        print(f"   可用格式: {', '.join(_TARGET_FORMATS)}")
        return 1

    if not converter_cls.is_available():
        deps = converter_cls.required_dependencies()
        print(f"❌ 目标格式 '{args.to_format}' 缺少依赖: {', '.join(deps)}")
        print(f"   安装命令: pip install {' '.join(deps)}")
        return 1

    # 3. 验证输入/输出目录
    input_dir = Path(args.input_dir)
    if not input_dir.exists():
        print(f"❌ 输入目录不存在: {args.input_dir}")
        return 1
    if not input_dir.is_dir():
        print(f"❌ 输入路径不是目录: {args.input_dir}")
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 4. 实例化适配器，获取支持的扩展名
    try:
        adapter = adapter_cls()
    except Exception as e:
        print(f"❌ 无法实例化适配器: {e}")
        return 1

    supported_exts = adapter.supported_extensions
    if not supported_exts:
        print(f"⚠️ 适配器 '{args.from_format}' 未声明支持的文件扩展名")
        print(f"   将尝试处理目录下所有文件")
        supported_exts = [".json", ".h5", ".hdf5", ".pkl", ".npy", ".parquet"]

    # 5. 发现匹配文件
    matched_files = []
    for ext in supported_exts:
        matched_files.extend(sorted(input_dir.rglob(f"*{ext}")))

    # 去重（同一文件可能匹配多个扩展名）
    seen = set()
    unique_files = []
    for f in matched_files:
        resolved = str(f.resolve())
        if resolved not in seen:
            seen.add(resolved)
            unique_files.append(f)

    if not unique_files:
        print(f"⚠️ 在目录 {input_dir} 中未找到匹配文件")
        print(f"   适配器 '{args.from_format}' 支持的格式: {', '.join(supported_exts)}")
        return 0

    print(f"🔄 批量转换: {args.from_format} → {args.to_format}")
    print(f"   输入目录: {args.input_dir}")
    print(f"   输出目录: {args.output_dir}")
    print(f"   发现 {len(unique_files)} 个匹配文件")
    print("=" * 60)

    # 6. 逐文件转换
    success_count = 0
    fail_count = 0
    failed_files = []

    for i, file_path in enumerate(unique_files, 1):
        rel_path = file_path.relative_to(input_dir)
        # 生成输出路径（保持相对目录结构，去掉原扩展名）
        output_name = str(rel_path.with_suffix(""))
        if args.to_format == "ftp1":
            output_path = str(output_dir / f"{output_name}.zarr")
        else:
            output_path = str(output_dir / output_name)

        print(f"\n[{i}/{len(unique_files)}] {rel_path}")

        try:
            # 加载数据
            tlabel_data = adapter.load(str(file_path))
            print(f"  ✅ 加载成功: {tlabel_data.num_frames} 帧")

            # 导出
            stats = converter_cls.export(
                tlabel_data,
                output_path,
                adapter=adapter,
            )
            print(f"  ✅ 导出完成: {output_path}")
            success_count += 1

        except Exception as e:
            print(f"  ❌ 失败: {e}")
            fail_count += 1
            failed_files.append((str(rel_path), str(e)))

    # 7. 汇总
    print("\n" + "=" * 60)
    print(f"📊 批量转换完成")
    print(f"   成功: {success_count}/{len(unique_files)}")
    print(f"   失败: {fail_count}/{len(unique_files)}")

    if failed_files:
        print(f"\n❌ 失败文件:")
        for fname, err in failed_files:
            print(f"   - {fname}: {err}")

    return 0 if fail_count == 0 else 1


def cmd_list_adapters(args):
    """执行 list-adapters 子命令 — 列出所有适配器

    显示: name, type, description, supported_extensions
    比 'list' 命令更详细，专为 convert 工作流设计。
    """
    from tlabel.core.registry import (
        list_adapters, _ensure_adapters,
    )
    from tlabel.adapters.base import DataAdapterBase, SensorAdapterBase
    from tlabel.adapters import AVAILABLE_ADAPTERS

    _ensure_adapters()
    all_adapters = list_adapters()

    print("📦 TLabel 适配器列表")
    print("=" * 70)
    print(f"{'名称':<16} {'类型':<8} {'支持格式':<24} {'描述'}")
    print("-" * 70)

    data_adapters = []
    sensor_adapters = []

    for name in sorted(all_adapters.keys()):
        cls = all_adapters[name]
        try:
            instance = cls()
            exts = ", ".join(instance.supported_extensions) or "(none)"
            desc = AVAILABLE_ADAPTERS.get(name, "")
            if not desc:
                doc = (cls.__doc__ or "").strip().split("\n")[0]
                desc = doc[:40] if doc else ""

            if issubclass(cls, SensorAdapterBase):
                sensor_adapters.append((name, exts, desc))
            else:
                data_adapters.append((name, exts, desc))
        except Exception:
            # 无法实例化（缺少依赖等）
            desc = AVAILABLE_ADAPTERS.get(name, "(无法实例化)")
            exts = "?"
            if issubclass(cls, SensorAdapterBase):
                sensor_adapters.append((name, exts, desc))
            else:
                data_adapters.append((name, exts, desc))

    # 打印数据集适配器
    print(f"\n📁 数据集适配器 (DataAdapterBase) — 可用于 convert/batch-convert:")
    for name, exts, desc in data_adapters:
        print(f"  {name:<16} {exts:<24} {desc}")

    # 打印传感器适配器
    if sensor_adapters:
        print(f"\n🔌 传感器适配器 (SensorAdapterBase) — 需要硬件支持:")
        for name, exts, desc in sensor_adapters:
            print(f"  {name:<16} {exts:<24} {desc}")

    print(f"\n总计: {len(data_adapters)} 数据集 + {len(sensor_adapters)} 传感器 = {len(data_adapters) + len(sensor_adapters)} 个适配器")
    print(f"\n💡 可用于 convert 的适配器 (--from): {', '.join(_CONVERTIBLE_ADAPTERS)}")
    print(f"💡 可用于 convert 的目标格式 (--to): {', '.join(_TARGET_FORMATS)}")
    return 0


def cmd_adapter_info(args):
    """执行 adapter-info 子命令 — 显示适配器详细信息

    显示: 描述、支持格式、字段映射表（capabilities）、compliance_level
    """
    from tlabel.core.registry import get_adapter, _ensure_adapters
    from tlabel.adapters.base import DataAdapterBase, SensorAdapterBase

    _ensure_adapters()
    adapter_cls = get_adapter(args.name)
    if adapter_cls is None:
        print(f"❌ 未找到适配器: {args.name}")
        print("使用 'tlabel list-adapters' 查看所有可用适配器")
        return 1

    # 确定适配器类型
    is_sensor = issubclass(adapter_cls, SensorAdapterBase)
    adapter_type = "SensorAdapterBase (传感器)" if is_sensor else "DataAdapterBase (数据集)"

    print(f"📋 适配器详情: {args.name}")
    print("=" * 60)
    print(f"  类名:       {adapter_cls.__name__}")
    print(f"  模块:       {adapter_cls.__module__}")
    print(f"  类型:       {adapter_type}")

    try:
        adapter = adapter_cls()
    except ImportError as e:
        print(f"\n  ⚠️ 无法实例化适配器（缺少依赖）: {e}")
        print(f"     请安装所需依赖后重试")
        return 0
    except Exception as e:
        print(f"\n  ⚠️ 无法实例化适配器: {e}")
        return 0

    # 基本信息
    print(f"  名称:       {adapter.name}")
    print(f"  支持格式:   {', '.join(adapter.supported_extensions) or '(无)'}")
    print(f"  合规等级:   {getattr(adapter, 'default_compliance_level', 'L1')}")

    # 文档描述
    doc = (adapter_cls.__doc__ or "").strip()
    if doc:
        print(f"\n  📝 描述:")
        for line in doc.split("\n")[:5]:
            print(f"     {line.strip()}")

    # 传感器信息
    try:
        sensor_info = adapter.get_sensor_info()
        if sensor_info:
            print(f"\n  🔌 传感器信息:")
            for k, v in sensor_info.items():
                print(f"     {k}: {v}")
    except Exception:
        pass

    # 能力声明 / 字段映射表
    try:
        caps = adapter.get_capabilities()
        if caps:
            print(f"\n  📊 能力声明 (字段映射表):")
            print(f"     {'字段':<28} {'支持':<6} {'说明'}")
            print(f"     {'-'*28} {'-'*6} {'-'*20}")

            # Schema V2 字段说明
            field_descriptions = {
                "contact": "是否有接触",
                "contact_centroid": "接触质心 [x, y]",
                "contact_region": "接触区域枚举",
                "contact_area": "接触面积",
                "confidence": "标注置信度 0-1",
                "compliance_level": "合规等级 L1-L4",
                "force_magnitude": "法向力大小",
                "force_vector": "3D 力向量 [fx, fy, fz]",
                "torque_vector": "3D 力矩向量 [tx, ty, tz]",
                "slip_velocity": "滑移速度 [vx, vy]",
                "slip_event": "滑移事件标志",
                "manipulation_phase": "操作阶段枚举",
                "texture_class": "纹理分类",
                "object_deformation": "物体变形量",
                "temperature": "温度 (°C)",
            }

            active_count = 0
            for field, supported in sorted(caps.items()):
                status = "✅" if supported else "—"
                desc = field_descriptions.get(field, "")
                print(f"     {field:<28} {status:<6} {desc}")
                if supported:
                    active_count += 1

            print(f"\n     活跃维度: {active_count}/{len(caps)}")
    except Exception:
        pass

    # 图像形状检测
    try:
        image_shape = adapter.detect_image_shape()
        if image_shape:
            print(f"\n  🖼️ 触觉图像形状: {image_shape} (H, W, C)")
    except Exception:
        pass

    # 是否可用于 convert
    if not is_sensor:
        print(f"\n  ✅ 此适配器可用于 'tlabel convert --from {args.name}'")
    else:
        print(f"\n  ⚠️ 此为传感器适配器，需要硬件支持")
        print(f"     convert/batch-convert 仅支持数据集适配器")

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

    # ─── v0.19.0-dev: 格式转换命令 ───────────────────────────────────

    # convert — 单文件格式转换
    p_convert = subparsers.add_parser(
        "convert",
        help="格式转换: 从指定适配器加载数据，导出为目标格式",
        description=(
            "将触觉数据从一种格式转换为另一种格式。\n\n"
            "流程: adapter.load(input) → TLabelData → converter.export(output)\n\n"
            "示例:\n"
            "  tlabel convert --from gelsight --to ftp1 --input data.pkl --output out.zarr\n"
            "  tlabel convert --from paxini --to lerobot --input data.h5 --output out_dir/\n"
            "  tlabel convert --from tlabel --to ftp1 --input anno.json --output out.zarr\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_convert.add_argument(
        "--from", dest="from_format", required=True,
        choices=_CONVERTIBLE_ADAPTERS,
        help="源数据适配器名称 (如 gelsight, paxini, daimon, tlabel 等)",
    )
    p_convert.add_argument(
        "--to", dest="to_format", required=True,
        choices=_TARGET_FORMATS,
        help="目标格式 (lerobot 或 ftp1)",
    )
    p_convert.add_argument(
        "--input", required=True,
        help="输入文件路径",
    )
    p_convert.add_argument(
        "--output", required=True,
        help="输出路径 (ftp1: .zarr 文件路径; lerobot: 输出目录路径)",
    )
    p_convert.set_defaults(func=cmd_convert)

    # batch-convert — 批量目录格式转换
    p_batch = subparsers.add_parser(
        "batch-convert",
        help="批量格式转换: 遍历目录，自动发现匹配文件并转换",
        description=(
            "批量将目录中的触觉数据文件转换为目标格式。\n\n"
            "自动遍历 input-dir，根据适配器声明的 supported_extensions\n"
            "发现匹配文件，逐个加载并转换到 output-dir。\n\n"
            "示例:\n"
            "  tlabel batch-convert --from gelsight --to ftp1 \\\n"
            "      --input-dir ./raw_data/ --output-dir ./converted/\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_batch.add_argument(
        "--from", dest="from_format", required=True,
        choices=_CONVERTIBLE_ADAPTERS,
        help="源数据适配器名称",
    )
    p_batch.add_argument(
        "--to", dest="to_format", required=True,
        choices=_TARGET_FORMATS,
        help="目标格式 (lerobot 或 ftp1)",
    )
    p_batch.add_argument(
        "--input-dir", required=True,
        help="输入目录路径（将递归搜索匹配文件）",
    )
    p_batch.add_argument(
        "--output-dir", required=True,
        help="输出目录路径（将自动创建）",
    )
    p_batch.set_defaults(func=cmd_batch_convert)

    # list-adapters — 列出所有适配器
    p_list_adapters = subparsers.add_parser(
        "list-adapters",
        help="列出所有可用适配器（含类型、支持格式、描述）",
        description=(
            "列出所有已注册的适配器，按类型分组显示。\n"
            "显示名称、类型（数据集/传感器）、支持文件格式和描述。\n\n"
            "比 'tlabel list' 更详细，专为 convert 工作流设计。"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_list_adapters.set_defaults(func=cmd_list_adapters)

    # adapter-info — 适配器详细信息
    p_adapter_info = subparsers.add_parser(
        "adapter-info",
        help="查看指定适配器的详细信息（字段映射表、合规等级等）",
        description=(
            "显示指定适配器的详细信息，包括:\n"
            "  - 基本属性（名称、类型、支持格式）\n"
            "  - 合规等级 (compliance_level)\n"
            "  - 能力声明 / 字段映射表 (capabilities)\n"
            "  - 传感器元信息\n"
            "  - 触觉图像形状\n\n"
            "示例:\n"
            "  tlabel adapter-info gelsight\n"
            "  tlabel adapter-info paxini\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_adapter_info.add_argument(
        "name",
        help="适配器名称 (如 gelsight, paxini, daimon 等)",
    )
    p_adapter_info.set_defaults(func=cmd_adapter_info)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main() or 0)
