# Test zeromq sink server
# binds pull socket to tcp://localhost:6372
# Author Jirawat I. <nodtem66@gmail.com>
from multiprocessing import Process
import time

import logging
import zmq

# logger variabler
logger = logging.getLogger('zmq-sink')
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)

class ZmqServer(Process):
    def __init__(self):
        # local variables
        self.receiver = None
        self.now = time.time()
        self.count = 0
        self.running = True
        Process.__init__(self, name='zmq-process')
    def run(self):
        # socket to receive message on
        context = zmq.Context()
        self.receiver = context.socket(zmq.PULL)
        self.receiver.bind('tcp://127.0.0.1:6372')
        logger.info('start pull at 127.0.0.1:6372')
        while self.running:
            # wait for start of batch
            try:
                self.process()
            except (zmq.Again, zmq.ZMQError):
                pass

            if time.time() - self.now > 1:
                self.now = time.time()
                logger.info('%d', self.count)
    def process(self):
        s = self.receiver.recv(flags=zmq.NOBLOCK)
        if s:
            self.count += 1
    def stop(self):
        self.running = False

if __name__ == '__main__':
    server = ZmqServer()
    server.start()
    server.join()
