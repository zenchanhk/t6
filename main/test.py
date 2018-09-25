#!/usr/bin/env python


#############################################################################
##
## Copyright (C) 2013 Riverbank Computing Limited.
## Copyright (C) 2010 Nokia Corporation and/or its subsidiary(-ies).
## All rights reserved.
##
## This file is part of the examples of PyQt.
##
## $QT_BEGIN_LICENSE:BSD$
## You may use this file under the terms of the BSD license as follows:
##
## "Redistribution and use in source and binary forms, with or without
## modification, are permitted provided that the following conditions are
## met:
##   * Redistributions of source code must retain the above copyright
##     notice, this list of conditions and the following disclaimer.
##   * Redistributions in binary form must reproduce the above copyright
##     notice, this list of conditions and the following disclaimer in
##     the documentation and/or other materials provided with the
##     distribution.
##   * Neither the name of Nokia Corporation and its Subsidiary(-ies) nor
##     the names of its contributors may be used to endorse or promote
##     products derived from this software without specific prior written
##     permission.
##
## THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
## "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
## LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
## A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
## OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
## SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
## LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
## DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
## THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
## (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
## OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE."
## $QT_END_LICENSE$
##
#############################################################################

from PyQt5 import QtCore
from PyQt5.QtCore import Qt, pyqtSignal, QPoint, QTimer
from PyQt5.QtGui import QKeySequence, QColor
from PyQt5.QtWidgets import (QAction, QActionGroup, QApplication, QFrame,
        QLabel, QMainWindow, QMenu, QMessageBox, QSizePolicy, QVBoxLayout,
        QWidget, QLineEdit, QHBoxLayout, QWidgetAction, QPushButton)
import qtawesome as qta
import os
import time
from datetime import datetime
#os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
os.environ["QT_SCALE_FACTOR"] = "1.5"
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

    def __init__(self, parent):
       super().__init__(parent)

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

class SymbolSearch(QWidget):
    enterPressed = pyqtSignal(str)
    cancelSearch = pyqtSignal()
    selected = pyqtSignal(object)

    _placeholder = 'placeholder'
    _loading = False
    _data = []
    _setting = []
    _aggregateTypes = ['section', 'group']
    isMenu = {'group': True, 'section': False}
    aggrProps = {'group': {'isMenu': True, 'fields': ['id', 'by']},
                'section': {'isMenu': False, 'fields': []}}

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
        lay.addWidget(self.input)

        self.label = MyLabel(self)
        self.label.setText(self.placeholder)
        self.label.setMargin(3)
        self.label.clicked.connect(self.focusInHandler)
        self.label.setGeometry(self.input.geometry().x(), self.input.geometry().y(),
            self.input.geometry().width(), self.input.geometry().height())
        fp = self.label.palette()
        fp.setColor(self.label.foregroundRole(), QColor('grey'))
        self.label.setPalette(fp)
               
        self.search_icon = qta.icon('fa.search', color='grey')
        self.search_action = QAction(self.search_icon, '', self, triggered=self.keyPressHandler)
        self.spin_icon = qta.icon('fa.spinner', color='blue',
                     animation=qta.Spin(self.input))
        self.waiting_action = QAction(self.spin_icon, '', self)
        self.input.setClearButtonEnabled(True)
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
            self.label.setText(value)
            self._placeholder = value

    @QtCore.pyqtProperty(bool)
    def loading(self):
        return self._loading

    @loading.setter
    def loading(self, value):
        if value != self._loading:
            self._loading = value
        if value:
            self.input.removeAction(self.search_action)
            self.input.addAction(self.waiting_action, QLineEdit.TrailingPosition)
        else:
            self.input.removeAction(self.waiting_action)
            self.input.addAction(self.search_action, QLineEdit.TrailingPosition)

    @QtCore.pyqtProperty(list)
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        if value != self._data:
            self._data = value
            self._createMenu()

    @QtCore.pyqtProperty(list)
    def setting(self):
        return self._setting

    @setting.setter
    def setting(self, value):
        if value != self._data:
            self._setting = value

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
        self.enterPressed.emit(e)
        self._showDropDown()

    def cancelHandler(self, e=None):
        if self.loading:
            self.loading = False
        self.cancelSearch.emit()

    def focusInHandler(self):
        self.label.hide()
        self.input.setFocus()

    def focusOutHandler(self):
        if self.menu == None:
            self.label.show()
        if self.menu != None and not self.menu.isVisible():
            self.label.show()

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
                    curMenu.addAction(self.item(self._getLabels(item, curIA['label']), fmt, delegate))
            else:
                #if no setting, the first key of item will be treated as label
                self.menu.addAction(self.item(list(item.keys()[0])))

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

    def item(self, text, fmt=None, delegate=None):
        if not fmt == None:
            text = fmt(text)

        if delegate == None:
            return QAction(text, self)
        else:
            return delegate(text, self)

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

class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()

        widget = QWidget()
        self.setCentralWidget(widget)

        topFiller = QWidget()
        topFiller.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.infoLabel = QLabel(
                "<i>Choose a menu option, or right-click to invoke a context menu</i>",
                alignment=Qt.AlignCenter)
        self.infoLabel.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)

        bottomFiller = QWidget()
        bottomFiller.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        vbox = QVBoxLayout()
        vbox.setContentsMargins(5, 5, 5, 5)
        vbox.addWidget(topFiller)
        vbox.addWidget(self.infoLabel)
        vbox.addWidget(bottomFiller)

        self.ss = SymbolSearch(self)
        self.ss.enterPressed.connect(self.enter)
        self.ss.setting = [{'aggregate': {'aggr': 'section', 'id': 'currency', 'label': ['longName', 'exchange', 'primaryExchange'], 'format': self.sectionFormat },  
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
        #print(a)
        self.ss.data = a
        self.ss.enterPressed.connect(self.ep)
        self.ss.cancelSearch.connect(self.ch)
        i = MyLineEdit(self)
        #datatime.strftime(i, '')
        i.placeholderText = 'test'
        vbox.addWidget(self.ss)
        vbox.addWidget(i)
        b = QPushButton(self)
        b.setText("Test")
        #b.clicked.connect(self.showmenu)
        vbox.addWidget(b)
        widget.setLayout(vbox)

        self.createActions()
        self.createMenus()

        message = "A context menu is available by right-clicking"
        self.statusBar().showMessage(message)

        self.setWindowTitle("Menus")
        self.setMinimumSize(160,160)
        self.resize(480,320)
        self.setStyleSheet('QMenu::item:disabled{background-color:red; color:black}')
        #self.setStyleSheet('QMenu::item:enabled{margin-left: 10px}')

    def ep(self, text):
        print('enter pressed: ' + text)

    def ch(self):
        print('search cancelled')

    def enter(self, e):
        self.timer = QTimer()
        print(e)
        self.ss.loading = True
        self.sec = 0
        self.timer.timeout.connect(self.__t)
        self.timer.start(1000)
        
    def __t(self):
        self.sec += 1
        if self.sec > 2:
            self.timer.stop()
            self.ss.loading = False

    def secType(self, x):
        if x == 'STK':
            return 0
        elif x == 'FUT':
            return 1
    def yfmt(self, x):
        return 'Year ' + datetime.strptime(x, '%Y%m').strftime("%Y")

    def mFormat(self, m):
        return 'Multiplier: ' + str(m)

    def sectionFormat(self, lbls):
        '''
            0. longName
            1. exchange
            2. primaryExchange
        '''
        if lbls[1] == 'SMART':
            return lbls[0] + " - " + lbls[2]
        else:
            return lbls[0] + " - " + lbls[1]

    def fmt(self, lbls):
        """convert security type"""
        result = {
            'STK': lambda x: 'Stock (SMART)' if x == 'SMART' else 'Stock',
            'FUT': lambda x: 'Future',
            'CASH': lambda x: 'Exchange',
        }[lbls[0]](lbls[1])
        return result

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.addAction(self.cutAct)
        menu.addAction(self.copyAct)
        menu.addAction(self.pasteAct)
        self.pasteAct.setEnabled(False)
        menu.exec_(event.globalPos())

    def newFile(self):
        self.infoLabel.setText("Invoked <b>File|New</b>")

    def open(self):
        self.infoLabel.setText("Invoked <b>File|Open</b>")
        	
    def save(self):
        self.infoLabel.setText("Invoked <b>File|Save</b>")

    def print_(self):
        self.infoLabel.setText("Invoked <b>File|Print</b>")

    def undo(self):
        self.infoLabel.setText("Invoked <b>Edit|Undo</b>")

    def redo(self):
        self.infoLabel.setText("Invoked <b>Edit|Redo</b>")

    def cut(self):
        self.infoLabel.setText("Invoked <b>Edit|Cut</b>")

    def copy(self):
        self.infoLabel.setText("Invoked <b>Edit|Copy</b>")

    def paste(self):
        self.infoLabel.setText("Invoked <b>Edit|Paste</b>")

    def bold(self):
        self.infoLabel.setText("Invoked <b>Edit|Format|Bold</b>")

    def italic(self):
        self.infoLabel.setText("Invoked <b>Edit|Format|Italic</b>")

    def leftAlign(self):
        self.infoLabel.setText("Invoked <b>Edit|Format|Left Align</b>")

    def rightAlign(self):
        self.infoLabel.setText("Invoked <b>Edit|Format|Right Align</b>")

    def justify(self):
        self.infoLabel.setText("Invoked <b>Edit|Format|Justify</b>")

    def center(self):
        self.infoLabel.setText("Invoked <b>Edit|Format|Center</b>")

    def setLineSpacing(self):
        self.infoLabel.setText("Invoked <b>Edit|Format|Set Line Spacing</b>")

    def setParagraphSpacing(self):
        self.infoLabel.setText("Invoked <b>Edit|Format|Set Paragraph Spacing</b>")

    def about(self):
        self.infoLabel.setText("Invoked <b>Help|About</b>")
        QMessageBox.about(self, "About Menu",
                "The <b>Menu</b> example shows how to create menu-bar menus "
                "and context menus.")

    def aboutQt(self):
        self.infoLabel.setText("Invoked <b>Help|About Qt</b>")

    def createActions(self):
        self.newAct = QAction("&New", self, shortcut=QKeySequence.New,
                statusTip="Create a new file", triggered=self.newFile)

        self.openAct = QAction("&Open...", self, shortcut=QKeySequence.Open,
                statusTip="Open an existing file", triggered=self.open)

        self.saveAct = QAction("&Save", self, shortcut=QKeySequence.Save,
                statusTip="Save the document to disk", triggered=self.save)

        self.printAct = QAction("&Print...", self, shortcut=QKeySequence.Print,
                statusTip="Print the document", triggered=self.print_)

        self.exitAct = QAction("E&xit", self, shortcut="Ctrl+Q",
                statusTip="Exit the application", triggered=self.close)

        self.undoAct = QAction("&Undo", self, shortcut=QKeySequence.Undo,
                statusTip="Undo the last operation", triggered=self.undo)

        self.redoAct = QAction("&Redo", self, shortcut=QKeySequence.Redo,
                statusTip="Redo the last operation", triggered=self.redo)

        self.cutAct = QAction("Cu&t", self, shortcut=QKeySequence.Cut,
                statusTip="Cut the current selection's contents to the clipboard",
                triggered=self.cut)

        self.copyAct = QAction("&Copy", self, shortcut=QKeySequence.Copy,
                statusTip="Copy the current selection's contents to the clipboard",
                triggered=self.copy)

        self.pasteAct = QAction("— Paste —————", self, shortcut=QKeySequence.Paste,
                statusTip="Paste the clipboard's contents into the current selection",
                triggered=self.paste)

        self.boldAct = QAction("&Bold", self, checkable=True,
                shortcut="Ctrl+B", statusTip="Make the text bold",
                triggered=self.bold)

        boldFont = self.boldAct.font()
        boldFont.setBold(True)
        self.boldAct.setFont(boldFont)

        self.italicAct = QAction("&Italic1", self, checkable=True,
                shortcut="Ctrl+I", statusTip="Make the text italic",
                triggered=self.italic)

        italicFont = self.italicAct.font()
        italicFont.setItalic(True)
        self.italicAct.setFont(italicFont)

        self.setLineSpacingAct = QAction("Set &Line Spacing...", self,
                statusTip="Change the gap between the lines of a paragraph",
                triggered=self.setLineSpacing)

        self.setParagraphSpacingAct = QAction("Set &Paragraph Spacing...",
                self, statusTip="Change the gap between paragraphs",
                triggered=self.setParagraphSpacing)

        self.aboutAct = QAction("&About", self,
                statusTip="Show the application's About box",
                triggered=self.about)

        self.aboutQtAct = QAction("About &Qt", self,
                statusTip="Show the Qt library's About box",
                triggered=self.aboutQt)
        self.aboutQtAct.triggered.connect(QApplication.instance().aboutQt)

        self.leftAlignAct = QAction("&Left Align", self, checkable=True,
                shortcut="Ctrl+L", statusTip="Left align the selected text",
                triggered=self.leftAlign)

        self.rightAlignAct = QAction("&Right Align", self, checkable=True,
                shortcut="Ctrl+R", statusTip="Right align the selected text",
                triggered=self.rightAlign)

        self.justifyAct = QAction("&Justify", self, checkable=True,
                shortcut="Ctrl+J", statusTip="Justify the selected text",
                triggered=self.justify)

        self.centerAct = QAction("&Center", self, checkable=True,
                shortcut="Ctrl+C", statusTip="Center the selected text",
                triggered=self.center)

        self.alignmentGroup = QActionGroup(self)
        self.alignmentGroup.addAction(self.leftAlignAct)
        self.alignmentGroup.addAction(self.rightAlignAct)
        self.alignmentGroup.addAction(self.justifyAct)
        self.alignmentGroup.addAction(self.centerAct)
        self.leftAlignAct.setChecked(True)

    def createMenus(self):
        self.fileMenu = self.menuBar().addMenu("&File")
        self.fileMenu.addAction(self.newAct)
        self.fileMenu.addAction(self.openAct)
        self.fileMenu.addAction(self.saveAct)
        self.fileMenu.addAction(self.printAct)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.exitAct)

        self.editMenu = self.menuBar().addMenu("&Edit")
        self.editMenu.addAction(self.undoAct)
        self.editMenu.addAction(self.redoAct)
        self.editMenu.addSeparator()
        self.editMenu.addAction(self.cutAct)
        self.editMenu.addAction(self.copyAct)
        self.editMenu.addAction(self.pasteAct)
        self.editMenu.addSeparator()

        self.helpMenu = self.menuBar().addMenu("&Help")
        self.helpMenu.addAction(self.aboutAct)
        self.helpMenu.addAction(self.aboutQtAct)

        #self.formatMenu = self.editMenu.addMenu("&Format")
        self.formatMenu = QMenu("&Format")
        self.editMenu.addMenu(self.formatMenu)
        '''
        self.formatMenu.addAction(self.boldAct)
        self.formatMenu.addAction(self.italicAct)
        self.formatMenu.addSeparator().setText("Alignment")
        self.formatMenu.addAction(self.leftAlignAct)
        self.formatMenu.addAction(self.rightAlignAct)
        self.formatMenu.addAction(self.justifyAct)
        self.formatMenu.addAction(self.centerAct)
        self.formatMenu.addSeparator()
        self.formatMenu.addAction(self.setLineSpacingAct)
        self.formatMenu.addAction(self.setParagraphSpacingAct)
        self.editMenu.addMenu(self.formatMenu)
        self.editMenu.actions()'''

if __name__ == '__main__':

    import sys

    app = QApplication(sys.argv)
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())