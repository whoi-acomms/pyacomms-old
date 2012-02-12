'''
Created on Feb 8, 2012

@author: Eric
'''

from modem import Micromodem
from time import sleep
import logging
from threading import Thread
import os


class DropBottle(object):
    '''
    classdocs
    '''


    def __init__(self):
        self.onboard_ledpath = '/sys/class/leds/whoi:blue:gpio232/brightness'
        self.logpath = '/media/mmcblk0p1/log/'
        self.um1_serialport = '/dev/ttyS0'
        self.um2_serialport = '/dev/ttyS1'
        
        # Set up the GPIO for the plug LED
        os.system('echo 229 > /sys/class/gpio/export')
        with open('/sys/class/gpio/gpio229/direction', 'w') as tf:
            tf.write('out')
        self.plug_ledpath = '/sys/class/gpio/gpio229/value'

        
        self.led_thread = Thread( target=self._led_blinker )
        self.led_thread.setDaemon(True)
        
        self.start_log()
        
        self.led_state = 'off'
        
    def start_log(self):
        logformat = logging.Formatter("%(asctime)s\t%(levelname)s\t%(message)s", "%Y-%m-%d %H:%M:%S")
        self.applog = logging.getLogger("dropbottle")
        self.applog.setLevel(logging.DEBUG)
        fh = logging.FileHandler(self.logpath + 'dropbottle.log')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logformat)
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(logformat)
        self.applog.addHandler(fh)
        self.applog.addHandler(ch)
        
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

if __name__ == '__main__':
    dbtl = DropBottle()
    
    um1 = Micromodem(logpath=(dbtl.logpath + 'um1/'))
    um1.connect(dbtl.um1_serialport, 19200)
    sleep(1)
    
    um2 = Micromodem(logpath=(dbtl.logpath + 'um2/'))
    um2.connect(dbtl.um2_serialport, 19200)
    sleep(1)
    
    um1.set_config('BND', 0)
    um1.set_config('FC0', 10000)
    um1.set_config('BW0', 2000)
    
    um2.set_config('BND', 0)
    um2.set_config('FC0', 3750)
    um2.set_config('BW0', 1000)
    
    um1.set_host_clock_from_modem()
    
       
    sleep(1)
    
    dbtl.led_start_blinking()
    
    '''
    while(1):
        dbtl.led_toggle()
        testdata = bytearray([0, 1, 2, 3, 4, 5, 6, 7]) 
        
        dbtl.applog.info("[Task 001] Send test data")
        um.send_packet_data(1, testdata)
        
        sleep(10)
    ''' 
    
    while(1):
        dbtl.led_toggle()
        
        testdata = bytearray([0, 1, 2, 3, 4, 5, 6, 7])        
        
        dbtl.applog.info("[UM1 001] Ping 76")
        um1.send_ping(76)
        
        sleep(10)
        
        dbtl.applog.info("[UM2 001] Ping 76")
        um2.send_ping(76)
        
        sleep(10)
        
        dbtl.applog.info("[Task 002] Ping 2")
        um1.send_ping(2)
                
        sleep(10)
        
        dbtl.applog.info("[Task 003] Send test data")
        #um.send_packet_data(1, testdata)
        um1.send_test_packet(127, 1)
        
        sleep(10)
        
        dbtl.applog.info("[Task 003] Send test data")
        um1.send_test_packet(127, 5)
        
        
        sleep(15)
        
        dbtl.applog.info("[Task 004] Upsweep")
        um1.send_sweep('up')
        
        sleep(5)
        
        dbtl.applog.info("[Task 005] Downsweep")
        um1.send_sweep('down')
        
        sleep(5)
        
        
    