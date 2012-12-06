'''
Created on Dec 6, 2012

@author: andrew
'''
import argparse
import traceback
import re, os
from acomms import CycleStats, Message, ChecksumException

class NMEACSTParser():
    def __init__(self):
        self.cst_listeners = []
    
    def parseFile(self, fi):
        f = open(fi,'r');
        for line in f:
            try:
                msg = Message(line.strip('\r\n'))
            except ChecksumException:
                print line.strip('\r\n')
                continue
            self.parse(msg)
        f.close()
    
    def parse(self, msg):
        try:
            func = getattr(self, msg['type'])
        except AttributeError, e:
            #self.modem.daemonlog.warn('Unrecognized message: ' + str(msg['type']))
            func = None
        try:
            if func != None:
                return func(msg)
        except Exception, e:
            #self.modem.daemonlog.error("Exception when parsing: " + str(sys.exc_info()[0]))
            traceback.print_exc()

    def CACST(self, msg):
        try:
            versionNumber = int(msg['params'][0])
            if( versionNumber >=6):
                mode = int(msg['params'][1])
                # Discard any PACKET_TIMEOUT CSTs for now
                if mode == 2:
                    return
                
                toa = str(msg['params'][2])
                toaMode = int(msg['params'][3])
                mfd_peak = int(msg['params'][4])
                mfd_pow = int(msg['params'][5])
                mfd_ratio = int(msg['params'][6])
                mfdSpl= int(msg['params'][7])
                shfAgn = int(msg['params'][8])
                ainShift = int(msg['params'][9])
                ainPShift = int(msg['params'][10])
                mfdShift = int(msg['params'][11])
                p2bshift = int(msg['params'][12])               
                rate_num = int(msg['params'][13])
                src = int(msg['params'][14])
                dest = int(msg['params'][15])
                psk_error = int(msg['params'][16])
                packetType = int(msg['params'][17])
                nFrames = int(msg['params'][18])
                bad_frames_num = int(msg['params'][19])
                snrRss = int(msg['params'][20])
                snr_in = float(msg['params'][21])
                snr_out = float(msg['params'][22])
                snr_sym = float(msg['params'][23])
                mse = float(msg['params'][24])
                dqf = int(msg['params'][25])
                dop = float(msg['params'][26])
                noise = int(msg['params'][27])
                carrier = int(msg['params'][28])
                bandwidth = int(msg['params'][29])


            else:             
                mode = int(msg['params'][0])
                # Discard any PACKET_TIMEOUT CSTs for now
                if mode == 2:
                    return
                
                toa = str(msg['params'][1])
                mfd_pow = int(msg['params'][4])
                mfd_ratio = int(msg['params'][5])
                rate_num = int(msg['params'][12])
                psk_error = int(msg['params'][15])
                bad_frames_num = int(msg['params'][18])
                snr_in = float(msg['params'][20])
                snr_out = float(msg['params'][21])
                snr_sym = float(msg['params'][22])
                mse = float(msg['params'][23])
                dop = float(msg['params'][25])
                
                noise = int(msg['params'][26])
            
            # Make a CycleStats
            cst = CycleStats.from_values(toa, mfd_pow, mfd_ratio, rate_num, psk_error, bad_frames_num, 
                                         snr_in, snr_out, snr_sym, mse, dop, noise, pcm_on=False)
        except :
            cst = None
            
        
        # Raise the event
        self.on_cst(cst, msg)
        
    def on_cst(self, cst, msg):
        for func in self.cst_listeners:
            func(cst, msg) # Pass on the CST message.        
    
    def registerListener(self,func):
        self.cst_listeners.append(func)

class ModemTMACSTParser():
    def __init__(self):
        self.NMEAParser = NMEACSTParser()

        
    
    def parseFile(self, fi):
        f = open(fi,'r');
        for line in f:
            for token in re.split('RX,',line):
                if token[0] == '$':
                    try:
                        msg = Message(token.strip('\r\n'))
                    except ChecksumException:
                        print token.strip('\r\n')
                        continue
                    self.NMEAParser.parse(msg)
        f.close()
    
    def registerListener(self,func):
        self.NMEAParser.registerListener(func)
        
class FileCSTParser():
    def __init__(self):
        self.NMEAParser = NMEACSTParser()

    def parseFile(self, fi):
        f = open(fi,'r');
        for line in f:
            if '$' in line:
                data = line[line.find("$"):line.find("*")]
                try:
                    msg =  Message(data.strip())
                except ChecksumException:
                    print data
                    continue                
                self.NMEAParser.parse(msg)
        f.close()
        
    def registerListener(self,func):
        self.NMEAParser.registerListener(func)
    

def printCSTData(cst, msg):
    print cst

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process Files Containing CST Messages.')
    parser.add_argument('FileType', default='RawNMEA',choices=['RawNMEA','ModemTMA','Other'], help='Type of File to Be processed (RawNMEA,ModemTMA,Other)', metavar='Type')
    parser.add_argument('Filename', help='File to be processed')
    
    args = parser.parse_args()
    
    print args
    
    Parser = None
    
    if args.FileType == 'RawNMEA':
        Parser = NMEACSTParser()
    elif args.FileType == 'ModemTMA':
        Parser = ModemTMACSTParser()
    elif args.FileType == 'Other':
        Parser = FileCSTParser()
        
    print str(Parser)    
    
    Parser.registerListener(printCSTData)
    
    if Parser != None and os.path.exists(args.Filename):
        print "Parsing File"
        Parser.parseFile(args.Filename)
    
    
    