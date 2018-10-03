from futuquant import *
from ...utils.event import Event
from ...utils.CONST import STATUS
from datetime import datetime


class FTHKTrade(OpenHKTradeContext):
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
        super(FTHKTrade, self).__init__(**kwargs)
        pwd_unlock = '618524'
        ret, msg = self.unlock_trade(pwd_unlock)
        if (ret != RET_OK):
            tmp = self.connectEvent.notify_all(self._con_status.HKTRADE_CLOSED).copy()
            tmp.update({'error': msg})
            self.errorEvent.notify_all(tmp)

    def disconnect(self):
        self.connectEvent.cleanup()
        self.errorEvent.cleanup()
        print('closing')
        self.close()         
            
    def is_connected(self):
        return self._isConnected

    def on_closed(self, conn_id):
        print('closed')
        self._isConnected = False
        self.connectEvent.notify_all(self._con_status.HKTRADE_CLOSED)
        super().on_closed(conn_id)

    def on_connected(self, conn_id):
        print('connected')
        self._isConnected = True
        self.connectEvent.notify_all(self._con_status.HKTRADE_OPENED)
        super().on_connected(conn_id)   

    def on_error(self, conn_id, err):
        self.errorEvent.notify_all(err)
        print(err)
        super().on_error(conn_id, err)     