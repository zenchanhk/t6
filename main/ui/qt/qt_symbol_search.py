from atom.api import (
   Event, List, Tuple, Bool, Int, Enum, Typed, ForwardTyped, observe, set_default
)

from enaml.core.declarative import d_
from enaml.qt.qt_control import QtControl

from enaml.QtCore import Qt
from .pyqt_symbol_search import QSymbolSearch


ALIGN_MAP = {
    'left': Qt.AlignLeft,
    'right': Qt.AlignRight,
    'center': Qt.AlignHCenter,
    'justify': Qt.AlignJustify,
}

class QtSymbolSearch(ProxyControl):
    """ The abstract definition of a proxy SymbolSearch object.
    """
    #: A reference to the SymbolSearch declaration.
    declaration = ForwardTyped(lambda: QSymbolSearch)