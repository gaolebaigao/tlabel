"""TouchLabel AI - Tactile Data Annotation Toolkit"""

from tlabel._version import __version__

from tlabel.core.loader import load
from tlabel.core.types import TLabelData
from tlabel.demo import demo, list_demos

__all__ = ["load", "TLabelData", "demo", "list_demos", "__version__"]
