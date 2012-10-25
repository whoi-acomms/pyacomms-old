'''
Created on Feb 8, 2012

@author: Eric
'''

from acomms import Micromodem
from time import sleep
import logging
from threading import Thread
import os


class DucerTest(object):
    '''
    classdocs
    '''


    def __init__(self):
        self.onboard_ledpath = '/sys/class/leds/whoi:blue:gpio232/brightness'
        self.logpath = '/home/acomms/pymodem/dtlog/'
        self.um3013_serialport = '/dev/ttyO0'
        self.um1810_serialport = '/dev/ttyO1'
        self.um_baud = 19200
        self.tx_interval_secs = 30
        
        # Set up the GPIO for the plug LED
        os.system('echo 229 > /sys/class/gpio/export')
        with open('/sys/class/gpio/gpio229/direction', 'w') as tf:
            tf.write('out')
        self.plug_ledpath = '/sys/class/gpio/gpio229/value'

        
        self.led_thread = Thread( target=self._led_blinker )
        self.led_thread.setDaemon(True)
        
        self.start_log()
        
        self.led_state = 'off'
        
        self.um3013 = Micromodem(logpath=(self.logpath + 'um3013/'))
        self.um1810 = Micromodem(logpath=(self.logpath + 'um1810/'))
        
    def start_log(self):
        logformat = logging.Formatter("%(asctime)s\t%(levelname)s\t%(message)s", "%Y-%m-%d %H:%M:%S")
        self.applog = logging.getLogger("dropbottle")
        self.applog.setLevel(logging.DEBUG)
        fh = logging.FileHandler(self.logpath + 'ducertest.log')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logformat)
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(logformat)
        self.applog.addHandler(fh)
        self.applog.addHandler(ch)
        self.applog.info("Started Transducer Test Logging")
        
    def led_on(self):
        with open(self.onboard_ledpath, 'w') as lf:
            lf.write('1')
        
        with open(self.plug_ledpath, 'w') as lf:
            lf.write('1')
            
        
        self.led_state = 'on'
        
    def led_off(self):
        with open(self.onboard_ledpath, 'w') as lf:
            lf.write('0')
            
        with open(self.plug_ledpath, 'w') as lf:
            lf.write('0')
        
        self.led_state = 'off'
        
    def led_toggle(self):
        if self.led_state == 'off':
            self.led_on()
        else:
            self.led_off()
            
    def _led_blinker(self):
        while(1):
            self.led_toggle()
            sleep(0.5)
    
    def led_start_blinking(self):
        try:
            self.led_thread.start()
        except:
            pass
        
    def setup_1810(self):
        self.um1810.connect(self.um2002_serialport, self.um_baud)
        sleep(1)
        self.um1810.set_config('FC0', 10500)
        self.um1810.set_config('BW0', 4000)
        self.um1810.set_config('SRC', 101)
        self.um1810.set_config('PAD', 1)
        self.um1810.set_config('AGN', 0)
        self.um1810.set_config('FMD', 1)
        self.um1810.set_config('FML', 200)
        sleep(1)
        
    def setup_3013(self):
        self.um3013.connect(self.um3013_serialport, self.um_baud)
        sleep(1)
        self.um3013.set_config('FC0', 10500)
        self.um3013.set_config('BW0', 4000)
        self.um3013.set_config('SRC', 102)
        self.um3013.set_config('PAD', 1)
        self.um3013.set_config('AGN', 0)
        self.um3013.set_config('FMD', 1)
        self.um3013.set_config('FML', 200)
        sleep(1)
        
    def do_3013_tx(self, rate):             
        self.applog.info("[3013] Rate {rate}".format(rate=rate))
        self.um3013.send_test_packet(127, int(rate))
        sleep(self.tx_interval_secs)
        
    def do_1810_tx(self, rate):
        self.applog.info("[AT18-10] Rate {rate}".format(rate=rate))
        self.um1810.send_test_packet(127, int(rate))
        sleep(self.tx_interval_secs)
        
    
        
    def do_standard_test(self):
        while(True):
            for rate in (1,4,5):
                self.do_3013_tx(rate)
                self.do_1018_tx(rate)
                      
            
    
        

if __name__ == '__main__':
    dt = DucerTest()
    
    dt.setup_1810()
    dt.setup_3013()
           
    dt.led_start_blinking()
    
    sleep(30)
    
    dt.do_standard_test()
        
        
    
