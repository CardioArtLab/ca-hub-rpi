#!/usr/bin/python

# File: bleServer.py
# Auth: P Srinivas Rao
# Desc: Bluetooth server application that uses RFCOMM sockets

import signal
import bluetooth
from logger import LOG

class bleServer:
    def __init__(self, serverSocket=None, clientSocket=None):
        if serverSocket is None:
            self.dataObj = None
            self.serverSocket = serverSocket
            self.clientSocket = clientSocket
            self.serviceName = "BluetoothServices"
            self.jsonFile = "text.json"
            self.uuid = "94f39d29-7d6d-437d-973b-fba39e49d4ee"
        else:
            self.serverSocket = serverSocket
            self.clientSocket = clientSocket

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

    def recvData(self):
        try:
            while True:
                data = self.clientSocket.recv(1024)
                if not data:
                    self.clientSocket.send("EmptyBufferResend")
                # remove the length bytes from the front of buffer
                # leave any remaining bytes in the buffer!
                dataSizeStr, _, data = data.partition(b':')
                dataSize = int(dataSizeStr)
                if len(data) < dataSize:
                    self.clientSocket.send("CorruptedBufferResend")
                else:
                    self.clientSocket.send("DataRecived")
                    break
            return data
        except (IOError, bluetooth.BluetoothError):
            pass

    def closeBluetoothSocket(self):
        try:
            self.clientSocket.close()
            self.serverSocket.close()
            LOG.info("Bluetooth sockets successfully closed ...")
        except bluetooth.BluetoothError:
            LOG.error("Failed to close the bluetooth sockets ", exc_info=True)

    def start(self):
        # Create the server socket
        self.getBluetoothSocket()
        # get bluetooth connection to port # of the first available
        self.getBluetoothConnection()
        # advertising bluetooth services
        self.advertiseBluetoothService()
        # Accepting bluetooth connection
        self.acceptBluetoothConnection()

    def mainloop(self):
        # receive data
        while True:
            dataRecv = self.recvData()
            LOG.info("recv: %s", dataRecv)

    def stop(self):
        # Disconnecting bluetooth sockets
        self.closeBluetoothSocket()

if __name__ == '__main__':
    #init server instance
    bleSvr = bleServer()
    # register signal event
    signal.signal(signal.SIGINT, bleSvr.stop)
    signal.signal(signal.SIGTERM, bleSvr.stop)
    # start bluetooth server
    bleSvr.start()
    bleSvr.mainloop()
