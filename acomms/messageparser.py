from messageparams import CycleInfo, DrqParams, DataFrame, Ack, data_from_hexstring, hexstring_from_data
from cyclestats import CycleStats, TransmitStats
from modemlog import ModemLog
from timeutil import *
import commstate
from binascii import hexlify, unhexlify
import datetime
import sys
import traceback
import os

class MessageParser:
    def __init__(self, modem):
        self.modem = modem    
    
    # This method gets called when the object is called as a function, and
    # tries to find a matching attribute for that message type.
    # This is a pythonic(?) way of implementing a switch case.
    def parse(self, msg):
        try:
            func = getattr(self, msg['type'])
        except AttributeError, e:
            self.modem._daemon_log.warn('Unrecognized message: ' + str(msg['type']))
            func = None
        try:
            if func != None:
                return func(msg)
        except Exception, e:
            self.modem._daemon_log.error("Exception when parsing: " + str(sys.exc_info()[0]))
            traceback.print_exc()

    def GPRMC(self,msg):
        pass

    def PUBX(self,msg):
        pass

    def CACFG(self, msg):
        # Only worry about the parameters that matter...
        key = msg["params"][0]
        value = msg["params"][1]
        
        if key == "SRC": self.modem.id = int(value)
        if key == "ASD": self.modem.asd = bool(int(value))
        if key == "PCM": self.modem.pcm_on = bool(int(value))
        self.modem.config_data[key] = value
        
    def CACYC(self, msg):
        src = int(msg["params"][1])
        dest = int(msg["params"][2])
        rate = int(msg["params"][3])
        ack = int(msg["params"][4]) == 1
        num_frames = int(msg["params"][5])
        
        cycleinfo = CycleInfo(src, dest, rate, ack, num_frames)
        
        # Pass this to the comms state machine.
        self.modem.state.got_cacyc(cycleinfo)
        
    def CATXF(self, msg):
        self.modem.state.got_catxf()
        
    def CADRQ(self, msg):
        src = int(msg["params"][1])
        dest = int(msg["params"][2])
        ack = int(msg["params"][3]) == 1
        num_bytes = int(msg["params"][4])
        frame_num = int(msg["params"][5]) 
        
        drqparams = DrqParams(src, dest, ack, num_bytes, frame_num)
        
        self.modem.state.got_cadrq(drqparams)
        
    def CARXD(self, msg):
        src = int(msg["params"][0])
        dest = int(msg["params"][1])
        ack = int(msg["params"][2]) == 1
        frame_num = int(msg["params"][3])
        data = data_from_hexstring(msg["params"][4])
        
        dataframe = DataFrame(src, dest, ack, frame_num, data)
        
        self.modem.state.got_carx(dataframe)
        self.modem.on_rxframe(dataframe)
        
    def CAMSG(self, msg):
        # CAMSG sucks.  We need to parse it to figure out what's going on.
        # This doesn't account for all of the possible CAMSG messages.
        if msg["params"][0] == "BAD_CRC":
            self.modem.state.got_badcrc()
        elif msg["params"][0] == "PACKET_TIMEOUT":
            self.modem.state.got_packettimeout()
        else:
            try:
                msg_type = msg["params"][0]
                number = int(msg["params"][1])
                self.modem.state.got_camsg(msg_type,number)
            except ValueError:
                pass
        #TODO: Add PSK errors here
            
    def CAERR(self, msg):
        # Sigh.  This really shouldn't be used to signal data timeouts, but it is.
        # This doesn't account for most of the CAERR messages.
        if msg["params"][1] == "DATA_TIMEOUT":
            frame_num = msg["params"][2]
            self.modem.state.got_datatimeout(frame_num)
        else:
            hhmmss = msg["params"][0]
            module = msg["params"][1]
            err_num = int(msg["params"][2])
            message = msg["params"][3]
            self.modem.state.got_caerr(hhmmss,module,err_num,message)
    
    def CAREV(self, msg):
        '''Revision Message'''
        self.modem.state.got_carev(msg)
        
    def CATXP(self, msg):
        '''Start of Packet Transmission Acoustically'''
        pass
    
    def CAMPA(self,msg):
        '''Ping Received Acoustically'''
        src = int(msg["params"][0])
        dest = int(msg["params"][1])
        self.modem.state.got_campa(src,dest)
        pass

    def CADQF(self,msg):
        '''Data Quality Factor Message'''
        dqf= int(msg["params"][0])
        p = int(msg["params"][1])        
        self.modem.state.got_cadqf(dqf,p)
        pass
    
    def CARSP(self, msg):
        '''Echo of CCRSP command'''
        pass
    
    def CAXST(self, msg):
        '''Transmit Statistics message'''
        try:
            xst = TransmitStats.from_nmea_msg(msg)

            # Raise the event
            self.modem.on_xst(xst, msg)
        except Exception, ex:
            self.modem._daemon_log.error("Error parsing XST: " + str(sys.exc_info()[0]))
        pass
    
    def CARXP(self, msg):
        '''Probe received (RX pending)'''
        pass
    
    def CAMPC(self, msg):
        '''Ping command echo'''
        pass

    def CAMPR(self, msg):
        '''Ping command reply'''
        pass
    
    def CAMUC(self, msg):
        '''User minipacket command echo'''
        pass
        
    def CAMUR(self, msg):
        '''User minipacket reply'''
        pass

    def CAMUA(self, msg):
        '''User minipacket received accoustically'''
        pass
        
    def CATXD(self, msg):
        '''CCTXD echo'''
        pass
        
    def CAMSC(self, msg):
        '''Sleep command echo'''
        pass

    def CATMS(self, msg):
        '''Time set command echo '''
        pass

    def CATMG(self, msg):
        '''Time status '''
        pass

    def CARBR(self, msg):
        '''Log message retreival
        '''
        pass

    def CAHIB(self, msg):
        '''hibernate echo
        '''
        pass

    def CATDP(self, msg):
        ''' Transmit echo of new packet
        '''
        pass

    def CARDP(self, msg):
        ''' Received new packet
        '''
        pass

    def CAHBR(self, msg):
        '''Hibernate status
        '''
        pass

    def CAALQ(self, msg):
        '''API level query response
        '''
        pass

    def CACLK(self, msg):
        # $CACLK,yyyy,MM,dd,HH,mm,ss
        args = msg["params"]
        datestr = str(args[1]) + str(args[2]) + str(args[3]) + str(args[4]) + str(args[0]) + '.' + str(args[5])
        if self.modem.set_host_clock_flag == True:
            self.modem._daemon_log.warn("Setting host clock to: " + datestr)
            #TODO: This probably shouldn't be part of this module.
            os.system('/bin/date -u ' + datestr)
            self.modem.set_host_clock_flag = False
    
    def CACST(self, msg):

        try:
            cst = CycleStats.from_nmea_msg(msg)

            # Raise the event
            self.modem.on_cst(cst, msg)
        except Exception, ex:
            self.modem._daemon_log.error("Error parsing CST: " + str(sys.exc_info()[0]))
            raise

    def CATRC(self, msg):
        pass

    def CAACK(self, msg):
        src = int(msg["params"][0])
        dest = int(msg["params"][1])
        frame_num = int(msg["params"][2])
        ack = int(msg["params"][3]) == 1

        ack = Ack(src, dest, ack, frame_num)
        self.modem.on_ack(ack,msg)

    def CATOA(self, msg):
        pass

    def CABBD(self,msg):
        pass

    def CABDD(self, msg):
        pass

    def CATDP(self,msg):
        #errflag = int(msg["params"][0])
        #uniqueID = int(msg["params"][1])
        #dest = int(msg["params"][2])
        #rate = int(msg["params"][3])
        #ack = int(msg["params"][4]) == 1
        #reserved = int(msg["params"][5])

        #mfdata = (msg(["params"][6])).split(';')
        #dfdata = (msg(["params"][7])).split(';')
        pass



    def CARDP(self,msg):
        #src = int(msg["params"][0])
        #dest = int(msg["params"][1])
        #rate = int(msg["params"][2])
        #ack = int(msg["params"][3]) == 1
        #reserved = int(msg["params"][4])

        #mfdata = (msg(["params"][5])).split(';')
        #mf_crc_check = mfdata[0]
        #mf_nbytes = mfdata[1]
        #mf_data = data_from_hexstring(mfdata[2])

        #dfdata = (msg(["params"][6])).split(';')
        #df_crc_check = dfdata[0]
        #df_nbytes = dfdata[1]
        #df_data = data_from_hexstring(dfdata[2])
        pass

    def CAALQ(self,msg):
        app_name = msg["params"][0]
        nmea_api_level = int(msg["params"][1])
        self.modem._daemon_log.info("Modem API Information: Application Name: {0} API Level: {1}".format(app_name,nmea_api_level))

		
    def CAFDR(self,msg):
        src = int(msg["params"][0])
        dest = int(msg["params"][1])
        rate = int(msg["params"][2])
        ack = int(msg["params"][3]) == 1
        nbytes  = int(msg["params"][4])


    def CATMG(self,msg):
        dt = convert_to_datetime(msg["params"][0])
        clksrc = msg["params"][1]
        pps_source = msg["params"][2]

        self.modem._daemon_log.info("Modem Date and Time Message:{0}\tClock Source:{1}\tPPS Source:{2}".format(dt,clksrc.replace('_',' '),pps_source.replace('_',' ')))

    def CATMQ(self,msg):
        dt = convert_to_datetime(msg["params"][0])
        clksrc = msg["params"][1]
        pps_source = msg["params"][2]

        self.modem._daemon_log.info("Modem Date and Time Query Response:{0}\tClock Source:{1}\tPPS Source:{2}".format(dt,clksrc.replace('_',' '),pps_source.replace('_',' ')))

    def CAPAS(self,msg):
        passthrough_msg = msg["params"][0]

        self.modem._daemon_log.info("Pass Through Message Received: {0}".format(passthrough_msg))

    def CAPST(self,msg):
        pass

    def CAHIB(self,msg):
        hibernate_cause = int(msg["params"][0])
        hibernate_time = convert_to_datetime(msg["params"][1])
        wake_cause = int(msg["params"][2])
        wake_time = convert_to_datetime(msg["params"][3])
        self.modem._daemon_log.info("Modem Hibernate Ack: Hibernate({0},{1}), Wake({2},{3})".format(hibernate_cause,hibernate_time,wake_cause,wake_time))
        pass

    def CAMEC(self,msg):
        pass

    def CAHBR(self,msg):
        wake_time = convert_to_datetime(msg["params"][0])
        self.modem._daemon_log.info("Modem Hibernate Start: Wake@{0}".format(wake_time))

    def CATMS(self,msg):
        dt = None
        timed_out = int(msg["params"][0])
        if msg["params"][1] is not None:
            dt = convert_to_datetime(msg["params"][1])
        self.modem._daemon_log.info("Modem Set Clock Response: Timed Out:{0} Time Set To:{1}".format(timed_out,dt))

    def CARBS(self,msg):
        pass
        #try:
        #    log = ModemLog.from_nmea_msg(msg)

            # Raise the event
        #    self.modem.on_modem_log(log, msg)
        #except Exception, ex:
        #    self.modem._daemon_log.error("Error parsing Retrieved Modem Log Message: " + str(sys.exc_info()[0]))

    def CARBR(self,msg):
        pass
        #try:
        #    log = ModemLog.from_nmea_msg(msg)

            # Raise the event
        #    self.modem.on_modem_log(log, msg)
        #except Exception, ex:
        #    self.modem._daemon_log.error("Error parsing Retrieved Modem Log Message: " + str(sys.exc_info()[0]))

    def CAMIZ(self,msg):
        pass

    def SNTTA(self,msg):
        pass

    def SNMFD(self,msg):
        pass

    def SNUTX(self,msg):
        pass

    def UPMFWA(self,msg):
        slot = int(msg["params"][0])
        data_loc = int(msg["params"][1])
        total_data_size = int(msg["params"][2])
        sha1_hash = msg["params"][3]
        self.modem._daemon_log.info("Modem Starting FW Update Process: Slot {}, {} bytes, SHA1 HASH = ({}).".format(slot,total_data_size,sha1_hash))
        pass

    def UPDATA(self,msg):
        nbytes_received = int(msg["params"][0])
        self.modem._daemon_log.info("Modem Received {} Bytes of Firmware File Upload.".format(nbytes_received))
        pass

    def UPDONE(self,msg):
        update_msg = msg["params"][0]
        self.modem._daemon_log.info("Modem FW Update Done: {}".format(update_msg))
        pass

    def UPERR(self,msg):
        errno = int(msg["params"][0])
        err_msg = msg["params"][1]
        self.modem._daemon_log.error("Modem FW Update Errored ({}): {}".format(errno,err_msg))
        pass
