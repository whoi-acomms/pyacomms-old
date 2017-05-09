from acomms import Micromodem, UnifiedLog
from time import sleep

unilog = UnifiedLog(console_log_level='INFO')

modem_a = Micromodem(name="MM1", unified_log=unilog )
modem_a.connect('COM7', 19200)

modem_a.set_config('SRC', 0)

i=0;
send_signals = [41,42,43,44]
receive_signals = [25,26,27,28]
for txsig in send_signals:
    modem_a.send_pgt(txsig,receive_signals[0]+i*5,receive_signals[1]+i*5,receive_signals[2]+i*5,receive_signals[3]+i*5,5000)
    sleep(10)

'''
#REMUS vehicle signals
send_signals = [41,42,43,44]
receive_signals = [21,22,23,24]
i = 0;
for txsig in send_signals:
    modem_a.send_pgt(txsig,receive_signals[0]+i*5,receive_signals[1]+i*5,receive_signals[2]+i*5,receive_signals[3]+i*5,5000)
    i = i+ 1
    sleep(10)

send_signals = [41,42,43,44]
receive_signals = [25,26,27,28]
i = 0;
for txsig in send_signals:
    modem_a.send_pgt(txsig,receive_signals[0]+i*5,receive_signals[1]+i*5,receive_signals[2]+i*5,receive_signals[3]+i*5,5000)
    i = i+ 1
    sleep(10)

send_signals = [40]
receive_signals = [71,72,73,74]
for txsig in send_signals:
    modem_a.send_pgt(txsig,receive_signals[0],receive_signals[1],receive_signals[2],receive_signals[3],5000)
    sleep(10)
    '''