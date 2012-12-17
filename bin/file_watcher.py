'''
Created on Dec 6, 2012

@author: andrew
'''
from acomms import Micromodem
try:
    import pyinotify
except(ImportError):
    sys.stderr.write("Error Importing pyinotify.Did you install it with \"pip install pyinotify\"?")
    sys.exit(-1)
import os


class FileWatcher():
    def __init__(self,DirectoryName, modem):
        if os.path.isdir(DirectoryName):
            self.Directory = DirectoryName
            
        self.Recvwm = pyinotify.WatchManager()
        
        #Only handle creation events because we delete the files when we are finished
        self.mask = pyinotify.IN_CREATE | pyinotify.IN_UNMOUNT
         
        self.RecvHandler = self.RecvDirEventHandler(modem,self)
        
        self.RecvNotifier = pyinotify.ThreadedNotifier(self.Recvwm, self.RecvHandler)
        self.RecvNotifier.start()
        self.Start()
    
    def Start(self):
        self.rwdd = self.Recvwm.add_watch(self.Directory +'/Recv', rec=True)
        self.Watching = True
        
    def Stop(self):
        self.Recvwm.rm_watch(self.rwdd)
        self.Watching = False
    
    def Terminate(self):
        self.RecvNotifier.stop()
    
    def isWatching(self):
        return self.Watching
        
    class RecvDirEventHandler(pyinotify.ProcessEvent):
        def __init__(self,modem, FW):
            self.modem = modem
            self.FW = FW
        
        def process_IN_CREATE(self, event):
            print "Files Created:", event.pathname
            self.HandleFiles(event)
        
        def process_IN_UNMOUNT(self,event):
            self.FW.Stop()
        
        def HandleFiles(self,event):
            dirList=os.listdir(event.pathname)
            #Process each file
            for fname in dirList:
                #Open
                f = open(fname, 'r')
                #For each line
                for line in f:
                    #Send to modem
                    print line
                    #self.modem.write_string(line)
                f.close()
                #Delete the file
                os.remove(fname)
    

if __name__ == '__main__':
    DirectoryName = '/home/acomms/logs'
    um = Micromodem()
    FW = FileWatcher(DirectoryName,um)
    FW.run()