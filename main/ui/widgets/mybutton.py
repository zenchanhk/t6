from atom.api import (Unicode, observe, ContainerList, Event)
from enaml.core.declarative import d_
from enaml.widgets.api import RawWidget
from qtpy.QtWidgets import QPushButton

class MyButton(RawWidget):

    text = d_(Unicode())
    data = d_(ContainerList(default=[]))
    enterPressed = d_(Event(), writable=False)

    def create_widget(self, parent):
        btn = QPushButton(parent)
        btn.setText(self.text)
        #btn.clicked.connect(self._ep)
        return btn

    def _ep(self):
        print('enter pressed:')

    def _observe_text(self, change):
        if change['type'] == 'update':
            widget = self.get_widget()
            if widget is not None:
                widget.setText(change['value'])