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
                if not self.getCD():
                    # Not connected via Iridium
                    # Processing I/O with Iridium dialer.
                    self.process_io(msg)
                else:
                    # We are connected, so pass through to NMEA
                    self.modem._process_incoming_nmea(msg)
                    self.modem._process_outgoing_nmea()
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
            self.modem.nmealog.info("$IRIDIUM,{0},{1}".format(self.modem.name, msg.strip()))


    def do_dial(self):
        #881676330186 is Buoy 3
        # Toggle DTR
        print("Iridium> Dialing...")
        sleep(2)
        self.modem.setDTR(False)
        sleep(0.05)
        self.modem.setDTR(True)
        self.modem.write("ATD{0}\r\n".format(self.number))
        self.state = "DIALING"
