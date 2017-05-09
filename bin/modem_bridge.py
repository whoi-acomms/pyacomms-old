import argparse
from Queue import Queue
from acomms import Micromodem, nmeaChecksum, unifiedlog
from twisted.internet import reactor
from twisted.internet.protocol import ServerFactory
from twisted.protocols.basic import LineReceiver
import logging


class BridgeProtocol(LineReceiver):
    def __init__(self, factory):
        self.factory = factory
        self.modem = self.factory.modem

    def lineReceived(self, line):
        # If we have data here, pass it to the modem.
        self.modem.write_string(line + "\r\n")

    def connectionMade(self):
        self.factory.clients.append(self)
        self.modem._daemon_log.info('TCP client connected ({} total)'.format(len(self.factory.clients)))

    def connectionLost(self, reason):
        self.factory.clients.remove(self)
        self.modem._daemon_log.info('TCP client disconnected ({} total)'.format(len(self.factory.clients)))

class BridgeFactory(ServerFactory):
    protocol = BridgeProtocol

    def buildProtocol(self, address):
        return BridgeProtocol(self)

class ModemBridge(object):
    def __init__(self):
        self.modem = None
        self.factory = None


    def on_modem_message(self, msg):
        # This is a tad ridiculous
        message = ",".join( [str(p) for p in [ msg['type'] ] + msg['params']] )
        chk = nmeaChecksum( message )
        message = "$" + message.lstrip('$').rstrip('\r\n*') + "*" + chk

        for client in self.factory.clients:
            reactor.callFromThread(client.sendLine,message)
        pass

    def connect_to_iridium(self, number, port, baudrate):
        unified_log = unifiedlog.UnifiedLog(console_log_level=logging.INFO)
        self.modem = Micromodem(unified_log=unified_log)
        self.modem.connect_iridium(number, port, baudrate)

        # Now, attach to NMEA message events.
        self.modem.nmea_listeners.append(self.on_modem_message)

    def start_server(self, port):
        self.factory = BridgeFactory()
        # Stick a property on the factory that we can use.
        self.factory.modem = self.modem
        self.factory.clients = []
        #self.factory.protocol = BridgeProtocol

        reactor.listenTCP(port, self.factory)

    def start_bridge(self, number, serial_port, baudrate, tcp_port):
        self.connect_to_iridium(args.iridium_number, args.iridium_serial_port, args.iridium_baud)
        self.start_server(tcp_port)

        reactor.run()




if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Connect a modem to a socket.')
    #ap.add_argument("-l", "--logfile", help="Save log with specified name")
    ap.add_argument("iridium_number", help="Iridium phone number to dial")
    ap.add_argument("iridium_serial_port", help="Iridium modem serial port")
    ap.add_argument("iridium_baud", help="Iridium modem baud rate")
    ap.add_argument("tcp_server_port", help="Listen on this port")


    args = ap.parse_args()

    bridge = ModemBridge()
    bridge.start_bridge(args.iridium_number, args.iridium_serial_port, int(args.iridium_baud), int(args.tcp_server_port))
