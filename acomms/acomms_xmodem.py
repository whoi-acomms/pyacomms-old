__author__ = 'andrew'

#This is an implementation of the Xmodem Protocol modified for the Microcmodem IO methods.
from messageparams import Rates, FDPRates, data_from_hexstring, hexstring_from_data
from unifiedlog import UnifiedLog
from acomms import Micromodem
from Queue import Queue,Empty,Full
import crcmod
import time
import os

class acomms_xymodem(object):
    '''
    XMODEM Like Protocol handler, expects an object to read from and an object to
    write to.
    :type mode: string
    :param pad: Padding character to make the packets match the packet size
    :type pad: char
    '''

    def __init__(self, micromodem, dest,rate = 1, timeout=60,pad='\x1a',ymodem_enabled = True,unified_log=None,log_path=None, ):
        assert isinstance(micromodem, Micromodem), "micromodem object isn't a Micromodem: %r" & micromodem
        assert rate in range(0,7), "Invalid Rate: %d" & rate
        assert dest != micromodem.id, "Can't send file to self."
        self.pad = pad

        self.rate = Rates[rate]
        self.micromodem = micromodem
        self.micromodem.set_config('RXP',1)
        self.micromodem.set_config('MOD',1)
        #use CRC-8/CDMA2000 instead of CRC-16 CCITT Unreflected.
        self.calc_crc = crcmod.mkCrcFun(0x19b, rev=False, initCrc=0xff, xorOut=0x00)
        if unified_log is None:
            unified_log = UnifiedLog(log_path=log_path)
        self.log = unified_log.getLogger("xmodem.{0}".format(micromodem.name))
        self.target_id = dest
        self.timeout = timeout
        self.ymodem_mode = True
        self.use_minipackets = False
        self.fsk_mode = self.rate.number == 0
        self.micromodem.ack_listeners.append(self.ack_recv)
        self.ack_list = Queue()

    SOH = '0001'
    STX = '0002'
    EOT = '0004'
    ACK = '0006'
    DLE = '0010'
    NAK = '0015'
    CAN = '0018'
    CRC = '0043'

    CRC_BIT_ID = 0xF000
    SEQ_NUM_BIT_ID = 0x0F00
    MAX_SEQ_NUM = 256

    def ack_recv(self,ack,msg):
        self.micromodem._daemon_log.info("Ack Received: {}".format(ack))
        self.ack_list.put_nowait(ack)


    def _receive_across_link(self,ack,timeout=None,delay=3,force_packet = False, validate_packet=False):
        if self.use_minipackets and not force_packet:
            data = self.micromodem.wait_for_minipacket(timeout=timeout)
            if ack:
                print("Acking Minipacket Data: {}".format(data))
                self.micromodem.send_minipacket(dest_id=self.target_id,databytes=self.ACK)
                self.micromodem.wait_for_xst(timeout)
                time.sleep(delay)
            return data
        else:
            data = self.micromodem.wait_for_data_packet(fsk=self.fsk_mode,timeout=timeout)
            #while data is None:
            #    data = self.micromodem.wait_for_data_packet(fsk=self.fsk_mode,timeout=timeout)
            if ack:
                self.micromodem._daemon_log.info("Waiting for Ack to Finish Transmitting")
                self.micromodem.wait_for_xst(timeout=timeout)
            return data

    def _send_across_link(self,data,ack,timeout = None,delay = 3,force_packet = False, validate_packet=False):
        value = True
        if self.use_minipackets and not force_packet:
            self.micromodem.send_minipacket(dest_id=self.target_id,databytes=data)
            self.micromodem.wait_for_xst(timeout)
            time.sleep(delay)
            if ack:
                self.micromodem._daemon_log.info("Waiting for Minpacket ACK")
                char = self.micromodem.wait_for_minipacket(timeout=None)
                if char != self.ACK:
                    self.micromodem._daemon_log.info("Nonack character received: {}".format(char))
                    value = False
            value = True
        else:
            self.micromodem.send_packet_data(dest=self.target_id,rate_num=self.rate.number,databytes=data,ack=ack)
            self.micromodem.ack_listeners.append(self.ack_recv)
            xst = self.micromodem.wait_for_xst(timeout=None)

            if validate_packet:
                self.micromodem._daemon_log.info("Validating Packet Transmission")
                if xst['num_frames_sent'] != xst['num_frames_expected']:
                    print("num_frames_sent != num_frames_expected: {} != {}".format(xst['num_frames_sent'] , xst['num_frames_expected']))
                    return False
            if ack:
                self.micromodem._daemon_log.info("Waiting for {} Acks".format(xst['num_frames_sent']))
                self.micromodem.wait_for_cst(timeout=timeout)
                #for i in range(1,xst['num_frames_sent']+1):
                #    ack_reply = self.micromodem.wait_for_nmea_type('CAACK',timeout=10)
                #    if ack_reply is None:
                #        print "No ACK received for frame {}.".format(i)
                #        return False
                    #if int(ack_reply['params'][2]) != int(i):
                    #    print "Ack Received not for current frame ({} != {}).".format(ack_reply['params'][2],i)
                    #    return False
                    #print("Received Ack: {}".format(ack_reply))
                self.micromodem.ack_listeners.remove(self.ack_recv)
                frames = range(1,xst['num_frames_sent']+1)
                self.micromodem._daemon_log.info("Frames to Match: {}".format(frames))
                while True:
                    try:
                        ack_recv = self.ack_list.get_nowait()
                        if ack_recv.frame_num in frames:
                            self.micromodem._daemon_log.info("Matched Frame #:{}".format(ack_recv.frame_num))
                            frames.remove(ack_recv.frame_num)
                            if not frames:
                                value = True
                                break
                    except Empty:
                        self.micromodem._daemon_log.info("Empty Queue")
                        break

                if frames:
                        self.micromodem._daemon_log.info("No ACK received for frames {}.".format(frames))
                        value = False
            try:
                self.micromodem.ack_listeners.remove(self.ack_recv)
            #Ignore if no longer in the list.
            except ValueError:
                pass
            #Reset the Queue
            while not self.ack_list.empty():
                self.ack_list.get_nowait()
        return value

    def calculate_packet_delay(self,timeout=30):
        #determine distance between nodes for 1-way travel time delay estimates.
        self.micromodem.send_ping(dest_id=self.target_id)
        delay = int(self.micromodem.wait_for_ping_reply(dest_id=self.target_id,timeout=timeout))  + 3 #Each packet takes roughly 3 seconds to transmit


    def abort(self, count=2, timeout=60):
        '''
        Send an abort sequence using CAN bytes.
        '''
        for counter in xrange(0, count):
            self.micromodem._daemon_log.info("Sending CAN")
            self._send_across_link(self.CAN,False,timeout=timeout)


    def send(self, file_io, retry=16, timeout=15, delay = 1, callback=None):
        '''
        Send a stream via the XMODEM Like protocol.

            >>> stream = file('/etc/issue', 'rb')
            >>> print modem.send(stream)
            True

        Returns ``True`` upon succesful transmission or ``False`` in case of
        failure.

        :param stream: The stream object to send data from.
        :type stream: stream (file, etc.)
        :param retry: The maximum number of times to try to resend a failed
                      packet before failing.
        :type retry: int
        :param timeout: The number of seconds to wait for a response before
                        timing out.
        :type timeout: int
        :param quiet: If 0, it prints info to stderr.  If 1, it does not print any info.
        :type quiet: int
        :param callback: Reference to a callback function that has the
                         following signature.  This is useful for
                         getting status updates while a xmodem
                         transfer is underway.
                         Expected callback signature:
                         def callback(total_packets, success_count, error_count)
        :type callback: callable
        '''
        assert delay != None, "Invalid Delay."
        if self.ymodem_mode:
            assert os.path.isfile(file_io), "Ymodem Mode Enabled and File not passed in."
        else:
            assert hasattr(file_io,"read"), "Stream not readable. "
        assert timeout > delay, "Timeout is less than delay."
        if callback != None:
            assert callable(callback), "Non-null callback isn't callable."


        # initialize protocol
        try:
            packet_size = self.rate.getpacketsize() - 1
        except AttributeError:
            raise ValueError("An invalid mode was supplied")


        if self.ymodem_mode:
            stream = open(file_io,'rb')
        else:
            stream = file_io

        error_count = 0
        crc_mode = 0
        cancel = 0

        #Wait for minipacket containing control character

        while True:
            self.micromodem._daemon_log.info("Waiting On Connection")
            minipacket_data = self._receive_across_link(ack=False, timeout=timeout)

            if minipacket_data:
                if minipacket_data == self.NAK:
                    self.micromodem._daemon_log.info("CRC Mode Off")
                    crc_mode = 0
                    break
                elif minipacket_data == self.CRC:
                    self.micromodem._daemon_log.info("CRC Mode On, Acking")
                    crc_mode = 1
                    self._send_across_link(data=self.ACK,ack=False,timeout=None,delay=delay)
                    break
                elif minipacket_data == self.CAN:
                    self.micromodem._daemon_log.info('received CAN')
                    if cancel:
                        return False
                    else:
                        cancel = 1
                else:
                    self.micromodem._daemon_log.warning('send ERROR expected NAK/CRC, got %s' % (minipacket_data))

                error_count += 1
                if error_count >= retry:
                    self.abort(timeout=timeout)
                    return False
            else:
                self.micromodem._daemon_log.info("No Connection Received in {} secs. Timeout Connection.".format(timeout))
                return False

        #Send Packet Header.

        # send data
        error_count = 0
        success_count = 0
        total_packets = 0
        sequence = 0
        while True:
            #Send Packet Header if in that mode.
            if sequence == 0 and self.ymodem_mode:
                stream.seek(0,2)
                data = os.path.basename(file_io).lower() + " " + \
                       str(stream.tell())
                stream.seek(0,0)
            #Otherwise just send data
            else:
                data = stream.read(packet_size)
            if not data:
                self.micromodem._daemon_log.info('No more data. End of Stream')
                # end of stream
                break
            total_packets += 1
            #data = data.ljust(packet_size, self.pad)
            if crc_mode:
                crc = self.calc_crc(data)
            # emit packet
            while True:
                self.micromodem._daemon_log.info("Starting Transmission")
                self._send_across_link(data=self.STX,ack=False,timeout=None,delay=delay)
                time.sleep(delay)

                #Send our sequence number
                sequence_num = sequence + self.SEQ_NUM_BIT_ID #Add Sequence Bit ID to the front.
                self.micromodem._daemon_log.info("Sending Sequence Number: {} ({})".format(sequence_num, "{:04X}".format(sequence_num)))
                ok = self._send_across_link(data="{:04X}".format(sequence_num),ack=True,timeout=None,delay=delay)
                if not ok:
                    self.micromodem._daemon_log.info('Sequence number not acked, Aborting')
                    self.abort(timeout=timeout)
                    return False

                self.micromodem._daemon_log.info("Sending Data.")
                outgoing_Data = bytearray(data)
                self.micromodem._daemon_log.info("Sending Data: {}".format(repr(outgoing_Data)))
                ok = self._send_across_link(data=outgoing_Data, ack=True, force_packet=True, validate_packet=True)
                if not ok:
                    error_count += 1
                    self.micromodem._daemon_log.warning('Not all frames transfered.')
                    self.abort(timeout=timeout)
                    return False

                if crc_mode:
                    self.micromodem._daemon_log.info("Sending CRC: {} ({:04X})".format(crc, crc + self.CRC_BIT_ID))
                    self._send_across_link(data="{:04X}".format(crc + self.CRC_BIT_ID),ack=False,timeout=None,delay=delay)

                self.micromodem._daemon_log.info("Waiting For Ack.")
                char = self._receive_across_link(ack=False,timeout=None)
                if char == self.ACK:
                    self.micromodem._daemon_log.info("Packet Acked.")
                    success_count += 1
                    if callback != None:
                        callback(total_packets, success_count, error_count)
                    # keep track of sequence
                    sequence = (sequence + 1) % self.MAX_SEQ_NUM
                    break
                if char == self.NAK:
                    self.micromodem._daemon_log.info("Packet Nacked.")
                    error_count += 1
                    if callback != None:
                        callback(total_packets, success_count, error_count)
                    if error_count >= retry:
                        # excessive amounts of retransmissions requested,
                        # abort transfer
                        self.abort(timeout=timeout)
                        self.micromodem._daemon_log.info('excessive NAKs, transfer aborted')
                        return False

                    # return to loop and resend
                    continue
                if char is None:
                    error_count +=1

                # protocol error
                self.abort(timeout=timeout)
                self.micromodem._daemon_log.warning('protocol error')
                return False

        while True:
            self.micromodem._daemon_log.info("Sending EOT")
            # end of transmission
            self._send_across_link(data=self.EOT,ack=False,timeout=None,delay=delay)
            ok = self._receive_across_link(ack=False,timeout=None)
            if ok == self.ACK:
                self.micromodem._daemon_log.info("File Transfer Success.")
                break
            if ok == self.NAK:
                self.micromodem._daemon_log.warning("File Transfer Failed")
                return False
            else:
                error_count += 1
                if error_count >= retry:
                    self.abort(timeout=timeout)
                    self.log.warning('EOT was not ACKd, transfer aborted')
                    return False

        return True

    def recv(self, file_io, crc_mode=1, retry=16, timeout=15, delay=1):
        assert delay != None, "Invalid Delay."
        if self.ymodem_mode:
            assert os.path.isdir(file_io), "Ymodem Mode Enabled and Directory for saving not passed in."
        else:
            assert hasattr(file_io,"write"), "Stream not writeable. "
        assert timeout > delay, "Timeout is less than delay."

        if not self.ymodem_mode:
            stream = file_io

        # initiate protocol
        error_count = 0
        char = 0
        cancel = 0
        size = 0
        while True:
            # first try CRC mode, if this fails,
            # fall back to checksum mode
            if error_count >= retry:
                self.abort(timeout=timeout)
                return None
            elif crc_mode and error_count < (retry / 2):
                self.micromodem._daemon_log.info("Sending CRC Mode")
                ok = self._send_across_link(data=self.CRC,ack=True,timeout=None,delay=delay)
                if not ok:
                        self.micromodem._daemon_log.info("CRC Mode Not Acked. {} Error Count:{}".format(char,error_count))
                        time.sleep(delay)
                        error_count += 1
                        continue
                else:
                        self.micromodem._daemon_log.info("CRC Mode Acked.")
            else:
                crc_mode = 0
                self.micromodem._daemon_log.info("CRC Mode Off. Sending NACK")
                self._send_across_link(data=self.NAK,ack=False,timeout=None,delay=delay)


            self.micromodem._daemon_log.info("Waiting For Start of Transmission.")
            char = self._receive_across_link(ack=False,timeout=None)

            if char == self.STX:
                break
            elif char == self.CAN:
                self.micromodem._daemon_log.info("CAN Received")
                if cancel:
                    self.micromodem._daemon_log.info("Canceling Transaction")
                    return None
                else:
                    cancel = 1
            else:
                self.micromodem._daemon_log.warning("WTF??")
                error_count += 1

        # read data
        error_count = 0
        income_size = 0
        if self.ymodem_mode:
            sequence = 0
        else:
            sequence = 1
        cancel = 0
        filename = ""
        while True:
            while True:
                if char == self.STX:
                    self.micromodem._daemon_log.info("STX received at beginning of packet.")
                    break
                elif char == self.EOT:
                    # We received an EOT, so send an ACK and return the received
                    # data length
                    self.micromodem._daemon_log.info("End of Transmission. Confirming File Transmission.")
                    if self.ymodem_mode:
                        stream.close()
                    if str(income_size) != str(size) and str(size) != "0":
                        self.micromodem._daemon_log.info("Invalid Size: ({} != {}). Nacking".format(str(income_size),str(size)))
                        self._send_across_link(data=self.NAK,ack=False,timeout=None,delay=delay)
                        os.remove(file_io + '/'+ str(filename))
                        return 0
                    self._send_across_link(data=self.ACK,ack=False,timeout=None,delay=delay)
                    return income_size
                elif char == self.CAN:
                    # cancel at two consecutive cancels
                    self.micromodem._daemon_log.info("CAN Received")
                    if cancel:
                        self.micromodem._daemon_log.info("Canceling Transaction")
                        return None
                    else:
                        cancel = 1
                else:
                    self.micromodem._daemon_log.info("recv ERROR expected SOH/EOT, got {}".format(char))
                    error_count += 1
                    if error_count >= retry:
                        self.abort()
                        return None
            # read sequence
            error_count = 0
            cancel = 0
            self.micromodem._daemon_log.info("Waiting For Sequence Number.")
            seq = self._receive_across_link(ack=True,timeout=None)


            self.micromodem._daemon_log.info("Waiting For Data.")
            data = self._receive_across_link(ack=True,timeout=None,force_packet=True)

            if crc_mode:
                    self.micromodem._daemon_log.info("Waiting For CRC.")
                    crc_recv= self._receive_across_link(ack=False,timeout=None)

            real_seq = int("0x{}".format(seq),16)  - self.SEQ_NUM_BIT_ID
            self.micromodem._daemon_log.info("Calculated Sequence Num: {}".format(real_seq))
            data = data.rstrip(self.pad)

            #Process Header
            if real_seq == 0 and self.ymodem_mode:
                (filename,size) = data.split()
                self.micromodem._daemon_log.info("Saving {}/{} of size: {}".format(file_io,filename,size))
                stream = open(file_io + '/'+ str(filename), 'w+')
                valid = 1
            #Otherwise process data.
            elif real_seq == sequence:
                # sequence is ok, read packet
                # packet_size + checksum
                if crc_mode:
                    self.micromodem._daemon_log.info("Calculating CRC")
                    csum = int("0x{}".format(crc_recv),16) - self.CRC_BIT_ID
                    calc_csum = self.calc_crc(str(data))
                    self.micromodem._daemon_log.info('CRC (%04x <> %04x)' % (csum, calc_csum))
                    valid = csum == calc_csum
                else:
                    if data != None:
                        valid = 1
                    else:
                        valid = 0
            # valid data, append chunk
            if valid:
                if real_seq > 0 :
                    income_size += len(data)
                    stream.write(data)
                    stream.flush()
                self.micromodem._daemon_log.info("Acking Data.")
                ok = self._send_across_link(data=self.ACK,ack=False,timeout=None,delay=delay)
                sequence = (sequence + 1) % self.MAX_SEQ_NUM
                char = self._receive_across_link(ack=False,timeout=None,delay=delay)
                continue
            else:
                self.micromodem._daemon_log.warning('expecting sequence %d, got %d' % (sequence, real_seq))

            # something went wrong, request retransmission
            self.micromodem._daemon_log.info("Nacking Data.")
            self._send_across_link(data=self.NAK,ack=False,timeout=None,delay=delay)
            char = self._receive_across_link(ack=False,timeout=None,delay=delay)


class acomms_xmodem(acomms_xymodem):
    def calculate_packet_delay(self, timeout = 30):
        super(acomms_xmodem, self).calculate_packet_delay(timeout)

    def recv(self, file_io, crc_mode = 1, retry = 16, timeout = 15, delay = 1):
        return super(acomms_xmodem, self).recv(file_io, crc_mode, retry, timeout, delay)

    def send(self, file_io, retry = 16, timeout = 15, delay = 1, callback = None):
        return super(acomms_xmodem, self).send(file_io, retry, timeout, delay, callback)

    def __init__(self, micromodem, dest, rate = 1, timeout = 60, pad = '\x1a',
                 unified_log = None, log_path = None):
        super(acomms_xmodem, self).__init__(micromodem, dest, rate, timeout, pad, False, unified_log, log_path)


class acomms_ymodem(acomms_xymodem):
    def calculate_packet_delay(self, timeout = 30):
        super(acomms_ymodem, self).calculate_packet_delay(timeout)

    def __init__(self, micromodem, dest, rate = 1, timeout = 60, pad = '\x1a',
                 unified_log = None, log_path = None):
        super(acomms_ymodem, self).__init__(micromodem, dest, rate, timeout, pad, True, unified_log, log_path)

    def recv(self, file_io, crc_mode = 1, retry = 16, timeout = 15, delay = 1):
        return super(acomms_ymodem, self).recv(file_io, crc_mode, retry, timeout, delay)

    def send(self, file_io, retry = 16, timeout = 15, delay = 1, callback = None):
        return super(acomms_ymodem, self).send(file_io, retry, timeout, delay, callback)



class acomms_zmodem(object):
    def __init__(self, micromodem, dest,rate = 1, timeout=60,pad='\x1a',ymodem_enabled = True,unified_log=None,log_path=None, ):
        assert isinstance(micromodem, Micromodem), "micromodem object isn't a Micromodem: %r" & micromodem
        assert rate in range(0,6), "Invalid Rate: %d" & rate
        assert dest != micromodem.id, "Can't send file to self."
        self.pad = pad

        self.rate = Rates[rate]
        self.micromodem = micromodem
        self.micromodem.set_config('RXP',1)
        self.micromodem.set_config('MOD',1)
        #use CRC-8/CDMA2000 instead of CRC-16 CCITT Unreflected.
        self.calc_crc = crcmod.mkCrcFun(0x19b, rev=False, initCrc=0xff, xorOut=0x00)
        if unified_log is None:
            unified_log = UnifiedLog(log_path=log_path)
        self.log = unified_log.getLogger("xmodem.{0}".format(micromodem.name))
        self.target_id = dest
        self.timeout = timeout
        self.ymodem_mode = True

    SOH = '0001'
    STX = '0002'
    EOT = '0004'
    ACK = '0006'
    DLE = '0010'
    NAK = '0015'
    CAN = '0018'
    CRC = '0043'
