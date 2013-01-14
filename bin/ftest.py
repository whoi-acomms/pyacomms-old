from acomms import Micromodem, CycleStats, Rates, DataFrame, Packet, CycleInfo
from bitstring import BitStream
from time import sleep
import logging

class FTest(object):
    def __init__(self):
        modem_a = Micromodem(name="Modem A", logpath="c:/temp", consolelog='INFO')
        modem_b = Micromodem(name="Modem B", logpath="c:/temp", consolelog='INFO')
        modem_a.connect('COM14', 115200)
        modem_b.connect('COM15', 115200)
        sleep(3)
        
        self.regex_test(modem_b)
        self.downlink_test(modem_a, modem_b)
        self.downlink_test(modem_b, modem_a)
        
    def regex_test(self, modem):
        assert isinstance(modem, Micromodem)
        modem.write_string("$CCCFQ,SRC\r\n")
        msg = modem.wait_for_regex("CACFG,SRC")
        print msg
        
        modem.write_string("$CCCFQ,BND\r\n")
        msg = modem.wait_for_regex("CACLK,", timeout=5)
        
        print msg
    
    def downlink_test(self, tx_modem, rx_modem):
        tx_modem.send_test_packet(rx_modem.id, rate_num=5)
        
        cst = rx_modem.wait_for_cst(timeout=10)
        
        print(cst)
        

ftest = FTest()