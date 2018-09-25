#import pyqtgraph.examples
#pyqtgraph.examples.run()
'''
from futuquant import *
import time

def main():
    for i in range(10):
        ft = OpenQuoteContext(host='127.0.0.1', port=11111)
        time.sleep(1)
        ft.close()

if __name__ == '__main__':
    main()
    print('end')
'''
import logging
from daemonize import Daemonize

pid = "/tmp/test.pid"
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.propagate = False
fh = logging.FileHandler("/tmp/test.log", "w")
fh.setLevel(logging.DEBUG)
logger.addHandler(fh)
keep_fds = [fh.stream.fileno()]


def main():
    logger.debug("Test")

daemon = Daemonize(app="test_app", pid=pid, action=main, keep_fds=keep_fds)
daemon.start()