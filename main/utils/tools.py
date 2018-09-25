from ib_insync import *
from datetime import datetime
import math

entries = ['Contract', 'Trade', 'Stock', 'Forex', 'CFD', 'Future', 'Option', 'Bond', 
            'TradeLogEntry', 'Fill', 'Execution', 'CommissionReport', 'OrderStatus', 
            'BarData', 'RealTimeBar', 
            'LimitOrder', 'MarketOrder', 'StopOrder', 'StopLimitOrder']


def to_json(obj):
    result = []
    if hasattr(obj, '__dict__'):
        return obj.__dict__
    else:
        for attr in dir(obj):
            if not attr.startswith('_'):
                result.append(attr)
        return result


def copyall(src, dest):
    """simple copy"""
    for attr in src.__dict__:
        #if type(getattr(src, attr)) in [int, bool, str, float]
        setattr(dest, attr, getattr(src, attr))


def convertDict(obj):
    if isinstance(obj, dict):
        dest = Struct(*obj.keys())()
        for key, value in obj.items():
            if type(value).__name__ in entries:
                setattr(dest, key, copy(value, None, True))
            else:
                setattr(dest, key, value)
        return dest
    else:
        return obj


def copy(src, dest=None, dt_truncate=False):
    """copy with the same attributes between src and dest"""
    if src == None:
        print('Warn: source is none.')
        return None
    #copy  
    try:
        src_type_name = type(src).__name__
        #only the empty dest will be assigned with same class as src
        if src_type_name in entries and dest == None:
            dest = classFactory(src_type_name)

        #primitive types
        if not hasattr(dest, '__dict__'):
            if src_type_name == 'datetime' and dt_truncate:
                dest = truncate_dt(src)
            else:
                dest = src
            return src

        for attr in dest.__dict__:
            if not attr.startswith('_') and attr in dir(src):
                #check if IB classes
                value = getattr(src, attr)
                type_name = type(value).__name__
                #in case of list
                if type_name == 'list' and len(value) > 0:
                    setattr(dest, attr, [])
                    for el in value:
                        if el != None:
                            tmp = copy(el, None, dt_truncate)
                            getattr(dest, attr).append(tmp)
                #in case of IB classes
                elif type_name in entries:
                    tmp = copy(value, None, True)
                    setattr(dest, attr, tmp)                    
                else:
                    #in case of datetime and transform is required
                    if type_name == 'datetime' and dt_truncate:
                        setattr(dest, attr, truncate_dt(value))
                    else: 
                        if type_name in ['float', 'int'] and math.isnan(value):
                            value = '--'
                        
                        setattr(dest, attr, value)
        
        return dest
    except Exception as e:
        print(e)


def truncate_dt(time):
    """convert datetime object to string YYYY-mm-DD HH:MM:SS:SSS+z"""

    t = datetime.strftime(time, "%Y-%m-%d %H:%M:%S.%f%z")
    i1 = t.rfind(".")
    i2 = t.rfind("+")
    t = t[0:i1+4] + t[i2:]
    return t


def classFactory(name):
    if name == 'Contract' or name == 'Stock' or name == 'Forex' or name == 'CFD' or name == 'option' or name == 'Bond' :
        return Struct(*'conId secType symbol contractMonth lastTradeDateOrContractMonth \
            localSymbol exchange primaryExchange currency multiplier longName tradingClass'.split())()
    elif name == 'OrderStatus':
        return Struct(*'status filled avgFillPrice lastFillPrice remaining permId clientId whyHeld'.split())()
    elif name == 'Trade':
        return Struct(*'contract order orderStatus fills log'.split())()
    elif name == 'MarketOrder' or name == 'LimitOrder' or name == 'StopOrder' or name == 'StopLimitOrder':
        tmp = Struct(*'orderId clientId permId action totalQuantity lmtPrice auxPrice \
            tif ocaType trailStopPrice openClose account orderType'.split())()
        tmp.orderType = name
        return tmp
    elif name == 'TradeLogEntry':
        return Struct(*'time status message '.split())()
    elif name == 'Fill':
        return Struct(*'contract execution time commissionReport'.split())()
    elif name == 'Execution':
        return Struct(*'execId acctNumber time side shares price permId cumQty avgPrice lastLiquidity'.split())()
    elif name == 'CommissionReport':
        return Struct(*'execId commission currency realizedPNL'.split())()
    elif name == 'RealTimeBar':
        return Struct(*'time open high low close volume'.split())()
    elif name == 'BarData':
        return Struct(*'time open high low close volume average'.split())()


def Struct(*args, **kwargs):
    def init(self, *iargs, **ikwargs):
        for k,v in kwargs.items():
            setattr(self, k, v)
        for i in range(len(iargs)):
            setattr(self, args[i], iargs[i])
        for k,v in ikwargs.items():
            setattr(self, k, v)

    name = kwargs.pop("name", "MyStruct")
    kwargs.update(dict((k, None) for k in args))
    return type(name, (object,), {'__init__': init}) #, '__slots__': kwargs.keys() used to prevent from creating more attributes


