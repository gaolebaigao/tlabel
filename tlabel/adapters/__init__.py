"""适配器包"""

from tlabel.adapters.base import BaseAdapter

__all__ = ["BaseAdapter"]

# 可选适配器（延迟导入，避免依赖缺失时报错）
def _get_univtac():
    try:
        from tlabel.adapters.univtac import UniVTACAdapter
        return UniVTACAdapter
    except ImportError:
        return None
