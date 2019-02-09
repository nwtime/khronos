import os
import sys
#my_ntplib_path = './my_ntplib.py'
#sys.path.append(os.path.abspath(my_ntplib_path))
import random
import math
#from my_ntplib import NTPClient
#import sys
import json
from ntplib import NTPClient
from time_update import _linux_adjtime, _linux_adjtime_quick
import time

QUERY_SERVERS = []
SERVERS_POOL = []
STATE_PATH = 'current_s.json'


def update_query_servers(m):
    global QUERY_SERVERS
    global SERVERS_POOL
    server_indices = random.sample(range(len(SERVERS_POOL)), m)
    QUERY_SERVERS = [SERVERS_POOL[idx] for idx in server_indices]
    json.dump(QUERY_SERVERS, open(STATE_PATH, 'wb'),
              sort_keys=True, indent=4, separators=(',', ': '))


def read_query_servers():
    global QUERY_SERVERS
    if os.path.isfile(STATE_PATH):
        QUERY_SERVERS = json.load(file(STATE_PATH, "rb"))


def read_servers_pool(pool_path='chronos_servers_pool.json'):
    global SERVERS_POOL
    if os.path.isfile(pool_path):
        SERVERS_POOL = json.load(file(pool_path, "rb"))


def req_multiple_servers(servers=QUERY_SERVERS):
    """
    send requests to a chosen list of ips, return the offsets they return
    :param server_indices:
    :return:
    """
    ntp_client = NTPClient()
    responses = []
    ips_failed = []
    for ip in servers:
        try:
            responses.append(ntp_client.request(ip))
        except Exception as err:
            ips_failed.append(ip)
            print ip, err
    for ip in ips_failed:
        try:
            responses.append(ntp_client.request(ip))
        except Exception as err:
            print ip, err
    return [res.offset for res in responses if res]


def get_offset(m, d, k, w, err):
    if len(QUERY_SERVERS) != m:
        update_query_servers(m)

    retries = 0
    while retries < k:

        # query chosen servers
        offsets = req_multiple_servers(QUERY_SERVERS)
        offsets.sort()

        # trim d from each side of the server responses (offsets)
        t = int(d * m)
        T = offsets[t:m - t]

        # check whether all surviving samples are "close"
        avg_offset = sum(T) / len(T)
        if (
                (math.fabs(max(T) - min(T)) <= 2 * w) and
                (math.fabs(avg_offset) <= w * 2 + err)
        ):
                return avg_offset
        retries += 1
        print "failure %d: %f > %f and/or %f > %f" % (
            retries, math.fabs(max(T) - min(T)), 2 * w, math.fabs(avg_offset), w * 2 + err)
    print("PANIC")
    raise Exception("Panic!")
    # PANIC
    offsets = req_multiple_servers(SERVERS_POOL)
    offsets.sort()
    t = int(d * m)
    T = offsets[t:m - t]
    avg_offset = sum(T) / float(len(T))
    return avg_offset


def get_offset_quick(m, d, k, w, err):
    if len(QUERY_SERVERS) != m:
        update_query_servers(m)

    retries = 0
    while retries < k:

        # query chosen servers
        offsets = req_multiple_servers(QUERY_SERVERS)
        offsets.sort()

        # trim d from each side of the server responses (offsets)
        t = int(d * m)
        T = offsets[t:m - t]

        # check whether all surviving samples are "close"
        avg_offset = sum(T) / len(T)
        if (
                (math.fabs(max(T) - min(T)) <= 2 * w)
        ):
                return avg_offset
        retries += 1
        print "failure %d: %f > %f" % (retries, math.fabs(max(T) - min(T)), 2 * w)
    print("PANIC")
    raise Exception("Panic!")
    # PANIC
    offsets = req_multiple_servers(SERVERS_POOL)
    offsets.sort()
    t = int(d * m)
    T = offsets[t:m - t]
    avg_offset = sum(T) / float(len(T))
    return avg_offset


def update_loop(update_query_interval, query_interval, server_pool_path, state_path, start_quick, output_path, **query_args):
    global QUERY_SERVERS
    global STATE_PATH
    STATE_PATH = state_path
    read_servers_pool(server_pool_path)
    r = int(update_query_interval / query_interval)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    file_name = timestamp + "_chronos_offsets.csv"
    file_path = os.path.join(output_path, file_name)
    out = file(file_path, "w")
    if start_quick:
        print "start quick"
        offset = get_offset_quick(**query_args)
        print _linux_adjtime_quick(offset)
        print "quick offset =", offset
        out.write("%f,%f\n" % (time.time(), offset))
        time.sleep(query_interval)
    while 1:
        QUERY_SERVERS = []
        for i in range(r):
            offset = get_offset(**query_args)
            print _linux_adjtime(offset)
            print "offset =", offset
            out.write("%f,%f\n" % (time.time(), offset))
            time.sleep(query_interval)


# sudo python /media/sf_temp/chronos_d.py -m 5 -d 0.2 -p /media/sf_temp/chronos_servers_pool.json -S /media/sf_temp/current_s.json
# sudo python /media/sf_temp/chronos_d.py -m 5 -d 0.2 -p /media/sf_temp/chronos_servers_pool.json -S /media/sf_temp/current_s.json -w 0.025 -e 0.05 -o /media/sf_temp/
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-m", "--query_size", type=int, default=9,
                        help="number of servers to query")
    parser.add_argument("-d", "--filter_bounds", type=float, default=0.334,
                        help="ratio of m to filter from each side")
    parser.add_argument("-k", "--panic_threshold", type=int, default=5,
                        help="number of update failure before panic")
    parser.add_argument("-w", "--distance_threshold", type=float, default=0.025,
                        help="offsets distance threshold")
    parser.add_argument("-e", "--local_error_bound", type=float, default=0.025,
                        help="offsets distance threshold")
    parser.add_argument("-u", "--update_query_interval", type=float, default=60.0,
                        help="time interval between choosing new m servers")
    parser.add_argument("-q", "--query_interval", type=float, default=10.0,
                        help="time interval between queries")
    parser.add_argument("-p", "--server_pool", default='chronos_servers_pool.json',
                        help="path for json of pool servers")
    parser.add_argument("-S", "--state", default='current_s.json',
                        help="path for json of chronos state (last queried servers)")
    parser.add_argument("-s", "--start_quick", action="store_true",
                        help="start with full update not smooth")
    parser.add_argument("-c", "--conf_path", default=None,
                        help="path for json of chronos configuration (overides all other params)")
    parser.add_argument("-o", "--output_path", default=".",
                        help="path output directory")
    args = parser.parse_args()

    conf = dict(
        m=args.query_size,
        d=args.filter_bounds,
        k=args.panic_threshold,
        w=args.distance_threshold,
        err=args.local_error_bound,
        update_query_interval=args.update_query_interval,
        query_interval=args.query_interval,
        server_pool_path=args.server_pool,
        state_path=args.state,
        start_quick=args.start_quick,
        output_path=args.output_path
    )
    if args.conf_path:
        fconf = json.load(file(args.conf_path))
        conf.update(fconf)
        json.dump(conf, file(args.conf_path, "wb"),
              sort_keys=True, indent=4, separators=(',', ': '))

    update_loop(**conf)




