import testcase
from acomms import Micromodem
from time import sleep
from collections import namedtuple
#import plotter

class SimpleTestScript(object):
    
    def run(self):      
        modem_a = Micromodem(name="Modem A", logpath="c:/temp", consolelog='INFO')
        modem_b = Micromodem(name="Modem B", logpath="c:/temp", consolelog='INFO')
        modem_a.connect('COM2', 19200)
        modem_b.connect('COM7', 19200)
        
        sleep(3)
        
        # set up the different test cases
        dl_rate1 = testcase.OneToOneUm1DownlinkCase(
            tx_modem=modem_a, rx_modem=modem_b, timeout=10, rate_num=1, 
            name="Downlink Rate1",  pass_criteria_list=[('snr_in', '>', 40)])
        
        tfmsg = {True:'Pass', False:'Fail', None:'Error'}
        
        for run_num in range(2):
            this_run_result = dl_rate1.run()
            print("{}: {}".format(this_run_result.number, tfmsg[this_run_result.passed]))
            
        print("Completed {} runs, Overall {}".format(dl_rate1.runcount, tfmsg[dl_rate1.results.all_runs_passed]))
        
        self.plot_results(dl_rate1.results)
            
        
    def plot_results(self, dl_results):
        results_list = dl_results.run_results
        plotter.plot_results(results_list)
        

sts = SimpleTestScript()
sts.run()
        
        
        