import logging
from time import sleep

def getLogger(name):
    LOG = logging.getLogger(name)
    formatter = logging.Formatter('%(levelname)s [%(name)s]: %(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
    h = logging.StreamHandler()
    h.setFormatter(formatter)
    #fh = logging.FileHandler('/opt/ca-hub-rpi/usb2mq.log', 'w')
    #fh.setFormatter(formatter)
    LOG.setLevel(logging.INFO)
    LOG.addHandler(h)
    #LOG.addHandler(fh)
    return LOG
