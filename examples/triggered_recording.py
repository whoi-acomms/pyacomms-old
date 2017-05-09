#!/usr/bin/env python
import os

__author__ = 'Eric'

from acomms.unifiedlog import UnifiedLog
from acomms.micromodem import Micromodem
import logging
from time import sleep

from recorder import Recorder

port = '/dev/ttyS5'
baud = 19200
log_location = '/home/eric/data/'
recording_location = '/home/eric/recordings'

# First, connect to get the time
um = Micromodem(name='umodem')
um.connect_serial(port, baud)
um.set_host_clock_from_modem()

sleep(2)

# Now that we have a good time, start a new log with a good timestamp.
unified_log = UnifiedLog(log_path=log_location, console_log_level=logging.INFO)
um.unified_log = unified_log

recorder = Recorder(output_directory=recording_location, unified_log=unified_log)


try:
    while True:
        cst = um.wait_for_cst()
        filename = cst.toa.strftime("%Y%m%dT%H%M%S.%fZ") + '.wav'
        recorder.trigger_recording(filename)

finally:
    um.disconnect()