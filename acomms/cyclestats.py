'''
Created on Jan 23, 2012

@author: Eric
'''
import datetime


class CycleStats(dict):
    '''
    A single set of Receive Cycle Statistics
    '''
    
    # Note that we don't override the dict initalizer.
    
    fields = ('mode', 'toa', 'toa_mode', 
              'mfd_peak', 'mfd_pow', 'mfd_ratio', 'mfd_spl', 
              'agn', 'shift_ain', 'shift_ainp', 'shift_mfd', 'shift_p2b',
              'rate_num', 'src', 'dest', 'psk_error', 'packet_type',
              'num_frames', 'bad_frames_num', 
              'snr_rss', 'snr_in', 'snr_out', 'snr_sym', 
              'mse', 'dqf', 'dop', 'noise', 'carrier', 'bandwidth', 
              'version_number')    
    
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

    #For backward compatibility with classes that directly access the values dict.
    @property
    def values(self):
        return self

        
    def __str__(self):
        ''' Default human-readable version of CycleStats. 
        Doesn't show all parameters, just the most common ones.'''
        hrstr = "{ts}\tRate: {rate_num:.0f}\t".format(
                    ts=self['toa'], rate_num=self['rate_num'])
        if self['rate_num'] is 0:
            hrstr = hrstr + "DQF: {dqf:.0f}\tBad Frames: {bad_frames:.0f}".format(dqf=self['dqf'], bad_frames=self['bad_frames_num'])
        if self['rate_num'] in range(1,7):
            hrstr = hrstr + "PSK Error: {psk_error:.0f}\tBad Frames: {bad_frames:.0f}\tInput SNR: {snr_in:.1f}\tMSE: {mse:.1f}".format(
                        snr_in=self['snr_in'], mse=self['mse'], bad_frames=self['bad_frames_num'], psk_error=self['psk_error'])
                   
        return hrstr
    
    
    @classmethod
    def from_nmea_msg(cls, msg, log_datetime=None, drop_packet_timeout=True):
        
        values = dict.fromkeys(CycleStats.fields)

        
        version_number = int(msg['params'][0])
        if( version_number >=6):
            values['version_number'] = version_number
            values['mode'] = int(msg['params'][1])

            
            # Parse the TOA field into a fractional datetime object.
            whole, fract = str(msg['params'][2]).split('.')
            toa = datetime.datetime.strptime(whole, '%Y%m%d%H%M%S')
            values['toa'] = toa.replace(microsecond = int(fract))
            
            # If we have a PACKET_TIMEOUT, just return with "None" in most fields
            if values['mode'] == 2:
                if drop_packet_timeout:
                    return None
                else:
                    return cls(values)            

            values['toa_mode'] = int(msg['params'][3])
            values['mfd_peak'] = int(msg['params'][4])
            values['mfd_pow'] = int(msg['params'][5])
            values['mfd_ratio'] = int(msg['params'][6])
            values['mfd_spl'] = int(msg['params'][7])
            values['agn'] = int(msg['params'][8])
            values['shift_ain'] = int(msg['params'][9])
            values['shift_ainp'] = int(msg['params'][10])
            values['shift_mfd'] = int(msg['params'][11])
            values['shift_p2b'] = int(msg['params'][12])               
            values['rate_num'] = int(msg['params'][13])
            values['src'] = int(msg['params'][14])
            values['dest'] = int(msg['params'][15])
            values['psk_error'] = int(msg['params'][16])
            values['packet_type'] = int(msg['params'][17])
            values['num_frames'] = int(msg['params'][18])
            values['bad_frames_num'] = int(msg['params'][19])
            values['snr_rss'] = int(msg['params'][20])
            values['snr_in'] = float(msg['params'][21])
            values['snr_out'] = float(msg['params'][22])
            values['snr_sym'] = float(msg['params'][23])
            values['mse'] = float(msg['params'][24])
            values['dqf'] = int(msg['params'][25])
            values['dop'] = float(msg['params'][26])
            values['noise'] = int(msg['params'][27])
            values['carrier'] = int(msg['params'][28])
            values['bandwidth'] = int(msg['params'][29])


        else:
            version_number = 0
            values['mode'] = int(msg['params'][0])
            
            
            if log_datetime is not None:
                values['toa'] = log_datetime
            else:
                # Use today's date, since this version of the CST message doesn't include a date.
                # Also, don't bother parsing the fractional seconds for the uM1.
                toastr = str(msg['params'][1])
                values['toa'] = datetime.datetime.combine(
                    datetime.date.today(), datetime.time(int(toastr[0:2]), 
                                                         int(toastr[2:4]), 
                                                         int(toastr[4:6])))
            
            # If we have a PACKET_TIMEOUT, just return with "None" in most fields
            if values['mode'] == 2:
                if drop_packet_timeout:
                    return None
                else:
                    return cls(values)
            
            values['toa_mode'] = -100
            values['mfd_peak'] = int(msg['params'][3])
            values['mfd_pow'] = int(msg['params'][4])
            values['mfd_ratio'] = int(msg['params'][5])
            values['mfd_spl'] = int(msg['params'][6])
            values['agn'] = int(msg['params'][7])
            values['shift_ain'] = int(msg['params'][8])
            values['shift_ainp'] = int(msg['params'][9])
            values['shift_mfd'] = int(msg['params'][10])
            values['shift_p2b'] = int(msg['params'][11])               
            values['rate_num'] = int(msg['params'][12])
            values['src'] = int(msg['params'][13])
            values['dest'] = int(msg['params'][14])
            values['psk_error'] = int(msg['params'][15])
            values['packet_type'] = int(msg['params'][16])
            values['num_frames'] = int(msg['params'][17])
            values['bad_frames_num'] = int(msg['params'][18])
            values['snr_rss'] = int(msg['params'][19])
            values['snr_in'] = float(msg['params'][20])
            values['snr_out'] = float(msg['params'][21])
            values['snr_sym'] = float(msg['params'][22])
            values['mse'] = float(msg['params'][23])
            values['dqf'] = int(msg['params'][24])
            values['dop'] = float(msg['params'][25])
            if len(msg['params']) >= 27:
                values['noise'] = int(msg['params'][26])
                version_number = 3
            else:
                values['noise'] = -100
            
            if len(msg['params']) >= 28:
                values['carrier'] = int(msg['params'][27])
                values['bandwidth'] = int(msg['params'][28])
                version_number = 4
            else:
                values['carrier'] = 0
                values['bandwidth'] = 0                  
            
            values['version_number'] = version_number
        
                   
        # Make a CycleStats
        cst = cls(values)
    
        return cst

class CycleStatsList(list):
    # We want to do list-ish things, with some extra sauce.
    
    def to_dict_of_lists(self):
        dol = {}        
        for field in CycleStats.fields:
            dol[field] = [cst[field] for cst in self]
        
        return dol

    # This automagically retrieves lists for each parameter when they are referenced as properties.
    # Whether this is awesome or sucks is open to debate.
    def __getattr__(self, item):
        """Maps values to attributes.
        Only called if there *isn't* an attribute with this name
        """
        if item in CycleStats.fields:
            return [cst[item] for cst in self]
        else:
            raise AttributeError(item)
    
            
class TransmitStats(dict):
    '''
    A single set of Receive Cycle Statistics
    '''

    # Note that we don't override the dict initalizer.

    fields = ('time','toa_mode','mode', 'probe_length',
              'bandwidth', 'carrier', 'rate_num', 'src', 'dest',
              'ack', 'num_frames_expected', 'num_frames_sent', 'packet_type',
              'nbytes', 'version_number')

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
        if not self.__dict__.has_key('_TransmitStats__initialized'):  # this test allows attributes to be set in the __init__ method
            return dict.__setattr__(self, item, value)
        elif self.__dict__.has_key(item):       # any normal attributes are handled normally
            dict.__setattr__(self, item, value)
        else:
            self.__setitem__(item, value)

    #For backward compatibility with classes that directly access the values dict.
    @property
    def values(self):
        return self


    def __str__(self):
        ''' Default human-readable version of CycleStats.
        Doesn't show all parameters, just the most common ones.'''
        hrstr = "{ts}\tRate: {rate_num:.0f}\tFrames: {NFSent}/{NFExp}\t# Bytes: {nbytes}".format(
                    ts=self['time'], rate_num=self['rate_num'],
                    NFSent=self['num_frames_sent'],NFExp=self['num_frames_expected'],
                    nbytes=self['nbytes'])
        return hrstr


    @classmethod
    def from_nmea_msg(cls, msg, log_datetime=None, drop_data_timeout=True):

        values = dict.fromkeys(CycleStats.fields)


        version_number = int(msg['params'][0])
        if( version_number ==6):
            values['version_number'] = version_number

            date = datetime.datetime.strptime(str(msg['params'][1]), "%Y%m%d")

            # Parse the time field into a fractional datetime object.
            whole, fract = str(msg['params'][2]).split('.')
            time = datetime.datetime.strptime(whole, '%H%M%S')
            values['time'] = time.replace(year=date.year,month=date.month,day=date.day,microsecond = int(fract))

            values['toa_mode'] = int(msg['params'][3])
            values['mode'] = int(msg['params'][4])
            # If we have a PACKET_TIMEOUT, just return with "None" in most fields
            if values['mode'] == 4:
                if drop_data_timeout:
                    return None
                else:
                    return cls(values)




            values['probe_length'] = int(msg['params'][5])
            values['bandwidth'] = int(msg['params'][6])
            values['carrier'] = int(msg['params'][7])
            values['rate_num'] = int(msg['params'][8])
            values['src'] = int(msg['params'][9])
            values['dest'] = int(msg['params'][10])
            values['ack'] = int(msg['params'][11])
            values['num_frames_expected'] = int(msg['params'][12])
            values['num_frames_sent'] = int(msg['params'][13])
            values['packet_type'] = int(msg['params'][14])
            values['nbytes'] = int(msg['params'][15])

        else:
            version_number = 0
            date = datetime.datetime.strptime(str(msg['params'][0]), "%Y%m%d")

            # Parse the time field into a fractional datetime object.
            whole, fract = str(msg['params'][1]).split('.')
            time = datetime.datetime.strptime(whole, '%H%M%S')
            values['time'] = time.replace(year=date.year,month=date.month,day=date.day,microsecond = int(fract))

            values['toa_mode'] = int(msg['params'][2])
            values['mode'] = int(msg['params'][3])
            # If we have a PACKET_TIMEOUT, just return with "None" in most fields
            if values['mode'] == 4:
                if drop_data_timeout:
                    return None
                else:
                    return cls(values)

            values['probe_length'] = int(msg['params'][4])
            values['bandwidth'] = int(msg['params'][5])
            values['carrier'] = int(msg['params'][6])
            values['rate_num'] = int(msg['params'][7])
            values['src'] = int(msg['params'][8])
            values['dest'] = int(msg['params'][9])
            values['ack'] = int(msg['params'][10])
            values['num_frames_expected'] = int(msg['params'][11])
            values['num_frames_sent'] = int(msg['params'][12])
            values['packet_type'] = int(msg['params'][13])
            values['nbytes'] = int(msg['params'][14])

            values['version_number'] = version_number


        # Make a CycleStats
        xst = cls(values)

        return xst

class TransmitStatsList(list):
    # We want to do list-ish things, with some extra sauce.

    def to_dict_of_lists(self):
        dol = {}
        for field in TransmitStats.fields:
            dol[field] = [xst[field] for xst in self]

        return dol

    # This automagically retrieves lists for each parameter when they are referenced as properties.
    # Whether this is awesome or sucks is open to debate.
    def __getattr__(self, item):
        """Maps values to attributes.
        Only called if there *isn't* an attribute with this name
        """
        if item in TransmitStats.fields:
            return [xst[item] for xst in self]
        else:
            raise AttributeError(item)