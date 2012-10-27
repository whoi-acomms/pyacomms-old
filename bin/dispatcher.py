'''
Created on Feb 15, 2012

@author: Eric

There is a good reason we don't use the multiprocessing module.  Trust me.
'''

from time import sleep
import subprocess
import os

class Dispatcher(object):
    '''
    classdocs
    '''


    def __init__(self):
        self.command_dir = '/home/acomms/sync/fromshore'
        self.command_file_path = '/home/acomms/sync/fromshore/mode'
        self.script_path = '/home/acomms/pyacomms/bin'
        self.python_path = '/usr/bin/python'
        self.current_mode = "off"
        
        self.running_process = None
        
        self.dodebug = False
        
        if self.dodebug: 
            print('Dispatcher: started')
    
    def check_command(self):
                
        # By default, don't change state
        new_mode = self.current_mode
        
        with open(self.command_file_path, 'r') as cmdfile:
            new_mode = str(cmdfile.read())
            new_mode = new_mode.lower().strip()
            if self.dodebug: 
                print("Dispatcher: new_mode = {0}".format(new_mode))
            
        if new_mode != self.current_mode:
            if new_mode == 'off':
                self.run_off()
            elif new_mode == 'longterm':
                self.run_longterm()
            elif new_mode == 'sourcedrop':
                self.run_sourcedrop()
            elif new_mode == 'tx2750':
                self.run_tx2750()
            elif new_mode == 'tx10k':
                self.run_tx10k()
            elif new_mode == 'txboth':
                self.run_txboth()
            else:
                # Catch unrecognized commands here
                new_mode = self.current_mode
            
            self.current_mode = new_mode
        
    def watch_for_command(self):
        while (True):
            self.check_command()
            sleep(30)
    
    def kill_running(self):
        if self.running_process != None:
            self.running_process.terminate()
        
    def run_txboth(self):
        if self.dodebug: 
            print('Dispatcher: txboth')
        self.kill_running()
        self.running_process = subprocess.Popen([self.python_path,os.path.join(self.script_path, 'glidertx.py'), '10k', '3750'])

    def run_tx3750(self):
        if self.dodebug: 
            print('Dispatcher: tx3750')
        self.kill_running()
        self.running_process = subprocess.Popen([self.python_path,os.path.join(self.script_path, 'glidertx.py'), '3750'])
    
    def run_tx10k(self):
        if self.dodebug: 
            print('Dispatcher: tx10k')
        self.kill_running()
        self.running_process = subprocess.Popen([self.python_path,os.path.join(self.script_path, 'glidertx.py'), '10k'])
        
    def run_sourcedrop(self):
        if self.dodebug: 
            print('Dispatcher: sourcedrop')
        self.kill_running()
        self.running_process = subprocess.Popen([self.python_path,os.path.join(self.script_path, 'gliderlisten.py')])
        
    def run_longterm(self):
        if self.dodebug: 
            print('Dispatcher: longterm')
        self.kill_running()
        self.running_process = subprocess.Popen([self.python_path,os.path.join(self.script_path, 'glider.py')])
    
    def run_off(self):
        if self.dodebug: 
            print('Dispatcher: off')
        self.kill_running()
        
        
if __name__ == '__main__':
    dispatcher = Dispatcher()
    
    dispatcher.watch_for_command()