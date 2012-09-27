'''
Created on Feb 16, 2012

@author: Eric
'''
from serial import Serial
from time import sleep

class Ctd(object):
    def __init__(self):
        ctd_serial_path = '/dev/ttyE0'
        
        self.ctd_serialport = Serial(ctd_serial_path, 9600, timeout=1)
        self.ctd_serialport.open()
        
        self.parseloop()
        
        pass
    
    def parseloop(self):
        while (True):
            line = self.ctd_serialport.readline()
            
            if len(line) > 0:
                # try to parse that line
                msgParts = [part.strip() for part in line.split(',')] # splits on commas and removes spaces/CRLF
                
                #Temp (degC), conductivity (S/m), pressure (dBar), PSU, sound speed (m/s), date, time
                depth_m = float(msgParts[2]) * 1.019716
                depth_m_round = int(depth_m)
                
                print("Depth: {0}".format(depth_m_round))
                           
             
        
    

if __name__ == '__main__':
    ctd = Ctd()
    # never returns