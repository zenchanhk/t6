from atom.api import (Typed, ForwardTyped, Bool, observe, set_default)
from enaml.core.declarative import d_
from enaml.widgets.control import Control, ProxyControl
from enaml.qt.qt_control import QtControl
#from PyQt5.QtCore import (QAbstractTableModel, Qt)
from enaml.qt.QtCore import QAbstractTableModel, Qt
from PyQt5 import QtCore
from PyQt5.QtWidgets import QTableView, QAbstractItemView, QHeaderView
from enaml.qt.QtGui import (QFontMetrics)
import numpy as np
import pandas as pd

class PandasModel(QAbstractTableModel):
    """
    Class to populate a table view with a pandas dataframe
    """
    def __init__(self, data=None, columns=None, *args, **kwds):
        super(PandasModel, self).__init__(*args, **kwds)
        m = False
        if m:
            self._data = np.array(data.values)
            self._cols = data.columns
            self.r, self.c = np.shape(self._data)
        else:
            self._data = np.array([[None]*len(columns)]) 
            self._cols = columns
            #self.r, self.c = (len(columns), 1)       
        self.r, self.c = np.shape(self._data)

    def rowCount(self, parent=None):
        return self.r

    def columnCount(self, parent=None):
        return self.c

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if index.isValid() or not (0 <= index.row() < len(self.data_frame)):
            if role == QtCore.Qt.DisplayRole:
                return self._data[index.row(),index.column()]
            elif role == Qt.TextAlignmentRole:
                if isinstance(self._data[index.row(),index.column()], str):
                    return int(Qt.AlignLeft | Qt.AlignVCenter)
                else:
                    return int(Qt.AlignRight | Qt.AlignVCenter)
            elif role == Qt.BackgroundColorRole:
                pass
        return None


    def headerData(self, p_int, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                return self._cols[p_int]
        return None

    def sort(self, column, order=Qt.AscendingOrder):        
        if column == -1:
            return

        order = 1 if (order == Qt.AscendingOrder) else -1
        self._data = self._data[self._data[:,column].argsort()][::order]
        self._emit_all_data_changed()

    def _emit_all_data_changed(self):
        """ Emit signals to note that all data has changed, e.g. by sorting.
        """
        self.r, self.c = np.shape(self._data)
        self.dataChanged.emit(
            self.index(0, 0),
            self.index(self.r - 1, self.c - 1),)
        self.headerDataChanged.emit(    
            Qt.Vertical, 0, self.r - 1)

    def insert(self, row):
        self._data = np.vstack([row, self._data])
        self._emit_all_data_changed()

    def remove(self, index=0):
        self._data = np.delete(self._data, (index), axis=0)
        self._emit_all_data_changed()

class ProxyTableView(ProxyControl):
    declaration = ForwardTyped(lambda: TableView)
    def set_model(self, model):
        raise NotImplementedError

    def set_sorting_enabled(self, sort_enabled):
        raise NotImplementedError

class TableView(Control):
    hug_width = set_default('ignore')
    hug_height = set_default('ignore')

    proxy = Typed(ProxyTableView)
    tableModel = d_(Typed(QAbstractTableModel))
    sortingEnabled = d_(Bool(False))
    
    @observe('tableModel', 'sortingEnabled')
    def _update_proxy(self, change):
        """ An observer which sends state change to the proxy.
        """
        # The superclass handler implementation is sufficient.
        super(TableView, self)._update_proxy(change)    

class QtTableView(QtControl, ProxyTableView):
    __weakref__ = None
    widget = Typed(QTableView)
    def create_widget(self):
        self.widget = QTableView(self.parent_widget())

    def init_widget(self):
        super(QtTableView, self).init_widget()
        self.widget.setSortingEnabled(True)
        d = self.declaration
        self.set_model(d.tableModel)
        self.widget.sortByColumn(-1, Qt.AscendingOrder)
        self.set_sorting_enabled(d.sortingEnabled)
        self.widget.setSelectionBehavior(QAbstractItemView.SelectRows)
    
    def set_model(self, model):
        self.widget.setModel(model)

    def set_sorting_enabled(self, sort_enabled):
        self.widget.setSortingEnabled(sort_enabled)

    def _init(self):
        self.widget.sortByColumn(-1, Qt.AscendingOrder)
        
        self.widget.setSelectionMode(QAbstractItemView.ContiguousSelection)
        self.widget.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.widget.setVerticalScrollMode(QAbstractItemView.ScrollPerItem)
        self.widget.setWordWrap(False)
        self.widget.vheader = QHeaderView(Qt.Vertical)
        self.widget.setVerticalHeader(self.widget.vheader)
        font = self.widget.vheader.font()
        font.setBold(True)
        fmetrics = QFontMetrics(font)
        max_width = fmetrics.width(u" {0} ".format(
        self.declaration.tableModel.rowCount()))
        self.widget.vheader.setMinimumWidth(max_width)
        #self.vheader.setClickable(True)
        self.widget.vheader.setStretchLastSection(False)

def table_view_factory():
    return QtTableView 