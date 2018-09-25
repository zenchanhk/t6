import sys
import zmq
import json
import ast
import threading
import pandas as pd
import numpy as np
from futuquant import *
from ..datasource.ft.ft_controller import FTController

subport = 5563
pubport = 5564

context = zmq.Context()
pub = context.socket(zmq.PUB)
pub.bind("tcp://127.0.0.1:%s" % pubport)
topics = ['command', 'data', 'result']

_ds = {}

class Messenger:
    @staticmethod
    def publish(topic, message):
        '''
            message must be a string array with topic and message body
        '''

        pub.send_multipart([topic.encode(encoding="utf-8"), json.dumps(message).encode(encoding="utf-8")])
    
    @staticmethod
    def subscribe():
        sub = context.socket(zmq.SUB)
        sub.connect("tcp://localhost:%s" % subport)
        
        for topic in topics:
            sub.setsockopt(zmq.SUBSCRIBE, topic.encode('utf-8'))
        
        def execute(statement):
            '''
                thread to execute commands from C#
                statement is bytes, not string
            '''
            try:
                result = eval(statement)
                #in case of tuple returned
                if isinstance(result, tuple):
                    ret_code, ret_val = result
                    if ret_code == RET_OK:
                        #ret_val is a pandas dataframe
                        ret_val = ret_val.to_dict(orient='list')    
                    else:
                        ret_val = result    #ret_val will be error description
                else:
                    ret_val = result
                msg = None
                if ret_val:
                    if hasattr(ret_val, '__dict__'):
                        msg = {"command": statement.decode("utf-8"), "ret_val": json.dumps(ret_val, default=lambda o:o.__dict__)}
                        Messenger.publish('return', msg)
                    else:
                        msg = {"command": statement.decode("utf-8"), "ret_val": ret_val}                            
                        Messenger.publish('return', msg)
            except Exception as e:
                msg = {"command": statement.decode("utf-8"), "exception": e.args[0]}
                Messenger.publish('exception', msg)
                
        try:
            while True:
                topic, msg = sub.recv_multipart()
                if topic == b'command':
                    t = threading.Thread(target=execute, args=(msg,))
                    t.start()                                            
                        
                print('   Topic: %s, msg:%s' % (topic, msg))
        except KeyboardInterrupt:
            pass        
        except Exception as e:
            print(e)

        print("Done.")

    @staticmethod
    def addDataSource(prefix, ds):
        if (prefix not in _ds):
            _ds[prefix] = ds


def isclass(obj):
    """Return true if the object is a class.

    Class objects provide these attributes:
        __doc__         documentation string
        __module__      name of module in which this class was defined"""
    return isinstance(object, type)
    #return type(obj) is type