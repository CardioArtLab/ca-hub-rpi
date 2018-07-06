#/usr/bin/python2
"""
Periperal bluetooth (server) waiting for connection from tablet
use zeromq sink server to collect the data from USB
binds pull socket to tcp://localhost:6372

Author: Jirawat I. <nodtem66@gmail.com>
Python version: 3.5
"""
import copy
import os
import signal
import queue
#import threading
from multiprocessing import Queue, Process, Manager

import bluetooth
import zmq
from logger import getLogger

# logger variabler
LOG = getLogger('zmq-sink')

# zmq instance
MAX_BUFFER_LENGTH = 120000
zmeSvr = None
class ZmqServer(Process):
    def __init__(self, q, devices, errors):
        self.running = True
        self.queue = q
        self.errors = errors
        self.devices = devices
        self.receiver = None
        LOG.info('start pull at 127.0.0.1:6372')
        Process.__init__(self, name='zmq-thread')

    def stop(self):
        self.running = False
        if self.receiver is not None:
            self.receiver.close()

    def process(self):
        data = self.receiver.recv(flags=zmq.NOBLOCK)
        if data:
            if data[0] == 0:
                try:
                    self.queue.put_nowait(data[1:])
                except queue.Full:
                    self.queue.get()
            else:
                key = str(data[1]) + ":" + str(data[2])
                productId = data[3]
                if data[0] == 1:
                    if not key in self.devices:
                        self.devices[key] = productId
                        LOG.info('Registered %s', key + ' ' + str(productId))
                elif data[0] == 2 or data[0] == 3:
                    if key in self.devices:
                        self.devices.pop(key)
                        LOG.info('Unregistered %s', key + ' ' + str(productId))
                if data[0] == 3:
                    e = key + ':' + data[4:].decode('utf8')
                    LOG.info('ERROR %s', e)
                    self.errors.append(e)

    def run(self):
        context = zmq.Context()
        self.receiver = context.socket(zmq.PULL)
        self.receiver.bind('tcp://127.0.0.1:6372')

        while self.running:
            try:
                self.process()
            except (zmq.Again, zmq.ZMQError):
                pass
            except (RuntimeError, IOError) as e:
                LOG.error('ZMQ Error: %s', str(e))

# bluetooth server instance
BLUETOOTH_STATE_READY = 0
BLUETOOTH_STATE_DATA = 1
bleSvr = None
class BluetoothServer(Process):

    """Bluetooth server thread"""
    # pylint: disable=too-many-instance-attributes

    def __init__(self, q, zmq_server, devices, errors, manager):
        self.serviceName = "CardioArtHub"
        self.uuid = "94f39d29-716d-437d-973b-fba39e49d2e1"
        self.queue = q
        self.devices = devices
        self.errors = errors
        self.zmq_server = zmq_server
        self.manager = manager
        self.clientSocket = None
        self.serverSocket = None

        # Create the server socket
        self.getBluetoothSocket()
        # get bluetooth connection to port # of the first available
        self.getBluetoothConnection()
        # advertising bluetooth services
        self.advertiseBluetoothService()

        # private properties
        self.running = True
        self.state = BLUETOOTH_STATE_READY

        Process.__init__(self, name='ble-thread')

    def getBluetoothSocket(self):
        try:
            self.serverSocket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
            #self.serverSocket.setblocking(0)
            LOG.info("Bluetooth server socket successfully created for RFCOMM service...")
        except (bluetooth.BluetoothError, SystemExit, KeyboardInterrupt):
            LOG.error("Failed to create the bluetooth server socket ", exc_info=True)

    def getBluetoothConnection(self):
        try:
            self.serverSocket.bind(("", bluetooth.PORT_ANY))
            LOG.info("Bluetooth server socket bind successfully on host "" to PORT_ANY...")
        except (bluetooth.BluetoothError, SystemExit, KeyboardInterrupt):
            LOG.error("Failed to bind server socket on host to PORT_ANY ... ", exc_info=True)
        try:
            self.serverSocket.listen(1)
            LOG.info("Bluetooth server socket put to listening mode successfully ...")
        except (bluetooth.BluetoothError, SystemExit, KeyboardInterrupt):
            LOG.error("Failed to put server socket to listening mode  ... ", exc_info=True)
        try:
            port = self.serverSocket.getsockname()[1]
            LOG.info("Waiting for connection on RFCOMM channel %d", port)
        except (bluetooth.BluetoothError, SystemExit, KeyboardInterrupt):
            LOG.error("Failed to get connection on RFCOMM channel  ... ", exc_info=True)

    def advertiseBluetoothService(self):
        try:
            bluetooth.advertise_service(self.serverSocket, self.serviceName,
                                        service_id=self.uuid,
                                        service_classes=[self.uuid, bluetooth.SERIAL_PORT_CLASS],
                                        profiles=[bluetooth.SERIAL_PORT_PROFILE],
                                        #protocols = [ OBEX_UUID ]
                                       )
            LOG.info("%s advertised successfully ...", self.serviceName)
        except (bluetooth.BluetoothError, SystemExit, KeyboardInterrupt):
            LOG.error("Failed to advertise bluetooth services  ... ", exc_info=True)

    def acceptBluetoothConnection(self):
        try:
            self.clientSocket, clientInfo = self.serverSocket.accept()
            #self.clientSocket.setblocking(0)
            #self.clientSocket.settimeout(0)
            LOG.info("Accepted bluetooth connection from %s", clientInfo)
        except (bluetooth.BluetoothError, SystemExit, KeyboardInterrupt):
            LOG.error("Failed to accept bluetooth connection ... ", exc_info=True)

    def closeBluetoothSocket(self):
        try:
            if self.clientSocket is not None:
                self.clientSocket.close()
            if self.serverSocket is not None:
                self.serverSocket.close()
            LOG.info("Bluetooth sockets successfully closed ...")
        except bluetooth.BluetoothError:
            LOG.error("Failed to close the bluetooth sockets ", exc_info=True)

    def readClient(self):
        while self.running:
            dataRecv = self.clientSocket.recv(10)
            if len(dataRecv) >= 3:
                if dataRecv[0:3] == b'lst':
                    self.state = BLUETOOTH_STATE_READY
                    device = []
                    devices = self.devices.copy()
                    self.clientSocket.send(str(len(devices.keys())) + '\r\n')
                    for k, v in devices.items():
                        device.append(str(k)+':'+str(v))
                    if device:
                        self.clientSocket.send(','.join(device) + '\r\n')
                elif dataRecv[0:3] == b'err':
                    self.state = BLUETOOTH_STATE_READY
                    errors = copy.deepcopy(self.errors)
                    # clear ListProxy
                    # see: https://stackoverflow.com/questions/23499507/how-to-clear-the-content-from-a-listproxy
                    self.errors[:] = []
                    self.clientSocket.send(str(len(errors)) + '\r\n')
                    if errors:
                        self.clientSocket.send(','.join(errors) + '\r\n')
                elif dataRecv[0:3] == b'len':
                    self.state = BLUETOOTH_STATE_READY
                    self.clientSocket.send(str(self.queue.qsize()) + '\r\n')
                elif dataRecv[0:3] == b'rdy':
                    self.state = BLUETOOTH_STATE_DATA

            try:
                if self.state == BLUETOOTH_STATE_DATA:
                    data = self.queue.get_nowait()
                    self.clientSocket.send(data)
            except queue.Empty:
                self.state = BLUETOOTH_STATE_READY

    def run(self):
        while self.running:
            try:
                # Accepting new bluetooth connection
                self.acceptBluetoothConnection()
                # Loop to communicate with connected client
                self.readClient()

            except (IOError, bluetooth.BluetoothError) as e:
                LOG.error(e)

    def stop(self):
        # Disconnecting bluetooth sockets
        self.running = False
        self.closeBluetoothSocket()

# shutdown event
def shutdown(signals, frame):
    LOG.info('Shuting down...')
    if zmqSvr is not None:
        zmqSvr.stop()
    if bleSvr is not None:
        bleSvr.stop()
    os._exit(0)

if __name__ == '__main__':
    # init ringbuffer
    #ring = ringbuffer.RingBuffer(slot_bytes=32, slot_count=12000)
    #ring.new_writer()
    #reader = ring.new_reader()
    _q = Queue(MAX_BUFFER_LENGTH)

    with Manager() as manager:
        dev = manager.dict()
        err = manager.list()
        #init server instance
        zmqSvr = ZmqServer(_q, devices=dev, errors=err)
        bleSvr = BluetoothServer(_q, zmq_server=zmqSvr, devices=dev, errors=err, manager=manager)
        # register signal event
        signal.signal(signal.SIGINT, shutdown)
        signal.signal(signal.SIGTERM, shutdown)
        # start bluetooth server
        bleSvr.start()
        zmqSvr.start()

        bleSvr.join()
        zmqSvr.join()
