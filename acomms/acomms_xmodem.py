__author__ = 'andrew'

#This is an implementation of the Xmodem Protocol modified for the Microcmodem IO methods.
from messageparams import Rates, FDPRates, data_from_hexstring, hexstring_from_data
from unifiedlog import UnifiedLog
from acomms import Micromodem
import crcmod
import time
import sys


class acomms_xmodem(object):
    '''
    XMODEM Like Protocol handler, expects an object to read from and an object to
    write to.
    :type mode: string
    :param pad: Padding character to make the packets match the packet size
    :type pad: char
    '''

    def __init__(self, micromodem, dest,rate = 1, timeout=60,pad='\x1a',unified_log=None,log_path=None, ):
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

    SOH = '0001'
    STX = '0002'
    EOT = '0004'
    ACK = '0006'
    DLE = '0010'
    NAK = '0015'
    CAN = '0018'
    CRC = '0043'

    def calculate_packet_delay(self,timeout=30):
        #determine distance between nodes for 1-way travel time delay estimates.
        self.micromodem.send_ping(dest_id=self.target_id)
        delay = int(self.micromodem.wait_for_ping_reply(dest_id=self.target_id,timeout=timeout))  + 3 #Each packet takes roughly 3 seconds to transmit


    def abort(self, count=2, timeout=60):
        '''
        Send an abort sequence using CAN bytes.
        '''
        for counter in xrange(0, count):
            print ("Sending CAN")
            self.micromodem.send_minipacket(dest_id=self.target_id,databytes=self.CAN)
            self.micromodem.wait_for_xst(timeout)


    def send(self, stream, retry=16, timeout=15, delay = 1, callback=None):
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
        assert hasattr(stream,"read"), "Stream not readable. "
        assert timeout > delay, "Timeout is less than delay."
        if callback != None:
            assert callable(callback), "Non-nulll callback isn't callable."


        # initialize protocol
        try:
            packet_size = self.rate.getpacketsize()
        except AttributeError:
            raise ValueError("An invalid mode was supplied")



        error_count = 0
        crc_mode = 0
        cancel = 0

        #Wait for minipacket containing control character

        while True:
            print("Waiting On Connection")
            minipacket_data = self.micromodem.wait_for_minipacket(timeout=None)

            if minipacket_data:
                if minipacket_data == self.NAK:
                    print("CRC Mode Off")
                    crc_mode = 0
                    break
                elif minipacket_data == self.CRC:
                    print("CRC Mode On, Acking")
                    crc_mode = 1
                    self.micromodem.send_minipacket(dest_id=self.target_id,databytes=self.ACK)
                    self.micromodem.wait_for_xst(timeout)
                    time.sleep(delay)
                    break
                elif minipacket_data == self.CAN:
                    print('received CAN')
                    if cancel:
                        return False
                    else:
                        cancel = 1
                else:
                    print('send ERROR expected NAK/CRC, got %s' % (minipacket_data))

            error_count += 1
            if error_count >= retry:
                self.abort(timeout=timeout)
                return False

        # send data
        error_count = 0
        success_count = 0
        total_packets = 0
        sequence = 1
        while True:
            data = stream.read(packet_size)
            if not data:
                print('sending EOT')
                # end of stream
                break
            total_packets += 1
            data = data.ljust(packet_size, self.pad)
            if crc_mode:
                crc = self.calc_crc(data)
            # emit packet
            while True:
                print("Starting Transmission")
                self.micromodem.send_minipacket(dest_id=self.target_id,databytes=self.STX)
                self.micromodem.wait_for_xst(timeout)
                time.sleep(delay)
                #Send our sequence number
                sequence_num = 3840 + sequence
                print("Sending Sequence Number: {} ({})".format(sequence_num, "{:04X}".format(sequence_num)))
                self.micromodem.send_minipacket(dest_id=self.target_id,databytes="{:04X}".format(sequence_num))
                self.micromodem.wait_for_xst(timeout)
                print ("Waiting for ACK")
                char = self.micromodem.wait_for_minipacket(timeout=None)
                if char != self.ACK:
                    print('Sequence number not acked, Restarting aborted')
                    continue
                print ("Sending Data.")
                self.micromodem.send_packet_data(dest=self.target_id, databytes=data, rate_num=self.rate.number, ack=True)
                xst = self.micromodem.wait_for_xst(timeout=None)
                time.sleep(delay * self.rate.numframes)
                if xst['num_frames_sent'] != xst['num_frames_expected']:
                    error_count += 1
                    print('Not all frames transfered.')
                    if error_count >= retry:
                        # excessive amounts of retransmissions requested,
                        # abort transfer
                        self.abort(timeout=timeout)
                        return False
                    continue
                self.micromodem.wait_for_nmea_type('CAACK',timeout=None)

                if crc_mode:
                    print("Sending CRC: {} ({:04X})".format(crc, crc + 4864))
                    time.sleep(5)
                    self.micromodem.send_minipacket(dest_id=self.target_id,databytes="{:04X}".format(crc + 4864))
                    self.micromodem.wait_for_xst(timeout)

                char = self.micromodem.wait_for_minipacket(timeout=None)
                if char == self.ACK:
                    success_count += 1
                    if callback != None:
                        callback(total_packets, success_count, error_count)
                    break
                if char == self.NAK:
                    error_count += 1
                    if callback != None:
                        callback(total_packets, success_count, error_count)
                    if error_count >= retry:
                        # excessive amounts of retransmissions requested,
                        # abort transfer
                        self.abort(timeout=timeout)
                        print('excessive NAKs, transfer aborted')
                        return False

                    # return to loop and resend
                    continue
                if char is None:
                    error_count +=1

                # protocol error
                self.abort(timeout=timeout)
                print('protocol error')
                return False

            # keep track of sequence
            sequence = (sequence + 1) % 256

        while True:
            print("Sending EOT")
            # end of transmission
            self.micromodem.send_minipacket(dest_id=self.target_id,databytes=self.EOT)
            self.micromodem.wait_for_xst(timeout)
            #An ACK should be returned
            char = self.micromodem.wait_for_minipacket(timeout=None)
            if char == self.ACK:
                break
            else:
                error_count += 1
                if error_count >= retry:
                    self.abort(timeout=timeout)
                    self.log.warning('EOT was not ACKd, transfer aborted')
                    return False

        return True

    def recv(self, stream, crc_mode=1, retry=16, timeout=15, delay=1):
        assert delay != None, "Invalid Delay."
        assert hasattr(stream,"write"), "Stream not writeable. "
        assert timeout > delay, "Timeout is less than delay."
        # initiate protocol
        error_count = 0
        char = 0
        cancel = 0
        while True:
            # first try CRC mode, if this fails,
            # fall back to checksum mode
            if error_count >= retry:
                self.abort(timeout=timeout)
                return None
            elif crc_mode and error_count < (retry / 2):
                print("Sending CRC Mode")
                self.micromodem.send_minipacket(dest_id=self.target_id,databytes=self.CRC)
                self.micromodem.wait_for_xst(timeout)
                char = self.micromodem.wait_for_minipacket(timeout = None)
                if char != self.ACK:
                    print("CRC Mode Not Acked. {} Error Count:{}".format(char,error_count))
                    time.sleep(delay)
                    error_count += 1
                else:
                    print("CRC Mode Acked.")
            else:
                crc_mode = 0
                print("CRC Mode Off. Sending NACK")
                self.micromodem.send_minipacket(dest_id=self.target_id,databytes=self.NAK)
                self.micromodem.wait_for_xst(timeout)

            print("Waiting For Start of Transmission.")
            char = self.micromodem.wait_for_minipacket(timeout = None)
            if char == self.STX:
                break
            elif char == self.CAN:
                print("CAN Received")
                if cancel:
                    print("Canceling Transaction")
                    return None
                else:
                    cancel = 1
            else:
                error_count += 1

        # read data
        error_count = 0
        income_size = 0
        sequence = 1
        cancel = 0
        while True:
            while True:
                if char == self.STX:
                    print("STX received at beginning of packet.")
                    break
                elif char == self.EOT:
                    # We received an EOT, so send an ACK and return the received
                    # data length
                    print("End of Transmission. Acking.")
                    self.micromodem.send_minipacket(dest_id=self.target_id,databytes=self.ACK)
                    self.micromodem.wait_for_xst(timeout)
                    return income_size
                elif char == self.CAN:
                    # cancel at two consecutive cancels
                    print("CAN Received")
                    if cancel:
                        print("Canceling Transaction")
                        return None
                    else:
                        cancel = 1
                else:
                    print 'recv ERROR expected SOH/EOT, got {}'.format(ord(char))
                    error_count += 1
                    if error_count >= retry:
                        self.abort()
                        return None
            # read sequence
            error_count = 0
            cancel = 0
            print("Waiting For Sequence Number.")
            seq =self.micromodem.wait_for_minipacket(timeout=None)
            print("Acking Sequence Number {}.".format(seq))
            self.micromodem.send_minipacket(dest_id=self.target_id,databytes=self.ACK)
            self.micromodem.wait_for_xst(timeout=None)
            print("Waiting For Data.")
            data = self.micromodem.wait_for_data_packet()
            if crc_mode:
                    print("Waiting For CRC.")
                    crc_recv = self.micromodem.wait_for_minipacket(timeout=None)
            real_seq = int("0x{}".format(seq),16)  - 3840
            print "Calculated Sequence Num: {}".format(real_seq)
            if real_seq == sequence:
                # sequence is ok, read packet
                # packet_size + checksum
                if crc_mode:
                    csum = int("0x{}".format(crc_recv),16) - 4864
                    print('CRC (%04x <> %04x)' % (csum, self.calc_crc(data)))
                    valid = csum == self.calc_crc(data)
                else:
                    if data != None:
                        valid = 1
                    else:
                        valid = 0
                # valid data, append chunk
                if valid:
                    income_size += len(data)
                    stream.write(data)
                    print("Acking Data.")
                    self.micromodem.send_minipacket(dest_id=self.target_id,databytes=self.ACK)
                    self.micromodem.wait_for_xst(timeout)
                    time.sleep(delay)
                    sequence = (sequence + 1) % 256
                    char = self.micromodem.wait_for_minipacket(timeout=None)
                    continue
            else:
                print('expecting sequence %d, got %d' % (sequence, real_seq))

            # something went wrong, request retransmission
            print("Nacking Data.")
            self.micromodem.send_minipacket(dest_id=self.target_id,databytes=self.NAK)
            self.micromodem.wait_for_xst(timeout)
            time.sleep(delay)


