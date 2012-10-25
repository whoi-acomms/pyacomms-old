'''
Created on Feb 8, 2012

@author: Eric
'''

from acomms import Micromodem
from time import sleep
import logging
from threading import Thread
import os
import sys


class VfinBottle(object):
    '''
    classdocs
    '''


    def __init__(self):
        self.logpath = '/var/log/pymodem'
        self.start_log()
        
        self.um_10k_path = '/dev/ttyS0'
        self.um_2750_path = '/dev/ttyS1'
        
        self.um_10k = Micromodem(logpath=(self.logpath + 'um_10k/'))
        self.um_2750 = Micromodem(logpath=(self.logpath + 'um_2750/'))
               

    def setup_2750(self):
        self.um_2750.connect(self.um_2750_path, self.um_baud)
        sleep(1)
        self.um_2750.set_config('FC0', 2750)
        self.um_2750.set_config('BW0', 1250)
        self.um_2750.set_config('SRC', 5)
        self.um_2750.set_config('PAD', 1)
        self.um_2750.set_config('AGN', 0)
        sleep(1)
        
    def setup_10k(self):
        self.um_10k.connect(self.um_10k_path, self.um_baud)
        sleep(1)
        self.um_10k.set_config('FC0', 2750)
        self.um_10k.set_config('BW0', 1250)
        self.um_10k.set_config('SRC', 6)
        self.um_10k.set_config('PAD', 1)
        self.um_10k.set_config('AGN', 0)
        sleep(1)

        
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
    vfin = VfinBottle()
    
    do_10k = False
    do_2750 = False
    
    if '2750' in sys.argv:
        do_2750 = True
        vfin.applog.info("Running TX at 2750Hz")
    if '10k' in sys.argv:
        do_10k = True
        vfin.applog.info("Running TX at 10kHz")
    
    if do_10k:
        vfin.setup_10k()
        vfin.um_10k.set_host_clock_from_modem()
        
    if do_2750:
        vfin.setup_2750()
        vfin.um_2750.set_host_clock_from_modem()
       
    sleep(1)
    
    while(True):
        
        if do_10k:
            vfin.um_10k.set_config('BW0', 2000)
            sleep(1)
            vfin.applog.info("[10kHz] Rate 1, 2kHz BW")
            vfin.um_10k.send_test_packet(127, 1)
            sleep(20)
            vfin.applog.info("[10kHz] Rate 2, 2kHz BW")
            vfin.um_10k.send_test_packet(127, 2)
            sleep(20)
            vfin.applog.info("[10kHz] Rate 4, 2kHz BW")
            vfin.um_10k.send_test_packet(127, 4)
            sleep(20)
            vfin.applog.info("[10kHz] Rate 5, 2kHz BW")
            vfin.um_10k.send_test_packet(127, 5)
            sleep(19)
            
            vfin.um_10k.set_config('BW0', 4000)
            sleep(1)
            vfin.applog.info("[10kHz] Rate 1, 4kHz BW")
            vfin.um_10k.send_test_packet(127, 1)
            sleep(20)
            vfin.applog.info("[10kHz] Rate 2, 4kHz BW")
            vfin.um_10k.send_test_packet(127, 2)
            sleep(20)
            vfin.applog.info("[10kHz] Rate 4, 4kHz BW")
            vfin.um_10k.send_test_packet(127, 4)
            sleep(20)
            vfin.applog.info("[10kHz] Rate 5, 4kHz BW")
            vfin.um_10k.send_test_packet(127, 5)
            sleep(19)
            
        if do_2750:
            vfin.um_2750.set_config('BW0', 500)
            sleep(1)
            vfin.applog.info("[2750Hz] Downsweep, 500Hz BW")
            vfin.um_2750.send_sweep('down')
            sleep(30)
            vfin.applog.info("[2750Hz] Rate 1, 500Hz BW")
            vfin.um_2750.send_test_packet(127, 1, 1)
            sleep(29)
            
            vfin.um_2750.set_config('BW0', 1250)
            sleep(1)
            vfin.applog.info("[2750Hz] Rate 1, 1250Hz BW")
            vfin.um_2750.send_test_packet(127, 1, 1)
            sleep(30)
            vfin.applog.info("[2750Hz] Rate 4, 1250Hz BW")
            vfin.um_2750.send_test_packet(127, 4, 1)
            sleep(29)
            
            
