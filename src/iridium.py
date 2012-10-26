'''
Created on Jul 13, 2012

@author: Eric
'''

import serial
from time import sleep

class Iridium(object):
    '''
    classdocs
    '''


    def __init__(self,modem,number):
        '''
        Constructor
        '''
        self.state = 'DISCONNECTED'
        self.modem = modem
        self.number = str(number)
        self.counter = 0


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

