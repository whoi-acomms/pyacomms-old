'''
Created on Jul 13, 2012

@author: Eric
'''

from threading import Thread
from time import sleep

from serial import Serial

from acomms.modem_connections.serial_connection import SerialConnection


class IridiumConnection(SerialConnection):
    '''
    classdocs
    '''


    def __init__(self, modem, port, baudrate, number, timeout=0.1):
        '''
        Constructor
        '''
        self._incoming_line_buffer = ""

        self.connection_type = "direct_iridium"

        self.modem = modem
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout

        self._serialport = Serial(port, baudrate, timeout=self.timeout)

        self._thread = Thread(target=self._listen)
        self._thread.setDaemon(True)
        self._thread.start()

        self.state = 'DISCONNECTED'
        self.modem = modem
        self.number = str(number)
        self.counter = 0


    def _listen(self):
        while True:
            if self._serialport.isOpen():
                msg = self.raw_readline()
                if not self._serialport.getCD():
                    # Not connected via Iridium
                    # Processing I/O with Iridium dialer.
                    self.process_io(msg)
                else:
                    # We are connected, so pass through to NMEA
                    self.modem._process_incoming_nmea(msg)
                    self.modem._process_outgoing_nmea()
                    #Send keep alive \r\n so iridium does think the connection is empty.
                    self._serialport.write("\r\n")
            else:  # not connected
                sleep(0.5) # Wait half a second, try again.

    def process_io(self, msg):
        # This is called by the primary serial processing loop.
        # It will be called whenever we have a line of data, or periodically (based on a timeout)
        if msg is None:
            msg = ""

        if self.state == "DIALING":
            if "CONNECT" in msg:
                self.state = "CONNECTED"
            elif "NO CARRIER" in msg:
                self.state = "DISCONNECTED"
            elif "NO ANSWER" in msg:
                self.state = "DISCONNECTED"
            elif "BUSY" in msg:
                self.state = "DISCONNECTED"
            elif "ERROR" in msg:
                self.state = "DISCONNECTED"
            if self.counter > 600: #Counts are about 0.1s
                self.state = "DISCONNECTED"
            self.counter += 1
        elif self.state == 'DISCONNECTED':
            self.counter = 0
            self.do_dial()
        elif self.state == "CONNECTED":
            # In theory, we shouldn't be here, because if we are connected, traffic is passed through to the umodem module.
            # So, give us a 1 message margin of error (basically, ignore this input) and try dialing on the next timeout/message.
            self.state = "DISCONNECTED"

        if msg is not "":
            self.modem._daemon_log.info("$IRIDIUM,{0},{1}".format(self.modem.name, msg.strip()))
        self.modem._daemon_log.debug("$IRIDIUM,{0},Current State:{1}".format(self.modem.name, self.state))

    def raw_readline(self):
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

    def do_dial(self):
        # Toggle DTR
        self.modem._daemon_log.info("$IRIDIUM,{0},Dialing {1}".format(self.modem.name, self.number))
        sleep(2)
        self._serialport.setDTR(False)
        sleep(0.1)
        self._serialport.setDTR(True)
        self._serialport.write("ATD{0}\r\n".format(self.number))
        self.state = "DIALING"

    def close(self):
        self._serialport.setDTR(False)
        sleep(0.2)
        self._serialport.close()

    def wait_for_connect(self):
        while self.state != "CONNECTED":
            sleep(1)