from PyQt5 import QtCore
from PyQt5.QtCore import Qt, pyqtSignal, QPoint
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (QAction, QApplication,
        QLabel, QMenu, QSizePolicy, QMainWindow,
        QWidget, QLineEdit, QHBoxLayout, QWidgetAction)
import qtawesome as qta
import os
from datetime import datetime
import math
from collections import namedtuple

#os.environ["QT_SCALE_FACTOR"] = "1.5"

STYLE = '''
SymbolSearch[state='false'] {
    background: lightgray;
}
'''

class WidgetAction(QWidgetAction):
    def __init__(self, parent=None):
       super().__init__(parent)
    
    def focusInEvent(self, event):
        self.focusNextPrevChild(True)
        super().focusInEvent(event)

class MyLineEdit(QLineEdit):
    focusIn = pyqtSignal()
    focusOut = pyqtSignal()
    enterPressed = pyqtSignal(str)
    cancelPressed = pyqtSignal()
    clearBtnClicked = pyqtSignal()

    def __init__(self, parent):
       super().__init__(parent)
       self.setClearButtonEnabled(True)
       for child in self.children():
           if isinstance(child, QAction):
               child.triggered.connect(self._clearBtnClicked)
               break

    def _clearBtnClicked(self):
        self.clearBtnClicked.emit()

    def focusInEvent(self, event):
        self.focusIn.emit()
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        self.focusOut.emit()
        super().focusOutEvent(event)

    def keyPressEvent(self, e):
        if e.key() in [Qt.Key_Enter, Qt.Key_Return]:
            self.enterPressed.emit(self.text())
        if e.key() in [Qt.Key_Escape]:
            self.cancelPressed.emit()
        super().keyPressEvent(e)

class MyLabel(QLabel):
    clicked=pyqtSignal()
    def __init__(self, parent=None):
        QLabel.__init__(self, parent)

    def mousePressEvent(self, e):
        self.clicked.emit()

class MyMenu(QMenu):
    cancelPressed = pyqtSignal()
    def __init__(self, parent=None):
        QLabel.__init__(self, parent)

    def keyPressEvent(self, e):
        if e.key() in [Qt.Key_Escape]:
            self.cancelPressed.emit()
        super().keyPressEvent(e)

class GroupItem(QWidget):
    def __init__(self, text, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 3, 0, 3)
        lay.setSpacing(3)
        self.l1 = QWidget(self)
        self.l1.setFixedHeight(2)
        self.l1.setFixedWidth(10)
        self.l1.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.l1.setStyleSheet("background-color: #393d3a;")
        self.l2 = QWidget(self)
        self.l2.setFixedHeight(2)
        self.l2.setMinimumWidth(10)
        self.l2.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.l2.setStyleSheet("background-color: #393d3a;")
        self.label = QLabel(self)
        self.label.setText(text)
        lay.addWidget(self.l1)
        lay.addWidget(self.label)
        lay.addWidget(self.l2)
        #set background
        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), QColor('#dee8e1'))
        self.setPalette(p)        
        self.setStyleSheet('color: black')

    def focusInEvent(self, e):
        print(e)

class QSymbolSearch(QWidget):
    enterPressed = pyqtSignal(str)
    cancelSearch = pyqtSignal()
    selected = pyqtSignal(object)

    _selectedItem = None
    _placeholder = 'placeholder'
    _loading = False
    _data = []
    _setting = []
    _aggregateTypes = ['section', 'group']
    isMenu = {'group': True, 'section': False}
    aggrProps = {'group': {'isMenu': True, 'fields': ['id', 'by']},
                'section': {'isMenu': False, 'fields': []}}

    _awaitingData = False

    def __init__(self, parent):
        super().__init__(parent)
        #self.setFocusPolicy(Qt.StrongFocus)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.input = MyLineEdit(self)
        self.input.setPlaceholderText(self.placeholder)
        self.input.focusIn.connect(self.focusInHandler)
        self.input.focusOut.connect(self.focusOutHandler)
        self.input.enterPressed.connect(self.keyPressHandler)
        self.input.cancelPressed.connect(self.cancelHandler)
        self.input.clearBtnClicked.connect(self.clear)
        lay.addWidget(self.input)

        self.label = MyLabel(self)
        self.label.setText(self._htmlLabel(self.placeholder))
        self.label.setMargin(3)
        self.label.clicked.connect(self.focusInHandler)
        self.label.setGeometry(self.input.geometry().x(), self.input.geometry().y(),
            self.input.geometry().width(), self.input.geometry().height())
        
        #set white background for label
        fs = self.property('font').pointSize()
        bgclr = self.palette().color(self.backgroundRole())
        #if bgclr == QColor('transparent'):
        fp = self.label.palette()
        fp.setColor(self.label.backgroundRole(), QColor('white'))
        self.label.setAutoFillBackground(True)
        self.label.setPalette(fp)
        
        self.search_icon = qta.icon('fa.search', color='grey')
        self.search_action = QAction(self.search_icon, '', self, triggered=self.keyPressHandler)
        self.spin_icon = qta.icon('fa.spinner', color='blue', animation=qta.Spin(self.input))
        self.waiting_action = QAction(self.spin_icon, '', self)        
        self.input.addAction(self.search_action, QLineEdit.TrailingPosition)

        #calculate the space of top and bottom
        self.winHeight = 0 
        self.topHeight = 0
        self.bottomHeight = 10
        
        self.menu = None
        '''
        self.setStyleSheet('QLabel{background-color: white; color: #8C8C8C}'
                           'QLineEdit{background-color: #41eef4}'
                           "GroupItem{background-color: #41eef4}" )
        '''
    @QtCore.pyqtProperty(str)
    def placeholder(self):
        return self._placeholder

    @placeholder.setter
    def placeholder(self, value):
        if value != self._placeholder:
            self.input.setPlaceholderText(value)
            self.label.setText(self._htmlLabel(value))
            self._placeholder = value

    def _showLoadingBtn(self, isLoading):
        #print('isLoading:')
        #print(isLoading)
        if isLoading:
            self.input.removeAction(self.search_action)
            self.input.addAction(self.waiting_action, QLineEdit.TrailingPosition)
        else:
            self.input.removeAction(self.waiting_action)
            self.input.addAction(self.search_action, QLineEdit.TrailingPosition)

    @QtCore.pyqtProperty(object)
    def selectedItem(self):
        return self._selectedItem

    @QtCore.pyqtProperty(list)
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        if value != None and len(value) > 0:
            self._showLoadingBtn(False) #hide loading animation
        if value != self._data:
            self._data = value
            self._createMenu()

        if self._awaitingData:
                self._showDropDown()    

    @QtCore.pyqtProperty(list)
    def setting(self):
        return self._setting

    @setting.setter
    def setting(self, value):
        if value != self._data:
            self._setting = value

    def _htmlLabel(self, text):
        return '<span style="color:grey">' + text + '</span>'

    def moveEvent(self, event):
        for w in QApplication.topLevelWidgets():
            if isinstance(w, QMainWindow):
                wg = w.geometry()
                self.winHeight = wg.height()
                g = self.geometry()
                self.topHeight = g.y()
                self.bottomHeight = self.winHeight - g.y() - g.height() 
                break
        super().moveEvent(event)

    def resizeEvent(self, event): 
        self.label.resize(event.size().width(), event.size().height())
        super().resizeEvent(event)

    def keyPressHandler(self, e=None):
        if e == None or not isinstance(e, str): 
            e = self.input.text()
        
        if e == None or e == '':
            self.clear()
            return
        
        self._data = []
        self.menu = None
        self._showLoadingBtn(True) #show loading animation
        self.enterPressed.emit(e)
        self._showDropDown()

    def cancelHandler(self, e=None):
        self._showLoadingBtn(False)
        self._awaitingData = False
        self.cancelSearch.emit()

    def focusInHandler(self):
        self.label.hide()
        self.input.setFocus()

    def focusOutHandler(self):
        if self.menu == None:
            self.label.show()
        if self.menu != None and not self.menu.isVisible():
            self.label.show()

    def itemSelected(self, item):
        item = namedtuple("Contract", item.keys())(*item.values())
        name = item.tradingClass if item.secType == 'CASH' else item.symbol
        lastTradeDate = datetime.strftime(datetime.strptime(item.lastTradeDateOrContractMonth, '%Y%m%d'), "%b%d'%y") \
            if item.contractMonth else ''
        exchange = item.primaryExchange if item.primaryExchange else item.exchange
        fontSize = str(self.label.property('font').pointSize()*0.9) + 'pt'        
        self.label.setText('<b>'+name+'</b><span style="font-size:'+fontSize+'">'+' '+lastTradeDate+" @"+exchange+'</span>')
        self.selected.emit(item)
        self._selectedItem = item
        self.parent().focusNextPrevChild(True)
        print(item)

    def clear(self):
        self.input.setPlaceholderText(self.placeholder)
        self.label.setText(self._htmlLabel(self.placeholder))
        self._selectedItem = None
        self._awaitingData = False
        self._showLoadingBtn(False)

    def _createMenu(self):
        """
            data = [{'aggregate': {'aggr': , 'by': , 'id': , 'eval': , 'isValid': , 'format': , 'label': , 'delegate': },  
                    'item': {'label': , 'format': , delegate': } }, ...]
            'aggr': should be in ['section', 'group']
            'eval': is a function to evaluate the column before comparison
            'by': group by which column
            'id': used to identify aggregate header
            'isValid': func used to valid the column id to judge if continue
            'label': used to show on menu
            'format': used to format label
        """
        self.menu = MyMenu('MainMenu')   
        self.menu.cancelPressed.connect(self.cancelHandler)     
        menuChain = [None]*len(self.setting)          
        prevItem = {}
        for data_i, item in enumerate(self.data):
            if self.setting != None and len(self.setting) > 0:
                menuChain[0] = self.menu
                curMenu = self.menu  
                curIA = None        #current Item Action
                isNewAggr = False

                for layer_i, layer in enumerate(self.setting):
                    #get the aggregator
                    aggr = None 
                    if 'aggregate' in layer:
                        aggr = layer['aggregate']
                        if aggr['aggr'] not in self._aggregateTypes:
                            raise AttributeError('SymbolSearch does not have an aggregate attribute: ' + aggr['aggr'])
                    
                    if aggr != None:
                        evalFunc = aggr['eval'] if 'eval' in aggr else lambda x: x
                        validFunc = aggr['isValid'] if 'isValid' in aggr else lambda x: True
                        validCol = 'validCol' if 'validCol' in aggr else 'id'

                        if (data_i > 0 and evalFunc(item[aggr['id']]) != evalFunc(prevItem[aggr['id']])) or data_i == 0 or isNewAggr:
                            
                            delegate = aggr['delegate'] if ('delegate' in aggr) else None
                            fmt = aggr['format'] if ('format' in aggr) else None
                            if validFunc(item[aggr[validCol]]):
                                if not self.aggrProps[aggr['aggr']]['isMenu']:
                                    curMenu = self._getPrevMenu(menuChain, layer_i - 1)
                                    curMenu.addAction(getattr(self, aggr['aggr'])(self._getLabels(item, aggr['label']), fmt, delegate))
                                    curIA = layer['item']
                                else:
                                    curMenu = self._getPrevMenu(menuChain, layer_i - 1)
                                    tmp = getattr(self, aggr['aggr'])(self._getLabels(item, aggr['label']), fmt)
                                    curMenu = curMenu.addMenu(tmp)
                                    menuChain[layer_i] = curMenu
                                    curIA = layer['item']

                                #reset the elements of menuChain after layer_i to None;
                                #otherwise, the following action may attach to the previous menu
                                self._restMenuChain(menuChain, layer_i + 1)
                                isNewAggr = True
                            else:                                
                                curMenu = self._getPrevMenu(menuChain, layer_i - 1)   #get the previous menu
                                break
                        else:
                            #the last item
                            if layer_i + 1 == len(self.setting):
                                curMenu = self._getPrevMenu(menuChain, layer_i)
                                curIA = layer['item']     

                #if no aggregate, suppose only one setting for item
                if curIA == None:
                    if len(self.setting) == 1 and 'item' in self.setting[0]:
                        curIA = self.setting[0]['item']
                    else:
                        raise ValueError('Assume only one item for setting if no aggregate')

                if curIA != None:
                    delegate = curIA['delegate'] if 'delegate' in curIA else None
                    fmt = curIA['format'] if ('format' in curIA) else None                    
                    curMenu.addAction(self.item(self._getLabels(item, curIA['label']), item, fmt, delegate))
            else:
                #if no setting, the first key of item will be treated as label
                self.menu.addAction(self.item(list(item.keys())[0], item))

            prevItem = item

    def _restMenuChain(self, menuChain, layer):
        while layer < len(menuChain):
            menuChain[layer] = None
            layer += 1
    
    def _getPrevMenu(self, menuChain, layer):
        if layer == -1: layer = 0
        while layer >= 0:
            if menuChain[layer] == None:
                layer -= 1
            else:
                return menuChain[layer]

    def _getLabels(self, item, labels):
        if isinstance(labels, str):
            return item[labels]
        elif isinstance(labels, list):
            return [item[l] for l in labels]
        else:
            raise TypeError('Unexpected type:' + type(labels).__name__)

    def item(self, text, item, fmt=None, delegate=None):
        if not fmt == None:
            text = fmt(text)

        if delegate == None:
            return QAction(text, self, triggered=lambda: self.itemSelected(item))
        else:
            return delegate(text, self, item)

    def section(self, text, fmt=None, delegate=None):
        if not fmt == None:
            text = fmt(text)

        if delegate == None:
            tmp = QWidgetAction(self)
            tmp.setDefaultWidget(GroupItem(text))      
            tmp.setEnabled(False)  #disable selectable and clickable
        else:
            tmp = delegate(text, self)
        return tmp
    '''
    def group(self, text, fmt=None, delegate=None):
        #delegate here will not work since it will be destroyed
        if not fmt == None:
                text = fmt(text)

            if delegate == None:
                #could be QMenu(text) here, since it will be destroyed after _createMenu() finish
                #addMenu(QMenu) does not take the ownership of menu
                return text
            else:
                return delegate(text)
    '''
    def group(self, text, fmt=None):
        if not fmt == None:
            text = fmt(text)

        return text        

    def _showDropDown(self):
        if self.menu != None:
            self.menu.popup(QPoint(0, 0))
            gm = self.menu.geometry()
            gs = self.mapToGlobal(self.pos()) - self.pos()
            if self.bottomHeight < gm.height() and self.topHeight > self.bottomHeight:
                y = gs.y() - gm.height()
            else:
                y = gs.y() + self.geometry().height()
            x = gs.x()
            
            self.menu.move(QPoint(x, y))
            self.geometry()
        else:
            self._awaitingData = True

'''SymbolSearch.py
setting = [{'aggregate': {'aggr': 'section', 'id': 'currency', 'label': ['longName', 'exchange', 'primaryExchange'], 'format': self.sectionFormat },  
        'item': {'label': ['secType', 'exchange'], 'format': self.fmt} },
        {'aggregate': {'aggr': 'group', 'id': 'secType', 'label': ['secType', 'exchange'], 
        'isValid': lambda x: x, 'validCol': 'contractMonth', 'format': self.fmt },  
        'item': {'label': 'contractMonth', 'format': lambda x: datetime.strptime(x, '%Y%m').strftime("%b%Y")}},
        {'aggregate': {'aggr': 'section', 'id': 'multiplier', 'label': 'multiplier', 'format': self.mFormat },  
        'item': {'label': 'contractMonth', 'format': lambda x: datetime.strptime(x, '%Y%m').strftime("%b%Y")} }, 
        {'aggregate': {'aggr': 'group', 'id': 'contractMonth', 
        'eval': lambda x: datetime.strptime(x, '%Y%m').strftime("%Y") if x else None,
        'label': 'contractMonth', 
        'isValid': lambda x: x, 'validCol': 'contractMonth', 'format': self.yfmt },  
        'item': {'label': 'contractMonth', 'format': lambda x: datetime.strptime(x, '%Y%m').strftime("%b%Y")} }]
data = [{"conId": 242394532, "secType": "STK", "symbol": "HSI", "contractMonth": "", "lastTradeDateOrContractMonth": "", "localSymbol": "HSI", "exchange": "SMART", "primaryExchange": "VENTURE", "currency": "CAD", "multiplier": "", "longName": "H-SOURCE HOLDINGS LTD", "tradingClass": "HSI"}, 
        {"conId": 324310187, "secType": "FUT", "symbol": "HSI", "contractMonth": "201806", "lastTradeDateOrContractMonth": "20180630", "localSymbol": "HSIQ8", "exchange": "HKFE", "primaryExchange": "", "currency": "HKD", "multiplier": "10", "longName": "Hang Seng Stock Index", "tradingClass": "HSI"}, 
        {"conId": 324310187, "secType": "FUT", "symbol": "HSI", "contractMonth": "201807", "lastTradeDateOrContractMonth": "20180730", "localSymbol": "HSIQ8", "exchange": "HKFE", "primaryExchange": "", "currency": "HKD", "multiplier": "10", "longName": "Hang Seng Stock Index", "tradingClass": "HSI"},
        {"conId": 324310187, "secType": "FUT", "symbol": "HSI", "contractMonth": "201805", "lastTradeDateOrContractMonth": "20180530", "localSymbol": "HSIQ8", "exchange": "HKFE", "primaryExchange": "", "currency": "HKD", "multiplier": "50", "longName": "Hang Seng Stock Index", "tradingClass": "HSI"},
        {"conId": 324310187, "secType": "FUT", "symbol": "HSI", "contractMonth": "201808", "lastTradeDateOrContractMonth": "20180830", "localSymbol": "HSIQ8", "exchange": "HKFE", "primaryExchange": "", "currency": "HKD", "multiplier": "50", "longName": "Hang Seng Stock Index", "tradingClass": "HSI"},
        {"conId": 305074193, "secType": "FUT", "symbol": "HSI", "contractMonth": "201809", "lastTradeDateOrContractMonth": "20180927", "localSymbol": "HSIU8", "exchange": "HKFE",
        "primaryExchange": "", "currency": "HKD", "multiplier": "50", "longName": "Hang Seng Stock Index", "tradingClass": "HSI"}, 
        {"conId": 309359834, "secType": "FUT", "symbol": "HSI", "contractMonth": "201812", "lastTradeDateOrContractMonth": "20181228",
        "localSymbol": "HSIZ8", "exchange": "HKFE", "primaryExchange": "", "currency": "HKD", "multiplier": "50", "longName": "Hang Seng Stock Index", "tradingClass": "HSI"}, 
        {"conId": 327970815, "secType": "FUT", "symbol": "HSI", "contractMonth": "201903",
        "lastTradeDateOrContractMonth": "20190328", "localSymbol": "HSIH9", "exchange": "HKFE", "primaryExchange": "", "currency": "HKD", "multiplier": "50", "longName": "Hang Seng Stock Index", "tradingClass": "HSI"}, 
        {"conId": 309359843, "secType": "FUT",
        "symbol": "HSI", "contractMonth": "201912", "lastTradeDateOrContractMonth": "20191230", "localSymbol": "HSIZ9", "exchange": "HKFE", "primaryExchange": "", "currency": "HKD", "multiplier": "50", "longName": "Hang Seng Stock Index", "tradingClass": "HSI"}, 
        {"conId": 309359846, "secType": "FUT", "symbol": "HSI", "contractMonth": "202012", "lastTradeDateOrContractMonth": "20201230", "localSymbol": "HSIZ0", "exchange": "HKFE", "primaryExchange": "", "currency": "HKD", "multiplier": "50", "longName":
        "Hang Seng Stock Index", "tradingClass": "HSI"}, 
        {"conId": 309359849, "secType": "FUT", "symbol": "HSI", "contractMonth": "202112", "lastTradeDateOrContractMonth": "20211230", "localSymbol": "HSIZ1", "exchange": "HKFE", "primaryExchange": "", "currency": "HKD", "multiplier": "50", "longName": "Hang Seng Stock Index", "tradingClass": "HSI"}, 
        {"conId": 309359839, "secType":
        "FUT", "symbol": "HSI", "contractMonth": "202212", "lastTradeDateOrContractMonth": "20221229", "localSymbol": "HSIZ2", "exchange": "HKFE", "primaryExchange": "", "currency": "HKD", "multiplier": "50", "longName": "Hang Seng Stock Index", "tradingClass": "HSI"}, 
        {"conId": 316263572, "secType": "FUT", "symbol": "HSI", "contractMonth": "202312", "lastTradeDateOrContractMonth": "20231228", "localSymbol": "HSIZ3", "exchange": "HKFE", "primaryExchange": "", "currency": "HKD", "multiplier": "50", "longName": "Hang Seng Stock Index", "tradingClass": "HSI"}, 
        {"conId": 41117892, "secType": "STK", "symbol": "HSI", "contractMonth": "", "lastTradeDateOrContractMonth": "", "localSymbol": "LYME", "exchange": "SMART", "primaryExchange": "SBF", "currency":
        "EUR", "multiplier": "", "longName": "LYXOR HONG KONG HSI-DIST", "tradingClass": "ETF"}]


a = sorted(data, key=lambda x:  (x['longName'], x['currency'], self.secType(x['secType']), x['multiplier'], datetime(1902, 3, 11) if x['lastTradeDateOrContractMonth']=="" \
            else datetime.strptime(x['lastTradeDateOrContractMonth'],'%Y%m%d')))
'''