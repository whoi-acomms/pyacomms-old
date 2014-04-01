
from acomms.modem_connections import ModemConnection
from serial import Serial
from time import sleep
from threading import Thread


class SerialConnection(ModemConnection):

    def __init__(self, modem, port, baudrate, timeout=0.1):
        self._incoming_line_buffer = ""

        self.connection_type = "serial"

        self.modem = modem
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout

        self._serialport = Serial(port, baudrate, timeout=self.timeout)

        self._thread = Thread(target=self._listen)
        self._thread.setDaemon(True)
        self._thread.start()

    @property
    def is_connected(self):
        return self._serialport.isOpen()

    @property
    def can_change_baudrate(self):
        return True

    def change_baudrate(self,baudrate):
        self.baudrate = baudrate
        self._serialport.baudrate = baudrate
        return baudrate


    def close(self):
        self._serialport.close()

    def _listen(self):
        while True:
            if self._serialport.isOpen():
                msg = self.readline()
                # We are connected, so pass through to NMEA
                self.modem._process_incoming_nmea(msg)
                self.modem._process_outgoing_nmea()
            else: # not connected
                sleep(0.5) # Wait half a second, try again.

    def readline(self):
        """Returns a \n terminated line from the modem.  Only returns complete lines (or None on timeout)"""
        rl = self._serialport.readline()

        if rl == "":
            return None

        # Make sure we got a complete line.  Serial.readline may return data on timeout.
        if rl[-1] != '\n':
            self._incoming_line_buffer += rl
            return None
        else:
            if self._incoming_line_buffer != "":
                rl = self._incoming_line_buffer + rl
            self._incoming_line_buffer = ""
            return rl

    def write(self, data):
        self._serialport.write(data)
