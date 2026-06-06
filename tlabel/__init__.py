"""TouchLabel AI - Tactile Data Annotation Toolkit"""

from tlabel._version import __version__

from tlabel.core.loader import load
from tlabel.core.types import TLabelData

__all__ = ["load", "TLabelData", "__version__"]
