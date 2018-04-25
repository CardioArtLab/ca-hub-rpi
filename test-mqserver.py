# Test zeromq sink server
# binds pull socket to tcp://localhost:6372
# Author Jirawat I. <nodtem66@gmail.com>
import zmq
import sys
import time
import hardware
import logging

context = zmq.Context()

# socket to receive message on
receiver = context.socket(zmq.PULL)
receiver.bind('tcp://127.0.0.1:6372')

# local variables
now = time.time()
count = {}

# logger variabler
logger = logging.getLogger('zmq-sink')
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)

logger.info('start pull at 127.0.0.1:6372')
while True:
    # wait for start of batch
    s = receiver.recv()
    deviceId = s[0]
    if (not count.has_key(deviceId)):
        count[deviceId] = 1
    else:
        count[deviceId] += 1
    if (time.time() - now > 10):
        now = time.time()
        logger.info('%s', count)
