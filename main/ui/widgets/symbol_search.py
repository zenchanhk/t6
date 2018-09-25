
from atom.api import (Typed, ForwardTyped, Unicode, Bool, observe, set_default, ContainerList, Event)
from enaml.core.declarative import d_
from enaml.widgets.control import Control, ProxyControl
from enaml.qt.qt_control import QtControl
from ..qt.pyqt_symbol_search import QSymbolSearch

class ProxySymbolSearch(ProxyControl):
    declaration = ForwardTyped(lambda: SymbolSearch)
    def set_data(self, model):
        raise NotImplementedError
    
    def set_setting(self, setting):
        raise NotImplementedError

    def set_placeholder(self, placeholder):
        raise NotImplementedError

class SymbolSearch(Control):
    proxy = Typed(ProxySymbolSearch)

    #enter pressed event
    enterPressed = d_(Event(str), writable=False)
    
    #data list
    data = d_(ContainerList(default=[]))

    #setting
    setting = d_(ContainerList(default=[]))

    #placeholder
    placeholder = d_(Unicode())

    @observe('data', 'placeholder', 'setting')
    def _update_proxy(self, change):
        """ An observer which sends state change to the proxy.
        """
        # The superclass handler implementation is sufficient.
        super(SymbolSearch, self)._update_proxy(change)    

class QtSymbolSearch(QtControl, ProxySymbolSearch):
    __weakref__ = None
    widget = Typed(QSymbolSearch)
    
    def create_widget(self):
        self.widget = QSymbolSearch(self.parent_widget())

    def init_widget(self):
        super(QtSymbolSearch, self).init_widget()
        d = self.declaration
        self.widget.enterPressed.connect(self._enterPressed)
        if d.data:
            self.set_data(d.data)
        if d.setting:
            self.set_setting(d.setting)
        if d.placeholder:
            self.set_placeholder(d.placeholder)

    def set_data(self, data):
        self.widget.data = data

    def set_setting(self, setting):
        self.widget.setting = setting

    def set_placeholder(self, placeholder):
        self.widget.placeholder = placeholder

    def _enterPressed(self, code):
        self.declaration.enterPressed(code)
        print(code)

def factory():
    return QtSymbolSearch 