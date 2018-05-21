#/usr/bin/python2
"""
udev service for USB
transfer USB data to zeromq pull server via tcp
required pull socket: tcp://localhost:6372

Author: Jirawat I. <nodtem66@gmail.com>
Python version: 2.7
"""
import argparse
import os
import signal
import struct
import sys

import usb1 as _usb1
import zmq as _zmq
import hardware
from logger import getLogger

parser = argparse.ArgumentParser()
parser.add_argument('bus')
args = parser.parse_args()
_args = args.bus.split(':')
LOG = getLogger('usb2mq')
if len(_args) < 2:
    LOG.error('invalid argument %s', args.bus)
    sys.exit(1)
bus, address = _args[0:2]


# write pid into file
#pidfile = open('/opt/ca-hub-rpi/pid/{}-{}'.format(bus, address), 'w')
#pidfile.write(str(os.getpid()))
#pidfile.close()

# init zmq broker
zmq = _zmq.Context()
sender = zmq.socket(_zmq.PUSH)
sender.linger = 250
sender.connect('tcp://127.0.0.1:6372')
LOG.info('connect zmq pull server')

# header in zmq packet
header = ((int(bus) & 0x0F) << 4) | (int(address) & 0x0F)

def send(*arr):
    if not sender:
        return
    try:
        data = bytearray()
        for x in arr:
            data += bytearray(x)
        sender.send(struct.pack('>' + str(len(data)) + 'B', *data), flags=_zmq.NOBLOCK)
    except _zmq.ZMQError:
        pass

# register signal handler
running = False
def shutdown(signum, frame):
    global running
    LOG.info('Shutting down...')
    if running and not sender.closed:
        running = False
        send([2, header, productId])
    running = False
    if handle is not None:
        handle.releaseInterface(0)
        handle.close()
    if type(device).__name__ == 'USBDevice':
        device.close()
    sender.close()
    zmq.term()
    os._exit(0)

signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)


# get device from bus and address
usb1 = _usb1.USBContext()
device = None
handle = None
productId = hardware.INVALID_PRODUCT_ID
productName = ''
maxPacketSize = 64
try:
    for _device in usb1.getDeviceIterator(skip_on_error=True):
        if (_device.getBusNumber() == int(bus) and _device.getDeviceAddress() == int(address)):
            LOG.info('Initialize device bus:%s address:%s', bus, address)
            productName = _device.getProduct()
            maxPacketSize = _device.getMaxPacketSize(hardware.ENDPOINT_ADDRESS)
            LOG.info('%s (%s)', productName, _device.getManufacturer())
            LOG.info('packet size: %d', maxPacketSize)
            productId = hardware.getIdFromProductName(productName)
            device = _device
            break
except (RuntimeError, IOError, _usb1.USBError) as e:
    LOG.error("Unexpected error: %s", e)
    send([3, header, productId], str(e))
    shutdown(0, 0)

if device is None:
    LOG.error('Device can not be initialized!')
    shutdown(0, 0)

if productId == hardware.INVALID_PRODUCT_ID:
    LOG.error('Unsupport USB device')
    shutdown(0, 0)

# transfer callback function
def mainloop():
    global handle
    global running
    # init device
    try:
        handle = device.open()
        handle.claimInterface(0)
        send([1, header, productId])
        running = True

        while running:
            try:
                data = handle.interruptRead(hardware.ENDPOINT_ADDRESS, maxPacketSize)
                isValid = False
                if productId == hardware.SPO2_PRODUCT_ID:
                    assert len(data) == 6
                    isValid = True
                elif productId == hardware.ECG_PRODUCT_ID:
                    assert len(data) == 27
                    isValid = True
                if isValid and running:
                    send([0, header, productId], data)
            except _usb1.USBErrorInterrupted as e:
                LOG.error(e)
                send([3, header, productId], str(e))
                shutdown(0, 0)
    except (RuntimeError, IOError, _usb1.USBError):
        LOG.error("Unexpected error: %s", sys.exc_info()[0])
        send([3, header, productId], str(sys.exc_info()[0]))

if __name__ == '__main__':
    mainloop()
