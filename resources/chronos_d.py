'''Copyright (c) <2019> <Neta Rozen Schiff>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.'''


import os
import socket
import random
import math
import json
from ntplib import NTPClient
from time_update import _linux_adjtime, _linux_adjtime_quick
import time


QUERY_SERVERS = []
SERVERS_POOL = []
STATE_PATH = 'current_s.json'


def calibration(n, server_pool_path, zone_pools_path, zone, max_time_secs=2*60*60):
    print("Starting to calibrate servers pool.")
    urls = json.load(open(zone_pools_path, 'r'))
    zone_urls = urls[zone]
    final_server_list = set()
    iterations = 1
    start = time.time()
    t = start
    while len(final_server_list) < n and t-start < max_time_secs:
        for url in zone_urls:
            print url
            ips = set(socket.gethostbyname_ex(url)[2])
            final_server_list |= ips
        print 'iteration {iterations}, so far collected {k} servers.'.format(
            iterations=iterations,
            k=len(final_server_list))
        json.dump(list(final_server_list), open(server_pool_path, 'wb'),
                      sort_keys=True, indent=4, separators=(',', ': '))
        iterations += 1
        print "going to sleep"
        time.sleep(60)
        t = time.time()


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
    responses = {}
    ips_failed = []
    for ip in servers:
        try:
            responses[ip] = ntp_client.request(ip)
        except Exception as err:
            ips_failed.append(ip)
            print ip, err
    for ip in ips_failed:
        try:
            responses[ip] = ntp_client.request(ip)
        except Exception as err:
            print ip, err
    return {ip: responses[ip].offset for ip in servers if ip in responses}


def get_offset_simple(m, d, k, w, err, servers):

    # query chosen servers
    T = req_multiple_servers(servers).values()
    # check whether all surviving samples are "close"
    avg_offset = sum(T) / len(T)
    if (
            (math.fabs(max(T) - min(T)) <= 2 * w) and
            (math.fabs(avg_offset) <= w * 2 + err)
    ):
            return avg_offset
    print "failure: %f > %f and/or %f > %f" % (
        math.fabs(max(T) - min(T)), 2 * w, math.fabs(avg_offset), w * 2 + err)
    return None


def get_offset(m, d, k, w, err):
    if len(QUERY_SERVERS) != m:
        update_query_servers(m)

    retries = 0
    while retries < k:

        # query chosen servers
        offsets_dict = req_multiple_servers(QUERY_SERVERS)
        sorted_servers = sorted(offsets_dict.keys(), key=offsets_dict.get)
        mm = len(offsets_dict)

        # trim d from each side of the server responses (offsets)
        t = int(d * mm)
        trimmed_servers = sorted_servers[t:mm - t]

        T = [offsets_dict[s] for s in trimmed_servers]
        min_offset = min(T, key=math.fabs)

        # check whether all surviving samples are "close"
        avg_offset = sum(T) / len(T)
        if (
                (math.fabs(max(T) - min(T)) <= 2 * w) and
                (math.fabs(avg_offset) <= w * 2 + err)
        ):
                return avg_offset, trimmed_servers, min_offset
        retries += 1
        print "failure %d: %f > %f and/or %f > %f" % (
            retries, math.fabs(max(T) - min(T)), 2 * w, math.fabs(avg_offset), w * 2 + err)
        update_query_servers(m)
    # PANIC
    print("PANIC")
    #raise Exception("Panic!")

    offsets_dict = req_multiple_servers(SERVERS_POOL)
    sorted_servers = sorted(offsets_dict.keys(), key=offsets_dict.get)
    mm = len(offsets_dict)
    t = int(d * mm)
    trimmed_servers = sorted_servers[t:mm - t]
    T = [offsets_dict[s] for s in trimmed_servers]
    avg_offset = sum(T) / float(len(T))
    return avg_offset, None, None


def get_offset_quick(m, d, k, w, err):
    if len(QUERY_SERVERS) != m:
        update_query_servers(m)

    retries = 0
    while retries < k:

        # query chosen servers
        offsets = req_multiple_servers(QUERY_SERVERS).values()
        #offsets = req_multiple_servers(SERVERS_POOL)
        offsets.sort()

        # trim d from each side of the server responses (offsets)
        mm = len(offsets)
        t = int(d * mm)
        T = offsets[t:mm - t]

        # check whether all surviving samples are "close"
        avg_offset = sum(T) / len(T)
        if (
                (math.fabs(max(T) - min(T)) <= 2 * w)
        ):
                return avg_offset
        retries += 1
        print "failure %d: %f > %f" % (retries, math.fabs(max(T) - min(T)), 2 * w)
        update_query_servers(m)
    # PANIC
    print("PANIC")
    #raise Exception("Panic!")
    offsets = req_multiple_servers(SERVERS_POOL).values()
    offsets.sort()
    mm = len(offsets)
    t = int(d * mm)
    T = offsets[t:mm - t]
    avg_offset = sum(T) / float(len(T))
    return avg_offset


def update_loop1(update_query_interval, query_interval, server_pool_path, state_path, start_quick, output_path, conf_path=None, **query_args):
    global QUERY_SERVERS
    global STATE_PATH
    STATE_PATH = state_path
    read_servers_pool(server_pool_path)
    r = int(update_query_interval / query_interval)
    print "r=", r
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    file_name = timestamp + "_chronos_offsets.csv"
    #file_path = os.path.join(output_path, file_name)
    file_path = output_path + file_name
    if conf_path:
        os.system("cp %s %s" % (conf_path, file_path[:-3]+"json") )
    out = file(file_path, "w")
    if start_quick:
        print "start quick"
        offset = get_offset_quick(**query_args)
        print "quick offset =", offset
        print _linux_adjtime_quick(offset)
        out.write("%f,%f\n" % (time.time(), offset))
        time.sleep(query_interval)
    last_offset = 0

    while 1:
        QUERY_SERVERS = []
        for i in range(r):
            offset, _, _ = get_offset(**query_args)
            if math.fabs(offset - last_offset) < 0.001:
                offset = last_offset
            else:
                offset = int(offset*1000) / 1000.0
                last_offset = offset
            print "offset =", offset
            print _linux_adjtime(offset)
            out.write("%f,%f\n" % (time.time(), offset))
            time.sleep(query_interval)


def update_loop(update_query_interval, query_interval, server_pool_path, state_path, start_quick, output_path, conf_path=None, **query_args):
    global QUERY_SERVERS
    global STATE_PATH
    STATE_PATH = state_path
    read_servers_pool(server_pool_path)
    r = int(update_query_interval / query_interval)
    print "r=", r
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    file_name = timestamp + "_chronos_offsets.csv"
    #file_path = os.path.join(output_path, file_name)
    file_path = output_path + file_name
    if conf_path:
        os.system("cp %s %s" % (conf_path, file_path[:-3]+"json") )
    out = file(file_path, "w")
    if start_quick:
        print "start quick"
        offset = get_offset_quick(**query_args)
        print "quick offset =", offset
        print _linux_adjtime_quick(offset)
        out.write("%f,%f\n" % (time.time(), offset))
        time.sleep(query_interval)

    while 1:
        QUERY_SERVERS = []
        for i in range(r):
            offset, _, min_offset = get_offset(**query_args)
            if min_offset is not None and math.fabs(offset - min_offset) < 0.001:
                offset = min_offset
            #else:
            #    offset = int(offset*1000) / 1000.0
            #offset = offset / 4
            thresh = 0.0005
            if math.fabs(offset) < thresh:
                offset = 0
            elif offset < 0:
                offset += thresh
            else:
                offset -= thresh
            print "offset =", offset
            print _linux_adjtime(offset)
            out.write("%f,%f\n" % (time.time(), offset))
            time.sleep(query_interval)


def update_loop2(update_query_interval, query_interval, server_pool_path, state_path, start_quick, output_path, conf_path=None, old_distance_thresh=0.010, **query_args):
    global QUERY_SERVERS
    global STATE_PATH
    STATE_PATH = state_path
    read_servers_pool(server_pool_path)
    r = int(update_query_interval / query_interval)
    print "r=", r
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    file_name = timestamp + "_chronos_offsets.csv"
    #file_path = os.path.join(output_path, file_name)
    file_path = output_path + file_name
    if conf_path:
        os.system("cp %s %s" % (conf_path, file_path[:-3]+"json") )
    out = file(file_path, "w")
    if start_quick:
        print "start quick"
        offset = get_offset_quick(**query_args)
        print "quick offset =", offset
        print _linux_adjtime_quick(offset)
        out.write("%f,%f\n" % (time.time(), offset))
        time.sleep(query_interval)

    QUERY_SERVERS = []
    old_offset, old_servers, _ = get_offset(**query_args)
    #old_offset = old_offset/4
    print "offset =", old_offset
    print _linux_adjtime(old_offset)
    out.write("%f,%f\n" % (time.time(), old_offset))
    time.sleep(query_interval)

    while 1:
        for i in range(r):
            if old_servers is not None:
                old_offset = get_offset_simple(servers=old_servers, **query_args)
            else:
                old_offset = None
            print "old_servers_offset =", old_offset
            new_offset, new_servers, _ = get_offset(**query_args)
            print "new_offset =", new_offset
            if old_offset is not None and math.fabs(new_offset - old_offset) > old_distance_thresh:
                print "using new offset"
                offset = new_offset
                old_servers = new_servers
            else:
                print "using old offset"
                offset = old_offset
            print _linux_adjtime(offset)
            out.write("%f,%f\n" % (time.time(), offset))
            time.sleep(query_interval)
        QUERY_SERVERS = []

# sudo python /media/sf_temp/chronos_d.py -m 5 -d 0.2 -p /media/sf_temp/chronos_servers_pool.json -S /media/sf_temp/current_s.json
# sudo python /media/sf_temp/chronos_d.py -m 5 -d 0.2 -p /media/sf_temp/chronos_servers_pool.json -S /media/sf_temp/current_s.json -w 0.025 -e 0.05 -o /media/sf_temp/
# sudo python /media/sf_temp/chronos_d.py -m 5 -d 0.2 -p /media/sf_temp/chronos_servers_pool_0.json -S /media/sf_temp/current_s_0.json -w 0.025 -e 0.05 -o /media/sf_temp/ -n 200 -M 300 -C -Z /media/sf_temp/zone_pools.json
# sudo service ntp stop
# sudo python chronos_d.py -m 12 -d 0.34  -w 0.025 -e 0.05 -n 500 -M 36000 -C -z usa -p chronos_servers_pool_oragon.json
# sudo python chronos_d.py -m 12 -d 0.34 -n 500 -M 36000 -C -z uk -p chronos_servers_pool_oragon.json -u 3600 -q 60
# sudo python chronos_d.py -m 12 -d 0.34 -z usa -p chronos_servers_pool_oragon.json -u 3600 -q 60
# sudo python chronos_d.py -m 12 -d 0.34 -n 500 -M 36000 -C -z germany -p chronos_servers_pool_frankfurt.json -u 3600 -q 60
# sudo python chronos_d.py -m 12 -d 0.34 -n 500 -M 36000 -C -z usa -p chronos_servers_pool_virginia.json -u 3600 -q 60
# sudo python chronos_d.py -m 12 -d 0.34 -n 500 -M 36000 -C -z uk -p chronos_servers_pool_london.json -u 3600 -q 60



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
    parser.add_argument("-e", "--local_error_bound", type=float, default=0.05,
                        help="offsets distance threshold")
    parser.add_argument("-u", "--update_query_interval", type=float, default=60.0,
                        help="time interval between choosing new m servers")
    parser.add_argument("-q", "--query_interval", type=float, default=60.0,
                        help="time interval between queries")
    parser.add_argument("-p", "--server_pool_path", default='chronos_servers_pool.json',
                        help="path for json of pool servers")
    parser.add_argument("-S", "--state", default='current_s.json',
                        help="path for json of chronos state (last queried servers)")
    parser.add_argument("-D", "--dont_start_quick", action="store_true",
                        help="dont start with full update (might lead to panic on first update)")
    parser.add_argument("-c", "--conf_path", default=None,
                        help="path for json of chronos configuration (overides all other params)")
    parser.add_argument("-o", "--output_path", default="./",
                        help="path output directory")
    parser.add_argument("-n", "--pool_size", type=int, default=9,
                        help="number of servers in the pool")
    parser.add_argument("-Z", "--zone_pools_path", default='zone_pools.json',
                        help="url per state"),
    parser.add_argument("-z", "--zone", default='global',
                        help="zone for calibration (default:global) [global,europe,uk,usa,germany,syngapore,australia,japan,asia,south_america]")
    parser.add_argument("-C", "--force_calibration", default=False, action="store_true",
                        help="force calibration (generating pool file")
    parser.add_argument("-M", "--max_calibration_time", type=int, default=2*60*60,
                        help="max calibration time in seconds")
    args = parser.parse_args()

    conf = dict(
        m=args.query_size,
        d=args.filter_bounds,
        k=args.panic_threshold,
        w=args.distance_threshold,
        err=args.local_error_bound,
        update_query_interval=args.update_query_interval,
        query_interval=args.query_interval,
        server_pool_path=args.server_pool_path,
        state_path=args.state,
        start_quick=not args.dont_start_quick,
        output_path=args.output_path
    )
    if args.conf_path:
        fconf = json.load(file(args.conf_path))
        conf.update(fconf)
        json.dump(conf, file(args.conf_path, "wb"),
                  sort_keys=True, indent=4, separators=(',', ': '))

    if not os.path.isfile(args.server_pool_path) or args.force_calibration:
        calibration_conf = dict(
            n=args.pool_size,
            server_pool_path=args.server_pool_path,
            zone_pools_path=args.zone_pools_path,
            zone=args.zone,
            max_time_secs=args.max_calibration_time
        )
        calibration(**calibration_conf)

    update_loop(**conf)
    #update_loop2(**conf)




