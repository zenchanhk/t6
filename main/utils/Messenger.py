import sys
import json
import threading
import asyncio
import concurrent
import pandas as pd
import numpy as np
from futuquant import *
from ..datasource.ft.ft_controller import FTController
import os 
dir_path = os.path.dirname(os.path.realpath(__file__))
import signal
import Ice
Ice.loadSlice(os.path.join(dir_path, 'traderex.ice'))
import TraderEx
import pydevd

_ds = {}


class Messenger(TraderEx.Server):

    _receiver = None

    def register(self, clientId, receiver, current):
        print('register')
        print(threading.currentThread().getName())
        self._receiver = receiver
        self._receiver.onData('register successfully')
    
    def execute(self, command, current):
        # print("receiver:")
        # print(_receiver)
        print('execute: ' + command)
        print(threading.currentThread().getName())   
        ret = Executor.execute(command)
        # print("ret")
        return ret

    def on_data(self, data):
        if self._receiver:
            self._receiver.onData(data)

    def on_error(self, error):
        if self._receiver:
            self._receiver.onError(error)

    def on_status(self, error):
        if self._receiver:
            self._receiver.onStatus(error)


class Executor:
    @staticmethod    
    def execute(command):
                
        def exe(statement):            
            try:
                # pydevd.settrace(suspend=True, trace_only_current_thread=True, patch_multiprocessing=True)
                result = eval(statement)                
                return Executor.convertRetValue(result)
            except Exception as e:
                msg = {"exception": e.args[0]}
                return msg
                
        try:
            return exe(command)            
        except KeyboardInterrupt:
            pass        
        except Exception as e:
            print(e)

        print("Done.")

    @staticmethod
    def add_data_source(id, ds):
        if id not in _ds:
            _ds[id] = ds
            return True
        else:
            return False
 
    @staticmethod
    def convertRetValue(result, is_serialized=True):
        '''
            convert returned value as string or future for ICE callbacks
        '''
        ret_code = None
        # in case of tuple returned
        if isinstance(result, tuple):
            ret_code, ret_val = result
            if ret_code == RET_OK:
                # ret_val is a pandas dataframe
                if isinstance(ret_val, pd.DataFrame):
                    ret_val = ret_val.to_dict(orient='list')
            else:
                ret_val = result    # ret_val will be error description
        else:
            ret_val = result

        msg = result
        if ret_code is not None:
            if ret_code == RET_OK:
                if hasattr(ret_val, '__dict__'):
                    msg = {"ret_val": json.dumps(ret_val, default=lambda o: o.__dict__)}
                else:
                    msg = {"ret_val": ret_val}
            elif ret_code == RET_ERROR:
                msg = {"error": ret_val}

        if is_serialized:
            if isinstance(msg, concurrent.futures.Future):
                return msg
            else:
                return json.dumps(msg)
        else:
            return msg


# =========================================================
#
# The Ice communicator is initialized with Ice.initialize
# The communicator is destroyed once it goes out of scope of the with statement
#
MESSENGER = Messenger()


def init():
    print(threading.currentThread().getName())
    with Ice.initialize(os.path.join(dir_path, "config.server")) as communicator:

        #
        # Install a signal handler to shutdown the communicator on Ctrl-C
        #
        signal.signal(signal.SIGINT, lambda signum, frame: communicator.shutdown())

        #
        # The communicator initialization removes all Ice-related arguments from argv
        #
        if len(sys.argv) > 1:
            print(sys.argv[0] + ": too many arguments")
            sys.exit(1)

        adapter = communicator.createObjectAdapter("DataCenterAdapter")
        adapter.add(MESSENGER, Ice.stringToIdentity("DataCenter"))
        adapter.activate()
        communicator.waitForShutdown()