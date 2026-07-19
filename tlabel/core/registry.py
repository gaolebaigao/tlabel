"""
Sensor adapter registry

Adapters digest format differences at load time, outputting unified TLabel Format v2.

v0.14: 重构为表驱动注册，新增适配器只需在 _ADAPTER_MODULES 加一行。

"""

import importlib
from typing import Dict, Type, Optional

_ADAPTERS: Dict[str, Type] = {}

_ADAPTER_MODULES = {
    "gelsight":      ("tlabel.adapters.gelsight",      "GelSightAdapter"),
    "paxini":        ("tlabel.adapters.paxini_dataset", "PaxiniAdapter"),
    "daimon":        ("tlabel.adapters.daimon_dataset", "DaimonAdapter"),
    "tlabel":        ("tlabel.adapters.tlabel_format",  "TLabelAdapter"),
    "touchd":        ("tlabel.adapters.touchd",         "ToucHDAdapter"),
    "univtac":       ("tlabel.adapters.univtac",        "UniVTACAdapter"),
    "vtouch":        ("tlabel.adapters.vtouch",         "VTouchAdapter"),
    "ycb_slide":     ("tlabel.adapters.ycb_slide",      "YCBSlideAdapter"),
    "tacquad":       ("tlabel.adapters.tacquad",        "TacQuadAdapter"),
    "paxini_gen3":   ("tlabel.adapters.paxini_gen3",    "PaxiniGen3Adapter"),
    "daimon_dm_tac": ("tlabel.adapters.daimon_dm_tac",  "DaimonDmTacAdapter"),
}


def register_adapter(name: str, adapter_cls: Type):
    """Register an adapter"""
    _ADAPTERS[name] = adapter_cls


def get_adapter(name: str) -> Optional[Type]:
    """Get an adapter class"""
    return _ADAPTERS.get(name)


def list_adapters() -> Dict[str, Type]:
    """List all registered adapters"""
    return dict(_ADAPTERS)


def auto_detect_format(file_path: str) -> Optional[str]:
    """Auto-detect format from file extension and content"""
    path = str(file_path).lower()

    if path.endswith(".pkl") or path.endswith(".pickle"):
        return "gelsight"
    if path.endswith(".npy"):
        return "ycb_slide"
    if path.endswith(".h5") or path.endswith(".hdf5"):
        try:
            import h5py
            with h5py.File(file_path, 'r') as f:
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
        import json
        from pathlib import Path
        try:
            p = Path(file_path)
            if not p.exists():
                return None
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "schema_version" in data and "frames" in data:
                return "tlabel"
            if "episodes" in data:
                return "tlabel"
            if "robot_type" in data and "codebase_version" in data:
                return "daimon"
            if "frames" in data and "channels" in data:
                return "daimon"
        except (json.JSONDecodeError, UnicodeDecodeError, OSError):
            pass
        return None

    from pathlib import Path
    p = Path(file_path)
    if p.is_dir():
        if (p / "meta" / "info.json").exists() or list(p.glob("data/chunk-*/file-*.parquet")):
            return "daimon"
        if (p / "all_data_direction.json").exists():
            return "touchd"
        if any(p.glob("*/synced_data.npy")) or any(p.glob("*/tactile_data.pkl")):
            return "ycb_slide"
        if (p / "synced_data.npy").exists() or (p / "tactile_data.pkl").exists():
            return "ycb_slide"

        # TacQuad detection: directory with contact_indoor.csv or contact_outdoor.csv
        # Also check for data_indoor/ + data_outdoor/ structure
        if ((p / "contact_indoor.csv").exists() and (p / "data_indoor").exists()) or \
           ((p / "contact_outdoor.csv").exists() and (p / "data_outdoor").exists()):
            return "tacquad"
        # TacQuad parent directory: tactile_datasets/ with tacquad/ subdirectory
        if (p / "tacquad" / "contact_indoor.csv").exists() and \
           (p / "tacquad" / "data_indoor").exists():
            return "tacquad"

    return None


def _ensure_adapters():
    """Lazy registration — 一张表搞定，新增适配器只需加一行"""
    for name, (module_path, class_name) in _ADAPTER_MODULES.items():
        if name not in _ADAPTERS:
            try:
                mod = importlib.import_module(module_path)
                cls = getattr(mod, class_name)
                register_adapter(name, cls)
            except (ImportError, AttributeError):
                pass

