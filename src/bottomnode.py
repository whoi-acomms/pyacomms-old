'''
Created on Feb 3, 2012

@author: Eric
'''

from modem import Micromodem
from cyclestats import CycleStats
from messageparams import Rates, DataFrame, Packet, CycleInfo
from bitstring import BitStream
from time import sleep
import logging
import pickle

class BottomNode(object):
    
    def __init__(self):
        self.logpath = '/var/log/'
        self.cstpicklepath = '/var/cst.dat'
        self.modempath = '/dev/ttyS0'
        self.gliderid = 10
        self.hibernate_minutes = 60 * 6
        
        self.csts = {}
        
        self.read_csts()
        
        self.um = Micromodem()
        
    def start(self):
        # Connect to the modem
        um.connect(self.modempath, 19200)
        
        # Attach to the events.
        um.cst_listeners.append(self.on_cst)
        
        # Wait for the settings to be read.
        sleep(2)
        
        # Now, send up as many CST data as we can, using one packet of each rate that we like
        self.send_cst_data(1)
        sleep(20)
        self.send_cst_data(2)
        sleep(20)
        self.send_cst_data(4)
        sleep(20)
        self.send_cst_data(5)
        
        # Wait 3 minutes for replies from the WaveGlider
        sleep(180)
        
        # Now hibernate.
        self.um.start_hibernate(self.hibernate_minutes)
        
    
    def on_cst(self, cst):
        if not isinstance(cst, CycleStats):
            raise TypeError("BottomNode.on_cst: not a CycleStats object")
        
        # Add this CST to the CST dictionary
        self.csts[cst.packed_timestamp] = cst
        
    def on_rxframe(self, dataframe):
        # Make sure this is a frame for us before we do anything.
        if dataframe.dest != self.modem.id:
            self.logger.info("Overheard data frame for " + str(dataframe.dest))
            return
        
        # Now, see if it was an acknowledgment of CST data
        if dataframe.framedata[0] == 0x31:
            if dataframe.framedata[1] == 0x21:
                # CST ack frame
                # Following the header are a sequence of packed CST timestamps.
                ackbitstream = BitStream(dataframe.framedata[2:])
                acklist = ackbitstream.readlist('uint:24')
                
                # When we get an ack, remove the corresponding CST from the dictionary
                for ackitem in acklist:
                    if ackitem in self.csts:
                        self.logger.info("Got ACK for " + str(ackitem))
                        del self.csts[ackitem]       
        
    
    def start_log(self):
        # Configure logging
        logformat = logging.Formatter("%(asctime)s\t%(levelname)s\t%(message)s", "%Y-%m-%d %H:%M:%S")
        self.logger = logging.getLogger("bottomnode")
        self.logger.setLevel(logging.DEBUG)
        fh = logging.FileHandler(self.logpath + 'bottomnode.log')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logformat)
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(logformat)
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)
        
    def read_csts(self):
        self.csts = pickle.load(self.cstpicklepath)
        
    def write_csts(self):
        pickle.dump(self.csts, self.cstpicklepath)
        
    
        

    def send_cst_data(self, rate_num):
        '''Send a packet at the specified rate containing as many unacknowledged CST messages as possible.
        If there are no unacknowledged CST messages, send test frames to ensure that we have full packets.'''
        
        # Make a packet
        thispacket = Packet(CycleInfo(self.modem.id, self.gliderid, rate_num))
        
        # how many CSTs do we have to send?
        if len(self.csts) == 0:
            # We have none, so just send test data (with a special header so that we know to respond)
            for frame_num in range(Rates[rate_num].numframes):
                thispacket.append_framedata([0x31, 0x12])
            self.modem.send_packet(thispacket)
            return
        
        # We have something to send.  Loop through our CSTs as many times as we can.
        cst_queue_keys = sorted(self.csts.iterkeys(), reverse=True)
        currentidx = 0
        
        # How many CSTS can we send in each frame? (2 bytes are used as a header)
        payloadsize = Rates[rate_num].framesize - 2
        
        csts_per_frame = int(payloadsize / CycleStats.packed_size)
        
        
        for frame_num in range(Rates[rate_num].numframes):
            framedata = bytearray(0x31, 0x11)
            for i in range(csts_per_frame):
                currentidx = currentidx % len(cst_queue_keys)
                framedata.extend(self.csts[cst_queue_keys[currentidx]].tobytes())
                currentidx += 1
                
            # Add this frame to the packet
            thispacket.append_framedata(framedata)
        
        # Send the packet we just created.
        self.modem.send_packet(thispacket)
        
        
        
                
                
                
            
        
        
        
        


if __name__ == '__main__':
    # Connect to the modem
    um = Micromodem()
    um.connect('/dev/ttyS0', 19200)
    
    # Attach to the events.
    um.cst_listeners.append()
    
    # Wait for the settings to be read.
    sleep(2)
    
    # Now, send up as many CST data as we can
    
    