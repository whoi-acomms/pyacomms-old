#!/usr/bin/env python
import os
from time import sleep, time
from datetime import datetime, date
import timeutil
import re
from Queue import Empty, Full
from Queue import Queue
import logging
import struct
import timer2
from collections import namedtuple
from bitstring import BitArray
import hashlib
from binascii import hexlify
from serial import Serial

import commstate
from messageparser import MessageParser
from messageparams import Packet, CycleInfo, hexstring_from_data, Rates, DataFrame,FDPRates
from acomms.modem_connections import SerialConnection
from acomms.modem_connections import IridiumConnection
from acomms.modem_connections import SBDEmailConnection
from unifiedlog import UnifiedLog


# Convert a string to a byte listing
toBytes   = lambda inpStr: map(ord,inpStr)
# Convert a list to a hex string (each byte == 2 hex chars)
toHexStr  = lambda inpLst: "".join(["%02X" % x for x in inpLst])
# Calculate hex-encoded, XOR checksum for input string per NMEA 0183.
nmeaChecksum = lambda inpStr: toHexStr([reduce(lambda x,y: x^y, toBytes(inpStr))])
# Convert boolean to C / CCL / Modem representation (0,1)
bool2int = lambda inbool: inbool and 1 or 0


class ChecksumException(Exception):
    pass

class UnavailableInApiLevelError(Exception):
    pass


class ModemResponseTimeout(Exception):
    pass


class ModemResponseError(Exception):
    pass


class Micromodem(object):
    def __init__(self, name='modem', unified_log=None, log_path=None, log_level='INFO'):

        name = str(name)
        # Strip non-alphanumeric characters from name
        self.name = ''.join([ch for ch in name if ch.isalnum()])

        self.connection = None

        self.nmea_listeners = []

        self.parser = MessageParser(self)
        self.state = commstate.Idle(modem=self)
        self.state_timer = timer2.Timer()
        
        self.rxframe_listeners = []
        self.cst_listeners = []
        self.xst_listeners = []
        self.ack_listeners = []

        self.incoming_dataframe_queues = []
        self.incoming_cst_queues = []
        self.incoming_xst_queues = []
        self.incoming_msg_queues = []

        self._api_level = 1
        self.default_nmea_timeout = 1

        self.id = -1
        self.asd = False
        self.pcm_on = False
        
        # state tracking variables
        self.current_rx_frame_num = 1
        self.current_tx_frame_num = 1
        self.current_cycleinfo = None
        self.current_txpacket = None
        self.current_rxpacket = None
        self.set_host_clock_flag = False
        
        self.serial_tx_queue = Queue()

        self.get_uplink_data_function = None

        # Set up logging
        if unified_log is None:
            unified_log = UnifiedLog(log_path=log_path)
        self._daemon_log = unified_log.getLogger("daemon.{0}".format(self.name))
        self._daemon_log.setLevel(log_level)
        self._nmea_in_log = unified_log.getLogger("nmea.from.{0}".format(self.name))
        self._nmea_in_log.setLevel(logging.INFO)
        self._nmea_out_log = unified_log.getLogger("nmea.to.{0}".format(self.name))
        self._nmea_out_log.setLevel(logging.INFO)
        self.unified_log = unified_log
        self.config_data = {}



    @property
    def api_level(self):
        return self._api_level

    def force_api_level(self, api_level):
        self._api_level = api_level

    def connect(self, serialport=None, baudrate=19200):
        ''' Convenience function to establish a connection using a serial port.  Included for backward-compatibility.
        '''
        self.connect_serial(serialport, baudrate)

    def connect_serial(self, port, baudrate=19200):
        self.connection = SerialConnection(self, port, baudrate)
        self._daemon_log.info("Connected to {0} ({1} bps)".format(port, baudrate))
        sleep(0.05)
        self.get_config('SRC')
        #self.query_modem_info()
        #self.query_nmea_api_level()

    def connect_iridium(self, number, port, baudrate=19200):
        self.connection = IridiumConnection(modem = self, port=port, baudrate=baudrate,number=number)
        self._daemon_log.info("Connected to Iridium #:{0} on Serial {1}({2} bps)".format(number,port, baudrate))

    def connect_sbd_email(self, IMEI, email_account='acomms-sbd@whoi.edu',
                 username = None,pw = None,
                 check_rate_sec = 30,
                 imap_srv = "imap.whoi.edu", imap_port = 143,
                 smtp_svr = "outbox.whoi.edu", smtp_port = 25, DoD = False):
        self.connection = SBDEmailConnection(modem=self,
                                             IMEI=IMEI,
                                             email_account=email_account,
                                             username=username, pw=pw,
                                             check_rate_min=check_rate_sec / 60,
                                             imap_srv = imap_srv,imap_port=imap_port,
                                             smtp_svr=smtp_svr, smtp_port=smtp_port,
                                             DoD=DoD)
        self._daemon_log.info("Using Email Based SBD Connection (IMEI#: {0} Address: {1} IMAP Server: {2}:{3} SMTP Server: {4}:{5} Checking Every {6} Minutes)".format(
            IMEI, email_account,imap_srv,imap_port,smtp_svr,smtp_port, check_rate_sec / 60))

    def disconnect(self):
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def query_modem_info(self):
        sleep(0.05)
        self.get_config_param("SRC")
        sleep(0.05)
        # All of the salient properties on this object are populated automatically by the NMEA config handler.

    def query_nmea_api_level(self):
        api_level = 0

        msg = {'type': "CCALQ", 'params': [0]}
        self.write_nmea(msg)

        response = self.wait_for_nmea_type('CAALQ', timeout=5)

        if response:
            if response['type'] == 'CAALQ':
                api_level = int(response['params'][1])
            else:
                api_level = 0
        else:
            api_level = 0

        self._api_level = api_level
        return api_level

    def set_nmea_api_level(self,api_level=11):

        self._api_level = api_level
        return api_level


    def start_nmea_logger(self, nmea_log_format, log_path=None, file_name=None):
        """ This starts an additional log file that only logs NMEA messages, primarily for compatibility with other
            systems.
        """
        nmea_log_format = nmea_log_format.lower()
        if nmea_log_format == "modemtma":
            logformat = logging.Formatter("%(asctime)sZ,RX,%(message)s", "%Y-%m-%d %H:%M:%S")
        elif nmea_log_format == "messagesonly":
            logformat = logging.Formatter("%(message)s")
        elif nmea_log_format == "timestamped":
            logformat = logging.Formatter("%(asctime)s\t%(message)s", "%Y-%m-%dT%H:%M:%SZ")
        else:
            raise(ValueError("Unrecognized nmea_log_format"))

        # If no log path is specified, use (or create) a directory in the user's home directory
        if log_path is None:
            log_path = os.path.expanduser('~/acomms_logs')
        log_path = os.path.normpath(log_path)

        # Create the directory if it doesn't exist
        if not os.path.isdir(log_path):
            os.makedirs(log_path)

        if file_name is None:
            now = datetime.utcnow()
            file_name = "nmea_{0}_{1}.log".format(self.name, now.strftime("%Y%m%dT%H%M%SZ"))

        log_file_path = os.path.join(log_path, file_name)

        handler = logging.FileHandler(log_file_path)
        handler.setLevel(logging.INFO)

        self._nmea_in_log.addHandler(handler)

        self._daemon_log.debug("Started new NMEA log")

    def _process_outgoing_nmea(self):
        # Now, transmit anything we have in the outgoing queue.
        try:
            txstring = self.serial_tx_queue.get_nowait()
            self.connection.write(txstring)
            self._nmea_out_log.info(txstring.rstrip('\r\n'))
        #If the queue is empty, then pass, otherwise log error
        except Empty:
            pass
        except:
            self._daemon_log.exception("NMEA Output Error")
                
    def _process_incoming_nmea(self, msg):
        if msg is not None:
            try:
                #self.nmealog.info("< " + msg.rstrip('\r\n'))
                self._nmea_in_log.info(msg.rstrip('\r\n'))

                msg = Message(msg)
                
                self.parser.parse(msg)

                try:
                    for func in self.nmea_listeners:
                        func(msg)  # Pass the message to any custom listeners.
                except Exception, e:
                    self._daemon_log.warn("Error in custom listener: ")
                    self._daemon_log.warn(repr(e))
                
                # Append this message to all listening queues
                for q in self.incoming_msg_queues:
                    try:
                        q.put_nowait(msg)
                    except:
                        self._daemon_log.warn("Error appending to incoming message queue")
            except ChecksumException:
                self._daemon_log.warn("NMEA Checksum Error: %s" % (msg.rstrip('\r\n')))
            except:
                self._daemon_log.warn("NMEA Input Error")


    def _message_waiting(self):
        return not self.serial_tx_queue.empty()

    def close_loggers(self):
        for hdlr in self._daemon_log.handlers:
            hdlr.flush()
            hdlr.close()
            self._daemon_log.removeHandler(hdlr)
        
        for hdlr in self._nmea_in_log.handlers:
            hdlr.flush()
            hdlr.close()
            self._nmea_in_log.removeHandler(hdlr)

        for hdlr in self._nmea_out_log.handlers:
            hdlr.flush()
            hdlr.close()
            self._nmea_out_log.removeHandler(hdlr)
        
        
    def _changestate(self, newstate):
        self.state = newstate(modem=self)
        self._daemon_log.debug("Changed state to " + str(self.state))
        self.state.entering()

    def write_nmea(self, msg):
        """Call with the message to send, as an NMEA message.  Correct checksum will be computed."""

        if type(msg) == str:
            # Automagically convert it into an NMEA message (or try, at least)
            msg = Message(msg)
        
        message = ",".join( [str(p) for p in [ msg['type'] ] + msg['params']] )
        chk = nmeaChecksum( message )
        message = "$" + message.lstrip('$').rstrip('\r\n*') + "*" + chk + "\r\n"
        # print message # for debug.
        #Serial.write(self, message )
        
        # Queue this message for transmit in the serial thread
        self._daemon_log.debug("Writing NMEA to output queue: %s" % (message.rstrip('\r\n')))
        try:
            self.serial_tx_queue.put(message, block=False)
        #If queue full, then ignore
        except Full:
            self._daemon_log.debug("write_nmea: Serial TX Queue Full")

        
    def write_string(self, string):
        self._daemon_log.debug("Writing string to output queue: %s" % (string.rstrip('\r\n')))
        try:
            self.serial_tx_queue.put(string, block=False)
        #If queue full, then ignore
        except Full:
            self._daemon_log.debug("write_string: Serial TX Queue Full")


        
    def get_config_param(self, param):
        msg = { 'type':"CCCFQ", 'params':[ param ] }
        self.write_nmea( msg )
        
    def get_config(self, param, response_timeout=2):
        msg = {'type': "CCCFQ", 'params': [param]}
        self.write_nmea(msg)

        config_dict = {}

        if response_timeout:
            while True:
                msg = self.wait_for_nmea_type('CACFG', timeout=response_timeout)
                if msg:
                    param_name = msg['params'][0]
                    param_value = msg['params'][1]
                    self.config_data[param_name] = param_value
                    # If we queried a config group, there is no associated value to add to the dictionary.
                    if param_value != "":
                        config_dict[param_name] = param_value
                    # We aren't done unless this config parameter matched the one we queried
                    if param_name == param:
                        break
                    else:
                        continue
                else:
                    break

            if config_dict:
                return config_dict
            else:
                return None
        else:
            return None


    def raw_readline(self):
        """Returns a raw message from the modem."""
        rl = Serial.readline(self)

        if rl == "":
            return None

        # Make sure we got a complete line.  Readline will return data on timeout.	
        if rl[-1] != '\n':
            self.temp_incoming_nmea += rl
            return None
        else:
            if self.temp_incoming_nmea != "":
                rl = self.temp_incoming_nmea + rl
            self.temp_incoming_nmea = ""
            
        return rl

    def on_rxframe(self, dataframe):
        self._daemon_log.debug("I got a frame!  Yay!")
        for func in self.rxframe_listeners:
            func(dataframe)
        # Append this message to all listening queues
        for q in self.incoming_dataframe_queues:
            try:
                q.put_nowait(dataframe)
            except:
                self._daemon_log.warn("Error appending to incoming dataframe queue")

    def on_minipacket_tx_failed(self):
        self._daemon_log.warn("Minipacket transmit failed.")

    def on_packettx_failed(self):
        self._daemon_log.warn("Packet transmit failed.")
        
    def on_packettx_success(self):
        self._daemon_log.info("Packet transmitted successfully")
        
    def on_packetrx_failed(self):
        self._daemon_log.warn("Packet RX failed")
        
    def on_packetrx_success(self):
        self._daemon_log.info("Packet RX succeeded")

    def on_ack(self,ack,msg):
        self._daemon_log.debug("Got ACK message")
        for func in self.ack_listeners:
            func(ack, msg) # Pass on the ACK message.

    def on_cst(self, cst, msg):
        self._daemon_log.debug("Got CST message")

        for func in self.cst_listeners: 
            func(cst, msg) # Pass on the CST message.
            
        # Append this message to all listening queues
        for q in self.incoming_cst_queues:
            try:
                q.put_nowait(cst)
            except:
                self._daemon_log.warn("Error appending to incoming CST queue")

    def on_xst(self, xst, msg):
        self._daemon_log.debug("Got XST message")

        for func in self.xst_listeners:
            func(xst, msg) # Pass on the CST message.

        # Append this message to all listening queues
        for q in self.incoming_xst_queues:
            try:
                q.put_nowait(xst)
            except:
                self._daemon_log.warn("Error appending to incoming XST queue")

    def on_log_msg(self,log,msg):
        self._daemon_log.debug("Got Logged message")

        for func in self.log_listeners:
            func(log, msg) # Pass on the Log message.

        # Append this message to all listening queues
        for q in self.incoming_log_queues:
            try:
                q.put_nowait(log)
            except:
                self._daemon_log.warn("Error appending to incoming modem log queue")

    def send_packet(self, packet):
        # FIXME this is a hack
        self.state.send_packet(packet)
    
    def send_packet_frames(self, dest, rate_num, frames):
        cycleinfo = CycleInfo(self.id, dest, rate_num, False, len(frames))
        packet = Packet(cycleinfo, frames)
        
        self.send_packet(packet)
        
    def send_packet_data(self, dest, databytes, rate_num=1, ack=False):
        # When life gives you data, make frames.
        rate = Rates[rate_num]
        src = self.id
        
        # For now, truncate the data to fit in this packet
        databytes = databytes[0:(rate.maxpacketsize - 1)]
        
        # Now, make frames.
        frames = []
        for framenum in range(rate.numframes):
            startidx = (framenum * rate.framesize)
            endidx = startidx + rate.framesize - 1
            thisdata = databytes[startidx:endidx]
            
            if len(thisdata) > 0:
                thisframe = DataFrame(src, dest, ack, framenum, thisdata)
                frames.append(thisframe)
        
        self.send_packet_frames(dest, rate_num, frames)
        
    def send_test_packet(self, dest, rate_num=1, num_frames=None, ack=False):
        rate = Rates[rate_num]
        src = self.id
        
        # How many frames shall we send?
        if num_frames == None:
            num_frames = rate.numframes
            
        # Make frames
        frames = []
        for framenum in range(num_frames):
            framedata = bytearray(struct.pack('!BBBBi', 0, 0, 1, 0, int(time())))
            frame = DataFrame(src, dest, ack, framenum, framedata)
            frames.append(frame)
        
        # Send a packet
        self.send_packet_frames(dest, rate_num, frames)

    def _send_current_txframe(self, frame_num=None):
        # TODO: Make sure we actually have a packet to send
                
        if frame_num == None:
            frame_num = self.current_tx_frame_num
                   
        self.send_frame(self.current_txpacket.frames[frame_num-1])

    def send_frame(self, dataframe):
        # Build the corresponding CCTXD message
        msg = {'type':'CCTXD', 'params':[dataframe.src, dataframe.dest, int(dataframe.ack), 
                                         hexstring_from_data(dataframe.data)]}
        self.write_nmea(msg)
    
    def send_cycleinit(self, cycleinfo):
        self._daemon_log.debug("Sending CCCYC with Following Parameters: %s" % (str([0, cycleinfo.src, cycleinfo.dest, cycleinfo.rate_num,
                                         int(cycleinfo.ack), cycleinfo.num_frames])))
        # Build the corresponding CCCYC message
        msg = {'type':'CCCYC', 'params':[0, cycleinfo.src, cycleinfo.dest, cycleinfo.rate_num, 
                                         int(cycleinfo.ack), cycleinfo.num_frames]}
        
        self.write_nmea(msg)
        
    def send_uplink_request(self, src_id, dest_id=None, rate_num=1, ack=False):
        if dest_id is None:
            dest_id = self.id
            
        #The number of frames isn't transmitted acoustically, so it doesn't matter
        cycleinfo = CycleInfo(src_id, dest_id, rate_num, ack, 1)
        
        self.send_cycleinit(cycleinfo)

    def send_uplink_frame(self,drqparams):
        if self.get_uplink_data_function is not None:
            data = self.get_uplink_data_function(drqparams)
        else:
            data = bytearray(struct.pack('!BBBBi', 0, 0, 1, 0, int(time())))
            
        self.send_frame(DataFrame(src = drqparams.src,dest = drqparams.dest, ack = drqparams.ack, frame_num = drqparams.frame_num, data=data))    

    def send_ping(self, dest_id):
        # Build the CCMPC message
        msg = {'type':'CCMPC', 'params':[self.id, dest_id]}
        
        self.write_nmea(msg)

    def wait_for_ping_reply(self,dest_id,timeout=30):
        time = None
        ping_reply = self.wait_for_nmea_type('CAMPR',timeout=timeout)

        if ping_reply is not None:
            dest = int(ping_reply["params"][1])
            if dest == self.id:
                time = abs(float(ping_reply["params"][2]))
        return time


    def send_minipacket(self,dest_id,databytes=[]):
        msg = {'type':'CCMUC', 'params':[self.id, dest_id, databytes[0:4]]}
        self.write_nmea(msg)

    def send_tdp(self, dest_id=None,databytes=[], rate_num=None, ack=False,base64data=False):
        rate = FDPRates[rate_num]
        ack = int(ack)
        # For now, truncate the data to fit in this packet
        #databytes=bytearray(range(0,rate.maxpacketsize,1))
        databytes=bytearray(range(0,8,1))
        # Build the CCTDP message
        msg = {'type':'CCTDP', 'params':[dest_id, rate_num,ack,base64data,hexstring_from_data(databytes)]}

        self.write_nmea(msg)

    def send_sweep(self, direction):
        '''This will send a sweep using the CCRSP command.'''
        # try to guess what was meant by the direction
        if str(direction).lower() in ['up', 'fsk', '1']:
            direction = 1
        elif str(direction).lower() in ['down', 'psk', '2']:
            direction = 2
        else:
            direction = 1
            
        # Build a CCRSP message
        msg = {'type':'CCRSP', 'params':[0, direction, 0]}
        
        self.write_nmea(msg)
        
    def set_config(self, name, value, response_timeout=2):
        params = [str(name), str(value)]
        msg = {'type':'CCCFG', 'params':params}
        self.write_nmea(msg)

        if not response_timeout:
            return

        response = self.wait_for_nmea_type('CACFG', timeout=response_timeout, params=params)
        if not response:
            return None
        else:
            return {str(name), str(value)}

    def change_gpio(self, pin, value, toggle = False, duration=0):
        if pin == 1:
            MECValue = 5
        elif pin == 2:
            MECValue =  6
        elif pin == 3:
            MECValue = 3
        elif pin == 4:
            MECValue = 2
        elif pin == 5:
            MECValue = 4
        else:
            MECValue = 5
        if not toggle:
            if value == 0:
                mode = 1
                arg = 0
            if value == 1:
                mode = 1
                arg = 1
            if value == -1:
                mode = 0
                arg = 0
        else:
            if duration < .5:
                arg = 0
            elif duration > .5 and duration < 1:
                arg = 1
            elif duration >= 1 and duration < 2:
                arg = 2
            elif duration >= 2 and duration < 6:
                arg = 3
            elif duration >= 6 and duration < 10:
                arg = 4
            elif duration >= 10 and duration < 20:
                arg = 5
            elif duration >= 20 and duration < 30:
                arg = 6
            elif duration >= 30:
                arg = 7                
            if value == 0:
                mode = 3
            else:
                mode = 3
                
        message = "$CCMEC,{0},{0},{1},{2},{3}".format(self.config_data["SRC"],MECValue,mode,arg)
        self.write_nmea(message)
        response = self.wait_for_nmea_type("CAMEC", timeout=self.default_nmea_timeout)
        return int(response['params'][4])

    def send_passthrough(self,msg):
        #Truncate our message to 48 characters
        info = msg[:46] + (msg[46:] and '..')
	    # Build a CCRSP message
        msg = {'type':'CCPAS', 'params':[info]}

        self.um.write_nmea(msg)		
        
			
    def start_hibernate(self, wake_at=None, wake_in=None, hibernate_at=None, hibernate_in=None, disable_schedule=False, ignore_response=False):
        ''' Start hibernating this modem.  This function will attempt to adapt to the limited capabilities of older
            (uM1) hardware.
        :param wake_at: Absolute time at which to wake.  May be a datetime object, Unix timestamp, or ISO 8601 datetime
            string.  If this is not None, wake_in may *not* be set.
        :param wake_in: Relative time to hibernate before waking.  May be a timedelta object, number of seconds to
            hibernate, or an ISO 8601 duration string.  If this is not None, wake_at may *not* be set.
        :param hibernate_at: Absolute time at which to start hibernate.  May be a datetime object, Unix timestamp, or
            ISO 8601 datetime string.  If this is not None, hibernate_in may *not* be set.
        :param hibernate_in: Relative time to wait before starting hibernate.  May be a timedelta object, number of
            seconds to wait, or an ISO 8601 duration string.  If this is not None, hibernate_at may *not* be set.
        :param disable_schedule: (Modem API level >= 10) If this is True and other parameters are all None, this will
            set the wake mode to 0, which causes the modem to ignore any defined wake schedule in its configuration and
            hibernate until an external wake signal is asserted.
        :param ignore_response: (ignored if API Level < 10) if this is True, this command won't block until a CAHIB
            response is received (but immediately return None).  If False (default), this function will return the
            parameters from the CAHIB message.
        '''
        # Make sure that we aren't overconstrained by parameters
        if wake_at is not None and wake_in is not None:
            raise(ValueError("Can't specify both an wake time (wake_at) and wake interval (wake_in)"))
        if hibernate_at is not None and hibernate_in is not None:
            raise(ValueError("Can't specify both a hibernate time (hibernate_at) and hibernate interval (hibernate_in)"))

        # Convert the parameters into more useful versions.  This will attempt to parse ISO date/duration strings.
        if wake_at is not None:
            wake_at = timeutil.convert_to_datetime(wake_at)
        if wake_in is not None:
            wake_in = timeutil.convert_to_timedelta(wake_in)
        if hibernate_at is not None:
            hibernate_at = timeutil.convert_to_datetime(hibernate_at)
        if hibernate_in is not None:
            hibernate_in = timeutil.convert_to_timedelta(hibernate_in)

        # Now, we need to generate a message, which varies depending on the API Level (uM1 vs uM2, mostly.)
        if self._api_level < 10:
            # This is a uM1, so we need to use CCMSC, with all its limitations
            # First, are we ever going to wake?
            if wake_at is None and wake_in is None:
                sleep_arg = -1
            else:
                # We need to get a duration in minutes to hibernate.
                if wake_at is not None:
                    sleep_delta = wake_at - datetime.utcnow()
                else:
                    sleep_delta = wake_in

                # We can only hibernate for multiples of 6 minutes.  Yeah...
                # First, round up to the nearest minute.
                # The following intermediate calculation is required by Python 2.6, which lacks the total_seconds() function.
                sleep_delta_seconds = sleep_delta.days * 84000 + sleep_delta.seconds
                sleep_arg = (sleep_delta_seconds + 60) // 60
                # Now round up to the nearest 6 minute interval (this takes advantage of the floor in integer division)
                sleep_arg = ((sleep_arg + 6) // 6) * 6

            if self._api_level < 6:
                # This API level is defined to be firmware that doesn't include delayed hibernate
                if (hibernate_at is not None) or (hibernate_in is not None):
                    # Not all uM1 firmware supports delayed hibernate.  The API level must be manually set to use this feature.
                    raise(UnavailableInApiLevelError("This API level (and probably modem) doesn't support delayed hibernate"))

                msg = {'type':'CCMSC', 'params':[self.id, self.id, sleep_arg]}
                self.write_nmea(msg)
                return None

            else:  # API level 6-9
                # We need to get a duration in seconds to delay hibernate.
                if hibernate_at is not None:
                    delay_delta = hibernate_at - datetime.utcnow()
                    hibernate_delay_secs = delay_delta.days * 84000 + delay_delta.seconds
                elif hibernate_in is not None:
                    hibernate_delay_secs = hibernate_in.days * 84000 + hibernate_in.seconds
                else:
                    hibernate_delay_secs = 0

                msg = {'type':'CCMSC', 'params':[self.id, self.id, sleep_arg, hibernate_delay_secs]}
                self.write_nmea(msg)
                return None

        else:  # API level 10 and higher (uM2)
            # Make a CCHIB command.
            # Figure out the modes
            if hibernate_in is not None:
                hibernate_time = int(hibernate_in.total_seconds())
            elif hibernate_at is not None:
                hibernate_time = timeutil.to_utc_iso8601(hibernate_at, strip_fractional_seconds=True)
            else:
                hibernate_time = 0

            if wake_in is not None:
                wake_time = int(wake_in.total_seconds())
            elif wake_at is not None:
                wake_time = timeutil.to_utc_iso8601(wake_at, strip_fractional_seconds=True)
            elif not disable_schedule:
                wake_time = 0
            else:
                wake_time = 0

            msg = {'type':'CCHIB', 'params':[hibernate_time, wake_time]}
            self.write_nmea(msg)

            if not ignore_response:
                response = self.wait_for_nmea_type("CAHIB", timeout=self.default_nmea_timeout)
                if response is None:
                    return None
                # parse the response.
                ret = namedtuple("CAHIB", ["hibernate_cause", "hibernate_time", "wake_cause", "wake_time"])
                ret.hibernate_cause = int(response['params'][0])
                ret.hibernate_time = timeutil.convert_to_datetime(response['params'][1])
                ret.wake_cause = int(response['params'][2])
                ret.wake_time = timeutil.convert_to_datetime(response['params'][3])
                return ret

            return None

        
    def set_host_clock_from_modem(self):
        self.set_host_clock_flag = True        
        msg = {'type':'CCCLQ', 'params':[0,]}
        self.write_nmea(msg)
        # The actual clock setting is done by the CACLQ parser when the flag is true.

    def set_time(self, time_to_set=None, mode=None, ignore_response=False, extpps_drive_fxn=None):
        ''' Set the modem clock to the specified time (or the current time of the host system if time_to_set is not
         specified.
         Requires that the modem support the $CCTMS command.
        '''
        # For now, don't support the old $CCCLK command.
        if self._api_level < 11:
            raise(UnavailableInApiLevelError("This API level doesn't support the enhanced time-setting functionality.  Use the $CCCLK command manually."))

        if time_to_set is None:
            time_to_set = datetime.utcnow()

        if mode is None:
            mode = 0


        # Generate the command
        cmd = {'type': "CCTMS", 'params':["{0}Z".format(timeutil.to_utc_iso8601(time_to_set, True)), mode]}
        # Send it.
        self.write_nmea(cmd)

        # If the user has specified a function to call to control the EXTPPS line in mode 1, call it.
        if (mode == 1) and (extpps_drive_fxn is not None):
            extpps_drive_fxn()

        # If timeout is not None, check the response.
        if not ignore_response:
            # CCTMS may take up to 3 seconds to time out in mode 1.
            response = self.wait_for_nmea_type('CATMS', timeout=4)
            if response is None:
                # We timed out... this could be an error condition
                return None
            # Return the argumenst of the CATMS command, more or less...
            CATMS = namedtuple("CATMS", ["time", "timed_out"])
            ret = CATMS(time= timeutil.convert_to_datetime(response['params'][1]), timed_out = response['params'][0])
            return ret
        else:
            return None

    def get_time(self, timeout=0.5):
        modem_time = self.get_time_info(timeout)[0]
        return modem_time

    def get_time_info(self, timeout=0.5):
        # For now, don't support the old $CCCLQ command.
        if self._api_level < 11:
            raise(UnavailableInApiLevelError("This API level doesn't support the enhanced time-query functionality.  Use the $CCCLQ command manually."))

        self.write_nmea("$CCTMQ,0")

        response = self.wait_for_nmea_type("CATMQ", timeout=timeout)
        if response is None:
            return None

        # first argument is the time as an ISO8601 string.
        modem_time = timeutil.convert_to_datetime(response['params'][0])
        clock_source = response['params'][1]
        pps_source = response['params'][2]

        return (modem_time, clock_source, pps_source)


    def wait_for_minipacket(self,timeout=30):
        data = None
        userminipacket_recpt = self.wait_for_nmea_type('CAMUA',timeout=timeout)

        if userminipacket_recpt is not None:
            dest = int(userminipacket_recpt["params"][1])
            if dest == self.id:
                data = str(userminipacket_recpt["params"][2])
        return data

    def attach_incoming_dataframe_queue(self, queue_to_attach):
        self.incoming_dataframe_queues.append(queue_to_attach)

    def detach_incoming_dataframe_queue(self, queue_to_detach):
        self.incoming_dataframe_queues.remove(queue_to_detach)

    def wait_for_data_packet(self,fsk = False, timeout=30):
        data_frame_queue = Queue()
        self._daemon_log.debug("wait_for_data_packet: Waiting for CARXP")
        self.wait_for_nmea_type(type_string='CARXP',timeout=timeout)
        self.attach_incoming_dataframe_queue(data_frame_queue)
        self._daemon_log.debug("wait_for_data_packet: Got CARXP")
        #If FSK packet, wait for secondary CACYC
        if fsk:
            #Wait for CST for CACYC
            self._daemon_log.debug("wait_for_data_packet: Waiting for CACYC CST")
            cst = self.wait_for_cst(timeout=timeout)
        #Wait for CST for Data packet.
        cst = self.wait_for_cst(timeout=timeout)
        self.detach_incoming_dataframe_queue(data_frame_queue)

        self._daemon_log.debug("wait_for_data_packet: Processing Data Packets Received.")
        data = bytearray()
        #Reject packet if some of the data didn't make it or if the message received wasn't for me.
        if cst is None or cst['bad_frames_num'] > 0 or cst['dest'] != self.id:
            self._daemon_log.warn("CST not valid. {}".format(cst))
            return None
        frame_count = cst['num_frames']
        self._daemon_log.debug("wait_for_data_packet: Number of Data Frames expected: {}".format(frame_count))
        while frame_count > 0:
            try:
                data_frame = data_frame_queue.get(block=True,timeout=timeout)
            except Empty:
                #Reject packet if not enough data frames were received.
                self._daemon_log.debug("wait_for_data_packet: Empty Dataframe Queue before total frames received. Frames Left:{}".format(frame_count))
                return None
            #Reject data_frames not destined for me.
            if data_frame.dest != self.id:
                self._daemon_log.debug("wait_for_data_packet: Skipping data frame not destined for {}".format(self.id))
                continue
            data.extend(data_frame.data)
            self._daemon_log.debug("wait_for_data_packet: Processed Frame #{}.".format(frame_count))
            frame_count = frame_count - 1


        self._daemon_log.info("wait_for_data_packet: Returning Data ({}).".format(repr(data)))
        return data

    def attach_incoming_cst_queue(self, queue_to_attach):
        self.incoming_cst_queues.append(queue_to_attach)
        
    def detach_incoming_cst_queue(self, queue_to_detach):
        self.incoming_cst_queues.remove(queue_to_detach)    



    def wait_for_cst(self, timeout=None):
        incoming_cst_queue = Queue()
        self.attach_incoming_cst_queue(incoming_cst_queue)

        try:
            cst = incoming_cst_queue.get(block=True, timeout=timeout)
        except Empty:
            cst = None

        self.detach_incoming_cst_queue(incoming_cst_queue)

        return cst

    def attach_incoming_xst_queue(self, queue_to_attach):
        self.incoming_xst_queues.append(queue_to_attach)

    def detach_incoming_xst_queue(self, queue_to_detach):
        self.incoming_xst_queues.remove(queue_to_detach)

    def wait_for_xst(self,timeout=None):
        incoming_xst_queue = Queue()
        self.attach_incoming_xst_queue(incoming_xst_queue)

        try:
            xst = incoming_xst_queue.get(block=True, timeout=timeout)
        except Empty:
            xst = None

        self.detach_incoming_xst_queue(incoming_xst_queue)

        return xst

    def attach_incoming_msg_queue(self, queue_to_attach):
        self.incoming_msg_queues.append(queue_to_attach)
        
    def detach_incoming_msg_queue(self, queue_to_detach):
        self.incoming_msg_queues.remove(queue_to_detach)

    def attach_incoming_modem_log_queue(self, queue_to_attach):
        self.incoming_log_queues.append(queue_to_attach)

    def detach_incoming_modem_log_queue(self, queue_to_detach):
        self.incoming_log_queues.remove(queue_to_detach)

    def wait_for_regex(self, regex_pattern, timeout=None):
        incoming_msg_queue = Queue()
        self.attach_incoming_msg_queue(incoming_msg_queue)
        
        regex = re.compile(regex_pattern)
        matching_msg = None
        
        remaining_time = timeout
        if remaining_time is not None:
            # If this program is ported to Python 3, this should be changed to use time.steady().
            end_time = time() + timeout    
        
        while (remaining_time is None) or (remaining_time > 0):
            try:
                new_msg = incoming_msg_queue.get(timeout=remaining_time)
                matchobj = regex.search(new_msg['raw'])
                if matchobj is not None:
                    matching_msg = new_msg
                    break
                else:
                    if remaining_time is not None:
                        remaining_time = end_time - time()
                    continue
            except Empty:
                break
        
        self.detach_incoming_msg_queue(incoming_msg_queue)
            
        return matching_msg

    def wait_for_nmea_type(self, type_string, timeout=None, params=None):
        incoming_msg_queue = Queue()
        self.attach_incoming_msg_queue(incoming_msg_queue)

        matching_msg = None

        remaining_time = timeout
        if remaining_time is not None:
            # If this program is ported to Python 3, this should be changed to use time.steady().
            end_time = time() + timeout

        while (remaining_time is None) or (remaining_time > 0):
            try:
                new_msg = incoming_msg_queue.get(timeout=remaining_time)
                if new_msg['type'] == type_string:
                    if params:
                        if len(new_msg['params']) != len(params):
                            continue
                        for (n, p) in zip(new_msg['params'], params):
                            # make sure that any non-None parameter matches.
                            if p and (n != p):
                                continue

                    matching_msg = new_msg
                    break
                else:
                    if remaining_time is not None:
                        remaining_time = end_time - time()
                    continue
            except Empty:
                break

        self.detach_incoming_msg_queue(incoming_msg_queue)

        return matching_msg

    def wait_for_nmea_types(self, type_string_list, timeout=None):
        incoming_msg_queue = Queue()
        self.attach_incoming_msg_queue(incoming_msg_queue)

        matching_msg = None

        remaining_time = timeout
        if remaining_time is not None:
            # If this program is ported to Python 3, this should be changed to use time.steady().
            end_time = time() + timeout

        while (remaining_time is None) or (remaining_time > 0):
            try:
                new_msg = incoming_msg_queue.get(timeout=remaining_time)
                if new_msg['type'] in type_string_list:
                    matching_msg = new_msg
                    break
                else:
                    if remaining_time is not None:
                        remaining_time = end_time - time()
                    continue
            except Empty:
                break

        self.detach_incoming_msg_queue(incoming_msg_queue)

        return matching_msg

    def set_uplink_data_function(self,func):
        if hasattr(func, '__call__'):
            self.get_uplink_data_function = func

    def request_modem_log(self, all_or_newest=1, order=0, num_to_retrieve=0, filter_params=[],timeout =None):
        filtr = BitArray(hex='0x00')
        if 'Modem To Host' in filter_params:
            filtr.set(1,1)
        if 'Host to Modem' in filter_params:
            filtr.set(1,2)
        if 'CARXD' in filter_params:
            filtr.set(1,3)
        if 'CACST' in filter_params:
            filtr.set(1,4)
        if 'CAXST' in filter_params:
            filtr.set(1,5)

        params = [1,all_or_newest, order,num_to_retrieve,filtr.uint]

        # Build the CCRBR message
        msg = {'type':'CCRBR', 'params': params}
        #Not this waits for a response of
        self.write_nmea(msg)

        response = self.wait_for_nmea_type('CARBR', timeout=timeout, params=[1,0,'','',''])

    def update_firmware(self, firmware_file_path, slot=1, reboot=False, File_location=0, data_upload_callback_fxn = None, done_call_back_fxn=None):
        size_of_acceptable_data_chunks = 1013

        filesize = os.path.getsize(firmware_file_path)
        self.packets_to_send = filesize / size_of_acceptable_data_chunks
        self.packet_count = 0
        filename = os.path.basename(firmware_file_path)

        rev_timeout = self.get_config_param('CTO')



        if self.connection.can_change_baudrate():
            #Set Baud Rate on Modem
            self.set_config(name='uart1.bitrate',value=115200,response_timeout=None)
            #Change Local Baudrate
            self.connection.change_baudrate(115200)
            response = self.wait_for_nmea_type('CAREV',timeout=rev_timeout + 5)
            if response is None:
                self._daemon_log.error("REV message not received. Aborting.")
                return

        data_timeout_rate = size_of_acceptable_data_chunks / (self.connection.baudrate / 8)

        with open(firmware_file_path, 'rb') as firmware_file:
            sha1hash = hashlib.sha1(firmware_file.read(filesize)).hexdigest()
            firmware_file.seek(0)

            #Send the Update Modem FW Command
            params = [slot,File_location,filesize,int(reboot),sha1hash,filename]
            msg = {'type':'UPMFW', 'params':params}
            self.write_nmea(msg)
            response = self.wait_for_nmea_types(['UPMFWA','UPERR'],timeout=2)
            if response is None:
                self._daemon_log.error("Update FW Command not acknowledged. Aborting.")
                return
            elif response['type'] == 'UPERR':
                if 'Restarting' not in response['params'][1]:
                    self._daemon_log.error("Update FW Command Error ({}). Aborting.".format(response['params'][1]))
                else:
                    self._daemon_log.info("Update FW Command Error ({}). Continuing Update.".format(response['params'][1]))
            elif response['type'] == 'UPMFWA':
                for (n, p) in zip(response['params'], params):
                    # make sure that any non-None parameter matches.
                    if p and (n != p):
                        self._daemon_log.error("Update FW Command Parameter Mismatch ({} != {} ). Aborting.".format(params, response['params']))
                        return

            #Send our firmware file.
            data_chunk = firmware_file.read(size_of_acceptable_data_chunks)
            while data_chunk != "":
                params = [hexlify(bytes(data_chunk))]
                msg = {'type': 'UPDAT', 'params':params}
                self.write_nmea(msg)
                response = self.wait_for_nmea_types(['UPDATA','UPERR'],timeout= data_timeout_rate + 2)
                if response is None:
                    self._daemon_log.error("Update FW Data Upload not acknowledged. Aborting.")
                    return
                elif response['type'] == 'UPERR':
                    self._daemon_log.error("Update FW Data Upload Error ({}). Aborting.".format(response['params'][1]))
                    return
                elif response['type'] == 'UPDATA':
                    if int(response['params'][0]) != len(data_chunk):
                        self._daemon_log.error("Update FW Data Upload Error ({} != {}). Aborting.".format(len(data_chunk),response['params'][0]))
                        return
                    self.packet_count += 1
                    if data_upload_callback_fxn is not None:
                        data_upload_callback_fxn()
                data_chunk= firmware_file.read(size_of_acceptable_data_chunks)

            response = self.wait_for_nmea_types(['UPDONE','UPERR'],timeout=None)
            if response['type'] == 'UPDONE':
                self._daemon_log.info("Update FW Command Completed. ({})".format(response['params']))
                if done_call_back_fxn is not None:
                    done_call_back_fxn()
            elif response['type'] == 'UPERR':
                self._daemon_log.error("Update FW Update Error ({}). Aborting.".format(response['params'][1]))


        
        
class Message(dict):
    def __init__(self, raw):
        """Strips off NMEA checksum and leading $, returns command dictionary
        (or throws an exception if the checksum is invalid)."""
        dict.__init__(self)
        if raw == "": return None
        msg = raw.lstrip('$').rstrip('\r\n').rsplit('*')
        if len(msg) == 2:
            msg, chksum = msg
            correctChksum = nmeaChecksum( msg )
            if chksum and (chksum != correctChksum ):
                raise ChecksumException("Checksum Error. Rec'd: %s, Exp'd: %s\n" % (chksum, correctChksum) )
        else:
            msg = msg[0]

        msgParts = [part.strip() for part in msg.split(',')] # splits on commas and removes spaces/CRLF
        self['type']   = msgParts[0]
        self['params'] = msgParts[1:]
        self['raw']    = raw


