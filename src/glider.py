'''
Created on Feb 10, 2012

@author: Eric
'''
import logging
from modem import Micromodem
from cyclestats import CycleStats
from time import sleep

class NodeData(object):
    def __init__(self):
        self.csts = {}
        self.acklist = []
        
        #TODO NOW Read from file
        pass
    
    

class Glider(object):
    '''
    classdocs
    '''


    def __init__(self):
        self.um_10_path = '/dev/ttyS1'
        self.um_3_path = '/dev/ttyS0'
        self.um_array_path = '/dev/ttyE0'
        
        self.logpath = '/var/log/glider/'
        
        self.nodedata = {}
        
        self.csts = {}
    
    def start_log(self):
        # Configure logging
        logformat = logging.Formatter("%(asctime)s\t%(levelname)s\t%(message)s", "%Y-%m-%d %H:%M:%S")
        logger = logging.getLogger("glider")
        logger.setLevel(logging.DEBUG)
        fh = logging.FileHandler('/var/log/glider.log')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logformat)
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(logformat)
        logger.addHandler(fh)
        logger.addHandler(ch)
        
    def on_rxframe(self, dataframe):
        # Make sure this is a frame for us before we do anything.
        if dataframe.dest != self.modem.id:
            self.logger.info("Overheard data frame for " + str(dataframe.dest))
            return
        
        workingdata = dataframe.framedata
        
        # Now, see if it was a CST data frame
        if workingdata[0] == 0x31:
            if workingdata[1] == 0x11:
                # CST frame
                # Get the nodedata object for this node
                # Create one if it doesn't exist.
                if dataframe.src not in self.nodedata:
                    self.nodedata[dataframe.src] = NodeData()
                self.nodedata[dataframe.src]
                
                # Following the header are a sequence of packed CST messages.
                workingdata = workingdata[2:]
                
                while (len(workingdata) >= 13):
                    cstbytes = workingdata[0:13]
                    thecst = CycleStats.from_packed(cstbytes)
                    workingdata = workingdata[13:0]
                    
                    # See if we've already received this one
                    if thecst.packed_timestamp not in self.csts:
                        self.nodedata[dataframe.src].csts[thecst.packed_timestamp] = thecst
                        
                    # Update the ack list.
                    # If this was already in the list, just move it to the end of the list.
                    if thecst.packed_timestamp in self.acklist:
                        self.nodedata[dataframe.src].acklist.remove(thecst.packed_timestamp)    
                    self.nodedata[dataframe.src].acklist.append(thecst.packed_timestamp)
                    
                

if __name__ == '__main__':
    glider = Glider()
    
    um_10 = Micromodem(logpath=(glider.logpath + 'um_10/'))
    um_10.connect(glider.um_10_path, 19200)
    sleep(1)
    
    um_10.set_config('FC0', 10000)
    um_10.set_config('BW0', 2000)
    um_10.set_config('BND', 0)
    
    sleep(1)
    
    um_10.set_host_clock_from_modem()
    
    sleep(1)
    
    # Send some test packets
    um_10.send_test_packet(66, 1)
    
    sleep(10)