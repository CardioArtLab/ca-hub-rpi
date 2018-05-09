#/usr/bin/python2
"""
Periperal bluetooth (server) waiting for connection from tablet
use zeromq sink server to collect the data from USB
binds pull socket to tcp://localhost:6372

Author: Jirawat I. <nodtem66@gmail.com>
Python version: 3.5
"""
import logging
import signal
import sys
import threading

import bluetooth
import zmq

# logger variabler
LOG = logging.getLogger('zmq-sink')
LOG.addHandler(logging.StreamHandler())
LOG.setLevel(logging.INFO)

# zmq instance
context = zmq.Context()
zmeSvr = None
class ZmqServer(threading.Thread):
    def __init__(self):
        self.receiver = context.socket(zmq.PULL)
        self.receiver.bind('tcp://127.0.0.1:6372')
        self.running = True
        threading.Thread.__init__(self, name='zmq-thread')
        LOG.info('start pull at 127.0.0.1:6372')
    def stop(self):
        self.running = False
        if self.receiver is not None:
            self.receiver.close()

    def run(self):
        while self.running:
            data = self.receiver.recv()
            LOG.info(data)

# bluetooth server instance
bleSvr = None
class BluetoothServer(threading.Thread):
    def __init__(self, serverSocket=None, clientSocket=None):
        if serverSocket is None:
            self.serverSocket = serverSocket
            self.clientSocket = clientSocket
            self.serviceName = "CardioArtHub"
            self.uuid = "94f39d29-716d-437d-973b-fba39e49d2e1"
        else:
            self.serverSocket = serverSocket
            self.clientSocket = clientSocket

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
                        if dataRecv[0] == b'l' and dataRecv[1] == b's' and dataRecv[2] == b't':
                            self.clientSocket.send("list of devices")
                        if dataRecv[0] == b'r' and dataRecv[1] == b'd' and dataRecv[2] == b'y':
                            self.clientSocket.send('a lot of data')
            except (IOError, bluetooth.BluetoothError) as e:
                LOG.error(e)

    def stop(self):
        # Disconnecting bluetooth sockets
        self.running = False
        self.closeBluetoothSocket()

# shutdown event
def shutdown(signals, frame):
    LOG.info('shuting down...')
    if zmqSvr is not None:
        zmqSvr.stop()
    if bleSvr is not None:
        bleSvr.stop()
    sys.exit(0)

if __name__ == '__main__':
    #init server instance
    bleSvr = BluetoothServer()
    zmqSvr = ZmqServer()
    # register signal event
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    # start bluetooth server
    bleSvr.start()
    zmqSvr.start()
