"""Adapter package"""

from tlabel.adapters.base import BaseAdapter

# Lazy imports to avoid dependency failures
# Adapters are registered via registry._ensure_adapters()

__all__ = ["BaseAdapter"]

# Available adapters (for documentation and autocomplete)
AVAILABLE_ADAPTERS = {
    "gelsight": "GelSight Mini / DIGIT (.pkl)",
    "paxini": "PaXini PXCap (.h5)",
    "daimon": "Daimon DM-TacClaw (.parquet / LeRobot)",
    "tlabel": "TLabel Format JSON (.json)",
    "touchd": "ToucHD-Force (AnyTouch 2, ICLR 2026) -- directory",
    "univtac": "UniVTAC Cross-Dataset (.hdf5 / .h5)",
    "vtouch": "VTouch (vision-based tactile) (.h5 / .hdf5)",
    "ycb_slide": "YCB-Slide CMU DIGIT sliding tactile (.npy / directory)",
    "tacquad": "TacQuad AnyTouch ICLR 2025 multi-sensor (directory)",
}
