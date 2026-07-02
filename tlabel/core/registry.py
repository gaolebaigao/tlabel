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
    if path.endswith(".npy"):
        return "ycb_slide"
    if path.endswith(".h5") or path.endswith(".hdf5"):
        # Distinguish PaXini / UniVTAC / VTouch by checking internal structure
        try:
            import h5py
            with h5py.File(file_path, 'r') as f:
                # VTouch: tactile/hand_left or tactile/hand_right
                if 'tactile' in f:
                    tactile_keys = list(f['tactile'].keys())
                    if any('gsmini' in k for k in tactile_keys):
                        return "univtac"
                    if any(k.startswith('hand_') for k in tactile_keys):
                        return "vtouch"
            return "paxini"
        except (ImportError, Exception):
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
            # 优先检测 TLabel Format（有 schema_version + frames）
            if "schema_version" in data and "frames" in data:
                return "tlabel"
            if "episodes" in data:
                return "tlabel"
            # Daimon info.json
            if "robot_type" in data and "codebase_version" in data:
                return "daimon"
            if "frames" in data and "channels" in data:
                return "daimon"
        except (json.JSONDecodeError, UnicodeDecodeError, OSError):
            pass
        return None

    # 目录路径: 检测是否为Daimon episode目录、ToucHD目录或YCB-Slide目录
    from pathlib import Path
    p = Path(file_path)
    if p.is_dir():
        if (p / "meta" / "info.json").exists() or list(p.glob("data/chunk-*/file-*.parquet")):
            return "daimon"
        # ToucHD-Force: 含all_data_direction.json
        if (p / "all_data_direction.json").exists():
            return "touchd"
        # YCB-Slide: real/<object>/dataset_X/synced_data.npy 或 sim/<object>/XX/tactile_data.pkl
        if any(p.glob("*/synced_data.npy")) or any(p.glob("*/tactile_data.pkl")):
            return "ycb_slide"
        # YCB-Slide 子目录本身
        if (p / "synced_data.npy").exists() or (p / "tactile_data.pkl").exists():
            return "ycb_slide"

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
    if "tlabel" not in _ADAPTERS:
        try:
            from tlabel.adapters.tlabel_format import TLabelAdapter
            register_adapter("tlabel", TLabelAdapter)
        except ImportError:
            pass
    if "touchd" not in _ADAPTERS:
        try:
            from tlabel.adapters.touchd import ToucHDAdapter
            register_adapter("touchd", ToucHDAdapter)
        except ImportError:
            pass
    if "univtac" not in _ADAPTERS:
        try:
            from tlabel.adapters.univtac import UniVTACAdapter
            register_adapter("univtac", UniVTACAdapter)
        except ImportError:
            pass
    if "vtouch" not in _ADAPTERS:
        try:
            from tlabel.adapters.vtouch import VTouchAdapter
            register_adapter("vtouch", VTouchAdapter)
        except ImportError:
            pass
    if "ycb_slide" not in _ADAPTERS:
        try:
            from tlabel.adapters.ycb_slide import YCBSlideAdapter
            register_adapter("ycb_slide", YCBSlideAdapter)
        except ImportError:
            pass
