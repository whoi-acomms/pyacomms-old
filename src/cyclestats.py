'''
Created on Jan 23, 2012

@author: Eric
'''
import datetime
import bitstring


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
    


    def __init__(self, toa, mfd_pow, mfd_ratio, rate_num, psk_error, bad_frames_num, snr_in, snr_out, snr_sym, 
                 mse, dop, noise, date=None):
        '''
        Constructor
        '''
        
        if date == None:
            date = datetime.date.today()
        
        self.date = date
        self.toa = toa
        self.mfd_pow = mfd_pow
        self.mfd_ratio = mfd_ratio
        self.rate_num = rate_num
        self.psk_error = psk_error
        self.bad_frames_num = bad_frames_num
        self.snr_in = decimal(snr_in)
        self.snr_out = snr_out
        self.snr_sym = snr_sym
        self.mse = mse
        self.dop = dop
        self.noise = noise
        
    def to_packed(self):
        # Make a neat, binary representation.
        # First, turn the values into range-limited fixed point values.
        
        
        
    def from_packed(self):
        
        pass
    

    
        
                