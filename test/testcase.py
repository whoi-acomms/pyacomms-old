from acomms import Micromodem, CycleStats
from collections import namedtuple

class TestCase(object):
    name = ""
    
    @property
    def description(self):
        return self.name
    
    def __init__(self, name=None):
        self.name = name
        
class OneToOneUm1DownlinkResults(object):
    RunResult = namedtuple('Result', 'number number_passed number_failed passed cst')
    
    run_results = []
    all_runs_passed = True
    
    def append_run_result(self, number,number_passed, number_failed, passed, cst):
        this_run_result = self.RunResult(number, number_passed, number_failed,passed, cst)
        self.run_results.append(this_run_result)
        self.all_runs_passed = self.all_runs_passed and passed
        
        return this_run_result
    
class OneToOneUm1DownlinkCase(TestCase):
    
    @property
    def runcount(self):
        return self._runcount

    @property
    def passcount(self):
        return self._passcount

    @property
    def failcount(self):
        return self._failcount

    @property
    def description(self):
        return "{tx_modem_name} ({tx_modem_id}) transmits uM1 packet to " \
               "{rx_modem_name} ({rx_modem_id}), rate {rate_num}, " \
               "{num_frames} frames".format(
                   tx_modem_name = self.tx_modem.name,
                   tx_modem_id = self.tx_modem.id,
                   rx_modem_name = self.rx_modem.name,
                   rx_modem_id = self.rx_modem.id,
                   rate_num = self.rate_num,
                   num_frames = self.num_frames)
                   
    
    def __init__(self, tx_modem, rx_modem, timeout=30, rate_num=1, 
                 num_frames=None, name="One-to-one Downlink", 
                 pass_criteria_list=None):
        # These asserts are just here to make Wing do Intellisense
        assert isinstance(tx_modem, Micromodem)
        assert isinstance(rx_modem, Micromodem)    
        
        self._runcount = 0
        self._passcount = 0
        self._failcount = 0

        self.results = OneToOneUm1DownlinkResults()

        self.timeout = timeout
        
        self.tx_modem = tx_modem
        self.rx_modem = rx_modem
        self.rate_num = rate_num
        self.num_frames = num_frames
        self.name = name
        
        if pass_criteria_list is not None:
            self.pass_criteria_list = pass_criteria_list
        else:
            self.pass_criteria_list = []
        
        # Always check the mode
        self.pass_criteria_list.append(('mode', '==', 0))
        
        
    def run(self):
        self._runcount += 1
        
        self.tx_modem.send_test_packet(self.rx_modem.id, rate_num=self.rate_num, num_frames=self.num_frames)
        
        cst = self.rx_modem.wait_for_cst(timeout=self.timeout)
        
        # Do the pass/fail for this run
        if cst is not None:
            passed = check_cst_values(cst, self.pass_criteria_list)
        else:
            passed = False
        
        # store this run result
        if passed == False:
            self._failcount +=1
        else:
            self._passcount +=1

        this_result = self.results.append_run_result(self._runcount, self._passcount, self._failcount, passed, cst)
        
        return this_result
        
        
        
        
        
        


        
def check_cst_values(cst, criteria_list):
    assert isinstance(cst, CycleStats)
    result = True
    # We could return as soon as we get a False result, but we might want to
    # pass the specific failures on in some later implementation.
    for criterion in criteria_list:
        field, operator, value = criterion
        evalstr = "cst['{field}'] {operator} {value}".format(field=field, operator=operator, value=value)
        thisresult = eval(evalstr)
        result = result and thisresult
        
    return result
        