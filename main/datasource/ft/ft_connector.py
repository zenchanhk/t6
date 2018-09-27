from futuquant import *
from ...utils.event import Event
from datetime import datetime


class ERROR(object):
    NO_MARKET_DATA = {'code': 4, 'desc': 'No market data during competing live session'}
    
    def __setattr__(self, *_):
        pass


class STATUS(object):
    CONNECTED = {'code': 0, 'desc': 'connected with OpenFutuD', 'id': ''}
    CLOSED = {'code': 1, 'desc': 'connection closed', 'id': ''}
    DISCONNECTED = {'code': 2, 'desc': 'disconnected from OpenFutuD', 'id': ''}
    
    def __init__(self, id):
        self.CONNECTED['id'] = id
        self.CLOSED['id'] = id
        self.DISCONNECTED['id'] = id

    def __setattr__(self, *_):
        pass


ERROR = ERROR()


class FTConnector(OpenQuoteContext):
    _name = 'FuTu'          # show on tabbar
    _vid = 'FT'             # identify vendor
    _vendor = 'FuTu Co.'    # vendor

    def __init__(self, id, host, port):
        kwargs = {'host': host, 'port': port}
        
        self._host = host
        self._port = port
        self._id = id
        self._con_status = STATUS(id)       # init connection status with id
        self.connectEvent = Event()
        self.errorEvent = Event()
        super(FTConnector, self).__init__(**kwargs)

    def disconnect(self):
        self.connectEvent.cleanup()
        self.errorEvent.cleanup()
        print('closing')
        self.close()
        self._isConnected = False 
        self.connectEvent.notify_all(self._con_status.CONNECTED)

    def is_connected(self):
        return self._isConnected

    def on_closed(self, conn_id):
        print('closed')
        super().on_closed(conn_id)

    def on_connected(self, conn_id):
        print('connected')
        self._isConnected = True
        self.connectEvent.notify_all(self._con_status.CONNECTED)
        super().on_connected(conn_id)   

    def on_error(self, conn_id, err):
        self.errorEvent.notify_all(err)
        print(err)
        super().on_error(conn_id, err) 

    '''
    def on_activate(self, conn_id, now):
        #print(datetime.strftime(now,'%m%d %H:%M:%S'))
        super().on_activate(conn_id, now)
    '''