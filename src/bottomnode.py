'''
Created on Feb 3, 2012

@author: Eric
'''

from modem import Micromodem
from time import sleep
import logging

# Configure logging
logformat = logging.Formatter("%(asctime)s\t%(levelname)s\t%(message)s", "%Y-%m-%d %H:%M:%S")
logger = logging.getLogger("filexfer")
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('c:/temp/var/log/filexfer.log')
fh.setLevel(logging.DEBUG)
fh.setFormatter(logformat)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(logformat)
logger.addHandler(fh)
logger.addHandler(ch)

if __name__ == '__main__':
    # Connect to the modem
    um = Micromodem()
    um.connect('COM1', 19200)
    
    # Wait for the settings to be read.
    sleep(2)
    
    # Now, send up as many CST data as we can
    