"""
Author Jirawat I. <nodtem66@gmail.com>
"""
import argparse
import sys
import signal

import usb1 as _usb1
import zmq as _zmq
import hardware
from logger import LOG

parser = argparse.ArgumentParser()
parser.add_argument('bus')
parser.add_argument('address')
args = parser.parse_args()

usb1 = _usb1.USBContext()
isFound = False

device = None
productId = hardware.INVALID_PRODUCT_ID
productName = ''
maxPacketSize = 64
for _device in usb1.getDeviceIterator(skip_on_error=True):
    if (_device.getBusNumber() == int(args.bus) and _device.getDeviceAddress() == int(args.address)):
        isFound = True
        LOG.info('Initialize device bus:%s address:%s', args.bus, args.address)
        productName = _device.getProduct()
        maxPacketSize = _device.getMaxPacketSize(hardware.ENDPOINT_ADDRESS)
        LOG.info('%s (%s)', productName, _device.getManufacturer())
        LOG.info('packet size: %d', maxPacketSize)
        productId = hardware.getIdFromProductName(productName)
        device = _device
        break

if not isFound:
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
def shutdown(signum, frame):
    LOG.info('Shutting down...')
    if type(device).__name__ == 'USBDevice':
        device.close()
    sender.close()
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)

# init device
try:
    handle = device.open()
    #handle.resetDevice()
    #handle.releaseInterface(0)
    #handle.claimInterface(0)

except (RuntimeError, IOError, _usb1.USBError):
    LOG.error("Unexpected error: %s", sys.exc_info()[0])
    shutdown(signal.SIGINT, 0)
