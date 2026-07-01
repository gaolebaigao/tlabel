"""适配器包"""

from tlabel.adapters.base import BaseAdapter

# 延迟导入 — 避免依赖缺失时整个包无法加载
# 实际适配器通过 registry._ensure_adapters() 注册

__all__ = ["BaseAdapter"]

# 可用适配器列表 (供文档和自动补全参考)
AVAILABLE_ADAPTERS = {
    "gelsight": "GelSight Mini / DIGIT (.pkl)",
    "paxini": "PaXini PXCap (.h5)",
    "daimon": "Daimon DM-TacClaw (.parquet / LeRobot)",
    "tlabel": "TLabel Format JSON (.json)",
    "touchd": "ToucHD-Force (AnyTouch 2, ICLR 2026) — 目录",
    "univtac": "UniVTAC Cross-Dataset (.hdf5 / .h5)",
}
