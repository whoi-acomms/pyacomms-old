import testcase
from acomms import Micromodem
from time import sleep

class DownlinkTestScript(object):
    
    def run(self, num_runs=1):
        modem_a = Micromodem(name="Modem A", logpath="c:/temp", consolelog='INFO')
        modem_b = Micromodem(name="Modem B", logpath="c:/temp", consolelog='INFO')
        modem_a.connect('COM14', 19200)
        modem_b.connect('COM15', 19200)
        
        sleep(3)
        
        # set up the different test cases
        #dl_rate0 = testcase.OneToOneUm1DownlinkCase(
        #    tx_modem=modem_a, rx_modem=modem_b, timeout=20, rate_num=0,
         #   name="Downlink Rate0",  pass_criteria_list=[('dqf', '>', 240)])

        rates_to_test = [1,2,3,4,5]
        dl_cases = {}

        # Set up the test case for each rate.
        for rate in rates_to_test:
            dl_cases[rate] = testcase.OneToOneUm1DownlinkCase(
                tx_modem=modem_a, rx_modem=modem_b, timeout=20, rate_num=rate,
                name="Downlink Rate {}".format(rate),  pass_criteria_list=[('mse', '<', -14)])

        # Run each case the specified number of times.
        for run_num in range(num_runs):
            for rate in rates_to_test:
                dl_cases[rate].run()

        # Print the results.
        for rate in rates_to_test:
            print(dl_cases[rate].result_text)



sts = DownlinkTestScript()
sts.run(num_runs=20)
        
        
        