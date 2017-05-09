import argparse
import logging
from serial import Serial
from acomms import Message, nmeaChecksum, Micromodem
from acomms import UnifiedLog
from Queue import Queue, Empty, Full
from time import sleep
from threading import Thread


class IridiumCsdListener(object):
    def __init__(self, port, baudrate=9600, timeout=0.1, unified_log=None):
        self._incoming_line_buffer = ""

        self.connection_type = "iridium_csd_listener"

        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout

        if unified_log is None:
            unified_log = UnifiedLog(log_path='.')
        self._daemon_log = unified_log.getLogger("iridium_csd_listener")
        self._nmea_in_log = unified_log.getLogger("nmea.from.iridium_csd")
        self._nmea_out_log = unified_log.getLogger("nmea.to.iridium_csd")
        self._daemon_log.setLevel(logging.INFO)
        self._nmea_in_log.setLevel(logging.INFO)
        self._nmea_out_log.setLevel(logging.INFO)

        self._serialport = Serial(port, baudrate, timeout=self.timeout)
        self.serial_tx_queue = Queue()

        self.nmea_listeners = []

        self.iridium_buffer_length = 20

        self._last_connected_status = self.is_connected

        self._thread = Thread(target=self._listen)
        self._thread.setDaemon(True)
        self._thread.start()

        self._daemon_log.info("Iridium Listener Started")
        self.iridium_init()


    @property
    def is_connected(self):
        connected = self._serialport.getCD() and self._serialport.isOpen()
        return connected

    @property
    def can_change_baudrate(self):
        return True

    def change_baudrate(self,baudrate):
        self.baudrate = baudrate
        self._serialport.baudrate = baudrate
        return baudrate

    def iridium_init(self):
        sleep(1)
        self._serialport.setDTR(False)
        self._daemon_log.info("Clear DTR")
        sleep(0.1)
        self._serialport.setDTR(True)
        self._daemon_log.info("Set DTR")
        sleep(0.1)
        self._serialport.write("AT+CREG?\r\n")
        self._daemon_log.info("> AT+CREG?")
        sleep(1)
        self._serialport.write("AT+CEER\r\n")
        self._daemon_log.info("> AT+CEER")
        sleep(1)
        self._serialport.write("AT+CSQ?\r\n")
        self._daemon_log.info("> AT+CSQ?")
        sleep(5)

    def close(self):
        self._serialport.setDTR(False)
        sleep(0.2)
        self._serialport.close()

    def _listen(self):
        while True:
            # Log connection changes
            if self.is_connected is not self._last_connected_status:
                self._daemon_log.info("Iridium Connected: {}".format(self.is_connected))
                self._last_connected_status = self.is_connected

            if self._serialport.isOpen():
                msg = self.readline()
                if msg is None:
                    msg = ""

                # Figure out if this is an NMEA message or Iridium traffic, in the dumbest way possible.
                if len(msg) > 0:
                    if msg[0] == '$':
                        self._process_incoming_nmea(msg)
                    else:
                        self.process_iridium(msg)

                self._process_outgoing_nmea()

            else:  # not connected
                sleep(0.5)  # Wait half a second, try again.

    def process_iridium(self, msg):
        # This is called by the primary serial processing loop.
        # It will be called whenever we have a line of data, or periodically (based on a timeout)

        # Basically, all we do here is pick up the phone.
        if "RING" in msg:
            self._serialport.write("ATA\r\n")
            self._daemon_log.info("> ATA")

        # and log messages
        if msg is not "":
            self._daemon_log.info("< {}".format(msg.strip()))

    def _process_incoming_nmea(self, msg):
        self._nmea_in_log.info(msg.rstrip('\r\n'))

        msg = Message(msg)

        try:
            for func in self.nmea_listeners:
                func(msg)  # Pass the message to any custom listeners.
        except Exception as e:
            self._daemon_log.warn("Error in NMEA listener: ")
            self._daemon_log.warn(repr(e))

    def _process_outgoing_nmea(self):
        # Now, transmit anything we have in the outgoing queue.
        if self.is_connected:
            try:
                txstring = self.serial_tx_queue.get_nowait()
                self._serialport.write(txstring)
                self._nmea_out_log.info(txstring.rstrip('\r\n'))
            #If the queue is empty, then pass, otherwise log error
            except Empty:
                pass
            except:
                self._daemon_log.exception("NMEA Output Error")
        else:
            # If we aren't connected, remove old messages from the queue.
            overflow = self.serial_tx_queue.qsize() - self.iridium_buffer_length
            if overflow > 0:
                for i in range(overflow):
                    txstring = self.serial_tx_queue.get_nowait()
                    self._daemon_log.info("Dropped outgoing NMEA: {}".format(txstring.rstrip('\r\n')))



    def write_nmea(self, msg):
        """Call with the message to send, as an NMEA message.  Correct checksum will be computed."""

        if type(msg) == str:
            # Automagically convert it into an NMEA message (or try, at least)
            msg = Message(msg)

        message = ",".join([str(p) for p in [msg['type']] + msg['params']])
        chk = nmeaChecksum(message)
        message = "$" + message.lstrip('$').rstrip('\r\n*') + "*" + chk + "\r\n"

        # Queue this message for transmit in the serial thread
        self._daemon_log.debug("Writing NMEA to output queue: %s" % (message.rstrip('\r\n')))
        try:
            self.serial_tx_queue.put(message, block=False)
        # If queue full, then ignore
        except Full:
            self._daemon_log.debug("write_nmea: Serial TX Queue Full")

    def write_string(self, string):
        self._daemon_log.debug("Writing string to output queue: %s" % (string.rstrip('\r\n')))
        try:
            self.serial_tx_queue.put(string, block=False)
        # If queue full, then ignore
        except Full:
            self._daemon_log.debug("write_string: Serial TX Queue Full")

    def readline(self):
        """Returns a \n terminated line from the modem.  Only returns complete lines (or None on timeout)"""
        rl = self._serialport.readline()

        if rl == "":
            return None

        # Make sure we got a complete line.  Serial.readline may return data on timeout.
        if rl[-1] != '\n':
            self._incoming_line_buffer += rl
            return None
        else:
            if self._incoming_line_buffer != "":
                rl = self._incoming_line_buffer + rl
            self._incoming_line_buffer = ""
            return rl

    def write(self, data):
        self._serialport.write(data)




def start_bridge(modem_serial_port, modem_baud, iridium_serial_port, iridium_baud):
    unified_log = UnifiedLog(console_log_level=logging.INFO)

    modem = Micromodem(unified_log=unified_log)
    modem.connect_serial(modem_serial_port, modem_baud)

    iridium_csd_listener = IridiumCsdListener(iridium_serial_port, iridium_baud, unified_log=unified_log)

    # connect them
    # modem -> iridium
    modem.nmea_listeners.append(iridium_csd_listener.write_nmea)
    # iridium -> modem
    iridium_csd_listener.nmea_listeners.append(modem.write_nmea)

    try:
        while True:
            sleep(1)
    finally:
        iridium_csd_listener.close()
        modem.disconnect()


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Connect incoming Iridium calls to a modem.')
    #ap.add_argument("-l", "--logfile", help="Save log with specified name")
    ap.add_argument("iridium_serial_port", help="Iridium modem serial port")
    ap.add_argument("iridium_baud", help="Iridium modem baud rate", type=int)
    ap.add_argument("modem_serial_port", help="Micromodem serial port")
    ap.add_argument("modem_baud", help="Micromodem serial baud rate", type=int)

    args = ap.parse_args()

    start_bridge(**vars(args))
