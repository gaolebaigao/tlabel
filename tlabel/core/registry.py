"""
传感器适配器注册表

适配器在load阶段消化格式差异，输出统一的TLabel Format v2。
"""

from typing import Dict, Type, Optional

_ADAPTERS: Dict[str, Type] = {}


def register_adapter(name: str, adapter_cls: Type):
    """注册适配器"""
    _ADAPTERS[name] = adapter_cls


def get_adapter(name: str) -> Optional[Type]:
    """获取适配器类"""
    return _ADAPTERS.get(name)


def list_adapters() -> Dict[str, Type]:
    """列出所有注册的适配器"""
    return dict(_ADAPTERS)


def auto_detect_format(file_path: str) -> Optional[str]:
    """根据文件扩展名和内容自动检测格式"""
    path = str(file_path).lower()

    if path.endswith(".pkl") or path.endswith(".pickle"):
        return "gelsight"
    if path.endswith(".h5") or path.endswith(".hdf5"):
        return "paxini"
    if path.endswith(".parquet"):
        return "daimon"
    if path.endswith(".json"):
        # 进一步检测JSON内容
        import json
        from pathlib import Path
        try:
            p = Path(file_path)
            if not p.exists():
                return None  # 文件不存在时无法判断内容格式
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "schema_version" in data and "sensor" in data:
                sensor_type = data.get("sensor", {}).get("type", "")
                if "taxel" in sensor_type or "paxini" in str(data.get("sensor", {})):
                    return "paxini"
                return "tlabel"
            if "frames" in data and "channels" in data:
                return "daimon"
            if "episodes" in data:
                return "tlabel"
            # Daimon info.json
            if "robot_type" in data and "codebase_version" in data:
                return "daimon"
        except (json.JSONDecodeError, UnicodeDecodeError, OSError):
            pass
        return None

    # 目录路径: 检测是否为Daimon episode目录
    from pathlib import Path
    p = Path(file_path)
    if p.is_dir():
        if (p / "meta" / "info.json").exists() or list(p.glob("data/chunk-*/file-*.parquet")):
            return "daimon"

    return None


# 延迟注册 — 避免import时依赖缺失
def _ensure_adapters():
    if "gelsight" not in _ADAPTERS:
        try:
            from tlabel.adapters.gelsight import GelSightAdapter
            register_adapter("gelsight", GelSightAdapter)
        except ImportError:
            pass
    if "paxini" not in _ADAPTERS:
        try:
            from tlabel.adapters.paxini import PaxiniAdapter
            register_adapter("paxini", PaxiniAdapter)
        except ImportError:
            pass
    if "daimon" not in _ADAPTERS:
        try:
            from tlabel.adapters.daimon import DaimonAdapter
            register_adapter("daimon", DaimonAdapter)
        except ImportError:
            pass
    if "univtac" not in _ADAPTERS:
        try:
            from tlabel.adapters.univtac import UniVTACAdapter
            register_adapter("univtac", UniVTACAdapter)
        except ImportError:
            pass


def _detect_hdf5_variant(file_path: str) -> str:
    """区分 HDF5 文件的传感器来源（PaXini vs UniVTAC）

    UniVTAC 特征: 包含 tactile/left_gsmini 或 tactile/right_gsmini
    PaXini 特征: 其他结构
    """
    try:
        import h5py
        with h5py.File(file_path, 'r') as f:
            # UniVTAC 特征检测
            if 'tactile' in f:
                tactile_keys = list(f['tactile'].keys())
                if any('gsmini' in k for k in tactile_keys):
                    return "univtac"
        return "paxini"
    except (ImportError, Exception):
        return "paxini"
