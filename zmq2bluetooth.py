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
import select
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
    # pylint: disable=too-many-branches
    # pylint: disable=too-many-nested-blocks

    def __init__(self, q, zmq_server, devices, errors, manager):
        self.serviceName = "CardioArtHub"
        self.uuid = "94f39d29-716d-437d-973b-fba39e49d2e1"
        self.queue = q
        self.internal_queue = {}
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
        self.state = {}

        Process.__init__(self, name='ble-thread')

    def getBluetoothSocket(self):
        try:
            self.serverSocket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
            self.serverSocket.setblocking(0)
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
            clientSocket, clientInfo = self.serverSocket.accept()
            clientSocket.setblocking(0)
            #self.clientSocket.settimeout(0)
            LOG.info("Accepted bluetooth connection from %s", clientInfo)
            return clientSocket
        except (bluetooth.BluetoothError, SystemExit, KeyboardInterrupt):
            LOG.error("Failed to accept bluetooth connection ... ", exc_info=True)

    def closeSocket(self, s):
        if s in self.internal_queue:
            del self.internal_queue[s]
        if s in self.state:
            del self.state[s]
        s.close()

    def readClient(self, client):
        dataRecv = client.recv(10)
        if len(dataRecv) >= 3 and (client in self.internal_queue):
            if dataRecv[0:3] == b'lst':
                self.state[client] = BLUETOOTH_STATE_READY
                device = []
                devices = self.devices.copy()
                msg = str(len(devices.keys()))
                for k, v in devices.items():
                    device.append(str(k)+':'+str(v))
                if device:
                    msg += '\x1f' + (','.join(device))
                self.internal_queue[client].put(msg + '\n')
            elif dataRecv[0:3] == b'err':
                self.state[client] = BLUETOOTH_STATE_READY
                errors = copy.deepcopy(self.errors)
                # clear ListProxy
                # see: https://stackoverflow.com/questions/23499507/how-to-clear-the-content-from-a-listproxy
                self.errors[:] = []
                msg = str(len(errors))
                if errors:
                    msg += '\x1f' + (','.join(errors))
                self.internal_queue[client].put(msg + '\n')
            elif dataRecv[0:3] == b'len':
                self.state[client] = BLUETOOTH_STATE_READY
                self.internal_queue[client].put(str(self.queue.qsize()) + '\n')
            elif dataRecv[0:3] == b'rdy':
                self.state[client] = BLUETOOTH_STATE_DATA

        return len(dataRecv)

    def run(self):
        inputs = [self.serverSocket]
        outputs = []
        while inputs and self.running:
            try:
                readable, writable, exceptional = select.select(inputs, outputs, inputs)
                for s in readable:
                    if s is self.serverSocket:
                        # Accepting new bluetooth connection
                        connection = self.acceptBluetoothConnection()
                        inputs.append(connection)
                        self.state[connection] = BLUETOOTH_STATE_READY
                        self.internal_queue[connection] = queue.Queue()
                    else:
                        # Loop to communicate with connected client
                        if self.readClient(s):
                            if s not in outputs:
                                outputs.append(s)
                        else:
                            # Interpret empty result as closed connection
                            if s in outputs:
                                outputs.remove(s)
                            if s in inputs:
                                inputs.remove(s)
                            self.closeSocket(s)
                for s in writable:
                    try:
                        if self.state[s] == BLUETOOTH_STATE_DATA:
                            next_msg = self.queue.get_nowait()
                        else:
                            next_msg = self.internal_queue[s].get_nowait()
                    except queue.Empty:
                        outputs.remove(s)
                    else:
                        s.send(next_msg)
                for s in exceptional:
                    if s in outputs:
                        outputs.remove(s)
                    if s in inputs:
                        inputs.remove(s)
                    self.closeSocket(s)

            except (IOError, bluetooth.BluetoothError) as e:
                LOG.error(str(e))

    def stop(self):
        # Disconnecting bluetooth sockets
        self.running = False

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
