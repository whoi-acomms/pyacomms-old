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


class GliderTx(object):
    def __init__(self):
        self.um_10_path = '/dev/ttyS1'
        #self.um_10_path = 'COM10'
        
        self.um_2750_path = '/dev/ttyS0'
        self.um_array_path = '/dev/ttyE0'
        
        self.um_baud = 19200
        
        self.logpath = '/var/log/glidertx/'
        #self.logpath = 'c:/temp/glider/'
        self.start_log()
                
        self.um_10k = Micromodem(logpath=(self.logpath + 'um_10k/'))
        self.um_2750 = Micromodem(logpath=(self.logpath + 'um_2750/'))
        self.um_array = Micromodem(logpath=(self.logpath + 'um_array/'))
        
    
    def start_log(self):
        # Configure logging
        logformat = logging.Formatter("%(asctime)s\t%(levelname)s\t%(message)s", "%Y-%m-%d %H:%M:%S")
        self.logger = logging.getLogger("glider")
        self.logger.setLevel(logging.DEBUG)
        fh = logging.FileHandler(self.logpath + 'glidertx.log')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logformat)
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(logformat)
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)
        
    def run_tx(self, do_10k=False, do_2750=False):
        if do_10k:
            self.setup_10k()
        
        if do_2750:
            self.setup_2750()
            
        while (1):
            if do_10k:
                self.um_10k.set_config('BW0', 2000)
                sleep(1)
                self.um_10k.send_test_packet(127, 1, 3)
                sleep(300)
                self.um_10k.send_test_packet(127, 4, 2)
                sleep(300)
                self.um_10k.set_config('BW0', 1000)
                sleep(1)
                self.um_10k.send_test_packet(127, 1, 2)
                sleep(300)
                self.um_10k.send_test_packet(127, 4, 1)
                sleep(300)
                
            if do_2750:
                self.um_2750.set_config('BW0', 1250)
                sleep(1)
                self.um_2750.send_test_packet(127, 1, 2)
                sleep(300)
                self.um_2750.send_test_packet(127, 4, 1)
                sleep(300)
                self.um_2750.set_config('BW0', 500)
                sleep(1)
                self.um_2750.send_test_packet(127, 1, 1)
                sleep(300)
            
        
    
    def setup_2750(self):
        self.um_2750.connect(self.um_2750_path, self.um_baud)
        sleep(1)
        self.um_2750.set_config('FC0', 2750)
        self.um_2750.set_config('BW0', 1250)
        self.um_2750.set_config('SRC', 101)
        sleep(1)
        
    def setup_10k(self):
        self.um_10k.connect(self.um_10k_path, self.um_baud)
        sleep(1)
        self.um_10k.set_config('FC0', 2750)
        self.um_10k.set_config('BW0', 1250)
        self.um_10k.set_config('SRC', 10)
        sleep(1)

if __name__ == '__main__':
    glider = GliderTx()
    
    glider.run_tx(do_10k=True, do_2750=True)