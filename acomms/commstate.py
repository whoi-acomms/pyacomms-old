'''
Created on Jan 25, 2012

@author: Eric
'''

from messageparams import Packet, Rates, DataFrame

import timer2

class CommState(object):
    '''
    classdocs
    '''

    # Default timeout for each state.  Call timeout method after this time has elapsed.
    timeout_seconds = 10

    def __init__(self, modem):
        self.modem = modem


    def entering(self):
        self.modem._daemon_log.debug("Entering new state: " + str(self))

        # Stop any timeout timer that is currently running.
        self.modem.state_timer.clear()

        # Start a new timeout timer, if this state requires one.
        if self.timeout_seconds:
            self.modem.state_timer.apply_after(self.timeout_seconds * 1000, self.timeout)


    def got_cacyc(self, cycleinfo):
        self.modem._daemon_log.debug("[" + str(self) + "]: Got CACYC")
        pass
    def got_catxf(self):
        self.modem._daemon_log.debug("[" + str(self) + "]: Got CATXF")
        pass
    def got_cadrq(self, drqparams):
        self.modem._daemon_log.debug("[" + str(self) + "]: Got CADRQ")
        pass
    def got_carx(self, rxdataframe):
        self.modem._daemon_log.debug("[" + str(self) + "]: Got CARXD")
        pass
    def got_badcrc(self):
        self.modem._daemon_log.debug("[" + str(self) + "]: Got Bad CRC")
        pass
    def got_datatimeout(self, frame_num):
        self.modem._daemon_log.debug("[" + str(self) + "]: Got DATA_TIMEOUT")
        pass
    def got_packettimeout(self):
        self.modem._daemon_log.debug("[" + str(self) + "]: Got PACKET_TIMEOUT")
        pass
    def got_pskerror(self, message):
        self.modem._daemon_log.debug("[" + str(self) + "]: Got PSK Error")
        pass
    def got_carev(self, msg):
        self.modem._daemon_log.debug("[" + str(self) + "]: Got CAREV")
        # See if we just rebooted.
        if msg['params'][1] == "INIT":
            if self.modem.current_txpacket:
                self.modem.on_packettx_failed()
            self.modem._changestate(Idle)
        pass
    
    def got_caerr(self,hhmmss,module,err_num,message):
        self.modem._daemon_log.debug("[" + str(self) + "]: Got CAERR. (Time:%s Module: %s Number:%d Message:%s)" % (hhmmss,module,err_num,message))
        pass
    
    def got_camsg(self,msg_type,number):
        self.modem._daemon_log.debug("[" + str(self) + "]: Got CAMSG. (Type:%s Number:%d)" % (msg_type,number))
        pass
    
    def got_campa(self, src, dest):
        self.modem._daemon_log.debug("[" + str(self) + "]: Heard Ping Request From %d to %d" % (src,dest))
        pass

    def got_camea(self, src, dest):
        self.modem._daemon_log.debug("[" + str(self) + "]: Heard Line Control Command From %d to %d" % (src,dest))
        pass

    def got_camsa(self, src, dest):
        self.modem._daemon_log.debug("[" + str(self) + "]: Heard Sleep Command From %d to %d" % (src,dest))
        pass

    def got_minipacket_cmd(self, cmd, src):
        self.modem._daemon_log.debug("[{state}]: Got {cmd} Command from {src}".format(self, cmd, src))

    def send_minipacket_cmd(self, cmd, dest):
        pass

    def got_cadqf(self, dqf, packet_type):
        self.modem._daemon_log.debug("[" + str(self) + "]: Got CADQF. (DQF:%d Packet Type:%d)" % (dqf,packet_type))
        pass

    def sent_cccyc(self, cycleinfo):
        self.modem._daemon_log.debug("[" + str(self) + "]: Sent CCCYC")
        pass

    def timeout(self):
        self.modem._daemon_log.debug("[" + str(self) + "]: Timed out")
        pass
    
    def send_packet(self, packet):
        self.modem._daemon_log.warn("Trying to send packet while modem is {0}.".format(self.__class__.__name__))


class Idle(CommState):

    # Idle is the only state that never times out.
    timeout_seconds = None

    def entering(self):
        super(Idle, self).entering()
        
        # stop any timeout timers that are currently running
        #self.modem.stop_timeouts()
        
        # Reset our status objects
        self.modem.current_rx_frame_num = 1
        self.modem.current_tx_frame_num = 1
        self.modem.current_cycleinfo = None
        self.modem.current_txpacket = None
        self.modem.current_rxpacket = None
        
    def sent_cccyc(self, cycleinfo):
        super(Idle, self).sent_cccyc(cycleinfo)
        
        self.modem.current_cycleinfo = cycleinfo
        
        self.modem._changestate(WaitingForCacyc)
        
    def got_cacyc(self, cycleinfo):
        super(Idle, self).got_cacyc(cycleinfo)
        
        self.modem.current_cycleinfo = cycleinfo
        
        # check to see if this is an uplink request or incoming data
        if (cycleinfo.src == self.modem.id):
            self.modem._changestate(WaitingForDrq)
        else:
            self.modem._changestate(WaitingForRxData)


            
    def send_packet(self, packet):
        self.modem._daemon_log.info("Sending packet from Idle")
        
        # copy the packet to the output buffer
        self.modem.current_txpacket = packet
        self.modem.current_cycleinfo = packet.cycleinfo
        
        # Send the cycle init
        self.modem.send_cycleinit(packet.cycleinfo)
        
        self.modem._changestate(WaitingForCacyc)

    def send_minipacket_cmd(self, cmd, dest):
        self.modem._daemon_log.info("Sending {cmd} Command from Idle".format(cmd))
        self.modem.send_ping()
        self.modem._changestate(WaitingForMinipacketTxf)

    def got_minipacket_cmd(self, cmd, src):
        super(Idle, self).got_minipacket_cmd(cmd, src)

        # Once we get a minipacket command, we send a reply...
        self.modem._changestate(WaitingForMinipacketTxf)

    def got_camsg(self,msg_type,number):
        super(Idle,self).got_camsg(msg_type,number)

    def __str__(self):
        return "Idle"
        
class WaitingForCacyc(CommState):
    ''' State: Waiting for the modem to echo a $CACYC message in response to a $CCCYC message that we issued. '''

    def entering(self):
        super(WaitingForCacyc, self).entering()
        
        # Start a new timeout timer
        #self.modem.timeout_start(settings.cacyc_timeout)
        
    def got_cacyc(self, cycleinfo):
        super(WaitingForCacyc, self).got_cacyc(cycleinfo)
        
        # Make sure this is the CACYC we expect
        # If not, it arrived acoustically or from another serial port, and we need to abort 
        # our current transmit to receive this packet.
        if (cycleinfo == self.modem.current_cycleinfo):
            # Is this an uplink or downlink?
            if (cycleinfo.src == self.modem.id):
                # Downlink.  Is it an FSK (rate 0) downlink (will it send a minipacket CI)?
                if cycleinfo.rate_num == 0:
                    self.modem._changestate(WaitingForCiTxf)
                else:
                    self.modem._changestate(WaitingForDrq)
            else:
                # Uplink.  Wait for the cycle init to finish transmitting.
                self.modem._changestate(WaitingForCiTxf)
        else:
            # This CACYC doesn't match what we expect
            # TODO: Add log message here
            
            # Abort the transmit
            self.modem.on_packettx_failed()
            self.modem.current_cycleinfo = cycleinfo
            
            # Is this an uplink request for us?
            if cycleinfo.src == self.modem.id:
                self.modem._changestate(WaitingForDrq)
            else:
                self.modem._changestate(WaitingForRxData)
                
        # if we got here, something is wrong
        #self.modem._daemon_log.warn("Impossible state in WaitingForCacyc.got_cacyc")
                    
    def timeout(self):
        super(WaitingForCacyc, self).timeout()
        
        # TODO: Log this error
        self.modem.on_packettx_failed()
        
        self.modem._changestate(Idle)
        
    def __str__(self):
        return "Waiting For CACYC"
        

class WaitingForDrq(CommState):
    ''' State: Waiting for modem to issue a $CADRQ message, since we got a CACYC and plan to transmit data. '''

    timeout_seconds = 10

    def entering(self):
        super(WaitingForDrq, self).entering()

        
    def got_cadrq(self, drqparams):
        CommState.got_cadrq(self, drqparams)
        
        # See if we have a downlink packet to send
        if self.modem.current_txpacket != None:
            # Make sure that this DRQ matches the packet we plan to send
            if (drqparams.src == self.modem.current_txpacket.cycleinfo.src
                    and drqparams.dest == self.modem.current_txpacket.cycleinfo.dest
                    and drqparams.num_bytes == Rates[self.modem.current_txpacket.cycleinfo.rate_num].framesize
                    and drqparams.frame_num == self.modem.current_tx_frame_num):
                # Send the frame
                self.modem._send_current_txframe()
                
                # Was this the last frame?
                if drqparams.frame_num < self.modem.current_txpacket.cycleinfo.num_frames:
                    # It wasn't, so get ready to send the next frame.
                    self.modem.current_tx_frame_num += 1
                    self.modem._changestate(WaitingForDrq)
                else:
                    # That was the last frame, so wait for the packet to transmit
                    self.modem._changestate(WaitingForTxf)
                    
            else:
                # The DRQ we just received does not match the packet we have queued for transmit.
                # Therefore, we don't know what state we're in.  Say that we failed and go back to Idle.
                self.modem.on_packettx_failed()
                self.modem._changestate(Idle)
        else:
            # We don't have a current TX packet, so this is an uplink request
            
            # This is probably not always what we want to do
            #TODO: Add better uplink support
            self.modem.send_uplink_frame(drqparams)
            
            # Do we expect to send more frames?
            if drqparams.frame_num < self.modem.current_cycleinfo.num_frames:
                self.modem._changestate(WaitingForDrq)
            else:
                self.modem._changestate(WaitingForTxf)
    
    def got_datatimeout(self, frame_num):
        CommState.got_datatimeout(self, frame_num)
        
        # Note that if we are doing an uplink and we are configured not to respond, this is expected behavior.
        
        # See if we are trying to send a packet.
        if self.modem.current_txpacket != None:
            # We failed.  Oh well.
            self.modem.on_packettx_failed()
            
        # Now, see if the modem will still transmit for any reason
        if self.modem.asd == True:
            # The modem will generate a test frame and still transmit
            self.modem._changestate(WaitingForTxf)
        else:
            # See if we already sent a frame, in which case the modem will still transmit.
            if frame_num > 1:
                self.modem._changestate(WaitingForTxf)
            else:
                self.modem._changestate(Idle)
    
    def timeout(self):
        CommState.timeout(self)
        
        # See if we are trying to send a packet
        if self.modem.current_txpacket != None:
            # We failed.  Signal an error
            self.modem.on_packettx_failed()
        
        # We don't really know what state we're in.
        self.modem._changestate(Idle)
        
    def got_catxf(self):
        CommState.got_catxf(self)
        
        # We can get here if there was a frame in the mdoem's FIFO from an ealier CCTXD message
        # However, we don't know what that frame might contain.  It's probably not what we want to send.
        if self.modem.current_txpacket != None:
            self.modem.on_packettx_failed()
            
        self.modem._changestate(Idle)
        
    def __str__(self):
        return "Waiting for CADRQ"
    

class WaitingForTxf(CommState):
    ''' State: Waiting for the $CATXF message when we expect the modem to transmit. '''

    def entering(self):
        CommState.entering(self)
        
        # Start the timeout timer
        #self.modem.start_timeout(settings.txf_timeout)
        #TODO: Adjust this interval based on the packet type, number of frames, and BW0.
        
    def got_catxf(self):
        CommState.got_catxf(self)
        
        # If we were trying to send a packet, we just succeeded.
        if self.modem.current_txpacket != None:
            self.modem.on_packettx_success()
        
        # Now, go back to Idle.
        self.modem._changestate(Idle)
        
        
    def __str__(self):
        return "Waiting for CATXF"
        
class WaitingForCiTxf(CommState):
    ''' State: Waiting for the $CATXF message when we expect the modem to transmit a cycle init. '''

    def entering(self):
        CommState.entering(self)
        
        # Start the timeout timer
        #self.modem.start_timeout(settings.citxf_timeout)
        
    def got_catxf(self):
        CommState.got_catxf(self)
        
        # See if we are in the middle of an FSK downlink
        if self.modem.current_txpacket != None:
            self.modem._changestate(WaitingForDrq)
        else:
            self.modem._changestate(WaitingForPacket)
    
    def timeout(self):
        CommState.timeout(self)
        
        # We timed out, so signal an error
        # Note that the modem might not really be done transmitting.
        
        # Were we in the middle of an FSK downlink?
        if self.modem.current_txpacket != None:
            self.modem.on_packettx_failed()
        else:
            self.modem.on_uplink_failed()
        
        self.modem._changestate(Idle)
        
    def __str__(self):
        return "Waiting for CI CATXF"


class WaitingForMinipacketTxf(CommState):
    def got_catxf(self):
        CommState.got_catxf(self)

        # That should do it.
        self.modem._changestate(Idle)

    def timeout(self):
        CommState.timeout(self)

        # We timed out, so signal an error
        # Note that the modem might not really be done transmitting.
        self.modem.on_minipacket_tx_failed()

        self.modem._changestate(Idle)

    def __str__(self):
        return "Waiting for Minipacket Command CATXF"


class WaitingForPacket(CommState):
    ''' State: Waiting for a packet following an uplink request. '''

    def entering(self):
        CommState.entering(self)
        
        # Start the timeout timer
        #self.modem.start_timeout(settings.packet_timeout)

    def got_cacyc(self, cycleinfo):
        CommState.got_cacyc(self, cycleinfo)
        
        # Make sure this is the packet we expect.
        if cycleinfo == self.modem.current_cycleinfo:
            # This is the packet for which we were waiting, so wait for the CARXDs.
            self.modem._changestate(WaitingForRxData)
        else:
            # This was not the CACYC we expected.
            # Replace the current_cycleinfo to match this incoming message and raise an error
            self.modem.on_uplink_failed()
            self.modem.current_cycleinfo = cycleinfo
            
            self.modem._changestate(WaitingForRxData)
        
    def got_packettimeout(self):
        CommState.got_packettimeout(self)
        
        #TODO: Raise error here
        
        self.modem._changestate(Idle)
        
    def timeout(self):
        CommState.timeout(self)
        
        #TODO: Raise error here
        
        self.modem._changestate(Idle)
        
    def __str__(self):
        return "Waiting for packet"
        
class WaitingForRxData(CommState):
    ''' State: Waiting for $CARXD or $CARXA messages after getting a $CACYC message that suggests we should.  '''

    def entering(self):
        CommState.entering(self)
        
        self.modem.current_rxpacket = Packet(cycleinfo=self.modem.current_cycleinfo)
        
        # Start the timeout timer
        #self.modem.start_timeout(settings.timeout_rxdata)
        
    def got_carx(self, rxdataframe):
        CommState.got_carx(self, rxdataframe)
        
        # Make sure that the frame we received has parameters matching the packet we think we're receiving.
        if (rxdataframe.src == self.modem.current_rxpacket.cycleinfo.src
                and rxdataframe.dest == self.modem.current_rxpacket.cycleinfo.dest):
            # Copy this new data to our packet in progress
            self.modem.current_rxpacket.frames.append(rxdataframe)

            # Check to see if this frame had the ACK bit set.
            if rxdataframe.ack:
                self.modem.current_rxpacket.cycleinfo.ack = True
            
            # See if this was the last frame
            if rxdataframe.frame_num >= self.modem.current_rxpacket.cycleinfo.num_frames:
                # We got a complete packet
                # See if it had BAD_CRCs on any frame.
                if any(frame.bad_crc for frame in self.modem.current_rxpacket.frames):
                    self.modem.on_packetrx_failed
                else:
                    self.modem.on_packetrx_success()

                # Are we sending ACKs?  If so, wait for that.
                if self.modem.current_rxpacket.cycleinfo.ack:
                    self.modem._changestate(WaitingForMinipacketTxf)
                else:
                    # Go back to Idle
                    self.modem._changestate(Idle)
            

            else:
                # We are waiting for another frame
                pass
        else:
            # This is not the frame we were expecting
            # We can't make a good packet, so signal an error
            self.modem.on_packetrx_failed()
            self.modem._changestate(Idle)
        
    def got_badcrc(self):
        CommState.got_badcrc(self)

        # Add this BAD_CRC as a "frame" to the current packet.
        this_frame_num = self.modem.current_rxpacket.frames[-1].frame_num + 1
        this_quote_frame = DataFrame(self.modem.current_rxpacket.cycleinfo.src,
                                     self.modem.current_rxpacket.cycleinfo.dest,
                                     self.modem.current_rxpacket.cycleinfo.ack,
                                     this_frame_num,
                                     None,
                                     bad_crc=True)
        self.modem.current_rxpacket.frames.append(this_quote_frame)

        # See if this was the last frame
        if this_frame_num >= self.modem.current_rxpacket.cycleinfo.num_frames:
            # This packet is done, and it failed.
            self.modem.on_packetrx_failed()
            self.modem._changestate(Idle)
        else:
            # We are still waiting for the next frame.
            pass
        
    def timeout(self):
        CommState.timeout(self)
        
        # If we are receiving a packet, we just failed.
        if self.modem.current_rxpacket != None:
            self.modem.on_packetrx_failed()
        
        self.modem._changestate(Idle)

    def got_camsg(self,msg_type,number):
        CommState.got_camsg(self,msg_type,number)
        self.modem.on_packetrx_failed()
        self.modem._changestate(Idle)


    def __str__(self):
        return "Waiting for RX Data"
                
