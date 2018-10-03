class STATUS(object):
    CONNECTED = {'code': 0, 'desc': 'connected with OpenFutuD', 'id': ''}
    CLOSED = {'code': 1, 'desc': 'connection closed', 'id': ''}
    DISCONNECTED = {'code': 2, 'desc': 'disconnected from OpenFutuD', 'id': ''}
    HKTRADE_UNLOCK_FAILED = {'code': 3, 'desc': 'HK trade unlock failed', 'id': ''}
    USTRADE_UNLOCK_FAILED = {'code': 4, 'desc': 'US trade unlock failed', 'id': ''}
    HKCCTRADE_UNLOCK_FAILED = {'code': 5, 'desc': 'HKCC(A股通) trade unlock failed', 'id': ''}
    CNTRADE_UNLOCK_FAILED = {'code': 6, 'desc': 'CN trade unlock failed', 'id': ''}
    HKTRADE_OPENED = {'code': 7, 'desc': 'HK Trade opened', 'id': ''}
    USTRADE_OPENED = {'code': 8, 'desc': 'HK Trade opened', 'id': ''}
    CNTRADE_OPENED = {'code': 9, 'desc': 'HK Trade opened', 'id': ''}
    HKCCTRADE_OPENED = {'code': 10, 'desc': 'HK Trade opened', 'id': ''}
    HKTRADE_CLOSED = {'code': 7, 'desc': 'HK Trade CLOSED', 'id': ''}
    USTRADE_CLOSED = {'code': 8, 'desc': 'HK Trade CLOSED', 'id': ''}
    CNTRADE_CLOSED = {'code': 9, 'desc': 'HK Trade CLOSED', 'id': ''}
    HKCCTRADE_CLOSED = {'code': 10, 'desc': 'HK Trade CLOSED', 'id': ''}
    
    def __init__(self, id):
        self.CONNECTED['id'] = id
        self.CLOSED['id'] = id
        self.DISCONNECTED['id'] = id
        self.HKCCTRADE_OPENED['id'] = id
        self.HKCCTRADE_UNLOCK_FAILED['id'] = id
        self.HKTRADE_OPENED['id'] = id
        self.HKTRADE_UNLOCK_FAILED['id'] = id
        self.USTRADE_OPENED['id'] = id
        self.USTRADE_UNLOCK_FAILED['id'] = id
        self.CNTRADE_OPENED['id'] = id
        self.CNTRADE_UNLOCK_FAILED['id'] = id
        self.CNTRADE_CLOSED['id'] = id
        self.HKCCTRADE_CLOSED['id'] = id
        self.HKTRADE_CLOSED['id'] = id
        self.USTRADE_CLOSED['id'] = id

    def __setattr__(self, *_):
        pass