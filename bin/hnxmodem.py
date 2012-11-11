'''
Created on Feb 10, 2012

@author: Eric
'''
import logging
from acomms import Micromodem, CycleStats
from time import sleep
from threading import Thread
import bitstring
import sys
import os


class HnxModem(object):
    def __init__(self):
        self.command_file_path = '/home/acomms/sync/fromshore/mode'
        self.syncpath = '/home/acomms/toshore/'
        self.cstlogpath = self.syncpath + 'cst.log'        
        
        self.um_10_path = '/dev/ttyO0'        
        self.um_baud = 19200
        
        self.logpath = '/home/acomms/log/hnxmodem/'
        self.start_log()
        self.start_cst_log()        
                
        self.setup_3013()
        
    
    def start_log(self):
        # Configure logging
        logformat = logging.Formatter("%(asctime)s\t%(levelname)s\t%(message)s", "%Y-%m-%d %H:%M:%S")
        self.logger = logging.getLogger("glider")
        self.logger.setLevel(logging.DEBUG)
        
        # Create the log directory if it doesn't exist.
        if not os.path.isdir(self.logpath):
            os.makedirs(self.logpath)
        fh = logging.FileHandler(self.logpath + 'hnxmodem.log')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logformat)
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(logformat)
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)
        
    def start_cst_log(self):
        cst_logformat = logging.Formatter('%(asctime)s\t%(name)s\t%(message)s', "%Y-%m-%d %H:%M:%S")
        
        self.cstlog_3013 = logging.getLogger("cst-3013")
        self.cstlog_3013.setLevel(logging.INFO)
        
        fh = logging.FileHandler(self.cstlogpath)
        fh.setLevel(logging.INFO)
        fh.setFormatter(cst_logformat)
        
        self.cstlog_3013.addHandler(fh)
        
    def on_cst_3013(self, cst, msg):
        # Just log the full CST message
        self.cstlog_3013.info(msg['raw'].strip())
    
    
    def run_loop(self):
        
        while (True):
            # At the beginning of each run through the loop, check to see if we have new instructions          
            # Logging CSTs and modem messages is event-driven, so it is always running after setup.
            commands = self.read_commands()
            
            if 'ping' in commands:
                self.run_ping()
                
            if 'downlink' in commands:
                self.run_downlink()
            
            if 'uplink' in commands:
                self.run_uplink()
                
            
            sleep(1)  
    
    def read_commands(self):
        commands = []
        with open(self.command_file_path, 'r') as cmdfile:
            commandstr = str(cmdfile.read())
            commands = commandstr.lower().split()
                    
        return commands
    
    def run_downlink(self):
        self.downlink_interval_secs = 60
        
        self.um3013.send_test_packet(127, 1)
        sleep(self.downlink_interval_secs)
        self.um3013.send_test_packet(127, 2)
        sleep(self.downlink_interval_secs)
        self.um3013.send_test_packet(127, 4)
        sleep(self.downlink_interval_secs)
        self.um3013.send_test_packet(127, 5)
        sleep(self.downlink_interval_secs)
        
    def run_ping(self):
        self.ping_interval_secs = 30
        
        self.um3013.send_ping(10)
        sleep(self.ping_interval_secs)
        
    def run_uplink(self):
        self.uplink_interval_secs = 60
        
        self.um3013.send_uplink_request(src_id = 10, rate_num = 1)
        sleep(self.uplink_interval_secs)

        
    def setup_3013(self):
        self.um3013 = Micromodem(name='um3013', logpath=os.path.join(self.logpath, 'um3013/'))
        sleep(1)
        self.um3013.set_config('BND', 0)
        self.um3013.set_config('FC0', 10000)
        self.um3013.set_config('BW0', 2000)
        self.um3013.set_config('SRC', 21)
        self.um3013.set_config('PCM', 0)
        sleep(1)
        self.um3013.cst_listeners.append(self.on_cst_3013) 
        

if __name__ == '__main__':
    hnxmodem = HnxModem()
    
    hnxmodem.run_loop()