'''
Created on Feb 10, 2012

@author: Eric
'''
import logging
from modem import Micromodem
from messageparams import Packet, CycleInfo, Rates
from cyclestats import CycleStats
from time import sleep
from threading import Thread
import bitstring
import pickle
import sys

class NodeData(object):
    def __init__(self):
        self.csts = {}
        self.csts[0] = CycleStats.from_values('000000', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, False, CycleStats.ts_epoch)
        self.acklist = []
        
        #TODO NOW Read from file
        pass
    
    

class Glider(object):
    def __init__(self):
        self.gliderid = 10
        
        #self.um_10_path = '/dev/ttyS1'
        self.um_10_path = 'COM10'
        
        self.um_3_path = '/dev/ttyS0'
        #self.um_array_path = '/dev/ttyE0'
        self.um_array_path = 'COM12'
        
        #self.logpath = '/var/log/glider/'
        self.logpath = 'c:/temp/glider/'
        self.start_log()
        
        self.syncpath = '/media/card/sync/'
        self.syncpath = 'c:/temp/glider/'
        
        self.cstlogpath = self.syncpath + 'cst.log'
        
        self.nodedata_picklepath = self.syncpath + 'nodedata.pickle'
        self.nodedata_array_picklepath = self.syncpath + 'nodedata_array.pickle'
        
        self.reply_delay_secs = 90
        
        self.nodedata = {}
        self.nodedata_array = {}
        
        self.load_nodedata()
        self.load_nodedata_array()
        
        self.ackthread = None
        
        self.modem = Micromodem(name='modem-10k', logpath=(self.logpath))
        self.arraymodem = Micromodem(name='modem-array', logpath=(self.logpath))
        
        self.start_cst_log()
        
    
    
    def start_log(self):
        # Configure logging
        logformat = logging.Formatter("%(asctime)s\t%(levelname)s\t%(message)s", "%Y-%m-%d %H:%M:%S")
        self.logger = logging.getLogger("glider")
        self.logger.setLevel(logging.DEBUG)
        fh = logging.FileHandler(self.logpath + 'glider.log')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logformat)
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(logformat)
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)
        
    def start_cst_log(self):
        cst_logformat = logging.Formatter('%(asctime)s\t%(name)s\t%(message)s', "%Y-%m-%d %H:%M:%S")
        
        self.cstlog_10k = logging.getLogger("cst-10k")
        self.cstlog_10k.setLevel(logging.INFO)
        self.cstlog_array = logging.getLogger("cst-array")
        self.cstlog_array.setLevel(logging.INFO)
        
        fh = logging.FileHandler(self.cstlogpath)
        fh.setLevel(logging.INFO)
        fh.setFormatter(cst_logformat)
        
        self.cstlog_10k.addHandler(fh)
        self.cstlog_array.addHandler(fh)
        
        
        
    def start_cst_processing(self):
        
        # Connect the listeners
        self.modem.rxframe_listeners.append(self.on_rxframe)
        self.modem.cst_listeners.append(self.on_cst_10k)
        
        self.modem.connect(self.um_10_path, 19200)
        
        # Just to be safe...
        self.modem.set_config('SRC', self.gliderid)
        sleep(1)
        
        # Connect to the array and start logging
        self.arraymodem.cst_listeners.append(self.on_cst_array)
        self.arraymodem.rxframe_listeners.append(self.on_rxframe_array)
        self.arraymodem.connect(self.um_array_path, 19200)
        sleep(1)
        
        
        # Everything is now event driven.
        while (True):
            sleep(1)
        
        
    def on_cst_10k(self, cst, msg):
        # Just log the full CST message
        self.cstlog_10k.info(msg['raw'].strip())
    
    def on_cst_array(self, cst, msg):
        self.cstlog_array.info(msg['raw'].strip())
        
    def on_rxframe_array(self, dataframe):
        # we just decode and save the data... we don't reply here.
        # Make sure this is a frame for us before we do anything.
        if dataframe.dest != self.gliderid:
            self.logger.debug("Array overheard data frame for " + str(dataframe.dest))
            return
        
        workingdata = dataframe.data
        
        # Now, see if it was a CST data frame
        if workingdata[0] == 0x31:
            self.logger.debug("Array received frame from node " + str(dataframe.src))
            
                        
            if workingdata[1] == 0x11:
                
                # CST frame
                # Get the nodedata object for this node
                # Create one if it doesn't exist.
                if dataframe.src not in self.nodedata_array:
                    self.nodedata_array[dataframe.src] = NodeData()
                self.nodedata_array[dataframe.src]
                
                # Following the header are a sequence of packed CST messages.
                workingdata = workingdata[2:]
                
                while (len(workingdata) >= 13):
                    cstbytes = workingdata[0:13]
                    thecst = CycleStats.from_packed(cstbytes)
                    workingdata = workingdata[13:]
                    
                    # See if we've already received this one
                    if thecst.packed_timestamp not in self.nodedata_array[dataframe.src].csts:
                        self.nodedata_array[dataframe.src].csts[thecst.packed_timestamp] = thecst
                        self.logger.debug("Array Got new CST: " + str(thecst.packed_timestamp))
                    else:
                        self.logger.debug("Array Got duplicate CST: " + str(thecst.packed_timestamp))
                
                # Save the file.
                self.save_nodedata_array()
                        
      
        
        
    def on_rxframe(self, dataframe):
        # Make sure this is a frame for us before we do anything.
        if dataframe.dest != self.modem.id:
            self.logger.debug("Overheard data frame for " + str(dataframe.dest))
            return
        
        workingdata = dataframe.data
        
        # Now, see if it was a CST data frame
        if workingdata[0] == 0x31:
            self.logger.debug("Received frame from node " + str(dataframe.src))
            
            # This is a message from the bottom node, and we should send a reply.
            # If we aren't already planning to send one, schedule it now.
            self.schedule_reply(dataframe.src, self.reply_delay_secs)
            
            if workingdata[1] == 0x11:
                
                # CST frame
                # Get the nodedata object for this node
                # Create one if it doesn't exist.
                if dataframe.src not in self.nodedata:
                    self.nodedata[dataframe.src] = NodeData()
                
                
                # Following the header are a sequence of packed CST messages.
                workingdata = workingdata[2:]
                
                while (len(workingdata) >= 13):
                    cstbytes = workingdata[0:13]
                    thecst = CycleStats.from_packed(cstbytes)
                    workingdata = workingdata[13:]
                    
                    # See if we've already received this one
                    if thecst.packed_timestamp not in self.nodedata[dataframe.src].csts:
                        self.nodedata[dataframe.src].csts[thecst.packed_timestamp] = thecst
                        self.logger.debug("Got new CST: " + str(thecst.packed_timestamp))
                    else:
                        self.logger.debug("Got duplicate CST: " + str(thecst.packed_timestamp))
                        
                    # Update the ack list, inserting the new entry at the top
                    # If this was already in the list, just move it to the top of the list.
                    if thecst.packed_timestamp in self.nodedata[dataframe.src].acklist:
                        self.nodedata[dataframe.src].acklist.remove(thecst.packed_timestamp)    
                    self.nodedata[dataframe.src].acklist.insert(0, thecst.packed_timestamp)
                    
                # Save this one to the file.
                self.save_nodedata()
                    
    def schedule_reply(self, node_id, delay_secs=90):
        # Are we already planning to do this?
        # Is the thread already running?
        if self.ackthread != None:
            if self.ackthread.isAlive():
                # Don't start it again...
                self.logger.debug('ACK thread already started')
                return
        
        self.ackthread = Thread(target=self.do_acks, args=(node_id, delay_secs))
        self.ackthread.setDaemon(True)
        
        self.logger.debug("Starting ACK reply thread")
        self.ackthread.start()
        

    def do_acks(self, node_id, delay_secs):
        self.logger.debug("ACK reply thread started")
        # Wait the appropriate number of seconds and then transmit the replies
        sleep(delay_secs)
        
        self.logger.debug("Transmitting ACK Packets")
        
        self.transmit_acks(node_id, 1)
        sleep(20)
        self.transmit_acks(node_id, 2)
        sleep(20)
        self.transmit_acks(node_id, 4)
        sleep(20)
        self.transmit_acks(node_id, 5)
        
    def transmit_acks(self, node_id, rate_num=1):
        # Make a packet
        thispacket = Packet(CycleInfo(self.modem.id, node_id, rate_num))
        
        # Do we have at least one ACK to send
        if node_id in self.nodedata.keys():
            if len(self.nodedata[node_id].csts) == 0:
                # We have none, so just send a test packet
                self.modem.send_test_packet(node_id, rate_num)
                return
        
        
        currentidx = 0
        
        # How many acks can we send in each frame? (2 bytes are used as a header)
        payloadsize = Rates[rate_num].framesize - 2
      
        acks_per_frame = int(payloadsize / 3) # 3 bytes per ack        
        
        for frame_num in range(Rates[rate_num].numframes):
            framedata = bytearray([0x31, 0x21])
            for i in range(acks_per_frame):
                # Pack each one into 3 bytes
                currentidx = currentidx % len(self.nodedata[node_id].acklist)
                currentack = (bitstring.pack('uint:24', self.nodedata[node_id].acklist[currentidx]).tobytes())
                framedata.extend(currentack)
                currentidx += 1
                
            # Add this frame to the packet
            thispacket.append_framedata(framedata)
        
        # Send the packet we just created.
        self.modem.send_packet(thispacket)
        
    def save_nodedata(self):
        with open(self.nodedata_picklepath, 'wb') as cstpicklefile:
            pickle.dump(self.nodedata, cstpicklefile, protocol=2)
            
        self.logger.debug("Saved nodedata")
    
    def save_nodedata_array(self):
        with open(self.nodedata_array_picklepath, 'wb') as cstpicklefile:
            pickle.dump(self.nodedata_array, cstpicklefile, protocol=2)
            
        self.logger.debug("Saved array nodedata")
        
    def load_nodedata(self, picklepath=None):
        if picklepath == None:
            picklepath = self.nodedata_picklepath
        
        try:
            with open(self.nodedata_picklepath, 'rb') as cstpicklefile:
                self.nodedata = pickle.load(cstpicklefile)
                self.logger.debug("Read nodedata file.")
        except:
            self.logger.exception('Error Reading nodedata File')
            
        
    
    def load_nodedata_array(self):
        try:
            with open(self.nodedata_array_picklepath, 'rb') as cstpicklefile:
                self.nodedata_array = pickle.load(cstpicklefile)
                self.logger.debug("Read nodedata_array file.")
        except:
            self.logger.error('Error Reading nodedata_array File')
            
    def print_nodedata(self):
        print("3013 RX Data")
        for key in self.nodedata.keys():
            print("Node {0} ({1} CSTS):".format(key, len(self.nodedata[key].csts)))
            for cstkey in sorted(self.nodedata[key].csts.iterkeys()):
                print(self.nodedata[key].csts[cstkey])
                
        print("Array RX Data")
        for key in self.nodedata_array.keys():
            print("Node {0}:".format(key))
            for cstkey in sorted(self.nodedata[key].csts.iterkeys()):
                print(self.nodedata[key].csts[cstkey])
        
    

if __name__ == '__main__':
    glider = Glider()
    
    if 'shore' not in sys.argv:  
        glider.start_cst_processing()
    else:
        glider.print_nodedata()