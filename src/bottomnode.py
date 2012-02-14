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
import os

class BottomNode(object):
    
    def __init__(self):
        self.logpath = '/var/log/'
        #self.logpath = 'c:/temp/glider/'
        
        self.cstpicklepath = '/var/log/cst.dat'
        #self.cstpicklepath = 'c:/temp/glider/cst.dat'
        
        
        self.modempath = '/dev/ttyS0'
        #self.modempath = 'COM11'
        
        self.gliderid = 10
        self.hibernate_minutes = 6 * 60
        self.hibernate_delay_secs = 15
        self.reply_timeout_secs = 5 * 60
        self.wakecount = 0
        
        self.start_log()
        
        self.csts = {}
        self.csts[0] = CycleStats.from_values('000000', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, False, CycleStats.ts_epoch)
        
        self.read_csts()
        self.update_wakecount()
        
        self.um = Micromodem(logpath=self.logpath)
        
        
        
    def start(self):
        # Keep track of wakes
        
        # Connect to the modem
        self.um.connect(self.modempath, 19200)
        
        # Attach to the events.
        self.um.cst_listeners.append(self.on_cst)
        self.um.rxframe_listeners.append(self.on_rxframe)
        
        # Wait for the settings to be read.
        sleep(1)
        
        # Set PCM appropriately.
        if (bool(self.wakecount % 2)):
            # PCM = 15 on even wakes
            self.um.set_config('PCM', 15)
        else:
            # PCM = 0 on odd wakes
            self.um.set_config('PCM', 0)
        
        # Set the clock
        self.um.set_host_clock_from_modem()
        sleep(1)
        
        # Now, send up as many CST data as we can, using one packet of each rate that we like
        self.send_cst_data(1)
        sleep(20)
        self.send_cst_data(2)
        sleep(20)
        self.send_cst_data(4)
        sleep(20)
        self.send_cst_data(5)
        
        # Wait 3 minutes for replies from the WaveGlider
        sleep(self.reply_timeout_secs)
        
        # Save the CSTS before we turn off
        self.logger.info("Saving CSTs")
        #TODO NOW Put this in a try/catch block
        self.write_csts()
        
        # Now hibernate.
        self.logger.info("Starting hibernate: hib_mins={0} delay={1}".format(self.hibernate_minutes, self.hibernate_delay_secs))
        self.um.start_hibernate(self.hibernate_minutes, self.hibernate_delay_secs)
        sleep(1)
        
        # We're done.  Time to shutdown.
        self.logger.info("Shutting down...")
        os.system('shutdown now')
        sleep(10)
    
    def on_cst(self, cst):
        if not isinstance(cst, CycleStats):
            raise TypeError("BottomNode.on_cst: not a CycleStats object")
        
        # Add this CST to the CST dictionary
        self.csts[cst.packed_timestamp] = cst
        
    def on_rxframe(self, dataframe):
        # Make sure this is a frame for us before we do anything.
        if dataframe.dest != self.um.id:
            self.logger.info("Overheard data frame for " + str(dataframe.dest))
            return
        
        # Now, see if it was an acknowledgment of CST data
        if dataframe.data[0] == 0x31:
            if dataframe.data[1] == 0x21:
                
                # CST ack frame
                # Following the header are a sequence of packed CST timestamps.
                ackbitstream = BitStream(dataframe.data[2:])
                acklist = []
                while ackbitstream.pos < ackbitstream.length:
                    acklist.append(ackbitstream.read('uint:24'))
                    
                # Remove duplicates from the ACK list
                acklist = list(set(acklist))
                
                self.logger.debug("Got " + str(len(acklist)) + " CST ACKs")
                
                removecount = 0
                # When we get an ack, remove the corresponding CST from the dictionary
                for ackitem in acklist:
                    self.logger.debug("=> ACK for " + str(ackitem))
                    if self.csts.has_key(ackitem):
                        #self.logger.info("Got ACK for " + str(ackitem))
                        del self.csts[ackitem]
                        removecount += 1
                
                self.logger.info("Glider Acknowledged " + str(removecount) + " new CSTs")
                        
    
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
        try:
            with open(self.cstpicklepath, 'r') as cstpicklefile:
                self.csts = pickle.load(cstpicklefile)
        except:
            self.logger.error('Error Reading CST Pickle File')
            
        self.logger.debug("Read " + str(len(self.csts)) + " unacknowledged CSTs from file.")
        
    def write_csts(self):
        with open(self.cstpicklepath, 'w') as cstpicklefile:
            pickle.dump(self.csts, cstpicklefile)
            
        self.logger.debug("Wrote " + str(len(self.csts)) + " unacknowledged CSTS to file.")
        
        
    
        

    def send_cst_data(self, rate_num):
        '''Send a packet at the specified rate containing as many unacknowledged CST messages as possible.
        If there are no unacknowledged CST messages, send test frames to ensure that we have full packets.'''
        
        # Make a packet
        thispacket = Packet(CycleInfo(self.um.id, self.gliderid, rate_num))
        
        # how many CSTs do we have to send?
        if len(self.csts) == 0:
            # We have none, so just send test data (with a special header so that we know to respond)
            for frame_num in range(Rates[rate_num].numframes):
                thispacket.append_framedata([0x31, 0x12])
            self.um.send_packet(thispacket)
            return
        
        # We have something to send.  Loop through our CSTs as many times as we can.
        cst_queue_keys = sorted(self.csts.iterkeys(), reverse=True)
        currentidx = 0
        
        # How many CSTS can we send in each frame? (2 bytes are used as a header)
        payloadsize = Rates[rate_num].framesize - 2
        
        csts_per_frame = int(payloadsize / CycleStats.packed_size)
        
        
        for frame_num in range(Rates[rate_num].numframes):
            framedata = bytearray([0x31, 0x11])
            for i in range(csts_per_frame):
                currentidx = currentidx % len(cst_queue_keys)
                packedcst = self.csts[cst_queue_keys[currentidx]].to_packed()
                self.logger.debug("Sending CST: " + str(cst_queue_keys[currentidx]))
                framedata.extend(packedcst.bytes)
                currentidx += 1
                
            # Add this frame to the packet
            thispacket.append_framedata(framedata)
        
        # Send the packet we just created.
        self.um.send_packet(thispacket)
        
        
    def update_wakecount(self):
        # Check our wake count. 
        try:
            wakecountpath = self.logpath + 'wakecount'
            if (os.path.exists(wakecountpath)):
                wakefile = open(wakecountpath, 'r+')
                wakecountstr = wakefile.read()
                self.wakecount = int(wakecountstr) + 1
            else:
                wakefile = open(wakecountpath, 'w')
                self.logger.debug('No wakecount found, setting to 1')
                self.wakecount = 1
            # Now, update the saved wakecount.
            wakefile.seek(0)
            wakefile.write(str(self.wakecount))
            wakefile.truncate()
            wakefile.close()
        except:
            self.logger.error("Error reading/writing wakecount, set to 65535")
            self.wakecount = 65535
            
        self.logger.info("This is wakeup # " + str(self.wakecount))            


if __name__ == '__main__':
    bn = BottomNode()
    bn.start()
    
    