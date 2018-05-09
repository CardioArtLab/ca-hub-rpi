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
import threading

import usb1 as _usb1
import zmq as _zmq
import hardware
from logger import LOG

parser = argparse.ArgumentParser()
parser.add_argument('bus')
parser.add_argument('address')
args = parser.parse_args()

usb1 = _usb1.USBContext()

device = None
handle = None
productId = hardware.INVALID_PRODUCT_ID
productName = ''
maxPacketSize = 64
for _device in usb1.getDeviceIterator(skip_on_error=True):
    if (_device.getBusNumber() == int(args.bus) and _device.getDeviceAddress() == int(args.address)):
        LOG.info('Initialize device bus:%s address:%s', args.bus, args.address)
        productName = _device.getProduct()
        maxPacketSize = _device.getMaxPacketSize(hardware.ENDPOINT_ADDRESS)
        LOG.info('%s (%s)', productName, _device.getManufacturer())
        LOG.info('packet size: %d', maxPacketSize)
        productId = hardware.getIdFromProductName(productName)
        device = _device
        break

if device is None:
    LOG.error('Device can not be initialized!')
    sys.exit(1)

if productId == hardware.INVALID_PRODUCT_ID:
    LOG.error('Unsupport USB device')
    sys.exit(1)
# init zmq broker
zmq = _zmq.Context()
sender = zmq.socket(_zmq.PUSH)
sender.connect('tcp://127.0.0.1:6372')
LOG.info('connect zmq pull server')

# register signal handler
running = True
waitForExitLoop = threading.Event()
def shutdown(signum, frame):
    LOG.info('Shutting down...')
    running = False
    if handle is not None:
        handle.releaseInterface(0)
        handle.close()
    if type(device).__name__ == 'USBDevice':
        device.close()
    sender.close()
    os._exit(1)

signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)

# transfer callback function
def mainloop():
    # init device
    try:
        handle = device.open()
        handle.claimInterface(0)
        header = ((int(args.bus) & 0x0F) << 4) | (int(args.address) & 0x0F)

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
                    data = bytearray([header, productId]) + data
                    sender.send(struct.pack('>' + str(len(data)) + 'B', *data))
            except (Exception, _usb1.USBErrorInterrupted) as e:
                LOG.error(e)
    except (RuntimeError, IOError, _usb1.USBError):
        LOG.error("Unexpected error: %s", sys.exc_info()[0])

if __name__ == '__main__':
    mainloop()
