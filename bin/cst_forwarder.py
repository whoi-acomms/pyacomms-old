__author__ = 'Eric Gallimore'


from acomms import micromodem, unifiedlog
import logging
from time import sleep
import argparse

if __name__ == '__main__':
        ap = argparse.ArgumentParser(description ='Forward some CST data from one modem acoustically using another modem')
        ap.add_argument("logpath", help="Location of Log File", default="/home/acomms/")
        ap.add_argument("-cs","--cstserial", help='CST modem serial port', default="/dev/ttyO1")
        ap.add_argument("-cb","--cstbaud", help="CST modem Baud Rate", default=19200)
        ap.add_argument("-ts","--txserial", help='TX modem serial port', default="/dev/ttyO2")
        ap.add_argument("-tb","--txbaud", help="TX modem baud rate", default=19200)
        ap.add_argument("-d","--dest", help="Destination modem address", default=1)


        args = ap.parse_args()

        unified_log = unifiedlog.UnifiedLog(log_path=args.logpath, console_log_level=logging.INFO)

        cst_modem = micromodem.Micromodem(name='CST_modem',unified_log=unified_log)
        tx_modem = micromodem.Micromodem(name="TX_modem", unified_log=unified_log)

        cst_modem.connect_serial(args.cstserial, args.cstbaud)
        tx_modem.connect_serial(args.txserial, args.txbaud)

        try:
            while True:
                new_cst = cst_modem.wait_for_cst()

                tx_modem.send_packet_data(args.dest, bytes(new_cst.snr_in));

        finally:
            cst_modem.disconnect()
            tx_modem.disconnect()