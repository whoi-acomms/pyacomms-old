import testcase
from acomms import Micromodem
from time import sleep
from collections import namedtuple
#import plotter

class SimpleTestScript(object):
    
    def run(self):      
        modem_a = Micromodem(name="Modem A", logpath="c:/temp", consolelog='INFO')
        modem_b = Micromodem(name="Modem B", logpath="c:/temp", consolelog='INFO')
        modem_a.connect('COM7', 19200)
        modem_b.connect('COM2', 19200)
        
        sleep(3)
        
        # set up the different test cases
        #dl_rate0 = testcase.OneToOneUm1DownlinkCase(
        #    tx_modem=modem_a, rx_modem=modem_b, timeout=20, rate_num=0,
         #   name="Downlink Rate0",  pass_criteria_list=[('dqf', '>', 240)])
        dl_rate1 = testcase.OneToOneUm1DownlinkCase(
            tx_modem=modem_a, rx_modem=modem_b, timeout=20, rate_num=1,
            name="Downlink Rate1",  pass_criteria_list=[('mse', '<', -18)])
        dl_rate2 = testcase.OneToOneUm1DownlinkCase(
            tx_modem=modem_a, rx_modem=modem_b, timeout=20, rate_num=2,
            name="Downlink Rate2",  pass_criteria_list=[('mse', '<', -18)])
        dl_rate3 = testcase.OneToOneUm1DownlinkCase(
            tx_modem=modem_a, rx_modem=modem_b, timeout=20, rate_num=3,
            name="Downlink Rate3",  pass_criteria_list=[('mse', '<', -18)])
        dl_rate4 = testcase.OneToOneUm1DownlinkCase(
            tx_modem=modem_a, rx_modem=modem_b, timeout=20, rate_num=4,
            name="Downlink Rate4",  pass_criteria_list=[('mse', '<', -18)])
        dl_rate5 = testcase.OneToOneUm1DownlinkCase(
            tx_modem=modem_a, rx_modem=modem_b, timeout=20, rate_num=5,
            name="Downlink Rate5",  pass_criteria_list=[('mse', '<', -18)])
        dl_rate6 = testcase.OneToOneUm1DownlinkCase(
            tx_modem=modem_a, rx_modem=modem_b, timeout=20, rate_num=6,
            name="Downlink Rate6",  pass_criteria_list=[('mse', '<', -18)])

        tfmsg = {True:'Pass', False:'Fail', None:'Error'}
        
        for run_num in range(2):
         #   run0_result = dl_rate0.run()
            run1_result = dl_rate1.run()
            run2_result = dl_rate2.run()
            run3_result = dl_rate3.run()
            run4_result = dl_rate4.run()
            run5_result = dl_rate5.run()
            run6_result = dl_rate6.run()

        print(run1_result)
        #print("Rate 0: Completed {} runs, Overall {}".format(dl_rate0.runcount, tfmsg[dl_rate0.results.all_runs_passed]))
        print("Rate 1: Completed {} runs, passed {}, failed {}".format(dl_rate1.runcount, dl_rate1.passcount, dl_rate1.failcount))
        print("Rate 2: Completed {} runs, passed {}, failed {}".format(dl_rate2.runcount, dl_rate2.passcount, dl_rate2.failcount))
        print("Rate 3: Completed {} runs, passed {}, failed {}".format(dl_rate3.runcount, dl_rate3.passcount, dl_rate3.failcount))
        print("Rate 4: Completed {} runs, passed {}, failed {}".format(dl_rate4.runcount, dl_rate4.passcount, dl_rate4.failcount))
        print("Rate 5: Completed {} runs, passed {}, failed {}".format(dl_rate5.runcount, dl_rate5.passcount, dl_rate5.failcount))
        print("Rate 6: Completed {} runs, passed {}, failed {}".format(dl_rate6.runcount, dl_rate6.passcount, dl_rate6.failcount))



sts = SimpleTestScript()
sts.run()
        
        
        