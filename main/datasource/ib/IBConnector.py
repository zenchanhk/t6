import sys
import collections
from ib_insync import *
import asyncio
import threading
from threading import Timer
import datetime
import time
import json

util.patchAsyncio()

class NETWORK(object):
    CONNECTED = {'code': 2, 'desc': 'Network ready'}
    DISCONNECTED = {'code': 3, 'desc': 'Network broken'}
    
    def __setattr__(self, *_):
        pass

class IBServerConnectivity(object):  
    CONNECTION_LOST = {'code': 5, 'desc': ['Connectivity between IB and Trader Workstation has been lost',
        'Connectivity between Trader Workstation and server is broken',
        'data farm connection is broken']}
    CONNECTION_REESTABLISHED = {'code': 4, 'desc': ['Connectivity between IB and Trader Workstation has been restored - data maintained',
        'data farm connection is OK']}
    
    def __setattr__(self, *_):
        pass

class ERROR(object):
    NO_MARKET_DATA = {'code': 4, 'desc': 'No market data during competing live session'}
    
    def __setattr__(self, *_):
        pass

class ACTION(object):
    RECONNECT = {'action': 1, 'timer': 10, 'desc': 'Attempting to connect to TWS/IBG in'}
    CONNECT = {'action': 0, 'desc': 'Connecting to TWS/IBG...'}
    
    def __setattr__(self, *_):
        pass

class STATUS(object):
    CONNECTED = {'code': 0, 'desc': 'connected with TWS/IBGateway', 'port': 0, 'account': ''}
    DISCONNECTED = {'code': 1, 'desc': 'disconnected from TWS/IBGateway'}
    
    def __setattr__(self, *_):
        pass

IBServerConnectivity = IBServerConnectivity()
NETWORK = NETWORK()
ACTION = ACTION()
STATUS = STATUS()
ERROR = ERROR()

class IBConnector:
    class Evt:
        def __init__(self):
            self.events = set()
        def __add__(self, event):
            self.events.add(event)
            return self
        def __sub__(self, event):
            self.events.remove(event)
            return self
        def notifyAll(self, msg):
            for e in self.events:
                e(msg)

    def __init__(self, config):
        self.connectEvent = self.Evt()
        self.contractEvent = self.Evt()
        #start a new thread with a new asyncio event loop
        self.loop = asyncio.new_event_loop()
        def f(loop):
            asyncio.set_event_loop(loop)
            loop.run_forever()
        t = threading.Thread(target=f, args=(self.loop,))
        t.start()

        self.ports = []   #7496 for real tradin, 7497 for paper trading
        self.port_names = []
        self.port_used_idx = 0  #to indicate which port is used
        #read ports
        if 'IB' in config and 'ports' in config['IB']:
            ports = config['IB']['ports']
            for key in ports.keys():
                self.ports.append(ports[key])
                self.port_names.append(key)
        else:
            self.ports = [7497, 7496]
            self.port_names = ['PAPER', 'LIVING']
        #network status
        self.serverConnected = False #to set a flag to check if test server connectivity        
        self.networkConnected = True
        self.website = config['network']['websites']
        self.check_interval_disconnected = 1
        self.check_interval_connected = 5
        self.checkThread = threading.Thread(target=self.checkNetwork)
        self.checkThread.start()

        self.api_errs = []
        self.max_apierrs = 2
        self.status_cb = None       #js callback for status 
        self.last_msg = None       
                
        self.id = 1         #connection clientId
        self.reconnect_interval = 10.0 #interval for reconnecting in case of disconnected
        self.connecting = False
        self.ib = None
        #self.connectIB() 
        self.PIB = collections.namedtuple('PIB', ['IB', 'loop'])
        print('after init')

    def addListener(self, func):
        func = 0

    def checkNetwork(self):
        try:
            while True:
                if self.networkConnected:
                    time.sleep(self.check_interval_connected)
                else:
                    time.sleep(self.check_interval_disconnected)
                self.networkConnected = self.__checkWebsite()
                
                if self.networkConnected:
                    self.__callback(NETWORK.CONNECTED)
                    if not self.serverConnected:
                        future = asyncio.run_coroutine_threadsafe(self.testIBServerConnectivity(), self.loop)
                        future.result()
                else:
                    self.__callback(NETWORK.DISCONNECTED)
                    self.serverConnected = False
        except Exception as e:
            print(e)
        

    def __checkWebsite(self):
        try:
            import httplib
        except:
            import http.client as httplib
        
        conn = httplib.HTTPConnection(self.website, timeout=5)
        try:
            conn.request("HEAD", "/")
            conn.close()
            return True
        except:
            conn.close()
            return False

    def getStatus(self, val, js_cb):
        if hasattr(js_cb, 'Call'):
            self.status_cb = js_cb   
            if (self.last_msg != None):
                self.__callback(self.last_msg)
                #resend STATUS.CONNECTED in case of getStatus
                if (self.last_msg != STATUS.CONNECTED and self.ib and self.ib.is_connected()):
                    STATUS.CONNECTED['port'] = self.ports[self.port_used_idx]
                    STATUS.CONNECTED['account'] = self.port_names[self.port_used_idx]
                    self.__callback(STATUS.CONNECTED)
                    if self.serverConnected:
                        self.__callback(IBServerConnectivity.CONNECTION_REESTABLISHED)

    def connect(self):
        t = threading.Thread(target=self.connectIB)
        t.start()

    def connectIB(self):
        if (not self.connecting) and \
            ((self.ib != None and not self.ib.is_connected()) or self.ib == None):
            self.__callback(ACTION.CONNECT)
            self.connecting = True
            future = asyncio.run_coroutine_threadsafe(self.__connectIB(), self.loop)
            #future.result() #wait for result

    async def __connectIB(self):  
        try:
            self.ib = IB()  #Very important to put initialization here to run in a same loop
            self.ib.connectedEvent += self.onConnected
            self.ib.disconnectedEvent += self.onDisconnected 
            self.ib.client.apiError += self.onApiError
            self.ib.errorEvent += self.onError            
            
            await self.ib.connectAsync('127.0.0.1', self.ports[self.port_used_idx], self.id)
            
            self.connecting = False
            if (self.ib.isConnected()):
                self.onConnected()
                self.connectEvent.notifyAll(STATUS.CONNECTED)
            
            await self.testIBServerConnectivity()
            #self.__callback(IBServerConnectivity.CONNECTION_REESTABLISHED)
        except Exception as e:
            print("connectIB err:")
            print(e)  
            #to enable to reconnect
            #self.connecting = False 
            await self.handleExceptions(e)
            print('finished')
            #self.connecting = False

    def onError(self, reqId, errorCode, errorString, contract):
        print('onError: ')
        print(errorString)
        print(contract)
        if self.ib.is_connected():
            if self.strFind(errorString, IBServerConnectivity.CONNECTION_LOST['desc']) != -1:
                self.onConnected()
                self.__callback(IBServerConnectivity.CONNECTION_LOST)
                self.serverConnected = False
            elif self.strFind(errorString, IBServerConnectivity.CONNECTION_REESTABLISHED['desc']) != -1:
                self.onConnected()
                self.__callback(IBServerConnectivity.CONNECTION_REESTABLISHED)
                self.serverConnected = True
        #elif errorString.find(ERROR.NO_MARKET_DATA['desc']) != -1:
        #    self.__callback(ERROR.NO_MARKET_DATA)
        if (reqId != -1):
            #Not to use the following line as it will create two more threads
            #self.contractEvent.notifyAll({'contract': contract, 'reqId': reqId, 'code': errorCode, 'message': errorString})
            if contract != None:
                self.contractEvent.notifyAll({'conId': contract.conId, 'reqId': reqId, 'code': errorCode, 'message': errorString})
            else:
                self.contractEvent.notifyAll({'reqId': reqId, 'code': errorCode, 'message': errorString})

    def onConnected(self):
        STATUS.CONNECTED['port'] = self.ports[self.port_used_idx]
        STATUS.CONNECTED['account'] = self.port_names[self.port_used_idx]
        self.__callback(STATUS.CONNECTED)
        self.connectEvent.notifyAll(STATUS.CONNECTED)
        print('connected')

    def onDisconnected(self):
        if (not self.connecting):
            self.__callback(STATUS.DISCONNECTED)
            self.connectEvent.notifyAll(STATUS.DISCONNECTED)
            #self.attempReconnect(self.reconnect_interval)
            self.connectIB()
        print('disconnected')

    def __callback(self, msg):
        self.last_msg = msg
        try:
            if hasattr(self.status_cb, 'Call'):
                self.status_cb.Call(json.dumps(msg, default=lambda o:o.__dict__ ))
        except Exception as e:
            print(e)
        
            
    def onApiError(self, err):
        if err.find('already in use') != -1:
            self.id += 1
        
        if len(self.api_errs) < self.max_apierrs:
            self.api_errs.append(err)
        else:
            self.api_errs.pop(0)
            self.api_errs.append(err)
    
    def findErr(self, str):
        for r in self.api_errs:
            if r.find(str) != -1:
                return True
        return False

    async def handleExceptions(self, e):
        """handle API errors"""
        #connection refused
        if type(e) == ConnectionRefusedError and self.findErr('ConnectionRefusedError(10061'):
            self.api_errs = []
            #if all ports have been tried, then attempt to reconnect
            if len(self.ports) == self.port_used_idx + 1:     
                self.connecting = False           
                self.attempReconnect(self.reconnect_interval) 
            else: 
                #try the next available port
                self.port_used_idx += 1
                await self.__connectIB()

        if self.findErr('API connection failed: TimeoutError') and self.findErr('already in use'):
            self.api_errs = []
            await self.__connectIB()

    def attempReconnect(self, interval):
        self.port_used_idx = 0  #reset port no.
        self.__callback(ACTION.RECONNECT)
        time.sleep(interval)
        self.connectIB()
        #r = Timer(interval, self.connectIB)
        #r.start()

    async def testIBServerConnectivity(self):
        c = Forex('EURUSD')
        if (self.ib and self.ib.is_connected()):
            await self.ib.qualifyContractsAsync(c)
            if (c.conId > 0):
                self.__callback(IBServerConnectivity.CONNECTION_REESTABLISHED)
            else:
                self.__callback(IBServerConnectivity.CONNECTION_LOST)        

    def getPIB(self):
        if (self.ib.is_connected()):
            self.PIB.IB = self.ib
            self.PIB.loop = self.loop
            return self.PIB
        else:
            return None

    def strFind(self, src, find_str):
        """src is a string, 
            find_str is a string or a list of str"""
        if isinstance(find_str, str):
            return src.find(find_str)
        else:
            for s in find_str:
                f = src.find(s)
                if f != -1:
                    return f
        return -1
        
        