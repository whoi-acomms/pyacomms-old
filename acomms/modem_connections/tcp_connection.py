__author__ = 'andrew'

from modem_connection import ModemConnection
import asyncore
from socket import AF_INET, SOCK_STREAM
from threading import Thread

class TcpConnection(ModemConnection, asyncore.dispatcher_with_send):

    def __init__(self,modem, ipaddr,port):
        asyncore.dispatcher_with_send.__init__(self)
        self.create_socket(AF_INET, SOCK_STREAM)
        self.connect((ipaddr,port))
        self.io_file = self.socket.makefile()
        self.modem = modem

        self._thread = Thread(target=self._listen)
        self._thread.setDaemon(True)
        self._thread.start()

    def _listen(self):
        asyncore.loop()


    def is_connected(self):
        return True

    def write(self, data):
        self.send(data)

    def can_change_baudrate(self):
        return False

    def change_baudrate(self, baudrate):
        return 9600

    def handle_close(self):
        self.io_file.close()
        asyncore.dispatcher_with_send.close(self)

    def writable(self):
        return self.modem._message_waiting()

    def handle_read(self):
        msg = self.io_file.readline()
        self.modem._process_incoming_nmea(msg)


    def handle_write(self):
        self.modem._process_outgoing_nmea()