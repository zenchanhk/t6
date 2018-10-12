import sys
#from .models.IBConnector import IBConnector
#from .models.Symbol import Symbol
#from .models.PlaceOrder import PlaceOrder
from configobj import ConfigObj
from collections import namedtuple
from .utils.tools import copyall
import json
from .utils.Messenger import Messenger
import re
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QDockWidget, QListView, QPushButton, QHBoxLayout, QLabel
from PyQt5.QtCore import Qt
from pyqtgraph.dockarea import *
import qtawesome as qta

import os 
dir_path = os.path.dirname(os.path.realpath(__file__))
import Ice

from concurrent.futures import ProcessPoolExecutor
from multiprocessing import Manager, Queue, Pipe
import threading

# show icon on windows task bar
import ctypes
myappid = 'mycompany.myproduct.subproduct.version' # arbitrary string
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

# =========================================================
#
# The Ice communicator is initialized with Ice.initialize
# The communicator is destroyed once it goes out of scope of the with statement
#
def create_endpoint(name, pipe, ui_queue, data_queue, shared_dict):    
    '''
        name: endpoint's name        
        pipe: actions sending from UI
        ui_queue: status or errors sending from datasource
        data_queue: transfer data to data_handling process
        shared_dict: dict sharing among the processes
    '''
    with Ice.initialize(os.path.join(dir_path, "config.server")) as communicator:
        # install a shutdown handler to release resource
        def shutdown(pipe, communicator):
            while True:
                msg = ui_queue.get()
                if isinstance(msg, dict) and 'action' in msg and msg['action'] == 'shutdown':                    
                    communicator.shutdown()
                    break
        t = threading.Thread(target=shutdown, args=(ui_queue, communicator,))
        t.daemon = True
        t.start()
        # initialization
        adapter = communicator.createObjectAdapter(name + "Adapter")
        adapter.add(Messenger(name, ui_queue, pipe, shared_dict), Ice.stringToIdentity(name))
        adapter.activate()
        communicator.waitForShutdown()


# create multiple processes to handle subscribtion, order_place, and request_historical_data, respectively
def init(ui_queue):    
    with ProcessPoolExecutor(max_workers=5) as executor:
        with Manager() as manager:
            shared_dict = manager.dict()    # store datasource and limiations           
            data_queue = Queue()            # for transfer data
            # request real-time data
            executor.submit(create_endpoint, 'DataCenter', ui_queue, data_queue, shared_dict)
            # for scheduled orders
            executor.submit(create_endpoint, 'OrderPlace', ui_queue, data_queue, shared_dict)
            # request historical data
            executor.submit(create_endpoint, 'LimitedReq', ui_queue, data_queue, shared_dict)


def read_datasource_config():
    cfgfile = os.path.join(dir_path, 'config.ini') 
    cfg = ConfigObj(cfgfile, encoding='UTF8') 
    ds = cfg['datasource']


# Runner lives on the runner thread
class MessageReceiver(QtCore.QObject, threading.Thread):
    
    msg_from_job = QtCore.pyqtSignal(object)

    def __init__(self, queue, parent=None):
        """
        :param pipe_list: pipe list for communicating between Qt and processes

        """
        QtCore.QObject.__init__(self, parent)
        threading.Thread.__init__(self)
        self._queue = queue

    def run(self):
        while True:
            print('receiving...')
            msg = self._queue.get()
            self.msg_from_job.emit(msg)
            if msg == 'done':
                break
                

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, pipes, msg_receiver, endpoints, datasources, parent=None):
        super(MainWindow, self).__init__(parent)
        self._pipes = pipes
        self._msg_receiver = msg_receiver
        self._msg_receiver.daemon = True
        self._msg_receiver.start()

        bar = self.menuBar()
        file = bar.addMenu("File")
        file.addAction("Quit")
        file = bar.addMenu("Help")
        file.addAction("About")

        area = DockArea()
        self.setCentralWidget(area)
        tmp = None
        for ep in reversed(endpoints):
            d = Dock(ep['name'], size=(1, 1))
            if tmp is None:            
                area.addDock(d, 'top')
            else:
                area.addDock(d, 'above', tmp)
            tmp = d

        tmp = None
        for ds in reversed(datasources):
            d = Dock(ds['name'], size=(1, 1))
            if tmp is None:            
                area.addDock(d, 'bottom')
            else:
                area.addDock(d, 'above', tmp)
            tmp = d

        self.setWindowIcon(qta.icon('mdi.owl', options=[{'color': 'green'}]))
        #self.setWindowIcon(QtGui.QIcon('d:\\ib\\t6\\main\\ui\\images\\owl-128.png'))
        self.setWindowTitle("Datasource Manager")

    def update_ui(self, msg):
        pass

    def connect(self, name):
        self._pipes[name].send({'action': 'connect'})

    def disconnect(self, name):
        self._pipes[name].send({'action': 'connect'})

def main():
    ui_queue = Queue()
    pipes = [{'ft1': Pipe()}]
    msg_receiver = MessageReceiver(ui_queue)
    # initialize data hanlding process
    # init(ui_queue)
    eps = [{'name': 't1'}, {'name': 't2'}, {'name': 't3'}]
    ds = [{'name': 'd1'}, {'name': 'd2'}, {'name': 'd3'}]
    app=QtWidgets.QApplication([])
    ex = MainWindow(pipes, msg_receiver, eps, ds)
    
    ex.show()
    app.exec_()

'''
    # with open("d:/ib/t2/data/stocks.txt", 'r', encoding='UTF-8') as f:
    #    b = ['HK.{0}'.format(re.split(r'\t+', x.strip(' \t\n\r'))[0]) for x in f if len(x.strip())>0]
    # del b[0]

    ft1 = FTController(id='ft1', host='127.0.0.1', port=11111)
    # ft2 = FTController(id='ft2', host='127.0.0.1', port=11112)
    ft1.connect()
    ft1.open_trade('HK')
    # ft2.connect()

    limit = {"no_of_stocks": 15, "interval": 30}

    # b = ['US.AAPL', 'US.QQQ']
    #b = ['HK.00700','HK.02318']
    # b = ['HK.00700','HK.02318','HK.03333','HK.00939','HK.00941','HK.01299','HK.00388','HK.00005','HK.00175']
    # ft1.request_history_data(b[:70], limit, start='2018-09-19', end='2018-09-19')
    # ft2.request_history_data(b[70:], limit, start='2018-09-19', end='2018-09-19')
    # ft1.scan(b[0:9], '5m', limit, date='2018-09-26')
    # ft2.scan(b[2:4], '1m', limit, date='2018-09-24')

    order_list = [{'Code':'HK.00700', 'Qty':1, 'Price': '300', 'TradeSide': 'BUY', 'Market': 'HK'}]
    ft1.place_order(json.dumps(order_list), limit)
    '''