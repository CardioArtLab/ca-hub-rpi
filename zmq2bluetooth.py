#/usr/bin/python2
"""
Periperal bluetooth (server) waiting for connection from tablet
use zeromq sink server to collect the data from USB
binds pull socket to tcp://localhost:6372

Author: Jirawat I. <nodtem66@gmail.com>
Python version: 3.5
"""
import os
import signal
import threading

import bluetooth
import zmq
from ringbuffer import ringbuffer
from logger import getLogger

# logger variabler
LOG = getLogger('zmq-sink')

# zmq instance
context = zmq.Context()
zmeSvr = None

class ZmqServer(threading.Thread):
    def __init__(self, out_ring):
        self.receiver = context.socket(zmq.PULL)
        self.receiver.bind('tcp://127.0.0.1:6372')
        self.running = True
        self.out_ring = out_ring
        self.errors = []
        self.devices = {}
        self.buffer = ''
        threading.Thread.__init__(self, name='zmq-thread')
        LOG.info('start pull at 127.0.0.1:6372')

    def getDevices(self):
        return self.devices

    def getErrors(self):
        e = self.errors
        self.errors = []
        return e

    def stop(self):
        self.running = False
        if self.receiver is not None:
            self.receiver.close()

    def run(self):
        while self.running:
            try:
                data = self.receiver.recv()
                if data:
                    if data[0] == 0:
                        self.buffer += data[1:] + '\n'
                        if len(self.buffer) >= 10000:
                            self.out_ring.try_write(self.buffer[:10000])
                            self.buffer = self.buffer[10000:]
                    elif data[0] == 1 or data[0] == 2:
                        busnum = (data[1] & 0xF0) >> 4
                        devnum = (data[1] & 0x0F)
                        key = str(busnum) + ":" + str(devnum)
                        productId = data[2]
                        if data[0] == 1:
                            if not key in self.devices:
                                self.devices[key] = productId
                                LOG.info('Registered %s', key + ' ' + str(productId))
                        elif data[0] == 2:
                            if key in self.devices:
                                self.devices.pop(key)
                                LOG.info('Unregistered %s', key + ' ' + str(productId))
                    elif data[0] == 3:
                        self.errors.append(data[1:])
            except ringbuffer.WaitingForReaderError:
                pass

# bluetooth server instance
BLUETOOTH_STATE_READY = 0
BLUETOOTH_STATE_DATA = 1
bleSvr = None
class BluetoothServer(threading.Thread):
    def __init__(self, in_ring, zmq_server, ring_reader, serverSocket=None, clientSocket=None):
        if serverSocket is None:
            self.serverSocket = serverSocket
            self.clientSocket = clientSocket
            self.serviceName = "CardioArtHub"
            self.uuid = "94f39d29-716d-437d-973b-fba39e49d2e1"
        else:
            self.serverSocket = serverSocket
            self.clientSocket = clientSocket

        self.in_ring = in_ring
        self.ring_reader = ring_reader
        self.zmq_server = zmq_server
        # Create the server socket
        self.getBluetoothSocket()
        # get bluetooth connection to port # of the first available
        self.getBluetoothConnection()
        # advertising bluetooth services
        self.advertiseBluetoothService()
        # private properties
        self.waitForExitLoop = threading.Condition()
        self.isExitLoop = False
        self.running = True
        self.state = BLUETOOTH_STATE_READY;

        threading.Thread.__init__(self, name='ble-thread')

    def getBluetoothSocket(self):
        try:
            self.serverSocket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
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
            self.clientSocket.setblocking = False
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
        except Exception:
            LOG.error("Failed to close the bluetooth sockets ", exc_info=True)

    def run(self):
        while self.running:
            try:
                # Accepting bluetooth connection
                self.acceptBluetoothConnection()
                while self.running:
                    dataRecv = self.clientSocket.recv(1024)
                    if len(dataRecv) >= 3:
                        if dataRecv[0] == ord('l') and dataRecv[1] == ord('s') and dataRecv[2] == ord('t'):
                            self.state = BLUETOOTH_STATE_READY
                            devices = self.zmq_server.getDevices()
                            self.clientSocket.send(str(len(devices.keys())) + '\r\n')
                            for k, v in devices.items():
                                self.clientSocket.send(str(k)+' '+str(v) + '\r\n')
                        elif dataRecv[0] == ord('e') and dataRecv[1] == ord('r') and dataRecv[2] == ord('r'):
                            self.state = BLUETOOTH_STATE_READY
                            errors = self.zmq_server.getErrors()
                            self.clientSocket.send(str(len(errors)) + '\r\n')
                            for err in errors:
                                self.clientSocket.send(err + '\r\n')
                        elif dataRecv[0] == ord('r') and dataRecv[1] == ord('d') and dataRecv[2] == ord('y'):
                            self.state = BLUETOOTH_STATE_DATA
                    if self.state == BLUETOOTH_STATE_DATA:
                        try:
                            data = self.in_ring.try_read(self.ring_reader)
                            self.clientSocket.send(data + '\r\n')
                        except (ringbuffer.WriterFinishedError, ringbuffer.WaitingForWriterError):
                            pass

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
    ring = ringbuffer.RingBuffer(slot_bytes=10000, slot_count=120)
    ring.new_writer()
    reader = ring.new_reader()
    #init server instance
    zmqSvr = ZmqServer(ring)
    bleSvr = BluetoothServer(ring, zmq_server=zmqSvr, ring_reader=reader)
    # register signal event
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    # start bluetooth server
    bleSvr.start()
    zmqSvr.start()
