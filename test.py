import os
import time
import asyncio
import aioprocessing
import multiprocessing

t = {}

def func(queue, event, lock, items, t):
    """ Demo worker function.

    This worker function runs in its own process, and uses
    normal blocking calls to aioprocessing objects, exactly 
    the way you would use oridinary multiprocessing objects.

    """
    print('processing pid:{0}'.format(os.getpid()))
    #with lock:
        #event.set()
    for item in items:
        for i in range(10000):
            t.update({i: i+1})
            if i % 1000 ==0:
                print('processing pid:{0}'.format(os.getpid()))
                print('length:{0}'.format(len(t)))
    queue.close()

@asyncio.coroutine
def example(queue, event, lock):
    l = [1,2,3,4,5]
    p = aioprocessing.AioProcess(target=func, args=(queue, event, lock, l, t))
    p2 = aioprocessing.AioProcess(target=func, args=(queue, event, lock, l, t))
    p.start()
    p2.start()
    while True:
        result = yield from queue.coro_get()
        if result is None:
            break
        print("Got result {0}: pid: {1}".format(result, os.getpid()))
    yield from p.coro_join()
    yield from p2.coro_join()

@asyncio.coroutine
def example2(queue, event, lock):
    yield from event.coro_wait()
    #with (yield from lock):
    yield from queue.coro_put(78)
    yield from queue.coro_put(None) # Shut down the worker

if __name__ == "__main__":
    print(t)
    print('current pid: {0}'.format(os.getpid()))
    loop = asyncio.get_event_loop()
    queue = aioprocessing.AioQueue()
    lock = aioprocessing.AioLock()
    event = aioprocessing.AioEvent()
    tasks = [
        asyncio.ensure_future(example(queue, event, lock)), 
        asyncio.ensure_future(example2(queue, event, lock)),
    ]
    f = loop.run_until_complete(asyncio.wait(tasks))
    
    loop.close()