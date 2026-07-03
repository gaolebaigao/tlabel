"""
Sensor adapter registry

Adapters digest format differences at load time, outputting unified TLabel Format v2.
"""

from typing import Dict, Type, Optional

_ADAPTERS: Dict[str, Type] = {}


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
    """Lazy registration to avoid import errors when dependencies are missing"""
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
    if "tacquad" not in _ADAPTERS:
        try:
            from tlabel.adapters.tacquad import TacQuadAdapter
            register_adapter("tacquad", TacQuadAdapter)
        except ImportError:
            pass
