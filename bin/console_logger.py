#!/usr/bin/env python
#__author__ = 'Andrew'

from acomms import micromodem, unifiedlog
import logging
from time import sleep
import argparse

if __name__ == '__main__':
        ap = argparse.ArgumentParser(description ='Connect to a MM for testing purposes')
        ap.add_argument("logpath", help="Location of Log File", default="/home/acomms/")
        ap.add_argument("-C","--COM", help='COM Port to connect', default="/dev/ttyO1")
        ap.add_argument("-BR","--Baudrate", help="COM Port Baud Rate", default=19200)
        

        args = ap.parse_args()

        unified_log = unifiedlog.UnifiedLog(log_path=args.logpath, console_log_level=logging.INFO)

        um1 = micromodem.Micromodem(name='Micromodem2',unified_log=unified_log)

        um1.connect_serial(args.COM, args.Baudrate)

        try:
            while True:
                sleep(1)
    
        finally:
            um1.disconnect()
