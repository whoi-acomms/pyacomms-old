'''
Created on Feb 1, 2012

@author: Eric
'''

from time import sleep
from threading import Thread


class Testing(object):
    
    def __init__(self):
        self.thread = Thread( target=self.listen )
        
    def start(self):
        if not self.thread.isAlive(): self.thread.start()
    
    def listen(self):
        while(True):
            sleep(1)
            
            self.changestate(StateClass)
        
    def changestate(self, newstate):
        self.state = newstate(ref=self)
        print "Changed state to " + str(self.state)
        self.state.entering()
        
    
class StateClass(object):
    def __init__(self, ref):
        pass

    def entering(self):
        raise Exception('Nobody expects the Spanish Exception!')
    

if __name__ == '__main__':
    testing = Testing()
    testing.start()
