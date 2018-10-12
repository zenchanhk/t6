from atom.api import Atom, Unicode, Range, Bool, Value, Int, Tuple, observe, ContainerList
import enaml
from enaml.qt.qt_application import QtApplication

import os 
dir_path = os.path.dirname(os.path.realpath(__file__))
import Ice

from concurrent.futures import ProcessPoolExecutor
from multiprocessing import Manager, Queue, Pipe
import threading

# show icon on windows task bar
import ctypes
myappid = 'stock.backend' # arbitrary string
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

# include enamlx
import enamlx
enamlx.install()

from .utils.Messenger import Messenger
import pickle
import enum

class Position(enum.IntEnum):
    TOP = 0
    BOTTOM = 1

class Status(enum.IntEnum):
    CONNECTED = 0
    DISCONNECTED = 1
    RETRYING = 2
    ERROR = 3

class MessageReceiver(threading.Thread):
    
    def __init__(self, queue, parent=None):
        """
        :param queue: receive messages from processes

        """
        threading.Thread.__init__(self)
        self._queue = queue

    def run(self):
        while True:
            print('receiving...')
            msg = self._queue.get()
            eval(msg)


class ListModel(Atom):
    lst = ContainerList()
    def add(self, item, position=Position.TOP):
        if position == Position.TOP:
            self.lst.insert(0, item)      
        elif position == Position.BOTTOM:
            self.lst.add(item)

    def remove(self, item):
        self.lst.remove(item)

    def clear(self):
        self.lst = ContainerList()

class EndPoint(Atom):
    name = Unicode()
    status = ListModel()

class Datasource(Atom):
    name = Unicode()
    status = Int(1)
    message = ListModel()

class Action:
    def __init__(self, pipes):
        self._pipes = pipes
    
    def send_action(self, statement):
        for p in self._pipes:
            p.send(statement)

# =========================================================
# create multiple processes to handle subscribtion, order_place, and request_historical_data, respectively
#
def init(c2p_queue, endpoints):    
    with ProcessPoolExecutor(max_workers=5) as executor:
        with Manager() as manager:
            shared_dict = manager.dict()    # store datasource and limiations           
            data_queue = Queue()            # for transfer data, only data handler process receives data
            for ep in endpoints:            
                executor.submit(create_endpoint, ep['pipe'], c2p_queue, data_queue, shared_dict)

# =========================================================
#
# The Ice communicator is initialized with Ice.initialize
# The communicator is destroyed once it goes out of scope of the with statement
#
def create_endpoint(name, pipe, c2p_queue, data_queue, shared_dict):    
    '''
        name: endpoint's name        
        pipe: actions sending from UI
        c2p_queue: status or errors sending from datasource, child to parent
        data_queue: transfer data to data_handling process
        shared_dict: dict sharing among the processes
    '''
    with Ice.initialize(os.path.join(dir_path, "config.server")) as communicator:        
        # initialization
        adapter = communicator.createObjectAdapter(name + "Adapter")
        adapter.add(Messenger(name, c2p_queue, pipe, shared_dict), Ice.stringToIdentity(name))
        adapter.activate()
        communicator.waitForShutdown()

# ========================================================
# main function
#
def main():
    # child to parent queue for transfering status and message
    c2p_queue = Queue()
    # create thread to receive message from processes
    msg_rcver = MessageReceiver(c2p_queue)
    msg_rcver.daemon = True
    msg_rcver.start()
    # create ICE end points for UI
    endpoints = [{'name':'DataCenter', 'pipe': []},    # request real-time data
                 {'name':'OrderPlace', 'pipe': []},    # for scheduled orders
                 {'name':'LimitedReq', 'pipe': []}]    # request historical data
    ep_model = ListModel()
    p_ins = []
    for ep in endpoints:
        p_in, p_out = Pipe()
        p_ins.append(p_in)
        ep['pipe'].append(p_out)
        ep_model.add(EndPoint(name=ep['name']))
    # create process for various purpose
    # init(c2p_queue, endpoints)
    # create action for UI sending action to process through pipe
    action = Action(pipes=p_ins)
    # create datasource for UI
    ds_model = ListModel()
    i = 0
    for ds in datasources:
        ds_model.add(Datasource(name=ds['name']+' - '+ds['vendor'], status=i))
        i += 1
    # starting up UI
    with enaml.imports():
        from .ui.main import Main
    app = QtApplication()
    view = Main(datasources1=ds_model, endpoints1=ep_model, action=action)
    view.show()
    app.start()


'''
    first layer: vendor ID
    second layer: general and level
    three layer: function name, if value is a tuple, then would be frequency within a period
                if value is number, that would be request limitation 
'''
limitaion = {
    'futu':
    {
        'general': 
            {'subscribe_kline': 100,
            'get_plate_list': (10,30),
            'request_history_kline': (10,30),
            'place_order': (15,30),
            'unlock_trade': (10,30),
            'modify_order': (20,30),
            'change_order': (20,30),
            'history_order_list_query': (10,30),
            'history_deal_list_query': (10,30),
            },
        'level':
            {'level1':
                {'get_market_snapshot': {'freq': (30,30), 'no': 400}},
            'level2':
                {'get_market_snapshot': {'freq': (20,30), 'no': 300}},
            'level3':
                {'get_market_snapshot': {'freq': (10,30), 'no': 200}},
            }
    },
    'ib':
    {
        'general':
            {
                'request_history': (60, 600),
                'request_history_same_contract': (6, 2),
            }
    }    
}
datasources = [
    {
        'name': 'CaoXiao',
        'vendor': 'futu',
        'port': 11111,
        'level': 2        
    },
    {
        'name': 'WHCHAN',
        'vendor': 'futu',
        'port': 11112,
        'level': 2        
    },
    {
        'name': 'Winton',
        'vendor': 'futu',
        'port': 11113,
        'level': 2        
    },
    {
        'name': 'Winton',
        'vendor': 'ib',
        'port': {'TWS': {'PAPER': 7497, 'REAL': 7496},
                'IBG': {'PAPER': 7497, 'REAL': 7496}},
    },
]