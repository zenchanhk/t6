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
from concurrent.futures import ProcessPoolExecutor


class Messenger(TraderEx.Server):

    def __init__(self, server_name):
        self._serv_name = server_name
        self._receiver = {}
        self._ds = {}
        self._clientid = 0

    def register(self, receiver, current):        
        print('Regsiter - PID:{0}, Thread:{1}'.format(os.getpid(), threading.currentThread().getName()))
        self._clientid += 1
        self._receiver[self._clientid] = {'receiver': receiver}
        return {'id': self._clientid}

    def set_strategy(self, client_id, strategy, code_list):
        self._receiver[self._clientid].update({'strategy': {strategy: code_list}})

    def execute(self, command, current):
        # print("receiver:")
        # print(_receiver)
        print('PID:{0}, Thread:{1}'.format(os.getpid(), threading.currentThread().getName()))
        print('execute: ' + command)
        ret = Executor.execute(command)
        print(ret)
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

    def add_data_source(self, id, ds):
        if id not in self._ds:
            self._ds[id] = ds
            return True
        else:
            return False


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
                return Executor.convertRetValue(msg)
                
        try:
            return exe(command)            
        except KeyboardInterrupt:
            pass        
        except Exception as e:
            print(e)

        print("Done.")
 
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
                pass    # ret_val will be error description
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
            elif isinstance(msg, str):
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
def create_endpoint(name):
    print('PID:{0}, Thread:{1}'.format(os.getpid(), threading.currentThread().getName()))
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

        adapter = communicator.createObjectAdapter(name + "Adapter")
        adapter.add(Messenger(), Ice.stringToIdentity(name))
        adapter.activate()
        communicator.waitForShutdown()

def init():
    with concurrent.futures.ProcessPoolExecutor(max_workers=5) as executor:
        executor.submit(create_endpoint, 'DataCenter')
        executor.submit(create_endpoint, 'OrderPlace')
        executor.submit(create_endpoint, 'LimitedReq')