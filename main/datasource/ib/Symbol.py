import sys
import os
#sys.path.append("..")
#sys.path.insert(1, os.path.join(sys.path[0], '..'))
import threading
from ib_insync import *
from ..utils.tools import copy, Struct
from .IBConnector import IBConnector
from datetime import datetime, timedelta
from atom.api import Atom
import json
import time
import asyncio
from atom.api import Atom

class CONST(object):
    secTypes = ['fut', 'stk']

    def __setattr__(self, *_):
        pass

class Symbol(Atom):
    def __init__(self, browser, ib):
        self.browser = browser
        self.ib = ib            # IBConnector
        self.ib.connectEvent += self.onConnect
        self.ib.contractEvent += self.onContractError
        self.detail_cb = None   # js callback for contract details
        self.mktData_cb = None  # js callback for maket data
        self.hisData_cb = None  # js callback for historical data
        self.error_cb = None
        # store contracts subscribing to market data. Key is conId; value consists of contract with full detail and ref to be used in unsubscribing data 
        self.subscriptions = {} 
        self.his_subs = {}
        self.s = []
        #check subscription
        #self.th = threading.Thread(target=self.checkSubscription)
        #self.th.start()
    
    def test(self):
        self.s = list(range(1000000))

    def onContractError(self, error):
        if hasattr(error, 'conId'):
            if hasattr(self.error_cb, 'Call'):
                self.error_cb.Call(json.dumps(error, default=lambda o:o.__dict__ ))

    def setErrorCallback(self, val, js_cb):
        if hasattr(js_cb, 'Call'):
            self.error_cb = js_cb

    def setHisDataCallback(self, val, js_cb):
        if hasattr(js_cb, 'Call'):
            self.hisData_cb = js_cb

    def onConnect(self, msg):
        #print(msg)
        if (msg['code'] == 1):
            if len(self.subscriptions) > 0:
                tmp = self.subscriptions
                self.subscriptions = {}
                for c in tmp:
                    self.subMktData(c['contract'])

    def getContractDetails(self, code, js_cb):
        ib = self.__checkIBReady()
        if ib == None: return
        
        if hasattr(js_cb, 'Call'):
            self.detail_cb = js_cb
        #get contract details in another thread
        asyncio.run_coroutine_threadsafe(self.__getContractDetails(ib, code), ib.loop)

    async def __getContractDetails(self, ib, code):
        """Get contract details from IB"""
        try:
            print('symbol:' + code)
            contracts = []        
            
            #just plain string like 'qqq', 'hsi'
            if type(code) == str and code.find("(") == -1:
                for st in CONST.secTypes:
                    contracts.append(Contract(symbol=code, secType=st))
            #if code's format is something like Forex('USDJPY')
            elif type(code) == str and code.find("(") != -1 and code.endswith(')'):
                i = code.find("(")
                class_name = code[0:i].capitalize()
                init_str = code[i+2:len(code)-2]
                contracts.append(globals()[class_name](init_str))   
            #Contract objects         
            elif type(code) == object:
                contracts.append(code)
            #print(contracts[0])    
            details = []
        
            tasks = [ib.IB.reqContractDetailsAsync(c) for c in contracts]
            print("awaiting...")
            a = await asyncio.gather(*tasks)
            details = [item for sublist in a for item in sublist]
            print("finished")
                
            #group data as needed
            self.__hanldeDataFromIB(details) 
        except Exception as e:
            print('error: ')
            print(e)   
    
    def __hanldeDataFromIB(self, details):
        """sort the data by longName and secType, then group them"""
        final_result = []
        ids = []
        if len(details) > 0:            
            for cd in details:
                c = cd.contract
                try:
                    i = ids.index(c.conId)
                    found = True
                except ValueError:
                    found = False
                if not found:
                    #copy the needed fields to a temp object
                    tmp = Struct(*'conId secType symbol contractMonth lastTradeDateOrContractMonth \
                        localSymbol exchange primaryExchange currency multiplier longName tradingClass'.split())()
                    copy(c, tmp)
                    copy(cd, tmp)

                    #in case of future, there is likely to have different lastTradeDate for the same month
                    #with the different conIds. Then wejust pick the latest one                    
                    if tmp.secType.upper() == 'FUT':
                        fut_found = self.__findAndReplace(final_result, tmp)
                        #no duplicated record found
                        if not fut_found:
                            ids.append(c.conId)
                            final_result.append(tmp)   
                    else:
                        ids.append(c.conId)
                        final_result.append(tmp)  
                elif found and final_result[i].primaryExchange != '' and final_result[i].exchange != 'SMART':
                    final_result[i].exchange = c.exchange
            
            #print(final_result)
            a = sorted(final_result, key=lambda x:  (x.longName, x.currency, x.secType, datetime(1902, 3, 11) if x.lastTradeDateOrContractMonth=="" \
                    else datetime.strptime(x.lastTradeDateOrContractMonth,'%Y%m%d')))
            #print(json.dumps(a, default=lambda o:o.__dict__ ))
            result = self.__groupByCategory(a)
            #print(json.dumps(result, default=lambda o:o.__dict__ ))
            if hasattr(self.detail_cb, "Call"):
                self.detail_cb.Call(json.dumps(result, default=lambda o:o.__dict__ ))
            #for r in result:
            #   print(json.dumps(r, default=lambda o:o.__dict__ ))
        else:
            if hasattr(self.detail_cb, "Call"):
                self.detail_cb.Call("")

    def __findAndReplace(self, src, target):
        """find the record in a list with the same contractMonth and less lastTradeDate.
            If found, then replace"""
        for i, r in enumerate(src):
            if r.contractMonth == target.contractMonth and r.secType == target.secType:
                #same contractMonth found
                if datetime.strptime(r.lastTradeDateOrContractMonth,'%Y%m%d') < \
                    datetime.strptime(target.lastTradeDateOrContractMonth,'%Y%m%d'):
                    src[i] = target
                return True
        #if not found
        return False
    
    def __groupByCategory(self, src):
        result = []
        print(len(src))
        #sort by currency and longName first:
        prev = None
        for r in src:         
            #print(json.dumps(result, default=lambda o:o.__dict__ ))
            if len(result) == 0:                
                result.append(self.__makeGroupItem(r))
            else:
                #different exchange
                if r.longName != prev.longName or (r.longName == prev.longName and r.currency != prev.currency):
                    result.append(self.__makeGroupItem(r))
                #different security type
                if r.longName == prev.longName and r.currency == prev.currency and r.secType != prev.secType:
                    r.secTypeLong = self.__convertST(r)
                    result[len(result)-1].types.append(self.__attachItem(r, 1))
                #different contract month if future
                if r.longName == prev.longName and r.currency == prev.currency and r.secType == prev.secType and r.secType == 'FUT':
                    r.secTypeLong = self.__convertST(r)
                    result[len(result)-1].types[len(result[len(result)-1].types)-1].contractMonths.append(r)
            prev = r
            
        #for r in result:
        #   print(json.dumps(r, default=lambda o:o.__dict__ ))
        return result
    
    def __makeGroupItem(self, r):
        """Exchange Header for different types of contracts"""
        #add some additional info
        r.secTypeLong = self.__convertST(r) #add full name of security type
        #make a new object
        tmp = Struct(*'exchange primaryExchange currency longName'.split())()
        copy(r, tmp)  #copy content from source to new object
        tmp.types = []        #attach a new prop for adding new security to this group
        tmp.types.append(self.__attachItem(r, 1)) #attach
        return tmp
    
    def __makeFutureItem(self, r):
        """Future Header for contract months"""
        #add some additional info
        r.secTypeLong = self.__convertST(r) #add full name of security type
        #make a new object
        tmp = Struct(*'secType exchange primaryExchange currency longName'.split())()
        tmp.secTypeLong = self.__convertST(r)
        copy(r, tmp)  #copy content from source to new object
        tmp.contractMonths = []        #attach a new prop for adding new security to this group
        tmp.contractMonths.append(r) #attach
        return tmp
    
    def __attachItem(self, r, level):
        """level: 0 -- group items
                1 -- secondary items (stock future...)
                2 -- third items (contract months for future)"""
        if r.secType == 'FUT':
            if level == 1:
                return self.__makeFutureItem(r)
            elif level == 2:
                return r
        elif r.secType == 'STK' or r.secType == 'CASH':
            return r
    
    def __convertST(self, s):
        """convert security type"""
        result = {
            'STK': lambda x: 'Stock (SMART)' if x == 'SMART' else 'Stock',
            'FUT': lambda x: 'Future',
            'CASH': lambda x: 'Exchange',
        }[s.secType](s.exchange)
        return result

    def __checkIBReady(self):
        ib = None
        if (self.ib.getPIB() == None):
            print('PIB is not initialized -- Symbol.__checkIBReady')
            return None
        else:
            ib = self.ib.getPIB()
        return ib

    def t(self):
        ib = self.__checkIBReady()
        if ib == None: return

        asyncio.run_coroutine_threadsafe(self.__test(ib.IB), ib.loop)

    def __test(self, ib):      
        
        ib = ib.IB
        c = Contract(conId=305074193)
        ib.qualifyContracts(c)
        result = ib.reqRealTimeBars(c, '5 secs', 'TRADE', True)
        ib.barUpdateEvent += self.__onBarUpdate
        print(result)

    def reqHisData(self, contract, end_date, duration, bar_size, keepUpToDate=True, js_cb=1):
        """Get historical data
            contract is either a object with conId or conId
        """
        try:
            ib = self.__checkIBReady()
            if ib == None: return
            
            id = self.__getConId(contract)
            c = Contract(conId = id)
            if id not in self.his_subs:
                self.his_subs[id] = ''
                asyncio.run_coroutine_threadsafe(self.__reqHisData(ib.IB, \
                    c, end_date, duration, bar_size, keepUpToDate), ib.loop)

            if hasattr(js_cb, 'Call'):
                self.hisData_cb = js_cb
        except Exception as e:
            print('reqHisData error:')
            print(e) 

    async def __reqHisData(self, ib, contract, end_date, duration, bar_size, keepUpToDate):
        result = []
        try:
            await ib.qualifyContractsAsync(contract)
            bars = ib.reqHistoricalData(contract, endDateTime=end_date, durationStr=duration, \
                barSizeSetting=bar_size, whatToShow='MIDPOINT', useRTH=True, formatDate=1)
            result = self.__handleBarData(bars)

            if keepUpToDate:
                b = ib.reqRealTimeBars(contract, 5, 'MIDPOINT', False)
                b.updateEvent += self.__onBarUpdate
            
            if len(result) > 0 and hasattr(self.hisData_cb, "Call"):
                self.hisData_cb.Call(json.dumps(result, default=lambda o:o.__dict__ ))
        except Exception as e:
            print(e)

    def __handleBarData(self, bars):
        #print(bars)
        if len(bars) == 0: return [] 
        result = []
        
        #get contract details
        contract = {}
        if hasattr(bars, 'contract'):
            contract = copy(bars.contract)
        else:
            print('cannot get contract details in __handleBarData')
        
        for bar in bars:
            #this line must put insdie for loop to create a blank object every time
            b = copy(bar, None, True)
            b.contract = contract
            result.append(b)
        return result

    def __onBarUpdate(self, bars, hasNewBar):
        #print('historical data:')
        result = self.__handleBarData(bars)  
                       
        if hasattr(self.hisData_cb, "Call"):
            self.hisData_cb.Call(json.dumps(result, default=lambda o:o.__dict__ ))

    def checkSubscription(self):
        '''check if market data is subscribed successfully'''
        while True:
            time.sleep(5)
            for id, sub in self.subscriptions.items():       
                if sub['1stTicker'] == None:
                    td = (datetime.now() - sub['time']) / timedelta(seconds=1)
                    if td > 10:
                        conId = id
                        print('subcribe again:' + conId)
                        del self.subscriptions[conId]
                        self.subMktData(conId)

    def subMktData(self, contract, js_cb=1):
        """Subscribe to market data
            contract: contract
            js_cb: js callback for sending maketdata
        """
        print('subscribing...')
        try:
            ib = self.__checkIBReady()
            if ib == None: return
            
            if hasattr(js_cb, 'Call'):
                self.mktData_cb = js_cb

            id = self.__getConId(contract)
            if id not in self.subscriptions:                
                asyncio.run_coroutine_threadsafe(self.__subMktData(ib.IB, contract), ib.loop)
                
        except Exception as e:
            print('subMktData error:')
            print(e)               

    def __getConId(self, contract):
        """Extract contract ID from contract"""
        if type(contract) is int:
            return contract
        elif hasattr(contract, 'conId'):
            return contract.conId
        else:
            return None


    async def __subMktData(self, ib, contract):
        if type(contract) is int:
            contract = Contract(conId=contract)
        
        await ib.qualifyContractsAsync(contract)
        
        #start to request market data
        ib.reqMarketDataType(4) #enable delayed-frozen data
        ib.reqMktData(contract, '', False, False)
        #append the contract to subscription dict
        self.subscriptions[contract.conId] = {'contract': contract, '1stTicker': None, 'time': datetime.now()}
        #add listener to tiker event for getting new tickers
        ib.pendingTickersEvent += self.__onPendingTickers        
        print('subscribed')

    def __onPendingTickers(self, tickers):
        #print('mktdata')
        result = []
        
        #print('incoming size:' + str(len(tickers)))
        #print(json.dumps(tickers, default=to_json ))
        for t in tickers:
            #this line must put insdie for loop to create a blank object every time
            ticker = Struct(*'contract bid bidSize ask askSize last lastSize high close low time volume'.split())()
            copy(t, ticker)
            ticker.marketPrice = round(t.marketPrice(), 5)
            if (self.subscriptions[t.contract.conId]['1stTicker'] == None):
                self.subscriptions[t.contract.conId]['1stTicker'] = datetime.now()
            self.__appendTicker(t.contract.conId, ticker, result)
        #convert datetime object to string YYYY-mm-DD HH:MM:SS:SSSSSSSS+z
        self.__convertTimeFormat(result)
        
        #if nothing from market data, then request historical data for the last trade day
        #if len(result) == 1 and not (isinstance(result[0].close, float) and isinstance(result[0].close, int)):
        #    self.reqHisData(result[0].contract, '', '1 D', '1 day')
        #print(json.dumps(result, default=lambda o:o.__dict__ ))        
            
        if hasattr(self.mktData_cb, "Call"):
            self.mktData_cb.Call(json.dumps(result, default=lambda o:o.__dict__ ))

    def __appendTicker(self, conId, ticker, result):
        """Append ticker to result, only latest data is to be kept"""
        
        i = 0
        for r in result:
            if (r.contract.conId == ticker.contract.conId and r.time < ticker.time):
                result[i] = ticker
                return
            i += 1
        #if not found, the append
        result.append(ticker)

    def __convertTimeFormat(self, result):
        """convert datetime object to string YYYY-mm-DD HH:MM:SS:SSS+z"""
        for r in result:
            if isinstance(r.time, datetime):
                t = datetime.strftime(r.time, "%Y-%m-%d %H:%M:%S.%f%z")
                i1 = t.rfind(".")
                i2 = t.rfind("+")
                t = t[0:i1+4] + t[i2:]
                r.time = t

    def unsubMktData(self, contract):
        """Unsubscribe to market data"""
        id = self.__getConId(contract)
        if id in self.subscriptions:
            c = self.subscriptions[id]['contract']
            asyncio.run_coroutine_threadsafe(self.__unsubMktData(c), self.ib.getPIB().loop)
            #remove contract from subscription
            del self.subscriptions[id]
            print("Contract has been remove from subscription:" + str(c.conId))        

    async def __unsubMktData(self, contract):
        ib = self.__checkIBReady()
        if (ib != None):
            ib.IB.cancelMktData(contract)
            #ib.IB.cancelTickByTickData(contract)