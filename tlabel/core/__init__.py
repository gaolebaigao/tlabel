"""TLabel core modules"""

from tlabel.core.loader import load
from tlabel.core.types import TLabelData
from tlabel.core.registry import get_adapter, register_adapter

__all__ = ["load", "TLabelData", "get_adapter", "register_adapter"]
