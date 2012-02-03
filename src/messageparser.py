from messageparams import CycleInfo, DrqParams, DataFrame, data_from_hexstring, hexstring_from_data
import commstate
from binascii import hexlify, unhexlify
import sys
import traceback

class MessageParser:
    def __init__(self, modem):
        self.modem = modem    
    
    # This method gets called when the object is called as a function, and
    # tries to find a matching attribute for that message type.
    # This is a pythonic(?) way of implementing a switch case.
    def parse(self, msg):
        try:
            func = getattr(self, msg['type'])
            return func(msg)
        except Exception, e:
            print ("Exception when parsing: ", sys.exc_info()[0])
            traceback.print_exc()
        
    def CACFG(self, msg):
        # Only worry about the parameters that matter...
        key = msg["params"][0]
        value = msg["params"][1]
        
        if key == "SRC": self.modem.id = int(value)
        if key == "ASD": self.modem.asd = bool(value)  
        
    def CACYC(self, msg):
        src = int(msg["params"][1])
        dest = int(msg["params"][2])
        rate = int(msg["params"][3])
        ack = int(msg["params"][4]) == 1
        num_frames = int(msg["params"][5])
        
        cycleinfo = CycleInfo(src, dest, rate, ack, num_frames)
        
        # Pass this to the comms state machine.
        self.modem.state.got_cacyc(cycleinfo)
        
    def CATXF(self, msg):
        self.modem.state.got_catxf()
        
    def CADRQ(self, msg):
        src = int(msg["params"][1])
        dest = int(msg["params"][2])
        ack = int(msg["params"][3]) == 1
        num_bytes = int(msg["params"][4])
        frame_num = int(msg["params"][5]) 
        
        drqparams = DrqParams(src, dest, ack, num_bytes, frame_num)
        
        self.modem.state.got_cadrq(drqparams)
        
    def CARXD(self, msg):
        src = int(msg["params"][0])
        dest = int(msg["params"][1])
        ack = int(msg["params"][2]) == 1
        frame_num = int(msg["params"][3])
        data = data_from_hexstring(msg["params"][4])
        
        dataframe = DataFrame(src, dest, ack, frame_num, data)
        
        self.modem.state.got_carx(dataframe)
        self.modem.on_rxframe(dataframe)
        
    def CAMSG(self, msg):
        # CAMSG sucks.  We need to parse it to figure out what's going on.
        # This doesn't account for all of the possible CAMSG messages.
        if msg["params"][0] == "BAD_CRC":
            self.modem.state.got_badcrc()
        elif msg["params"][0] == "PACKET_TIMEOUT":
            self.modem.state.got_packettimeout()
            
        #TODO: Add PSK errors here
            
    def CAERR(self, msg):
        # Sigh.  This really shouldn't be used to signal data timeouts, but it is.
        # This doesn't account for most of the CAERR messages.
        if msg["params"][1] == "DATA_TIMEOUT":
            frame_num = msg["params"][3]
            self.modem.state.got_datatimeout(frame_num)
    
    def CAREV(self, msg):
        self.modem.state.got_carev()
        
    def CATXP(self, msg):
        pass
    
         
    
        
        
        
        
        