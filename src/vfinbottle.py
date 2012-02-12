'''
Created on Feb 8, 2012

@author: Eric
'''

from modem import Micromodem
from time import sleep
import logging
from threading import Thread
import os


class VfinBottle(object):
    '''
    classdocs
    '''


    def __init__(self):
        self.logpath = '/var/log/pymodem'
        self.serialport = '/dev/ttyS0'

        self.start_log()

        
    def start_log(self):
        logformat = logging.Formatter("%(asctime)s\t%(levelname)s\t%(message)s", "%Y-%m-%d %H:%M:%S")
        self.applog = logging.getLogger("vfinbottle")
        self.applog.setLevel(logging.DEBUG)
        fh = logging.FileHandler(self.logpath + 'vfinbottle.log')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logformat)
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(logformat)
        self.applog.addHandler(fh)
        self.applog.addHandler(ch)
        


if __name__ == '__main__':
    bottle = VfinBottle()
    
    um1 = Micromodem(logpath=(bottle.logpath))
    um1.connect(bottle.serialport, 19200)
    sleep(1)
    

    
    um1.set_config('BND', 0)
    um1.set_config('FC0', 10000)
    um1.set_config('BW0', 2000)
    
    um1.set_host_clock_from_modem()

    
       
    sleep(1)
    
    
    while(1):
        
        testdata = bytearray([0, 1, 2, 3, 4, 5, 6, 7])        
        
        bottle.applog.info("[UM1 001] Ping 76")
        um1.send_ping(76)
        
        sleep(10)
       
        
        bottle.applog.info("[Task 002] Ping 2")
        um1.send_ping(2)
                
        sleep(10)
        
        bottle.applog.info("[Task 003] Send test data")
        #um.send_packet_data(1, testdata)
        um1.send_test_packet(127, 1)
        
        sleep(10)
        
        bottle.applog.info("[Task 003] Send test data")
        um1.send_test_packet(127, 5)
        
        
        sleep(15)
        
        bottle.applog.info("[Task 004] Upsweep")
        um1.send_sweep('up')
        
        sleep(5)
        
        bottle.applog.info("[Task 005] Downsweep")
        um1.send_sweep('down')
        
        sleep(5)
        
        
    