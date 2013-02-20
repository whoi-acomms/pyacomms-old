import bitstring
import calendar
import datetime
from netaddr.strategy.eui48 import packed_to_int
from acomms import CycleStats

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

class PackedCycleStats(dict):

    packed_fields = ('mode', 'toa', 'mfd_pow', 'mfd_radio', 'rate_num', 'psk_error', 'bad_frames_num', 'snr_in',
                     'snr_out', 'snr_sym', 'mse', 'dop', 'noise')

    packfmtstr = '''uint:32=toa,
                    uint:10=mfd_pow,
                    uint:14=mfd_ratio,
                    uint:3=rate_num,
                    uint:3=psk_error,
                    uint:4=bad_frames_num,
                    uint:9=snr_in,
                    uint:8=snr_out,
                    uint:5=snr_sym,
                    uint:9=mse,
                    uint:6=dop,
                    uint:8=noise,
                    uint:1=mode
                    '''
    
    packed_size = 14

    def to_bitstring(self):
        # Make a neat, binary representation.

        values = self

        # First, turn the values into range-limited fixed point values.
        clampvals = dict.fromkeys(PackedCycleStats.packed_fields)

        clampvals['toa'] = int(calendar.timegm(self['toa'].utctimetuple()))
        clampvals['mfd_pow'] = clampfixed(values['mfd_pow'], -30, 40, 0)
        clampvals['mfd_ratio'] = clampfixed(values['mfd_ratio'], 0, 16383, 0)
        clampvals['rate_num'] = clampfixed(values['rate_num'], -1, 6, 0)
        clampvals['psk_error'] = clampfixed(values['psk_error'], 0, 7, 0)
        clampvals['bad_frames_num'] = clampfixed(values['bad_frames_num'], 0, 8, 0)
        clampvals['snr_in'] = clampfixed(values['snr_in'], -10, 30, 1)
        clampvals['snr_out'] = clampfixed(values['snr_out'], 0, 25, 1)
        clampvals['snr_sym'] = clampfixed(values['snr_sym'], 0, 30, 0)
        clampvals['mse'] = clampfixed(values['mse'], -25, 5, 1)
        clampvals['dop'] = clampfixed(values['dop'], -3, 3, 1)
        clampvals['noise'] = clampfixed(values['noise'], 0, 255, 0)
        clampvals['mode'] = clampfixed(values['mode'], 0, 1, 0)
        
        # Now, pack it into a bitstring.
        bs = bitstring.pack(self.packfmtstr, **clampvals)
        return bs

    def to_bytes(self):
        return self.to_bitstring().tobytes()

    @classmethod
    def from_cyclestats(cls, cyclestats):
        values = dict.fromkeys(PackedCycleStats.packed_fields)
        for key in values:
            values[key] = cyclestats[key]

        self = PackedCycleStats(values)
        return self
        
    @classmethod    
    def from_packed(cls, databytes):
        bs = bitstring.BitStream(databytes)
        packedlist = bs.unpack(PackedCycleStats.packfmtstr)
        
        values = dict.fromkeys(PackedCycleStats.packed_fields)
        
        values['toa'] = datetime.datetime.utcfromtimestamp(packedlist[0])
        values['mfd_pow'] = unclampfixed(packedlist[1], -30, 0)
        values['mfd_ratio'] = unclampfixed(packedlist[2], 0, 0)
        values['rate_num'] = unclampfixed(packedlist[3], -1, 0)
        values['psk_error'] = unclampfixed(packedlist[4], 0, 0)
        values['bad_frames_num'] = unclampfixed(packedlist[5], 0, 0)
        values['snr_in'] = unclampfixed(packedlist[6], -10, 1)
        values['snr_out'] = unclampfixed(packedlist[7], 0, 1)
        values['snr_sym'] = unclampfixed(packedlist[8], 0, 0)
        values['mse'] = unclampfixed(packedlist[9], -25, 1)
        values['dop'] = unclampfixed(packedlist[10], -3, 1)
        values['noise'] = unclampfixed(packedlist[11], 0, 0)
        values['mode'] = unclampfixed(packedlist[12], 0, 0)
        
        self = PackedCycleStats(values)
        return self    