import sys
import os
#from .models.IBConnector import IBConnector
#from .models.Symbol import Symbol
#from .models.PlaceOrder import PlaceOrder
from configobj import ConfigObj
from collections import namedtuple
from .utils.tools import copyall

import numpy as np
import pandas as pd
from .utils.Messenger import MESSENGER, init
from .datasource.ft.ft_controller import FTController
import re


def main():
    init()


    # with open("d:/ib/t2/data/stocks.txt", 'r', encoding='UTF-8') as f:
    #    b = ['HK.{0}'.format(re.split(r'\t+', x.strip(' \t\n\r'))[0]) for x in f if len(x.strip())>0]
    # del b[0]
'''
    ft1 = FTController(id='ft1', host='127.0.0.1', port=11111)
    # ft2 = FTController(id='ft2', host='127.0.0.1', port=11112)
    ft1.connect()
    # ft2.connect()

    limit = {"no_of_stocks": 10, "interval": 30}

    # b = ['US.AAPL', 'US.QQQ']
    #b = ['HK.00700','HK.02318']
    b = ['HK.00700','HK.02318','HK.03333','HK.00939','HK.00941','HK.01299','HK.00388','HK.00005','HK.00175']
    # ft1.request_history_data(b[:70], limit, start='2018-09-19', end='2018-09-19')
    # ft2.request_history_data(b[70:], limit, start='2018-09-19', end='2018-09-19')
    ft1.scan(b[0:9], '5m', limit, date='2018-09-26')
    # ft2.scan(b[2:4], '1m', limit, date='2018-09-24')
'''