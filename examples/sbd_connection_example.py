__author__ = 'andrew'

from acomms import Micromodem, unifiedlog
import logging
from time import sleep

unified_log = unifiedlog.UnifiedLog(log_path="C:\\Users\\andrew\\acomms_logs", console_log_level=logging.INFO)

modem = Micromodem(name='imei4840', unified_log=unified_log)

modem.connect_sbd_email(IMEI=300125010114840,username='acomms-sbd',
                        pw='3meXDffhJsnm!',
                        check_rate_sec=60, DoD = True)

modem2 = Micromodem(name='imei7830', unified_log=unified_log)

modem2.connect_sbd_email(IMEI=300125010117830,username='acomms-sbd',
                        pw='3meXDffhJsnm!',
                        check_rate_sec=60, DoD = True)


modem2.write_string("$CCPST,1,0,0,0,0,,Test Message")
while True:
    sleep(5)