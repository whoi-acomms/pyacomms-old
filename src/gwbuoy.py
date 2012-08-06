'''
Created on Feb 10, 2012

@author: Eric
'''
import logging
from modem import Micromodem
from messageparams import Packet, CycleInfo, Rates
from cyclestats import CycleStats
from time import sleep
from threading import Thread
import bitstring


class GwBuoy(object):
    def __init__(self):
        self.gw3_path = 'COM10'
        self.gw3_phone = '881676330186'
        
        self.gw4_path = 'COM11'
        self.gw4_phone = None
        
        self.um_baud = 19200
        
        self.logpath = 'c:/temp/'
        
        self.logger = None
        self.start_log()

        
        self.logger.info("Started GW Buoy Daemon")
                
        self.um3 = Micromodem(name='modem3', logpath=self.logpath, iridiumnumber=self.gw3_phone)
        self.um4 = Micromodem(name='modem4', logpath=self.logpath, iridiumnumber=self.gw4_phone)
        
        
    
    def start_log(self):
        if self.logger == None:
            # Configure logging
            logformat = logging.Formatter("%(asctime)s\t%(levelname)s\t%(message)s", "%Y-%m-%d %H:%M:%S")
            self.logger = logging.getLogger("gwbuoys")
            self.logger.setLevel(logging.DEBUG)
            fh = logging.FileHandler(self.logpath + 'gwbuoys.log')
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(logformat)
            ch = logging.StreamHandler()
            ch.setLevel(logging.DEBUG)
            ch.setFormatter(logformat)
            self.logger.addHandler(fh)
            self.logger.addHandler(ch)
        
        self.logger.info("Started GW Buoy logging")
    
    
    
    def run_listen(self):
        self.setup_gw3()
        #self.setup_gw4()
        
        while (1):
            # We are event-driven.
            sleep(1)
    
        
    def setup_gw3(self):
        self.um3.connect(self.gw3_path, self.um_baud)
        sleep(1)
        self.um3.set_config('BND', 1)
        self.um3.set_config('SRC', 73)
        sleep(1)
    
    def setup_gw4(self):
        self.um4.connect(self.gw4_path, self.um_baud)
        sleep(1)
        self.um4.set_config('BND', 1)
        self.um4.set_config('SRC', 74)
        sleep(1)    

        

if __name__ == '__main__':
    gwbuoys = GwBuoy()
    
    gwbuoys.run_listen()