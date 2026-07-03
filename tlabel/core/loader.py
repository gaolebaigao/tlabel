"""
tlabel.load() -- unified loading entry point

Auto-detects file format, calls the corresponding adapter, returns TLabelData.
"""

from pathlib import Path
from typing import Optional, Union

from tlabel.core.types import TLabelData
from tlabel.core.registry import auto_detect_format, _ensure_adapters, get_adapter


def load(file_path: Union[str, Path],
         format: Optional[str] = None,
         trajectory_id: Optional[int] = None,
         **kwargs) -> TLabelData:
    """
    Load tactile data file, auto-detect format and convert to TLabel Format v2

    Args:
        file_path: Data file path
        format: Force format ("gelsight"/"paxini"/"daimon"/"tlabel"/"touchd"/"univtac"/"vtouch"/"ycb_slide"/"tacquad")
        trajectory_id: Trajectory ID (for GelSight dataset)
        **kwargs: Extra args passed to adapter

    Returns:
        TLabelData -- unified annotation container

    Usage:
        data = tlabel.load("gelsight_01.pkl")
        data = tlabel.load("paxini.h5", trajectory_id=0)
        data = tlabel.load("annotations.json")
        data = tlabel.load("vtouch_data.h5")
        data = tlabel.load("ycb_slide_dir/")
        data = tlabel.load("tacquad_dir/", format="tacquad")
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    _ensure_adapters()

    fmt = format or auto_detect_format(str(path))
    if fmt is None:
        raise ValueError(
            f"Cannot detect format: {file_path}\n"
            f"Supported formats:\n"
            f"  .pkl         -- GelSight / DIGIT\n"
            f"  .h5 / .hdf5  -- PaXini / UniVTAC / VTouch (auto-detect)\n"
            f"  .parquet     -- Daimon DM-TacClaw\n"
            f"  .json        -- TLabel Format / Daimon info.json\n"
            f"  .npy         -- YCB-Slide (synced_data.npy)\n"
            f"  directory    -- Daimon / ToucHD-Force / YCB-Slide / TacQuad (auto-detect)\n"
            f"You can specify: tlabel.load(path, format='gelsight')"
        )

    adapter_cls = get_adapter(fmt)
    if adapter_cls is None:
        available = [k for k in [
            "gelsight", "paxini", "daimon", "tlabel",
            "touchd", "univtac", "vtouch", "ycb_slide", "tacquad"
        ] if get_adapter(k)]
        raise ImportError(
            f"Adapter '{fmt}' unavailable (missing dependencies)\n"
            f"Available: {available or 'none'}\n"
            f"GelSight/DIGIT: pip install numpy opencv-python\n"
            f"PaXini: pip install h5py numpy\n"
            f"Daimon: pip install pyarrow numpy\n"
            f"UniVTAC: pip install h5py numpy\n"
            f"VTouch: pip install h5py numpy opencv-python\n"
            f"YCB-Slide: pip install numpy opencv-python\n"
            f"TacQuad: pip install numpy opencv-python"
        )

    adapter = adapter_cls()
    return adapter.load(str(path), trajectory_id=trajectory_id, **kwargs)
