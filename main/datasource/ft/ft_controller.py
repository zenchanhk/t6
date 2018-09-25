from .ft_connector import FTConnector
import threading
import asyncio
from futuquant import *
from ...utils import Messenger
from ...utils.event import Event
from collections import namedtuple
from datetime import datetime, timedelta
import pandas as pd
import pydevd

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

_max_c_last = {}    # max close of last day
_max_v_last = {}    # max volume of last_day
_max_c = {}         # max close of current day
_max_v = {}         # max volume of current day
_sdf = {}         # pd dataframe for stocks, key is stock code
_indicator = {"max_c4": float("nan"), "max_v4": float("nan"),
              "max_c5": float("nan"), "max_v5": float("nan")}     # indicators


class FTController:
    
    def __init__(self, id, host='127.0.0.1', port=11111):
        
        self._connector = None
        self._kline_handler = None
        self._sub_list = {}
        self._status = None

        self._id = id
        self._host = host
        self._port = port
        # record the time of request called
        self._req_time = {'request_history_kline': datetime.now() - timedelta(days=1)}
        # print("{0} init req time {1}".format(id, self._req_time['request_history_kline']))
        self.loop = asyncio.new_event_loop()
        def f(loop):
            asyncio.set_event_loop(loop)
            loop.run_forever()
        t = threading.Thread(target=f, args=(self.loop,))
        t.start()        

    def connect(self):  
        future = asyncio.run_coroutine_threadsafe(self._connect(), self.loop)
        return future.result()

    async def _connect(self): 
        # print('connecting...')
        if self._connector is None:
            self._connector = FTConnector(id=self._id, host=self._host, port=self._port)
        if self._kline_handler is None:
            self._kline_handler = CurKlineHandler(self)
        self._connector.set_handler(self._kline_handler)
        self._connector.connectEvent += Messenger.MESSENGER.on_status
        self._connector.errorEvent += Messenger.MESSENGER.on_error
        return '{"ret_val": 0}'

    def disconnect(self):
        # print(self._connector.isConnected())
        if self._connector and self._connector.is_connected():
            self._connector.close()

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

    def request_history_data(self, code_list, limit, **kwargs):
        future = asyncio.run_coroutine_threadsafe(
            self.request_history_data_async(code_list, limit, **kwargs), self.loop)
        return future.result()

    def scan(self, code_list, sub_type, limit, date=datetime.now().strftime("%Y-%m-%d"), req_history=True, **kwargs):
        future = asyncio.run_coroutine_threadsafe(
            self.scan_async(code_list, sub_type, limit, date, req_history, **kwargs), self.loop)
        return future

    @asyncio.coroutine
    async def request_history_data_async(self, code_list, sub_type, limit, **kwargs):
        # limitation of vendor, 10 stocks per 30 seconds interval
        if isinstance(limit, str):
            limit = json.loads(limit)

        no_of_stocks = limit['no_of_stocks']
        interval = limit['interval']

        ktype = KLType.K_5M
        if sub_type in KLTypeMap:
            ktype = KLTypeMap[sub_type]

        result = []
        error = {}

        for i in range(0, len(code_list), no_of_stocks):
            # calculate the time passed since last call
            # print('{0} last req_time: {1}'.format(self._id, self._req_time['request_history_kline'].strftime('%H:%M:%S')))
            time_passed = (datetime.now() - self._req_time['request_history_kline']).total_seconds()
            await asyncio.sleep(interval - time_passed + 5)
            self._req_time['request_history_kline'] = datetime.now()
            print('{0} retrieving: {1}'.format(self._id, datetime.now().strftime('%H:%M:%S')))
            for j in range(no_of_stocks):
                if i+j >= len(code_list):
                    break
                ret, data, prk = self._connector.request_history_kline(code=code_list[i+j], ktype=ktype, **kwargs)
                print('retrieving: {0}'.format(code_list[i+j]))
                if ret == RET_OK:
                    result.append(data)  
                else:
                    error[code_list[i+j]] = data
                    print('{0} retrieve error: {1}'.format(code_list[i+j], data))
        
        # pydevd.settrace(suspend=True, trace_only_current_thread=True, patch_multiprocessing=True)
        if len(result) == 0:
            return None, error
        else:
            return pd.concat(result), error

    @asyncio.coroutine
    async def scan_async(self, code_list, sub_type, limit, date, req_history, **kwargs):
        '''
            coroutine has to return serialized objects
        '''
        if self._connector is None:
            self.connect()
        
        if self._connector and self._connector.is_connected():
            # get subscription type            
            _sub_type = SubType.K_5M
            if sub_type in subTypeMap:
                _sub_type = subTypeMap[sub_type]

            # subscribe real-time kline
            ret, msg = self._connector.subscribe(code_list=code_list, subtype_list=[_sub_type])

            # store code_list for unsubscribing
            if ret == RET_OK:
                if sub_type not in self._sub_list:
                    self._sub_list[sub_type] = set(code_list)
                else:
                    self._sub_list[sub_type] |= set(code_list)
            else:
                # if error occurs, return error
                return Messenger.Executor.convertRetValue((ret, msg))
            
            # get history data
            if req_history:
                # get last trading date
                end = date
                start = (datetime.strptime(end, "%Y-%m-%d") - timedelta(days=10)).strftime("%Y-%m-%d")
                result, dates = self._connector.get_trading_days(MarketMap[code_list[0][:2]], start=start, end=end)
                if result == RET_OK:
                    if end == dates[-1]:
                        start = dates[-2]
                    else:
                        start = dates[-1]
                kwargs['start'] = start
                kwargs['end'] = end
                # get the historical data
                result, error = await self.request_history_data_async(code_list, sub_type, limit, **kwargs)
                # init ret_val for further use
                ret_val = {}
                if result is not None:
                    # fill in max last close and volume
                    max_close = result.groupby(['code', result.time_key.str[:10]])['close'].max()
                    max_vol = result.groupby(['code', result.time_key.str[:10]])['volume'].max()
                    # for close
                    for group, close in max_close.items():
                        code, date = group
                        if date == start:
                            _max_c_last[code] = close
                            ret_val[code] = {"close": close, "time_key": date}
                        if date == datetime.now().strftime('%Y-%m-%d') and \
                                ((code in _max_c and close > _max_c[code]) or code not in _max_c):
                            _max_c[code] = close
                    # for volume
                    for group, vol in max_vol.items():
                        code, date = group
                        # yesterday's highest
                        if date == start:
                            _max_v_last[code] = vol
                            ret_val[code].update({"volume": vol})
                        # today's highest
                        if date == datetime.now().strftime('%Y-%m-%d') and \
                                ((code in _max_v and vol > _max_v[code]) or code not in _max_v):
                            _max_v[code] = vol
                # attach error to return value
                ret_val = {"data": ret_val, 'error': error}

                return Messenger.Executor.convertRetValue((RET_OK, ret_val))
            else:
                return Messenger.Executor.convertRetValue((RET_OK, 'OK'))
        else:
            return Messenger.Executor.convertRetValue((RET_ERROR, 'Datasource is disconnected'))

    def stop_scan(self, subtype):
        ret, err = self._connector.unsubscribe(code_list=self._sub_list[subtype], subtype_list=[subtype])
        return ret, err

    def unsubscribe(self, code_list, subtype_list):
        ret, err = self._connector.unsubscribe(code_list=code_list, subtype_list=subtype_list)
        return ret, err


class CurKlineHandler(CurKlineHandlerBase):

    def __init__(self, controller):
        self._controller = controller
        self._dataEvent = Event()
        self._dataEvent += Messenger.MESSENGER.on_data

    def on_recv_rsp(self, rsp_str):
            ret_code, data = super(CurKlineHandler, self).on_recv_rsp(rsp_str)
            if ret_code != RET_OK:
                print("CurKlineTest: error, msg: %s" % data)
                return RET_ERROR, data

            self._dataEvent.notify_all({"req_type":"kline", "ret_val":
                                        json.dumps(data.to_dict(orient='list'), default=lambda o: o.__dict__)})
            # get the shape of result df
            r, c = data.shape

            for row in range(r):
                # initialization
                tmp = {}        # save row to compare
                bc = False      # close break for the bar closed
                bv = False      # volume break for the bar closed
                bc_rt = False   # close break for real-time data
                bv_rt = False   # volume break for real-time data
                new_bar = False
                # get row
                tmp = data.iloc[row:row+1].copy()   # copy the slice
                # debug printing
                print(tmp.values.tolist())
                # check the date first, drop it if not today
                # take the time-zone into consideration
                # if US, subtract 12 hours
                now = datetime.now()
                if tmp.iloc[-1]['code'][:2] == 'US':
                    now -= timedelta(hours=12)
                now = now.strftime('%Y-%m-%d')
                if tmp.iloc[-1]['time_key'][:10] != now:
                    # debug printing
                    print('row dropped: {0}'.format(tmp.values.tolist()))
                    break
                # if first seen
                t1 = tmp.iloc[-1]   # shortcut
                if t1['code'] not in _sdf:
                    _sdf[t1['code']] = tmp.assign(**_indicator)
                    # must reset index here; otherwise, adding new bar will not work
                    _sdf[t1['code']].reset_index(drop=True, inplace=True)
                else:
                    if _sdf[t1['code']].iloc[-1]['time_key'] != t1['time_key']:
                        if datetime.strptime(_sdf[t1['code']].iloc[-1]['time_key'], '%Y-%m-%d %H:%M:%S') < \
                                datetime.strptime(t1['time_key'], '%Y-%m-%d %H:%M:%S'):
                            # if new bar, add it to the dataframe and update the calculated columns
                            # update the last row of df first (calculated columns), and then insert new row
                            update_df(_sdf[t1['code']])
                            # new row index
                            upd_index = len(_sdf[t1['code']].index)
                            new_bar = True
                        else:
                            # drop bars with past time_key found
                            break
                    else:
                        # replace the whole row
                        upd_index = len(_sdf[t1['code']].index) - 1
                    # insert new row or update the row
                    _sdf[t1['code']].loc[upd_index] = tmp.assign(**_indicator).values.tolist()[0]

                    # debug printing
                    if new_bar:
                        # print(_sdf[t1['code']])
                        df = _sdf[t1['code']].iloc[-2]     # shortcut
                        if len(_sdf[t1['code']]) >= 5:
                            print('code:{0}, close:{1}, volume：{2}, time:{3}, last_close_max:{4}, last_vol_max:{5}, maxc4:{6},'
                                  'maxv4:{7}, maxc5:{8}, maxv5:{9}, maxc:{10}, maxv:{11}'.format(t1['code'],
                                  t1['close'], t1['volume'], t1['time_key'], 
                                  _max_c_last[t1['code']] if t1['code'] in _max_c_last else 0,
                                  _max_v_last[t1['code']] if t1['code'] in _max_v_last else 0, df['max_c4'], df['max_v4'],
                                  df['max_c5'], df['max_v5'],
                                  _max_c[t1['code']], _max_v[t1['code']]))
                        else:
                            print('code:{0}, close:{1}, volume：{2}, time:{3}, maxc:{4}, maxv:{5}'.format(t1['code'],
                                t1['close'], t1['volume'], t1['time_key'], _max_c[t1['code']], _max_v[t1['code']]))

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
                    result = {'code': code, 'time': t1['time_key'], 'fulfilled': [0],
                              'close': t1['close'], 'volume': t1['volume'], 
                              'time_key': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

                    # if break yesterday's highest
                    if code in _max_c_last and code in _max_v_last and \
                            t1['close'] > _max_c_last[code] and t1['volume'] > _max_v_last[code]:
                        result['fulfilled'].append(1)
                    # if break today's highest
                    if code in _max_c and code in _max_v and \
                            t1['close'] > _max_c[code] and t1['volume'] > _max_v[code]:
                        result['fulfilled'].append(2)

                    print(result)
                    self._dataEvent.notify_all('{"action":"scan", "ret_val":' + json.dumps(result) + '"}')

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



