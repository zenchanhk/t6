from .ft_connector import FTConnector
from .ft_hktrade import FTHKTrade
import threading
import asyncio
import aioprocessing
import multiprocessing
from futuquant import *
from ...utils.event import Event
from collections import namedtuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import pydevd
from concurrent.futures import ProcessPoolExecutor
import concurrent
import talib

subTypeMap = {
    'ticker': SubType.TICKER,
    'quote': SubType.QUOTE,
    'order_book': SubType.ORDER_BOOK,
    '1m': SubType.K_1M,
    '5m': SubType.K_5M,
    '15m': SubType.K_15M,
    '30m': SubType.K_30M,
    '60m': SubType.K_60M,
    '1d': SubType.K_DAY,
    '1w': SubType.K_WEEK,
    '1M': SubType.K_MON,
    'rt': SubType.RT_DATA,
}

KLTypeMap = {
    '1m': KLType.K_1M,
    '5m': KLType.K_5M,
    '15m': KLType.K_15M,
    '30m': KLType.K_30M,
    '60m': KLType.K_60M,
    '1d': KLType.K_DAY,
    '1w': KLType.K_WEEK,
    '1M': KLType.K_MON,
}

MarketMap = {
    "US": Market.US,
    "HK": Market.HK
}

TradePlatMap = {
    "HK": {'var': '_hktrade', 'class': FTHKTrade},
    'US': {'var': '_ustrade', 'class': FTHKTrade},
    'CN': {'var': '_cntrade', 'class': FTHKTrade},
    'HKCC': {'var': '_hkcctrade', 'class': FTHKTrade}
}

TradeSideMap = {
    'BUY': TrdSide.BUY,
    'BUYBACK': TrdSide.BUY_BACK,
    'SELL': TrdSide.SELL,
    'SELLSHORT': TrdSide.SELL_SHORT
}

_max_c_last = {}    # max close of last day
_max_v_last = {}    # max volume of last_day
_max_c = {}         # max close of current day
_max_v = {}         # max volume of current day
_sdf = {}         # pd dataframe for stocks, key is stock code
_indicator = {"max_c4": float("nan"), "max_v4": float("nan"),
              "max_c5": float("nan"), "max_v5": float("nan")}     # indicators


class Fifo:
    _latency = 5    # tolerance for network delay

    def __init__(self, period, quote):
        self._period = period
        self._list = []
        self._quote = quote

    def append(self, item):
        self._list.append(item)
    
    def get_quote(self):
        if len(self._list) == 0:
            return 0, self._quote
        # remove items that exceeds the period
        i = 0
        for item in self._list:
            if (datetime.now() - item.time).total_seconds() <= self._period:
                break
            i += 1
        del self._list[0: i]
        # get the remaining quote
        remaining = 0
        if len(self._list) == 0:
            return 0, self._quote
        else:
            for item in self._list:
                remaining += item.count
            if remaining < self._quote:
                return 0, self._quote - remaining
            else:
                return (datetime.now() - self._list[0].time).total_seconds(), self._list[0].count
            

class FTController:
    
    def __init__(self, name, messenger, lmt, queue, host='127.0.0.1', port=11111):
        
        if 'req_kline' in lmt:
            self._req_his = Fifo(lmt['req_kline'].period, lmt['req_kline'].quote)
        if 'order' in lmt:    
            self._order_his = Fifo(lmt['order'].period, lmt['order'].quote)

        self._connector = None
        self._messenger = messenger
        
        self._hktrade = None
        self._ustrade = None
        self._cntrade = None
        self._hkcctrade = None
        self._sysinfo_handler = SysNotifyHandlerBase(self)
        self._kline_handler = CurKlineHandler(self)
        self._trade_handler = TradeOrderHandler(self)
        self._sub_list = {}
        
        self._status = None
        self._queue = queue
        self._name = name

        self._host = host
        self._port = port
        
        self.loop = asyncio.new_event_loop()
        def f(loop):
            print('Loop thread name: {0}'.format(threading.currentThread().getName()))
            asyncio.set_event_loop(loop)
            loop.run_forever()
        t = threading.Thread(target=f, args=(self.loop,))
        t.start() 
        
    def connect(self):  
        # future = asyncio.run_coroutine_threadsafe(self._connect(), self.loop)
        #return future.result()
        return self._connect()

    def _connect(self): 
        # print('connecting...')
        if self._connector is None:
            self._connector = FTConnector(id=self._name, host=self._host, port=self._port)
            self._connector.set_handler(self._kline_handler)
            self._connector.set_handler(self._sysinfo_handler)
            self._connector.connectEvent += self._messenger.on_status
            self._connector.errorEvent += self._messenger.on_error
        return '{"ret_val": 0}'

    def disconnect(self):
        # print(self._connector.isConnected())
        if self._connector and self._connector.is_connected():
            self._connector.close()
    
    def open_trade(self, market):
        if market in TradePlatMap:
            future = asyncio.run_coroutine_threadsafe(self._open_trade(market), self.loop)
            return future.result()
        else:
            return '{"error": "Market {0} not found"}'.format(market)

    async def _open_trade(self, market):
        trade = getattr(self, TradePlatMap[market]['var'])
        if trade is None:
            setattr(self, TradePlatMap[market]['var'], 
                TradePlatMap[market]['class'](name=self._name, host=self._host, port=self._port))
            trade = getattr(self, TradePlatMap[market]['var'])
            trade.set_handler(self._trade_handler)
            trade.set_handler(self._sysinfo_handler)
        # self._hktrade.connectEvent += self._messenger.on_status
        # self._hktrade.errorEvent += self._messenger.on_error
        return '{"ret_val": 0}'

    def close_trade(self, market):
        trade = getattr(self, TradePlatMap[market]['var'])
        if trade and trade.is_connected():
            trade.close()

    def setting(self):
        pass

    def get_data_source(self):
        ds = {'status': self._status, 'controller': self}
        return namedtuple('DataSource', ds.keys())(*ds.values())

    def get_connector(self):
        if self._connector is None:
            self.connect()
        return self._connector

    def get_data_source_status(self):
        return self._status

    def place_order(self, order_list, limit=None, scheduled=None, **kwargs):
        #with concurrent.futures.ProcessPoolExecutor() as executor:
        #    f = executor.submit(place_order_mp, order_list, limit, scheduled, **kwargs)
        #return f 
        future = asyncio.run_coroutine_threadsafe(
            self.coro_place_order(order_list, limit, scheduled, **kwargs), self.loop)
        return future  

    @asyncio.coroutine
    async def coro_place_order(self, order_list, limit, scheduled, **kwargs):
        print('place-order PID:{0}, Thread:{1}'.format(os.getpid(), threading.currentThread().getName()))
        if scheduled is None:
            result = self.place_order_real(order_list, limit, **kwargs)
            return result
        else:
            scheduled = datetime.strptime(scheduled, '%Y-%m-%d %H:%M:%S')
            if datetime.now() < scheduled:
                while True:
                    await asyncio.sleep(1)
                    if datetime.now() < scheduled:
                        print('Now:' + datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f'))
                        continue
                    else:
                        # pydevd.settrace(suspend=True, trace_only_current_thread=True, patch_multiprocessing=True)
                        result = self.place_order_real(order_list, limit, **kwargs)
                        return result
            else:
                return RET_ERROR, {'error': 'scheduled time has been expired'}
    
    def place_order_real(self, order_list, limit):
        if isinstance(order_list, str):
            list = json.loads(order_list)
        else:
            list = order_list
        result = []
        error = {}
        # pydevd.settrace(suspend=True, trace_only_current_thread=True, patch_multiprocessing=True)
        for o in list:            
            ret, data = getattr(self, TradePlatMap[o['Market']]['var']).place_order(price=o['Price'], 
                code=o['Code'], qty=o['Qty'], trd_side=TradeSideMap[o['TradeSide']])
            if ret == RET_OK:
                result.append(data)  
            else:
                error[o['Code']] = data
                print('{0} place_order error: {1}'.format(o['Code'], data))
                
        if len(result) == 0:
            return RET_ERROR, {'error': error}
        else:
            return RET_OK, {"ret_val": pd.concat(result).to_dict(orient='list'), 'error': error}

    def request_history_data(self, code_list, limit, **kwargs):
        future = asyncio.run_coroutine_threadsafe(
            self.request_history_data_real(code_list, limit, **kwargs), self.loop)
        return future

    def scan(self, code_list, sub_type, limit, date=datetime.now().strftime("%Y-%m-%d"), req_history=True, **kwargs):
        future = asyncio.run_coroutine_threadsafe(
            self.scan_async(code_list, sub_type, limit, date, req_history, **kwargs), self.loop)
        return future

    @asyncio.coroutine
    async def request_history_data_real(self, code_list, kl_type, limit, **kwargs):
        result = []
        error = {}

        for i in range(0, len(code_list), no_of_stocks):
            # calculate the time passed since last call
            # print('{0} last req_time: {1}'.format(self._name, self._req_time['request_history_kline'].strftime('%H:%M:%S')))
            time_passed = (datetime.now() - self._req_time['request_history_kline']).total_seconds()
            print('{0} time passed. Now: {1}'.format(time_passed, datetime.now().strftime('%H:%M:%S')))
            if time_passed > 0:
                await asyncio.sleep(interval - time_passed + 5)
            self._req_time['request_history_kline'] = datetime.now()
            print('{0} retrieving: {1}'.format(self._name, datetime.now().strftime('%H:%M:%S')))
            for j in range(no_of_stocks):
                if i+j >= len(code_list):
                    break
                ret, data, prk = self._connector.request_history_kline(code=code_list[i+j], ktype=kl_type, **kwargs)
                print('retrieving: {0}'.format(code_list[i+j]))
                if ret == RET_OK:
                    result.append(data)  
                else:
                    error[code_list[i+j]] = data
                    print('{0} his_data retrieve error: {1}'.format(code_list[i+j], data))
        
        # pydevd.settrace(suspend=True, trace_only_current_thread=True, patch_multiprocessing=True)
        if len(result) == 0:
            return RET_ERROR, {'error': error}
        else:
            return RET_OK, {"ret_val": pd.concat(result).to_dict(orient='list'), 'error': error}

    def get_highest(self, code_list, kl_type, date, period, limit, **kwargs):
        future = asyncio.run_coroutine_threadsafe(
            self.coro_get_highest(code_list, kl_type, date, period, limit, **kwargs), self.loop)
        return future

    @asyncio.coroutine
    async def coro_get_highest(self, code_list, kl_type, date, period, limit, **kwargs):
        '''
            get the highest close and volume during the specific period
            code_list: list of code, must be in the same market
            kl_type: KLine type
            date: specify the date, excluding this date
            period: 
            limit: limitation of vendor
        '''
        print('coro-get-highest -- PID:{0}, Thread:{1}'.format(os.getpid(), threading.currentThread().getName()))
        if self._connector is None:
            self.connect()
        
        if self._connector and self._connector.is_connected():
            # get subscription type  
            if kl_type in subTypeMap:
                _kl_type = subTypeMap[kl_type]
            else:
                return {'error': 'kline_type {0} not found'.format(kl_type)}

            # initialize max dicts
            if _kl_type not in _max_c_last:
                _max_c_last[_kl_type] = {}
            if _kl_type not in _max_v_last: 
                _max_v_last[_kl_type] = {}

            # get last trading date
            # excluding the date first
            end = (datetime.strptime(date, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
            # retrieving a much larger date range to avoid the holidays
            start = (datetime.strptime(date, "%Y-%m-%d") - timedelta(days=period*10)).strftime("%Y-%m-%d")
            result, dates = self._connector.get_trading_days(MarketMap[code_list[0][:2]], start=start, end=end)
            if result == RET_OK:
                    start = dates[-period]
            else:
                return {'error': 'error occus during retreiving trading dates'}
            
            # remove the code if the requested data is already cached
            # init ret_val for further use
            ret_val = {}
            for code in code_list:
                if code+date+period in _max_c_last[_kl_type]:
                    ret_val[code] = {"close": _max_c_last[_kl_type][code+date+period]['close']}
                    code_list.remove(code)

            kwargs['start'] = start
            kwargs['end'] = end
            # get the historical data
            result, error = await self.request_history_data_real(code_list, _kl_type, limit, **kwargs)
            
            if result is not None:
                # fill in max last close and volume
                max_close = result.groupby(['code'])['close'].max()
                max_vol = result.groupby(['code'])['volume'].max()
                # for close
                for code, close in max_close.items():
                        _max_c_last[_kl_type][code+date+period] = {"close": close}
                        ret_val[code] = {"close": close}
                # for volume
                for code, vol in max_vol.items():
                        _max_v_last[_kl_type][code+date+period] = {"volume": vol, "start": start, 'end': end}
                        ret_val[code].update({"volume": vol, "start": start, 'end': end})
            # attach error to return value
            ret_val = {"data": ret_val, 'error': error}

            return RET_OK, ret_val
        else:
            return RET_ERROR, {'error': 'Vendor is disconnected'}

    @asyncio.coroutine
    async def scan_async(self, code_list, sub_type, limit, date, req_history, **kwargs):
        '''
            coroutine has to return serialized objects
        '''
        print('scan-sync PID:{0}, Thread:{1}'.format(os.getpid(), threading.currentThread().getName()))
        if self._connector is None:
            self.connect()
        
        if self._connector and self._connector.is_connected():
            # get subscription type            
            _sub_type = SubType.K_5M
            if sub_type in subTypeMap:
                _sub_type = subTypeMap[sub_type]
            
            # susbscribing
            ret, msg = self._connector.subscribe(code_list=code_list, subtype_list=[_sub_type])

            # store code_list for unsubscribing
            if ret == RET_OK:
                if sub_type not in self._sub_list:
                    self._sub_list[sub_type] = set(code_list)
                else:
                    self._sub_list[sub_type] |= set(code_list)
            else:
                # if error occurs, return error
                return ret, msg
        else:
            return RET_ERROR, {'error': 'Vendor is disconnected'}

    def stop_scan(self, subtype):
        ret, err = self._connector.unsubscribe(code_list=self._sub_list[subtype], subtype_list=[subtype])
        return ret, err

    def unsubscribe(self, code_list, subtype_list):
        ret, err = self._connector.unsubscribe(code_list=code_list, subtype_list=subtype_list)
        return ret, err

def set_strategy(code_list, strategy):
    pass

def apply_strategy(p_input):
    pass

class SysNotifyTest(SysNotifyHandlerBase):
    def __init__(self, controller):
        self._controller = controller
        self._dataEvent = Event()
        self._dataEvent += self._controller._messenger.on_data

    def on_recv_rsp(self, rsp_str):
        ret_code, data = super(SysNotifyTest, self).on_recv_rsp(rsp_pb)
        notify_type, sub_type, msg = data
        if ret_code != RET_OK:
            logger.debug("SysNotifyTest: error, msg: %s" % msg)
            return RET_ERROR, data
        print(msg)
        return RET_OK, data

class TradeOrderHandler(TradeOrderHandlerBase):
  """ order update push"""
  def __init__(self, controller):
        self._controller = controller
        self._dataEvent = Event()
        self._dataEvent += self._controller._messenger.on_data

  def on_recv_rsp(self, rsp_pb):
      print('recv thread name: {0}'.format(threading.currentThread().getName()))
      ret, content = super(TradeOrderHandler, self).on_recv_rsp(rsp_pb)

      if ret == RET_OK:
          print("* TradeOrderTest content={}\n".format(content))

      return ret, content


class CurKlineHandler(CurKlineHandlerBase):

    def __init__(self, controller):
        self._controller = controller
        self._dataEvent = Event()
        self._dataEvent += self._controller._messenger.on_data

    def on_recv_rsp(self, rsp_str):
        print('curline recv - PID:{0}, Thread:{1}'.format(os.getpid(), threading.currentThread().getName()))
        ret_code, data = super(CurKlineHandler, self).on_recv_rsp(rsp_str)
        if ret_code != RET_OK:
            print("CurKlineTest: error, msg: %s" % data)
            return RET_ERROR, data

        self._dataEvent.notify_all({"req_type":"kline", "ret_val":
                                    json.dumps(data.to_dict(orient='list'), default=lambda o: o.__dict__)})
        # get the shape of result df
        

        # print(_sdf)
        # if the number of bars exceeds 4, start comparing at bar no. 5
        df = _sdf[t1['code']]     # shortcut
        if len(df.index) > 4:                
            df = _sdf[t1['code']]
            bc_rt = t1['close'] > df.iloc[-2]['max_c4']
            bv_rt = t1['volume'] > df.iloc[-2]['max_v4']
        # if both break
        if bc_rt and bv_rt:
            code = t1['code']
            result = {'code': code, 'time': t1['time_key'], 'fulfilled': [],
                        'close': numpyGenericToNative(t1['close']), 
                        'volume': numpyGenericToNative(t1['volume']), 
                        'time_found': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

            # if break yesterday's highest
            if code in _max_c_last and code in _max_v_last and \
                    t1['close'] > _max_c_last[code] and t1['volume'] > _max_v_last[code]:
                result['fulfilled'].append('break last day highest')
            # if break today's highest
            if code in _max_c and code in _max_v and \
                    t1['close'] > _max_c[code] and t1['volume'] > _max_v[code]:
                result['fulfilled'].append('break today highest')

            print(result)
            self._dataEvent.notify_all({"action":"scan", "ret_val": json.dumps(result)})

        return RET_OK, data
 
 
def update_df(df):
    # cal the highest close and volume of past 4 bars
    if len(df.index) >= 4:
        df.iloc[-1, df.columns.get_loc('max_c4')] = df.tail(4)['close'].max()
        df.iloc[-1, df.columns.get_loc('max_v4')] = df.tail(4)['volume'].max()
    # cal the highest close and volume of past 5 bars
    if len(df.index) >= 5:
        df.iloc[-1, df.columns.get_loc('max_c5')] = df.tail(5)['close'].max()
        df.iloc[-1, df.columns.get_loc('max_v5')] = df.tail(5)['volume'].max()
    # cal the day high of close and volume
    code = df.iloc[-1]['code']
    _max_c[code] = max([_max_c[code] if code in _max_c else 0, df.iloc[-1]['close']])
    _max_v[code] = max([_max_v[code] if code in _max_v else 0, df.iloc[-1]['volume']])
    # debug printing
    # print(df.iloc[-1].values.tolist())


def numpyGenericToNative(obj):
    if isinstance(obj, np.generic):
        return np.asscalar(obj)
    else:
        return obj


