from multiprocessing import Queue
from threading import Thread
from random import randrange

queue = Queue(10)

class Consumer(Thread):
    def __init__(self, name, queue):
        Thread.__init__(self)
        self.queue = queue
        self._name = name

    def run(self):
        while True:
            num = self.queue.get()
            #self.queue.task_done()
            print(self._name + ' get number: ' + str(num))



class Producer(Thread):
    def __init__(self, queue):
        Thread.__init__(self)
        self.queue = queue

    def run(self):
        i = 0
        while True:
            num = randrange(1, 10)
            self.queue.put(num)

            print('producer produce number : ' + str(num))
            i += 1
            if i > 5:
                break


def main():
    #for i in range(5):
    p = Producer(queue)
    c = Consumer('c',queue)
    c1 = Consumer('c1',queue)
    p.setDaemon(True)
    c.setDaemon(True)
    c1.setDaemon(True)
    
    c.start()
    c1.start()
    p.start()
    #queue.join()


if __name__ == "__main__":
    main()