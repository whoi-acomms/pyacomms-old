'''
Created on Feb 8, 2012

@author: Eric
'''

from acomms import Micromodem
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
        self.logpath = '/home/acomms/pymodem/log/'
        self.um3013_serialport = '/dev/ttyO0'
        self.um2002_serialport = '/dev/ttyO1'
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
        self.um2002 = Micromodem(logpath=(self.logpath + 'um2002/'))
        
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
        
    def setup_2002(self):
        self.um2002.connect(self.um2002_serialport, self.um_baud)
        sleep(1)
        self.um2002.set_config('FC0', 3750)
        self.um2002.set_config('BW0', 1250)
        self.um2002.set_config('SRC', 5)
        self.um2002.set_config('PAD', 1)
        self.um2002.set_config('AGN', 0)
        self.um2002.set_config('FMD', 1)
        self.um2002.set_config('FML', 200)
        sleep(1)
        
    def setup_3013(self):
        self.um3013.connect(self.um3013_serialport, self.um_baud)
        sleep(1)
        self.um3013.set_config('FC0', 10000)
        self.um3013.set_config('BW0', 2000)
        self.um3013.set_config('SRC', 6)
        self.um3013.set_config('PAD', 1)
        self.um3013.set_config('AGN', 0)
        self.um3013.set_config('FMD', 1)
        self.um3013.set_config('FML', 200)
        sleep(1)
        
    def do_3013_tx(self, bandwidth):
        self.um3013.set_config('BW0', bandwidth)
        sleep(1)
        self.applog.info("[3013] Rate 1, {bw}Hz BW".format(bw=bandwidth))
        self.um3013.send_test_packet(127, 1)
        sleep(self.tx_interval_secs)
        self.applog.info("[3013] Rate 4, {bw}Hz BW".format(bw=bandwidth))
        self.um3013.send_test_packet(127, 4)
        sleep(self.tx_interval_secs)
        self.applog.info("[3013] Rate 5, {bw}Hz BW".format(bw=bandwidth))
        self.um3013.send_test_packet(127, 5)
        sleep(self.tx_interval_secs - 1)
        
        
    def do_2002_tx(self, bandwidth):
        
        if bandwidth not in (300, 500, 1250):
            self.applog.warn("Invalid 2002 Bandwidth: {bw}".format(bw=bandwidth))
        
        self.um2002.set_config('BW0', bandwidth)
        self.um2002.set_config('FMD', 0)
        sleep(1)
        self.applog.info("[2002] Upsweep, {bw}Hz BW".format(bw=bandwidth))
        self.um2002.send_sweep('psk')
        sleep(self.tx_interval_secs - 1)
        
        self.um2002.set_config('FMD', 1)
        sleep(1)
        self.applog.info("[2002] Rate 1, {bw}Hz BW, 1 Frame".format(bw=bandwidth))
        self.um2002.send_test_packet(127, 1, 1)
        sleep(self.tx_interval_secs)
        self.applog.info("[2002] Rate 4, {bw}Hz BW, 1 Frame".format(bw=bandwidth))
        self.um2002.send_test_packet(127, 4, 1)
        sleep(self.tx_interval_secs)
        self.applog.info("[2002] Rate 5, {bw}Hz BW, 1 Frame".format(bw=bandwidth))
        self.um2002.send_test_packet(127, 5, 1)
        sleep(self.tx_interval_secs - 1)
    
    def do_standard_test(self):
        while(True):
            self.do_2002_tx(300)
            self.do_2002_tx(500)
            self.do_2002_tx(1250)
            
            self.do_3013_tx(2000)
            self.do_3013_tx(4000)
            
            
    
        

if __name__ == '__main__':
    dbtl = DropBottle()
    
    dbtl.setup_2002()
    dbtl.setup_3013()
    
    #dbtl.um3013.set_host_clock_from_modem()
           
    sleep(1)
    
    dbtl.led_start_blinking()
    
    dbtl.do_standard_test()
        
        
    
