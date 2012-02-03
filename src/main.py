'''
Created on Feb 1, 2012

@author: Eric
'''

from modem import Micromodem
from time import sleep

if __name__ == '__main__':
    um = Micromodem()
    um.connect('COM1', 19200)
    
    testdata = bytearray([0, 1, 2, 3, 4, 5, 6, 7])
    
    sleep(1)
    
    um.send_ping(76)
    
    sleep(10)
    
    um.send_ping(2)
    
    sleep(10)
    
    um.send_packet_data(1, testdata)
    
    while(1):
        sleep(.1)

