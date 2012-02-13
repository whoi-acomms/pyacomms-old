'''
Created on Jan 23, 2012

@author: Eric
'''
import datetime
import bitstring
import calendar


def clampfixed(n, minn, maxn, decimalplaces):
   
    # "Clip" the value
    cn = max(min(maxn, n), minn)
    
    # Take care of the decimal places problem.
    # The integer conversion rounds down
    cn = int(cn * (10**decimalplaces))
    
    
    # Now, adjust it such that the minimum value == 0
    cminn = int(minn * (10**decimalplaces))
    
    cn = cn - cminn
    
    return cn

def unclampfixed(clamped, minn, decimalplaces):
    # Remove the offset
    cminn = int(minn * (10**decimalplaces))
    
    clamped = clamped + cminn
    
    # Convert to the proper floating-point value
    clamped = float(clamped) / (10 ** decimalplaces)
    
    return clamped


class CycleStats(object):
    '''
    classdocs
    '''
    fields = ('timestamp', 'mfd_pow', 'mfd_ratio', 'rate_num', 'psk_error', 'bad_frames_num', 
              'snr_in', 'snr_out', 'snr_sym', 'mse', 'dop', 'noise')
        
    packfmtstr = '''uint:24=timestamp,
                    uint:10=mfd_pow,
                    uint:15=mfd_ratio,
                    uint:3=rate_num,
                    uint:3=psk_error,
                    uint:4=bad_frames_num,
                    uint:9=snr_in,
                    uint:8=snr_out,
                    uint:5=snr_sym,
                    uint:9=mse,
                    uint:6=dop,
                    uint:8=noise
                    '''
    ts_epoch = datetime.datetime(2012, 2, 1)
    
    packed_size = 13
    
    

    def __init__(self, valuesdict):
        # make sure that the dictionary is complete
        for field in CycleStats.fields:
            if not valuesdict.has_key(field):
                raise KeyError("Invalid dictionary passed to CycleStats constructor.")
        
        self.values = valuesdict    
    
    def get_packed_timestamp(self):
        return (calendar.timegm(self.values['timestamp'].utctimetuple()) - 
                calendar.timegm(CycleStats.ts_epoch.utctimetuple()))
        
    packed_timestamp = property(get_packed_timestamp)
        
    def to_packed(self):
        # Make a neat, binary representation.
        # First, turn the values into range-limited fixed point values.
        
        
        values = self.values
        
        clampvals = dict.fromkeys(CycleStats.fields)
        
        clampvals['timestamp'] = self.get_packed_timestamp()
        
        clampvals['mfd_pow'] = clampfixed(values['mfd_pow'], -30, 40, 0)
        clampvals['mfd_ratio'] = clampfixed(values['mfd_ratio'], 0, 32767, 0)
        clampvals['rate_num'] = clampfixed(values['rate_num'], -1, 6, 0)
        clampvals['psk_error'] = clampfixed(values['psk_error'], 0, 7, 0)
        clampvals['bad_frames_num'] = clampfixed(values['bad_frames_num'], 0, 8, 0)
        clampvals['snr_in'] = clampfixed(values['snr_in'], -10, 30, 1)
        clampvals['snr_out'] = clampfixed(values['snr_out'], 0, 25, 1)
        clampvals['snr_sym'] = clampfixed(values['snr_sym'], 0, 30, 0)
        clampvals['mse'] = clampfixed(values['mse'], -25, 5, 1)
        clampvals['dop'] = clampfixed(values['dop'], -3, 3, 1)
        clampvals['noise'] = clampfixed(values['noise'], 0, 255, 0)
        
        # Now, pack it into a bitstring.
        bs = bitstring.pack(CycleStats.packfmtstr, **clampvals)
        
        
        return bs
        
    @classmethod    
    def from_packed(cls, databytes):
        bs = bitstring.BitStream(databytes)
        packedlist = bs.unpack(CycleStats.packfmtstr)
        
        values = dict.fromkeys(CycleStats.fields)
        
        values['timestamp'] = datetime.datetime.utcfromtimestamp(
                                packedlist[0] + calendar.timegm(CycleStats.ts_epoch.utctimetuple()))
        values['mfd_pow'] = unclampfixed(packedlist[1], -30, 0)
        values['mfd_ratio'] = unclampfixed(packedlist[2], 0, 0)
        values['rate_num'] = unclampfixed(packedlist[3], -1, 0)
        values['psk_error'] = unclampfixed(packedlist[4], 0, 7)
        values['bad_frames_num'] = unclampfixed(packedlist[5], 0, 8)
        values['snr_in'] = unclampfixed(packedlist[6], -10, 1)
        values['snr_out'] = unclampfixed(packedlist[7], 0, 1)
        values['snr_sym'] = unclampfixed(packedlist[8], 0, 0)
        values['mse'] = unclampfixed(packedlist[9], -25, 1)
        values['dop'] = unclampfixed(packedlist[10], -3, 1)
        values['noise'] = unclampfixed(packedlist[11], 0, 0)
        
        self = CycleStats(values)
        return self
    
    @classmethod
    def from_values(cls, toa, mfd_pow, mfd_ratio, rate_num, psk_error, bad_frames_num, snr_in, snr_out, snr_sym, 
                 mse, dop, noise, date=None):
                
        
        
        if date == None:
            date = datetime.date.today()
        
        values = dict.fromkeys(CycleStats.fields)
        
        values['timestamp'] = datetime.datetime.combine(date,
                                         datetime.time(int(toa[0:2]), int(toa[2:4]), int(toa[4:6])))
                                                 
        values['mfd_pow'] = mfd_pow
        values['mfd_ratio'] = mfd_ratio
        values['rate_num'] = rate_num
        values['psk_error'] = psk_error
        values['bad_frames_num'] = bad_frames_num
        values['snr_in'] = float(snr_in)
        values['snr_out'] = snr_out
        values['snr_sym'] = snr_sym
        values['mse'] = mse
        values['dop'] = dop
        values['noise'] = noise
        
        self = CycleStats(values)
        return self
    
        
                