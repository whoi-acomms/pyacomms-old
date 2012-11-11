'''
Created on Feb 10, 2012

@author: Eric
'''
import logging
from modem import Micromodem, Packet, CycleInfo, Rates, CycleStats
from time import sleep
from threading import Thread
import bitstring


class GliderListen(object):
    def __init__(self):
        self.um2002_path = '/dev/ttyO0'
        self.um3013_path = '/dev/ttyO1'
        
        self.um_baud = 19200
        
        self.syncpath = '/home/acomms/toshore/'
        #self.syncpath = 'c:/temp/glider/'
        
        self.cstlogpath = self.syncpath + 'cst.log'
        
        self.logpath = '/home/acomms/log/glider_listen/'
        #self.logpath = 'c:/temp/glider/'
        self.logger = None
        self.start_log()
        
        self.logger.info("Started gliderlisten")
                
        self.um2002 = Micromodem(name='modem2002', logpath=self.logpath)
        self.um3013 = Micromodem(name='modem3013', logpath=self.logpath)
        
        
    
    def start_log(self):
        if self.logger == None:
            # Configure logging
            logformat = logging.Formatter("%(asctime)s\t%(levelname)s\t%(message)s", "%Y-%m-%d %H:%M:%S")
            self.logger = logging.getLogger("glider_listen")
            self.logger.setLevel(logging.DEBUG)
            fh = logging.FileHandler(self.logpath + 'glider_listen.log')
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(logformat)
            ch = logging.StreamHandler()
            ch.setLevel(logging.DEBUG)
            ch.setFormatter(logformat)
            self.logger.addHandler(fh)
            self.logger.addHandler(ch)
        
        self.logger.info("Started gliderlisten logging")
        
    def start_cst_log(self):
        cst_logformat = logging.Formatter('%(asctime)s\t%(name)s\t%(message)s', "%Y-%m-%d %H:%M:%S")
        
        self.cstlog_2002 = logging.getLogger("cst-2002")
        self.cstlog_2002.setLevel(logging.INFO)
        self.cstlog_3013 = logging.getLogger("cst-3013")
        self.cstlog_3013.setLevel(logging.INFO)
        
        fh = logging.FileHandler(self.cstlogpath)
        fh.setLevel(logging.INFO)
        fh.setFormatter(cst_logformat)
        
        self.cstlog_2002.addHandler(fh)
        self.cstlog_3013.addHandler(fh)
            
    def on_cst_2002(self, cst, msg):
        # Just log the full CST message
        self.cstlog_2002.info(msg['raw'].strip())
    
    def on_cst_3013(self, cst, msg):
        # Just log the full CST message
        self.cstlog_3013.info(msg['raw'].strip())
    
    
    def run_listen(self):
        self.setup_2002()
        self.setup_3013()
                               
        self.um2002.cst_listeners.append(self.on_cst_2002)
        self.um3013.cst_listeners.append(self.on_cst_3013)
        
        while (1):
            # We are event-driven.
            sleep(1)
            
        
    def setup_3013(self):
        self.um3013.connect(self.um3013_path, self.um_baud)
        sleep(1)
        self.um3013.set_config('BND', 0)
        self.um3013.set_config('FC0', 10000)
        self.um3013.set_config('BW0', 2000)
        self.um3013.set_config('PCM', 0)
        self.um3013.set_config('SRC', 10)
        sleep(1)
    
    def setup_2002(self):
        self.um2002.connect(self.um2002_path, self.um_baud)
        sleep(1)
        self.um3013.set_config('BND', 0)
        self.um2002.set_config('FC0', 3750)
        self.um2002.set_config('BW0', 1250)
        self.um2002.set_config('PCM', 0)
        self.um2002.set_config('SRC', 30)
        sleep(1)
        

if __name__ == '__main__':
    glider = GliderListen()
    
    glider.run_listen()