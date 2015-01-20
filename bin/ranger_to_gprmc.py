__author__ = 'Eric'
import argparse
from acomms.modem_connections import UdpConnection
from acomms import micromodem, unifiedlog
from acomms import ccl
from acomms.timeutil import to_utc_iso8601
import datetime
import serial
import sys
import traceback
import logging
from time import sleep


class RangerToGprmc(object):
    def __init__(self):
        self.output_serial = None
        self.display_forward = False
        self.console_log = False

    def connect_modem(self, serial_port, baud_rate):
        if self.console_log:
            unified_log = unifiedlog.UnifiedLog(console_log_level=logging.INFO)
        else:
            unified_log = unifiedlog.UnifiedLog(console_log_level=None)

        self.modem = micromodem.Micromodem(name='Micromodem2', unified_log=unified_log)

        self.ccl_decoder = ccl.CclDecoder(self.modem)
        self.ccl_decoder.ccl_listeners.append(self.got_new_message)
        #self.um.connect_serial(serial_port, baud_rate)
        self.modem.connection = UdpConnection(self.modem, 'localhost', 2101, local_port=2102)
        #self.modem.write_string("$CCCFQ,SRC\r\n")

    def connect_output(self, serial_port, baud_rate):
        self.output_serial = serial.Serial(serial_port, baud_rate)

    def got_new_message(self, mdat_ranger):

        try:
            time_string = to_utc_iso8601(datetime.datetime.utcnow())

            display_message = "{}\t{}\t{}\t{}m\r\n".format(time_string, mdat_ranger['latitude'],
                                                           mdat_ranger['longitude'], mdat_ranger['depth'])

            #forward_message = "{},{},{},{}\r\n".format(time_string, mdat_ranger['latitude'], mdat_ranger['longitude'], mdat_ranger['depth'])

            current_time = datetime.datetime.utcnow()
            gps_time = current_time.strftime('%H%M%S')
            gps_date = current_time.strftime('%d%m%y')

            forward_message = "$GPRMC,{gps_time},A,{lat_deg}{lat_decmin},{lat_dir},{lon_deg}{lon_decmin},{lon_dir},{speed_kt},{heading},{gps_date},000.0,W\r\n".format(
                gps_time=gps_time,
                gps_date=gps_date,
                **mdat_ranger
            )

            if self.display_forward:
                print(forward_message)
            else:
                print(display_message)

            if self.output_serial:
                self.output_serial.write(forward_message)


        except Exception, e:
            self.modem._daemon_log.error("Exception when processing: " + str(sys.exc_info()[0]))
            traceback.print_exc()


if __name__ == '__main__':
    ap = argparse.ArgumentParser(
        description='Decode CCL messages received by a modem and generate fake GPRMC messages to send out a serial port')
    #ap.add_argument("-l", "--logfile", help="Save log with specified name")
    ap.add_argument("-f", "--display-forward", action='store_true',
                    help="Print the forwarded output to console rather than human-readable")
    ap.add_argument("-v", "--verbose", action='store_true', help="Show all modem traffic")
    ap.add_argument("modem_serial_port", help="Modem serial port")
    ap.add_argument("modem_baud", help="Modem baud rate")
    ap.add_argument("output_serial_port", help="Output serial port")
    ap.add_argument("output_baud", help="Output baud rate")

    args = ap.parse_args()

    cclforward = RangerToGprmc()

    if args.display_forward:
        cclforward.display_forward = True

    if args.verbose:
        cclforward.console_log = True

    cclforward.connect_output(args.output_serial_port, args.output_baud)

    cclforward.connect_modem(args.modem_serial_port, args.modem_baud)

    while True:
        sleep(1)




