from binascii import hexlify, unhexlify
import exceptions

def data_from_hexstring(hexstring):
    databytes = bytearray()
    try:
        databytes.extend([ord(c) for c in unhexlify(hexstring)])
    #Catch Odd-length String Error
    except exceptions.TypeError:
        pass
    
    return databytes

def hexstring_from_data(databytes):
    return hexlify(bytes(databytes))

class CycleInfo(object):
    def __init__(self, src, dest, rate_num, ack=False, num_frames=None):
        self.src = int(src)
        self.dest = int(dest)
        self.rate_num = int(rate_num)
        self.ack = bool(ack)
        
        if num_frames == None:
            self.num_frames = Rates[rate_num].numframes
        else:
            self.num_frames = int(num_frames)
        
    # This allows us to see if two cycleinfo objects match
    def __eq__(self, other):
        return self.__dict__ == other.__dict__
        
class DrqParams(object):
    def __repr__(self):
        return "SRC: {} DST: {} ACK: {} NUMBYTES: {} FRAME#: {}".format(self.src,self.dest,self.ack,self.num_bytes,self.frame_num)

    def __init__(self, src, dest, ack, num_bytes, frame_num):
        self.src = int(src)
        self.dest = int(dest)
        self.ack = bool(ack)
        self.num_bytes = int(num_bytes)
        self.frame_num = int(frame_num)
        
class Ack(object):
    def __repr__(self):
        return "SRC: {} DST: {} FRAME#: {}".format(self.src,self.dest,self.frame_num)

    def __init__(self, src, dest, ack, frame_num):
        self.src = int(src)
        self.dest = int(dest)
        self.ack = bool(ack)
        self.frame_num = int(frame_num)



class DataFrame(object):
    def __init__(self, src, dest, ack, frame_num, data, bad_crc=False):
        self.bad_crc = bad_crc
        self.src = src
        self.dest = dest
        self.ack = ack
        self.frame_num = frame_num
        if data:
            self.data = bytearray(data)
        else:
            self.data = None

    def __repr__(self):
        return "SRC: {} DST: {} ACK: {} FRAME#: {} BAD_CRC: {} DATA: {}".format(self.src,self.dest,self.ack,self.frame_num, self.bad_crc, repr(self.data))
        
class Packet(object):
    def __init__(self, cycleinfo, frames=None):
        self.cycleinfo = cycleinfo
        
        if frames != None:
            self.frames = frames
        else:
            self.frames = []
            
    def append_framedata(self, framedata):
        #TODO: Make sure we have room for another frame, and that the data fits in the frame.
        newframe = DataFrame(self.cycleinfo.src, self.cycleinfo.dest, self.cycleinfo.ack, 
                             (len(self.frames) + 1), framedata)
        self.frames.append(newframe)
            
        
class PacketRate(object):
    def __init__(self, name, number, framesize, numframes):
        self.name = name
        self.number = number
        self.framesize = framesize
        self.numframes = numframes
    
    def getpacketsize(self):
        return self.framesize * self.numframes
        
    maxpacketsize = property(getpacketsize)

Rates = {0:PacketRate('FH-FSK', 0, 32, 1),
         1:PacketRate('BCH 128:8', 1, 64, 3),
         2:PacketRate('DSS 1/15 (64B frames)', 2, 64, 3),
         3:PacketRate('DSS 1/7', 3, 256, 2),
         4:PacketRate('BCH 64:10', 4, 256, 2),
         5:PacketRate('Hamming 14:9', 5, 256, 8),
         6:PacketRate('DSS 1/15 (32B frames)', 6, 32, 6)}

FDPRates = {1:PacketRate('BCH 128:8', 1, 100, 1),
            3:PacketRate('BCH 64:10', 3, 100, 1)}


    