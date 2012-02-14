#!/usr/bin/env python
import cmd,sys
from time import sleep, time
from datetime import datetime
from serial import Serial
from threading import Thread
from Queue import Queue
import logging
import struct

import commstate
from messageparser import MessageParser
from messageparams import Packet, CycleInfo, hexstring_from_data, Rates, DataFrame

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

class Micromodem(Serial):
    def __init__(self, logpath='/var/log/', consolelog='WARN'):
        Serial.__init__(self)

        self.logpath = logpath
        if self.logpath[-1] != '/':
            self.logpath += '/'
        
        self.thread = None
        self.connected = False
        self.listeners = [ ]
        self.stopListeningCalled = False
        self.thread = Thread( target=self.listen )
        self.thread.setDaemon(True)
        self.doSerial = True

        self.parser = MessageParser(self)
        self.state = commstate.Idle(comms=self)
        
        self.rxframe_listeners = []
        self.cst_listeners = []
        
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
        
        self.start_nmea_logger()
        self.start_daemon_logger(consolelog)
        
    def start_nmea_logger(self):
        logformat = logging.Formatter("%(asctime)s\t%(levelname)s\t%(message)s", "%Y-%m-%d %H:%M:%S")
        self.nmealog = logging.getLogger("nmea")
        self.nmealog.setLevel(logging.DEBUG)
        fh = logging.FileHandler(self.logpath + 'nmea.log')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logformat)
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(logformat)
        self.nmealog.addHandler(fh)
        self.nmealog.addHandler(ch)
        
    def start_daemon_logger(self, consolelog):
        logformat = logging.Formatter("%(asctime)s\t%(levelname)s\t%(message)s", "%Y-%m-%d %H:%M:%S")
        self.daemonlog = logging.getLogger("pymodem")
        self.daemonlog.setLevel(logging.DEBUG)
        fh = logging.FileHandler(self.logpath + 'pymodem.log')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logformat)
        ch = logging.StreamHandler()
        ch.setLevel(consolelog)
        ch.setFormatter(logformat)
        self.daemonlog.addHandler(fh)
        self.daemonlog.addHandler(ch)

        
    def listen(self):
        while(True):
            if self.connected:
                msg = self.rawReadline()
                if msg is not None:
                    try:
                        self.nmealog.info("< " + msg.rstrip('\r\n'))
                        
                        msg = Message(msg)
                        
                        self.parser.parse(msg)
                        
                        for func in self.listeners: func(msg) # Pass on the message.
                    except ChecksumException:
                        self.daemonlog.warn("NMEA Checksum Error: ", msg.rstrip('\r\n'))
                
                # Now, transmit anything we have in the outgoing queue.
                try:
                    txstring = self.serial_tx_queue.get_nowait()
                    self.write(txstring)
                    self.nmealog.info("> " + txstring.rstrip('\r\n'))
                except:
                    pass
                     
            else: # not connected
                sleep(0.5) # Wait half a second, try again.

    def connect(self, port, baud, timeout=0.1):
        self.doSerial = True
        self.port = port
        self.baudrate = baud
        self.timeout = timeout
        try:
            if not self.thread.isAlive(): self.thread.start()
            self.open()
            self.connected = True
            sleep(0.05)
            self.getConfigParam("ALL")
            sleep(0.05)
        except Exception, inst:
            raise inst
        sleep(0.5) # Let config parameters return


    def disconnect(self):
        self.connected = False
        self.close()
        
        
    def changestate(self, newstate):
        self.state = newstate(comms=self)
        self.daemonlog.debug("Changed state to " + str(self.state))
        self.state.entering()

    def rawWrite(self, msg):
        """Call with the message to send, without leading $ or trailing checksums,
        linefeeds, and carriage returns.  Correct checksum will be computed."""
        
        message = ",".join( [str(p) for p in [ msg['type'] ] + msg['params']] )
        chk = nmeaChecksum( message )
        message = "$" + message.lstrip('$').rstrip('\r\n*') + "*" + chk + "\r\n"
        # print message # for debug.
        #Serial.write(self, message )
        
        # Queue this message for transmit in the serial thread
        self.serial_tx_queue.put_nowait(message)
        
    def getConfigParam(self, param):
        msg = { 'type':"CCCFQ", 'params':[ param ] }
        self.rawWrite( msg )

    def setConfigParam(self, param, value):
        # luckily, all param values are currently int's.
        msg = { 'type':"CCCFG", 'params':(param, value) }
        self.rawWrite( msg )

    def sendBinary(self, dest, binData, ack=False, src=None):
        ack = bool2int(ack)
        if src is None: src = self.config["SRC"]
        msg = { 'type' : "CCTXD", 'params':(src, dest, ack, toHexStr(binData)) }
        self.rawWrite( msg )

    def rawReadline(self):
        """Returns a raw message from the modem."""
        rl = Serial.readline(self)
        
        if rl == "": 
            return None
        else: 
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
        
    def on_cst(self, cst):
        self.daemonlog.debug("Got CST message")
        for func in self.cst_listeners: 
            func(cst) # Pass on the CST message.
    
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
            num_frames = Rates[rate_num].numframes
            
        # Make frames
        frames = []
        for framenum in range(rate.numframes):
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
        self.rawWrite(msg)
    
    def send_cycleinit(self, cycleinfo):
        # Build the corresponding CCCYC message
        
        
        msg = {'type':'CCCYC', 'params':[0, cycleinfo.src, cycleinfo.dest, cycleinfo.rate_num, 
                                         int(cycleinfo.ack), cycleinfo.num_frames]}
        
        self.rawWrite(msg)

    def send_ping(self, dest_id):
        # Build the CCMPC message
        msg = {'type':'CCMPC', 'params':[self.id, dest_id]}
        
        self.rawWrite(msg)
        
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
        
        self.rawWrite(msg)
        
    def set_config(self, name, value):
        msg = {'type':'CCCFG', 'params':[str(name), str(value)]}
        self.rawWrite(msg)
        
    def start_hibernate(self, num_minutes, delay_secs=0):
        msg = {'type':'CCMSC', 'params':[self.id, self.id, num_minutes, delay_secs]}
        self.rawWrite(msg)
    
        
    def set_host_clock_from_modem(self):
        self.set_host_clock_flag = True        
        msg = {'type':'CCCLQ', 'params':[0,]}
        self.rawWrite(msg)
        # The actual clock setting is done by the CACLQ parser when the flag is true.

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


