__author__ = 'andrew'

from timeutil import *


class ModemLog(dict):
        fields = ('finished', 'message_number', 'datetime',
              'logged_message')

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
            ''' Default human-readable version of ModemLog.
            Doesn't show all parameters, just the most useful ones.'''
            hrstr = "{dt}\tMessage: {msg}\t".format(
                        dt=self['datetime'], msg=self['logged_message'])

            return hrstr

        @classmethod
        def from_nmea_msg(cls, msg):

            values = dict.fromkeys(ModemLog.fields)
            values['finished'] = int(msg["params"][0])
            values['message_number'] = int(msg["params"][1])
            values['datetime']= convert_to_datetime(msg["params"][2])
            values['logged_message'] = (msg["params"][3:])

            log = cls(values)
            return log
