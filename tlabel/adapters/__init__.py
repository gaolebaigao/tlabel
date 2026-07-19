"""Adapter package"""

from tlabel.adapters.base import BaseAdapter

# Lazy imports to avoid dependency failures
# Adapters are registered via registry._ensure_adapters()

__all__ = ["BaseAdapter"]

# Available adapters (for documentation and autocomplete)
AVAILABLE_ADAPTERS = {
    "gelsight":      "GelSight Mini / DIGIT (.pkl)",
    "paxini":        "PaXini PXCap dataset (.h5)",
    "paxini_gen3":   "PaXini GEN3 realtime (SDK / .paxini)",
    "paxini_px6d":   "PaXini PX6D 6-axis force (Modbus)",
    "daimon":        "Daimon DM-TacClaw dataset (.parquet / LeRobot)",
    "daimon_dm_tac": "Daimon DM-Tac realtime (USB / UVC)",
    "tlabel":        "TLabel Format JSON (.json)",
    "touchd":        "ToucHD-Force / AnyTouch 2 (.npy / directory)",
    "univtac":       "UniVTAC Cross-Dataset (.hdf5 / .h5)",
    "vtouch":        "VTouch vision-based tactile (.h5 / .hdf5)",
    "ycb_slide":     "YCB-Slide CMU DIGIT sliding (.npy / directory)",
    "tacquad":       "TacQuad AnyTouch multi-sensor (directory)",

}
