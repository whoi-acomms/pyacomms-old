from acomms import Micromodem, CycleStats
from collections import namedtuple

class TestCase(object):
    name = ""
    
    @property
    def description(self):
        return self.name
    
    def __init__(self, name=None):
        self.name = name

    @property
    def result_text(self):
        return "No Result"
        
class OneToOneUm1DownlinkResults(object):
    RunResult = namedtuple('Result', 'number passed cst')

    def __init__(self):
        self.run_results = []
        self.all_runs_passed = True

    def append_run_result(self, number, passed, cst):
        this_run_result = self.RunResult(number, passed, cst)
        self.run_results.append(this_run_result)
        self.all_runs_passed = self.all_runs_passed and passed

        return this_run_result

    @property
    def num_runs_passed(self):
        return sum([int(run.passed) for run in self.run_results])

    @property
    def num_runs_failed(self):
        return len(self.run_results) - self.num_runs_passed
    
class OneToOneUm1DownlinkCase(TestCase):
    
    @property
    def run_count(self):
        return self._runcount

    @property
    def pass_count(self):
        return self.results.num_runs_passed

    @property
    def fail_count(self):
        return self.results.num_runs_failed

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
                   num_frames = ("max" if self.num_frames is None else self.num_frames))
                   
    
    def __init__(self, tx_modem, rx_modem, timeout=30, rate_num=1, 
                 num_frames=None, name="One-to-one Downlink", 
                 pass_criteria_list=None):
        # These asserts are just here to make Wing do Intellisense
        assert isinstance(tx_modem, Micromodem)
        assert isinstance(rx_modem, Micromodem)    
        
        self._runcount = 0

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
        this_result = self.results.append_run_result(self._runcount, passed, cst)
        
        return this_result
        
        
    @property
    def result_text(self):
        tfmsg = {True:'Pass', False:'Fail', None:'Error'}
        return "{}: {} ({} runs, {} passed, {} failed)".format(self.name, tfmsg[self.results.all_runs_passed],
                                                              self._runcount, self.pass_count, self.fail_count)


        
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
        