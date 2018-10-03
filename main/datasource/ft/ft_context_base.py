from ...utils.event import Event
from ...utils.CONST import STATUS

class FTContextBase:
    _name = 'FuTu'          # show on tabbar
    _vid = 'FT'             # identify vendor
    _vendor = 'FuTu Co.'    # vendor

    def __init__(self, id):
        self._kwargs = {'host': host, 'port': port}
        
        self._host = host
        self._port = port
        self._id = id
        self._con_status = STATUS(id)       # init connection status with id
        self.connectEvent = Event()
        self.errorEvent = Event()
        

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