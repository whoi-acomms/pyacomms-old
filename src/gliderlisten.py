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


class GliderListen(object):
    def __init__(self):
        self.um_10_path = '/dev/ttyS1'
        
        self.um_2750_path = '/dev/ttyS0'
        self.um_array_path = '/dev/ttyE0'
        
        self.um_baud = 19200
        
        self.syncpath = '/media/card/sync/'
        self.syncpath = 'c:/temp/glider/'
        
        self.cstlogpath = self.syncpath + 'sourcedrop_cst.log'
        
        self.logpath = '/var/log/glider_sourcedrop/'
        #self.logpath = 'c:/temp/glider/'
        self.start_log()
                
        self.um_10k = Micromodem(name='modem-10k', logpath=self.logpath)
        self.um_2750 = Micromodem(name='modem-2750', logpath=self.logpath)
        self.um_array = Micromodem(name='modem-array', logpath=self.logpath)
        
    
    def start_log(self):
        # Configure logging
        logformat = logging.Formatter("%(asctime)s\t%(levelname)s\t%(message)s", "%Y-%m-%d %H:%M:%S")
        self.logger = logging.getLogger("glider_sourcedrop")
        self.logger.setLevel(logging.DEBUG)
        fh = logging.FileHandler(self.logpath + 'glider_sourcedrop.log')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logformat)
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(logformat)
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)
        
    def start_cst_log(self):
        cst_logformat = logging.Formatter('%(asctime)s\t%(name)s\t%(message)s', "%Y-%m-%d %H:%M:%S")
        
        self.cstlog_10k = logging.getLogger("cst-10k")
        self.cstlog_10k.setLevel(logging.INFO)
        self.cstlog_2750 = logging.getLogger("cst-2750")
        self.cstlog_2750.setLevel(logging.INFO)
        self.cstlog_array = logging.getLogger("cst-array")
        self.cstlog_array.setLevel(logging.INFO)
        
        fh = logging.FileHandler(self.cstlogpath)
        fh.setLevel(logging.INFO)
        fh.setFormatter(cst_logformat)
        
        self.cstlog_10k.addHandler(fh)
        self.cstlog_2750.addHandler(fh)
        self.cstlog_array.addHandler(fh)
    
    def on_cst_10k(self, cst, msg):
        # Just log the full CST message
        self.cstlog_10k.info(msg['raw'].strip())
    
    def on_cst_2750(self, cst, msg):
        # Just log the full CST message
        self.cstlog_2750.info(msg['raw'].strip())
    
    def on_cst_array(self, cst, msg):
        self.cstlog_array.info(msg['raw'].strip())
        
        
    def run_listen(self):
        self.setup_10k()
        self.setup_2750()
        self.setup_array()
        
        self.um_10k.cst_listeners.append(self.on_cst_10k)
        self.um_2750.cst_listeners.append(self.on_cst_2750)
        self.um_array.cst_listeners.append(self.on_cst_array)
        
        while (1):
            # We are event-driven.
            sleep(1)
            
        
    def setup_10k(self):
        self.um_10k.connect(self.um_10k_path, self.um_baud)
        sleep(1)
        self.um_10k.set_config('FC0', 10000)
        self.um_10k.set_config('BW0', 2000)
        self.um_10k.set_config('SRC', 10)
        sleep(1)
    
    def setup_2750(self):
        self.um_2750.connect(self.um_2750_path, self.um_baud)
        sleep(1)
        self.um_2750.set_config('FC0', 2750)
        self.um_2750.set_config('BW0', 1250)
        self.um_2750.set_config('SRC', 101)
        sleep(1)
        
    def setup_array(self):
        self.um_array.connect(self.um_array_path, self.um_baud)
        sleep(1)
        self.um_10k.set_config('FC0', 2750)
        self.um_10k.set_config('BW0', 1250)
        self.um_10k.set_config('SRC', 102)
        sleep(1)

if __name__ == '__main__':
    glider = GliderListen()
    
    glider.run_listen()