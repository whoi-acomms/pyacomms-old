__author__ = 'andrew'

import abc

class NmeaListener(object):
    ''' Abstract class for connecting for processing Nmea Message via some connection (such as serial, TCP, etc).
    '''

    metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def _process_outgoing_nmea(self):
        pass

    @abc.abstractmethod
    def _process_incoming_nmea(self, msg):
        pass


    @abc.abstractmethod
    def _message_waiting(self):
        pass
