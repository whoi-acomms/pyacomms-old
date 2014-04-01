import abc

class ModemConnection(object):
    ''' Abstract class for connecting to a Micromodem via some protocol (such as serial, TCP, etc).
    '''

    metaclass__ = abc.ABCMeta

    @abc.abstractproperty
    def is_connected(self):
        pass

    @abc.abstractproperty
    def can_change_baudrate(self):
        pass

    @abc.abstractmethod
    def change_baudrate(self,baudrate):
        pass

    @abc.abstractmethod
    def _listen(self):
        pass

    @abc.abstractmethod
    def close(self):
        pass

    @abc.abstractmethod
    def write(self,data):
        pass