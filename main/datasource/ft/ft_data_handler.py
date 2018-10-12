from ...utils.event import Event
from ...utils.CONST import STATUS
import pandas as pd
import numpy as np

class FTDataHandler:
    
    def __init__(self, queue):
        self._queue = queue

        self._sdf = {}         # pd dataframe for stocks, key is stock code

    def on_data(self):
        while True:
            msg = self._queue.get()
            if isinstance(msg, pd.DataFrame):
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
            