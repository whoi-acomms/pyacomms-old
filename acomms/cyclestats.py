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


class CycleStats(dict):
    '''
    A single set of Receive Cycle Statistics
    '''
    
    # This automagically retrieves values from the dictionary when they are referenced as properties.
    # Whether this is awesome or sucks is open to debate.
    def __getattr__(self, item):
        """Maps values to attributes.
        Only called if there *isn't* an attribute with this name
        """
        try:
            return self.__getitem__(item)
        except KeyError:
            raise AttributeError(item)
        
    def __setattr__(self, item, value):
        """Maps attributes to values.
        Only if we are initialised
        """
        if not self.__dict__.has_key('_CycleStats__initialized'):  # this test allows attributes to be set in the __init__ method
            return dict.__setattr__(self, item, value)
        elif self.__dict__.has_key(item):       # any normal attributes are handled normally
            dict.__setattr__(self, item, value)
        else:
            self.__setitem__(item, value)    
    
    
    
    
    fields = ('mode', 'toa', 'toa_mode', 'mfd_pow', 'mfd_ratio', 'rate_num', 'psk_error', 'bad_frames_num', 
              'snr_in', 'snr_out', 'snr_sym', 'mse', 'dop', 'noise', 'pcm_on')
        
    packfmtstr = '''uint:24=toa,
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
                    bool=pcm_on
                    '''
    ts_epoch = datetime.datetime(2012, 10, 1)
    
    packed_size = 13
    
    #For backward compatibility with classes that directly access the values dict.
    @property
    def values(self):
        return self
    
    # We use the default dictionary initializer
    '''
    def __init__(self, valuesdict):
        # make sure that the dictionary is complete
        for field in CycleStats.fields:
            if not valuesdict.has_key(field):
                raise KeyError("Invalid dictionary passed to CycleStats constructor.")
        
        self.values = valuesdict
    '''    
        
    def __str__(self):
        hrstr = "{ts} Rate: {rate_num:.0f}\t PSK Error: {psk_error:.0f}\tBad Frames: {bad_frames:.0f}\tInput SNR: {snr_in:.1f}\tMSE: {mse:.1f}".format(
                    ts=self.values['toa'], rate_num=self.values['rate_num'], snr_in=self.values['snr_in'], 
                     mse=self.values['mse'], bad_frames=(self.values['bad_frames_num']*10e7), psk_error=(self.values['psk_error']*10e6))
        return hrstr
    
    def get_packed_timestamp(self):
        return (calendar.timegm(self.values['toa'].utctimetuple()) - 
                calendar.timegm(CycleStats.ts_epoch.utctimetuple()))
        
    packed_timestamp = property(get_packed_timestamp)
        
    def to_packed(self):
        # Make a neat, binary representation.
        # First, turn the values into range-limited fixed point values.
        
        
        values = self.values
        
        clampvals = dict.fromkeys(CycleStats.fields)
        
        clampvals['toa'] = self.get_packed_timestamp()
        
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
        clampvals['pcm_on'] = values['pcm_on']
        
        # Now, pack it into a bitstring.
        bs = bitstring.pack(CycleStats.packfmtstr, **clampvals)
        
        
        return bs
        
    @classmethod    
    def from_packed(cls, databytes):
        bs = bitstring.BitStream(databytes)
        packedlist = bs.unpack(CycleStats.packfmtstr)
        
        values = dict.fromkeys(CycleStats.fields)
        
        values['toa'] = datetime.datetime.utcfromtimestamp(
                                packedlist[0] + calendar.timegm(CycleStats.ts_epoch.utctimetuple()))
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
        values['pcm_on'] = bool(packedlist[12])
        
        self = CycleStats(values)
        return self
    
    @classmethod
    def from_values(cls, mode, toa, toa_mode, mfd_pow, mfd_ratio, rate_num, psk_error, bad_frames_num, snr_in, snr_out, snr_sym, 
                 mse, dop, noise, pcm_on=False):
                
       
        values = dict.fromkeys(CycleStats.fields)
        
        values['mode'] = mode
        values['toa'] = toa
        values['toa_mode'] = toa_mode
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
        values['pcm_on'] = pcm_on
        
        self = CycleStats(values)
        return self
    
    @classmethod
    def from_nmea_msg(cls, msg, log_datetime=None):
    
        versionNumber = int(msg['params'][0])
        if( versionNumber >=6):
            mode = int(msg['params'][1])
            # Discard any PACKET_TIMEOUT CSTs for now
            if mode == 2:
                return
            
            # Parse the TOA field into a fractional datetime object.
            whole, fract = str(msg['params'][2]).split('.')
            toa = datetime.datetime.strptime(whole, '%Y%m%d%H%M%S')
            toa = toa.replace(microsecond = int(fract))
            
            toa_mode = int(msg['params'][3])
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
            
            if log_datetime is not None:
                toa = log_datetime
            else:
                # Use today's date, since this version of the CST message doesn't include a date.
                # Also, don't bother parsing the fractional seconds for the uM1.
                toastr = str(msg['params'][1])
                toa = datetime.datetime.combine(datetime.date.today() ,datetime.time(int(toastr[0:2]), int(toastr[2:4]), int(toastr[4:6])))                
            toa_mode = -100
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
        cst = CycleStats.from_values(mode, toa, toa_mode, mfd_pow, mfd_ratio, rate_num, psk_error, bad_frames_num, 
                                     snr_in, snr_out, snr_sym, mse, dop, noise)
    
        return cst

class CycleStatsList(list):
    # We want to do list-ish things, with some extra sauce.
    
    def to_dict_of_lists(self):
        dol = {}        
        for field in CycleStats.fields:
            dol[field] = [cst[field] for cst in self]
        
        return dol
    
    
            
    