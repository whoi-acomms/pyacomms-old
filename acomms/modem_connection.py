import abc

class ModemConnection(object):
    ''' Abstract class for connecting to a Micromodem via some protocol (such as serial, TCP, etc).
    '''

    metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def get_output_voltage(self):
        return

    @abc.abstractmethod
    def get_output_voltage_setting(self):
        return

    @abc.abstractmethod
    def set_output_voltage(self, volts):
        return

    @abc.abstractmethod
    def get_output_current(self):
        return

    @abc.abstractmethod
    def set_output_current(self, amps):
        return

    @abc.abstractmethod
    def get_output_current_setting(self):
        return

    @abc.abstractmethod
    def get_output_enable(self):
        return

    @abc.abstractmethod
    def set_output_enable(self, enabled):
        return

    def enable_output(self):
        self.set_output_enable(True)
        return


    def disable_output(self):
        self.set_output_enable(False)
        return
    