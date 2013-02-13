'''
Created on Jan 31, 2012

@author: Eric
'''

class MyClass(object):
    '''
    classdocs
    '''


    def __init__(selfparams):
        '''
        Constructor
        '''
        
        

# Basically just a sneaky switch-case below.
class _Formatter:
    # This method gets called when the object is called as a function, and
    # tries to find a matching attribute for that message type.
    def __call__(self, msg):
        try:
            func = getattr(self, msg['type'])
            return func(msg)
        except Exception, e:
            return "[%s] %s\n"% (msg['type'], ", ".join(msg['params']))
    def CACFG(self, msg):
        return "Configuration: %s=%s\n" % tuple(msg["params"])
    def CACYC(self, msg):
        src = int(msg["params"][1])
        dst = int(msg["params"][2])
        rate = int(msg["params"][3])
        ack = int(msg["params"][4]) == 1 and "" or "out"
        return "Cycle (R%d) from %d to %d initialized,"\
               " with%s ACK requested.\n" % (rate, src, dst, ack)
    def CADQF(self, msg):
        pkType = (int(msg["params"][1])==1) and "data" or "mini-"
        return "Data quality is %d/255 (from "\
               "%spacket.)\n" % (int(msg["params"][0]), pkType)
    def CAMFD(self, msg):
        return "Matched filter: peak=%d, power=%d, ratio=%d, spl=%d\n" %\
                                       tuple(map(int, msg["params"]))
    def CATXF(self, msg):
        return "Packet %d sending completed.\n" % (int(msg["params"][0]))
    def CATXP(self, msg):
        return "Packet %d sending begin.\n" % (int(msg["params"][0]))
    ### TODO
    def CAMSG(self, msg):
        return str(msg['raw']).strip()+"\n"
    def CATXD(self, msg):
        return str(msg['raw']).strip()+"\n"
    def CATOA(self, msg):
        return "TOA:%s Sync. mode:%d\n" %  (msg['params'][0], int(msg['params'][1]))
    def CAMPA(self, msg):
        return "PING from src=%d to dest=%d\n" %  (int(msg['params'][0]), int(msg['params'][1]))
##        return str(msg['raw']).strip()+"\n"
    def CACLK(self, msg):
        (yr,mon,dy,h,m,s) = [int(x) for x in msg["params"]]
        clktime = datetime(yr,mon,dy,h,m,s)
        now = datetime.now()
        if now.second != clktime.second:
            text = "Modem time is: %s (modem sec:%d PC sec:%d)\n" % (clktime.strftime('%c'), clktime.second, now.second)
        else:
            text = "Modem time is: %s (second matches PC)\n" % clktime.strftime('%c')
        return text
    def CAERR(self, msg):
        return str(msg['raw']).strip()+"\n"
    def CADRQ(self, msg):
        return str(msg['raw']).strip()+"\n"
    def CAMPR(self, msg):
        return "PING REPLY from src=%d to dest=%d, owtt = %.4fs, distance = %.2fm\n" %  (int(msg['params'][0]), int(msg['params'][1]),float(msg['params'][2]),(float(msg['params'][2]))*1500)
    def CAACK(self, msg):
        return str(msg['raw']).strip()+"\n"
    def CAMUA(self, msg):
        return str(msg['raw']).strip()+"\n"
    def SNPNT(self, msg):
        return str(msg['raw']).strip()+"\n"
    def SNTTA(self, msg):                
        return str(msg['raw']).strip()+"\n"
    ### END TODO
    def CAREV(self, msg):
        time, ident, version = msg['params']
        time = ":".join((time[0:2],time[2:4],time[4:]))
        return "Modem heartbeat: '%s' r%s, current modem time is %s\n" % (ident, version, time)
    def CACST(self, msg):
            
    def CARXD(self, msg):
        
        fr = unpackFrame(int(msg["params"][0]),int(msg["params"][1]),
                           int(msg["params"][2]),int(msg["params"][3]),
                          msg["params"][4])

        if (fr.data[0] == FrameType.StateXY):
            st = StateXY()
            RxStateXYFrame(fr, st)
            fmtdCcl = "X:%s, Y:%s, H:%s, d:%s, a:%s,"\
                      "gid:%s, gx:%s, gy:%s, gd:%s, lbl: %s" % \
                      (str(st.x), str(st.y), str(st.heading), str(st.depth),
                       str(st.altitude), str(st.goalId), str(st.goalX),
                       str(st.goalY), str(st.goalDepth),
                       ", ".join(["%0.4f" % x for x in st.lblTT]))
        if (fr.data[0] == FrameType.DownlinkOwtt):
            dl = DownlinkOwtt()
            unpackDownlinkOwtt(dl, fr)
            fmtdCcl = str(dl) + "\n"
        if (fr.data[0] == FrameType.SciXyOwtt):
            sc = SciXyOwtt()
            unpackSciXyOwtt(sc, fr)
            ackStr = (fr.ack == 1) and "ACK" or "no ACK"
            cclstr = "Science: %d=>%d,%s [%s]\n" % (fr.src,fr.dest,ackStr,str(sc))
            return cclstr
        else:
            fmtdCcl = "Unpacking not implemented: %s." % msg["params"][4]

        ackStr = (fr.ack == 1) and "ACK" or "no ACK"
        msg  = "CCL %d->%d, %s, %s(%s)\n" %\
               (fr.src, fr.dest, ackStr, FrameType.lookup(fr.data[0]),fmtdCcl)
        return msg
    
    def HRTBT(self, msg): # ACOMM Daemon Heartbeat
        tm=(int, float, str, float, float, int, float, float, float, float, float)
        (src, now, jul, t_procstart, dt_reboot, n_reboot, dt_sntta, dt_allCyc,
         dt_meCyc, dt_lastMsg, dt_lastSent) = msg["params"]
        fmtd = "Heartbeat: last reboot %.2fs ago.\n" % float(dt_reboot)
        return fmtd