'''
Created on Feb 10, 2012

@author: Eric
'''
import logging
from acomms import Micromodem, Packet, CycleInfo, Rates, CycleStats
from time import sleep
from threading import Thread
import bitstring
import sys
import os


class GliderTx(object):
    def __init__(self):
        self.um_10_path = '/dev/ttyO1'
        #self.um_10_path = 'COM10'
        
        self.um_3750_path = '/dev/ttyO0'
        #self.um_array_path = '/dev/ttyE0'
        
        self.um_baud = 19200
        
        self.logpath = '/home/acomms/log/glidertx/'
        #self.logpath = 'c:/temp/glider/'
        self.start_log()
                
        self.um_3013 = Micromodem(logpath=(self.logpath + 'um_3013/'))
        self.um_2002 = Micromodem(logpath=(self.logpath + 'um_2002/'))
        #self.um_array = Micromodem(logpath=(self.logpath + 'um_array/'))
        
    
    def start_log(self):
        # Configure logging
        logformat = logging.Formatter("%(asctime)s\t%(levelname)s\t%(message)s", "%Y-%m-%d %H:%M:%S")
        self.logger = logging.getLogger("glider")
        self.logger.setLevel(logging.DEBUG)
        
        # Create the log directory if it doesn't exist.
        if not os.path.isdir(self.logpath):
            os.makedirs(self.logpath)
        fh = logging.FileHandler(self.logpath + 'glidertx.log')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logformat)
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(logformat)
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)
        
    def run_tx(self, do_10k=False, do_3750=False):
        if do_10k:
            self.setup_10k()
        
        if do_3750:
            self.setup_3750()
            
        while (1):
            if do_10k:
                self.um_3013.set_config('BW0', 2000)
                sleep(1)
                self.um_3013.send_test_packet(127, 1, 3)
                sleep(300)
                self.um_3013.send_test_packet(127, 4, 2)
                sleep(300)
                self.um_3013.set_config('BW0', 1000)
                sleep(1)
                self.um_3013.send_test_packet(127, 1, 2)
                sleep(300)
                self.um_3013.send_test_packet(127, 4, 1)
                sleep(300)
                
            if do_3750:
                self.um_2002.set_config('BW0', 1250)
                sleep(1)
                self.um_2002.send_test_packet(127, 1, 2)
                sleep(300)
                self.um_2002.send_test_packet(127, 4, 1)
                sleep(300)
                self.um_2002.set_config('BW0', 500)
                sleep(1)
                self.um_2002.send_test_packet(127, 1, 1)
                sleep(300)
        
    
    def setup_3750(self):
        self.um_2002.connect(self.um_3750_path, self.um_baud)
        sleep(1)
        self.um_2002.set_config('FC0', 3750)
        self.um_2002.set_config('BW0', 1250)
        self.um_2002.set_config('SRC', 101)
        sleep(1)
        
    def setup_10k(self):
        self.um_3013.connect(self.um_10k_path, self.um_baud)
        sleep(1)
        self.um_3013.set_config('FC0', 10000)
        self.um_3013.set_config('BW0', 2000)
        self.um_3013.set_config('SRC', 10)
        sleep(1)

if __name__ == '__main__':
    glider = GliderTx()
    
    do_10k = False
    do_3750 = False
    
    if '3750' in sys.argv:
        do_3750 = True
    if '10k' in sys.argv:
        do_10k = True    
    
    glider.run_tx(do_10k=do_10k, do_3750=do_3750)