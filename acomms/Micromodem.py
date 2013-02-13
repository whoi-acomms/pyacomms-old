#!/usr/bin/env python
import os
from time import sleep, time
from datetime import datetime
import re
from Queue import Empty, Full
from multiprocessing import Queue
import logging
import struct

from serial import Serial

import commstate
from messageparser import MessageParser
from messageparams import Packet, CycleInfo, hexstring_from_data, Rates, DataFrame
from acomms.modem_connections import SerialConnection


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

class UnavailableInApiLevel(Exception):
    pass


class Micromodem(object):
    def __init__(self, name='modem', logpath='/var/log/', consolelog='WARN', logformat='Default'):

        name = str(name)
        # Strip non-alphanumeric characters from name
        self.name = ''.join([ch for ch in name if ch.isalnum()])

        self.logpath = logpath
        if self.logpath[-1] != '/':
            self.logpath += '/'

        self.logformat = logformat

        self.connection = None

        self.nmea_listeners = [ ]

        self.parser = MessageParser(self)
        self.state = commstate.Idle(comms=self)
        
        self.rxframe_listeners = []
        self.cst_listeners = []
        
        self.incoming_cst_queues = []
        self.incoming_msg_queues = []
        
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
        
        self.nmealog = None
        self.daemonlog = None        
        self.start_nmea_logger(consolelog)
        self.start_daemon_logger(consolelog)
        
        self.get_uplink_data_function = None

    def connect(self, serialport=None, baudrate=19200):
        ''' Convenience function to establish a connection using a serial port.  Included for backward-compatibility.
        '''
        self.connect_serial(serialport, baudrate)

    def connect_serial(self, port, baudrate=19200):
        self.connection = SerialConnection(self, port, baudrate)
        self.query_modem_info()

    def disconnect(self):
        if self.connection is not None:
            self.connection.disconnect()
            self.connection = None

    def query_modem_info(self):
        sleep(0.05)
        self.get_config_param("ALL")
        sleep(0.05)
        # All of the salient properties on this object are populated automatically by the NMEA config handler.

    def start_nmea_logger(self,consolelog):
        if self.nmealog == None:
            now = datetime.utcnow()
            logfilename = self.name + "_nmea_{0}.log".format(now.strftime("%Y-%m-%d_%H-%M-%S"))
            logformat = logging.Formatter("%(asctime)s\t%(levelname)s\t{0}\t%(message)s".format(self.name), "%Y-%m-%d %H:%M:%S")
            mtmaformat = logging.Formatter("%(asctime)sZ,RX,%(message)s", "%Y-%m-%d %H:%M:%S")
            self.nmealog = logging.getLogger(self.name + '_nmea')
            self.nmealog.setLevel(logging.DEBUG)
            
            # Create the log directory if it doesn't exist.
            if not os.path.isdir(self.logpath):
                os.makedirs(self.logpath)                 
            fh = logging.FileHandler(self.logpath + logfilename)
            fh.setLevel(logging.DEBUG)
            if self.logformat.lower() == "modemtma":
                fh.setFormatter(mtmaformat)
            else:		
                fh.setFormatter(logformat)
            if consolelog != 'DISABLED':
                ch = logging.StreamHandler()
                ch.setLevel(consolelog)
                ch.setFormatter(logformat)
                self.nmealog.addHandler(ch)
            self.nmealog.addHandler(fh)
            self.nmealog.info("$PYMODEM,Starting NMEA log,{0}".format(self.name))
        
    def start_daemon_logger(self, consolelog):
        if self.daemonlog == None:
            now = datetime.utcnow()
            logfilename = self.name + "_pymodem_{0}.log".format(now.strftime("%Y-%m-%d_%H-%M-%S"))
            logformat = logging.Formatter("%(asctime)s\t%(levelname)s\t%(message)s", "%Y-%m-%d %H:%M:%S")
            self.daemonlog = logging.getLogger(self.name + "_pymodem")
            self.daemonlog.setLevel(logging.DEBUG)

            # Create the log directory if it doesn't exist.
            if not os.path.isdir(self.logpath):
                os.makedirs(self.logpath)                             
            fh = logging.FileHandler(self.logpath + logfilename)
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(logformat)
            if consolelog != 'DISABLED':            
                ch = logging.StreamHandler()
                ch.setLevel(consolelog)
                ch.setFormatter(logformat)
                self.daemonlog.addHandler(ch)
            self.daemonlog.addHandler(fh)
            self.daemonlog.info("Starting daemon log,{0}".format(self.name))


    def _process_outgoing_nmea(self):
        # Now, transmit anything we have in the outgoing queue.
        try:
            txstring = self.serial_tx_queue.get_nowait()
            self.connection.write(txstring)
            self.nmealog.info(txstring.rstrip('\r\n'))
        #If the queue is empty, then pass, otherwise log error
        except Empty:
            pass
        except:
            self.daemonlog.exception("NMEA Output Error")        
                
    def _process_incoming_nmea(self, msg):
        if msg is not None:
            try:
                #self.nmealog.info("< " + msg.rstrip('\r\n'))
                self.nmealog.info(msg.rstrip('\r\n'))                

                msg = Message(msg)
                
                self.parser.parse(msg)
                
                for func in self.nmea_listeners: func(msg)  # Pass the message to any custom listeners.
                
                # Append this message to all listening queues
                for q in self.incoming_msg_queues:
                    try:
                        q.put_nowait(msg)
                    except:
                        self.daemonlog.warn("Error appending to incoming message queue")
            except ChecksumException:
                self.daemonlog.warn("NMEA Checksum Error: %s" % (msg.rstrip('\r\n')))
            except:
                self.daemonlog.warn("NMEA Input Error")


    def close_loggers(self):
        for hdlr in self.daemonlog.handlers:
            hdlr.flush()
            hdlr.close()
            self.daemonlog.removeHandler(hdlr)
        
        for hdlr in self.nmealog.handlers:
            hdlr.flush()
            hdlr.close()
            self.nmealog.removeHandler(hdlr)
        
        
    def _changestate(self, newstate):
        self.state = newstate(comms=self)
        self.daemonlog.debug("Changed state to " + str(self.state))
        self.state.entering()

    def write_nmea(self, msg):
        """Call with the message to send, as an NMEA message.  Correct checksum will be computed."""
        
        message = ",".join( [str(p) for p in [ msg['type'] ] + msg['params']] )
        chk = nmeaChecksum( message )
        message = "$" + message.lstrip('$').rstrip('\r\n*') + "*" + chk + "\r\n"
        # print message # for debug.
        #Serial.write(self, message )
        
        # Queue this message for transmit in the serial thread
        self.daemonlog.debug("WRITING NMEA TO QUEUE: %s" % (message))
        try:
            self.serial_tx_queue.put(message, block=False)
        #If queue full, then ignore
        except Full:
            self.daemonlog.debug("write_nmea: Serial TX Queue Full")

        
    def write_string(self, string):
        self.daemonlog.debug("WRITING STRING TO QUEUE: %s" % (string))
        try:
            self.serial_tx_queue.put(string, block=False)
        #If queue full, then ignore
        except Full:
            self.daemonlog.debug("write_string: Serial TX Queue Full")


        
    def get_config_param(self, param):
        msg = { 'type':"CCCFQ", 'params':[ param ] }
        self.write_nmea( msg )
        


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
        self.daemonlog.debug("I got a frame!  Yay!")
        for func in self.rxframe_listeners:
            func(dataframe)
        
    def on_packettx_failed(self):
        self.daemonlog.warn("Packet transmit failed.")
        
    def on_packettx_success(self):
        self.daemonlog.info("Packet transmitted successfully")
        
    def on_packetrx_failed(self):
        self.daemonlog.warn("Packet RX failed")
        
    def on_packetrx_success(self):
        self.daemonlog.info("Packet RX succeeded")
        
    def on_cst(self, cst, msg):
        self.daemonlog.debug("Got CST message")

        for func in self.cst_listeners: 
            func(cst, msg) # Pass on the CST message.
            
        # Append this message to all listening queues
        for q in self.incoming_cst_queues:
            try:
                q.put_nowait(cst)
            except:
                self.daemonlog.warn("Error appending to incoming CST queue")        
    
    def send_packet(self, packet):
        # FIXME this is a hack
        self.state.send_packet(packet)
    
    def send_packet_frames(self, dest, rate_num, frames):
        cycleinfo = CycleInfo(self.id, dest, rate_num, False, len(frames))
        packet = Packet(cycleinfo, frames)
        
        self.send_packet(packet)
        
    def send_packet_data(self, dest, databytes, rate_num=1):
        # When life gives you data, make frames.
        rate = Rates[rate_num]
        src = self.id
        ack = False
        
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
        
    def send_test_packet(self, dest, rate_num=1, num_frames=None):
        rate = Rates[rate_num]
        src = self.id
        ack = False
        
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
        
                
    
    def send_current_txframe(self, frame_num=None):
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
        self.daemonlog.debug("Sending CCCYC with Following Parameters: %s" % (str([0, cycleinfo.src, cycleinfo.dest, cycleinfo.rate_num, 
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
            data = self.get_uplink_data_function(drqparams.num_bytes,self.id)
        else:
            data = bytearray(struct.pack('!BBBBi', 0, 0, 1, 0, int(time())))
            
        self.send_frame(DataFrame(src = drqparams.src,dest = drqparams.dest, ack = drqparams.ack, frame_num = drqparams.frame_num, data=data))    
            

    def send_ping(self, dest_id):
        # Build the CCMPC message
        msg = {'type':'CCMPC', 'params':[self.id, dest_id]}
        
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
        
    def set_config(self, name, value):
        msg = {'type':'CCCFG', 'params':[str(name), str(value)]}
        self.write_nmea(msg)
        
    def start_hibernate(self, num_minutes, delay_secs=0):
        msg = {'type':'CCMSC', 'params':[self.id, self.id, num_minutes, delay_secs]}
        self.write_nmea(msg)
    
        
    def set_host_clock_from_modem(self):
        self.set_host_clock_flag = True        
        msg = {'type':'CCCLQ', 'params':[0,]}
        self.write_nmea(msg)
        # The actual clock setting is done by the CACLQ parser when the flag is true.
    
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
    
    def attach_incoming_msg_queue(self, queue_to_attach):
        self.incoming_msg_queues.append(queue_to_attach)
        
    def detach_incoming_msg_queue(self, queue_to_detach):
        self.incoming_msg_queues.remove(queue_to_detach)
        
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

    def wait_for_nmea_type(self, type_string, timeout=None):
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
                if new_msg['type'] is type_string:
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
            if (chksum != correctChksum ):
                raise ChecksumException("Checksum Error. Rec'd: %s, Exp'd: %s\n" % (chksum, correctChksum) )
        else:
            msg = msg[0]

        msgParts = [part.strip() for part in msg.split(',')] # splits on commas and removes spaces/CRLF
        self['type']   = msgParts[0]
        self['params'] = msgParts[1:]
        self['raw']    = raw


