'''********************************************************************
*                                                                     *
* Copyright (c) Network Time Foundation 2026                          *
*                                                                     *
* All Rights Reserved                                                 *
*                                                                     *
* Redistribution and use in source and binary forms, with or without  *
* modification, are permitted provided that the following conditions  *
* are met:                                                            *
* 1. Redistributions of source code must retain the above copyright   *
*    notice, this list of conditions and the following disclaimer.    *
* 2. Redistributions in binary form must reproduce the above          *
*    copyright notice, this list of conditions and the following      *
*    disclaimer in the documentation and/or other materials provided  *
*    with the distribution.                                           *
*                                                                     *
* THIS SOFTWARE IS PROVIDED BY THE AUTHORS ``AS IS'' AND ANY EXPRESS  *
* OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED   *
* WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE  *
* ARE DISCLAIMED. IN NO EVENT SHALL THE AUTHORS OR CONTRIBUTORS BE    *
* LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR *
* CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT   *
* OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR  *
* BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF          *
* LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT           *
* (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE   *
* USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH    *
* DAMAGE.                                                             *
***********************************************************************
'''
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
import argparse

import khronos_utils
from time_update import _linux_adjtime, _linux_adjtime_quick
import time

QUERY_SERVERS = []
SERVERS_POOL = []
STATE_PATH = 'current_s.json'


def calibration(n, server_pool_path, zone_pools_path, zone, max_time_secs=2 * 60 * 60):
    print("Starting to calibrate servers pool.")
    dns_name_list = json.load(open(zone_pools_path, 'r'))
    zone_dns_names = dns_name_list[zone]
    final_server_list = set()
    iterations = 1
    start = time.time()
    current_time = start
    while len(final_server_list) < n and current_time - start < max_time_secs:
        for dns_name in zone_dns_names:
            print(dns_name)
            ips = set(socket.gethostbyname_ex(dns_name)[2])
            final_server_list |= ips
        print('iteration {iterations}, so far collected {k} servers.'.format(
            iterations=iterations,
            k=len(final_server_list)))
        json.dump(list(final_server_list), open(server_pool_path, 'w'),
                  indent=4, separators=(',', ': '))
        iterations += 1
        print("going to sleep")
        time.sleep(60)
        current_time = time.time()


def get_random_server_list_from_pool(m):
    global QUERY_SERVERS
    global SERVERS_POOL
    server_indices = random.sample(range(len(SERVERS_POOL)), m)
    QUERY_SERVERS = [SERVERS_POOL[idx] for idx in server_indices]
    json.dump(QUERY_SERVERS, open(STATE_PATH, 'w'), indent=4, separators=(',', ': '))

def get_offset_list_from_pool(d, w, err=0):
    global QUERY_SERVERS
    global SERVERS_POOL
    # query chosen servers
    offsets_dict = khronos_utils.req_multiple_server_offsets(QUERY_SERVERS)
    sorted_servers = sorted(offsets_dict.keys(), key=offsets_dict.get)
    offset_list_size = len(offsets_dict)

    # trim d from each side of the server responses (offsets)
    needed_size = int(d * offset_list_size)
    trimmed_servers = sorted_servers[needed_size:offset_list_size - needed_size]

    offset_list = [offsets_dict[s] for s in trimmed_servers]
    return offset_list, trimmed_servers

def panic_threshhold_reached(k, len_list, len_servers):
    logger.warning(f"Panic threshhold of {k} reached for {len_list} offsets from {len_servers} in servers pool")

def get_offset(m, d, k, w, err=0.0):
    if len(QUERY_SERVERS) != m:
        get_random_server_list_from_pool(m)

    retries = 0
    while retries < k:
        offset_list, trimmed_servers = get_offset_list_from_pool(d, w, err)
        #Make sure we have offsets to work with
        if len(offset_list) == 0:
            logger.error("No servers available")
            return None, None, None

        min_offset = min(offset_list, key=math.fabs)

        # check whether all surviving samples are "close"
        avg_offset = sum(offset_list) / len(offset_list)
        if (
                (math.fabs(max(offset_list) - min(offset_list)) <= 2 * w) and
                (math.fabs(avg_offset) <= w * 2 + err)
        ):
            return avg_offset, trimmed_servers, min_offset
        retries += 1
        print(")failure %d: %f > %f and/or %f > %f" % (
            retries, math.fabs(max(offset_list) - min(offset_list)), 2 * w, math.fabs(avg_offset), w * 2 + err))
        get_random_server_list_from_pool(m)
    # PANIC
    panic_threshhold_reached(k, len(offset_list), len(trimmed_servers))

    # The randomly selected servers failed to get a good response
    # so we try again with the whole pool and try and get a good selected average
    # unlike the range limit check above it is not checked for the limits
    offsets_dict = khronos_utils.req_multiple_server_offsets(SERVERS_POOL)
    if len(offsets_dict) == 0:
        logger.error("No servers available")
        return None, None, None

    sorted_servers = sorted(offsets_dict.keys(), key=offsets_dict.get)
    offset_size = len(offsets_dict)
    needed_size = int(d * offset_size)
    trimmed_servers = sorted_servers[needed_size:offset_size - needed_size]
    offset_list = [offsets_dict[s] for s in trimmed_servers]
    avg_offset = sum(offset_list) / float(len(offset_list))
    return avg_offset, trimmed_servers, None


def get_offset_quick(m, d, k, w):
    if len(QUERY_SERVERS) != m:
        get_random_server_list_from_pool(m)

    retries = 0
    while retries < k:

        # query chosen servers
        offsets = list(khronos_utils.req_multiple_server_offsets(QUERY_SERVERS).values())
        #offsets = req_multiple_server_offsets(SERVERS_POOL)
        offsets.sort()

        # trim d from each side of the server responses (offsets)
        mm = len(offsets)
        t = int(d * mm)
        offset_list = offsets[t:mm - t]

        # check whether all surviving samples are "close"
        avg_offset = sum(offset_list) / len(offset_list)
        if (
                (math.fabs(max(offset_list) - min(offset_list)) <= 2 * w)
        ):
            return avg_offset
        retries += 1
        print("failure %d: %f > %f" % (retries, math.fabs(max(offset_list) - min(offset_list)), 2 * w))
        get_random_server_list_from_pool(m)
    # PANIC
    print("PANIC")
    #raise Exception("Panic!")
    offsets = khronos_utils.req_multiple_server_offsets(SERVERS_POOL).values()
    offsets.sort()
    mm = len(offsets)
    t = int(d * mm)
    offset_list = offsets[t:mm - t]
    avg_offset = sum(offset_list) / float(len(offset_list))
    return avg_offset


def update_loop1(update_query_interval, query_interval, server_pool_path, state_path, start_quick, output_path,
                 conf_path=None, **query_args):
    global QUERY_SERVERS
    global SERVERS_POOL
    global STATE_PATH
    STATE_PATH = state_path
    SERVERS_POOL = khronos_utils.read_server_list(server_pool_path)
    r = int(update_query_interval / query_interval)
    print("r=", r)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    file_name = timestamp + "_khronos_offsets.csv"
    #file_path = os.path.join(output_path, file_name)
    file_path = output_path + file_name
    if conf_path:
        os.system("cp %s %s" % (conf_path, file_path[:-3] + "json"))
    out = khronos_utils.open_write_file(file_path, "w")
    if start_quick:
        print("start quick")
        offset = get_offset_quick(**query_args)
        print("quick offset =", offset)
        print(_linux_adjtime_quick(offset))
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
                offset = int(offset * 1000) / 1000.0
                last_offset = offset
            print("offset =", offset)
            print(_linux_adjtime(offset))
            out.write("%f,%f\n" % (time.time(), offset))
            time.sleep(query_interval)


def update_loop(update_query_interval, query_interval, server_pool_path, state_path, start_quick, output_path,
                conf_path=None, **query_args):
    global QUERY_SERVERS
    global SERVERS_POOL
    global STATE_PATH
    loop_count = 0
    thresh = 0.0005
    delta = 0.0
    last_offset = 0.0
    STATE_PATH = state_path
    SERVERS_POOL = khronos_utils.read_server_list(server_pool_path)
    r = int(update_query_interval / query_interval)
    print("r=", r)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    file_name = timestamp + "_khronos_offsets.csv"
    #file_path = os.path.join(output_path, file_name)
    file_path = output_path + file_name
    if conf_path:
        os.system("cp %s %s" % (conf_path, file_path[:-3] + "json"))
    out = khronos_utils.open_write_file(file_path, "w")
    if start_quick:
        print("start quick")
        # offset = get_offset_quick(**query_args)
        offset = get_offset_quick(query_args["m"], query_args["d"], query_args["k"], query_args["w"])
        print("quick offset =", offset)
        # print (_linux_adjtime_quick(offset))
        out.write("%f,%f\n" % (time.time(), offset))
        time.sleep(query_interval)

    err = 0.0 #Initially no error
    while 1:
        QUERY_SERVERS = []
        for i in range(r):
            loop_count += 1
            offset, _, min_offset = get_offset(query_args["m"], query_args["d"], query_args["k"], query_args["w"])
            if offset == None:
                logger.error("offset not available")
            else:
                if min_offset is not None and math.fabs(delta) < 0.001:
                    delta = offset - min_offset
                    offset = min_offset
                #else:
                #    offset = int(offset*1000) / 1000.0
                #offset = offset / 4
                if math.fabs(offset) < thresh:
                    offset = 0
                    print("offset set to 0")
                elif offset < 0:
                    offset += thresh
                    print(f"offset increased by {thresh}")
                else:
                    offset -= thresh
                    print(f"offset decreased by {thresh}")
                print(f"count = {loop_count}, ind = {i}, offset = {offset}, delta = {delta}, min_offset = {min_offset}")
                # print (_linux_adjtime(offset))
                out.write("%f,%f\n" % (time.time(), offset))
                last_offset = offset

            time.sleep(query_interval)


def update_loop2(update_query_interval, query_interval, server_pool_path, state_path, start_quick, output_path,
                 conf_path=None, old_distance_thresh=0.010, **query_args):
    global QUERY_SERVERS
    global SERVERS_POOL
    global STATE_PATH
    STATE_PATH = state_path
    SERVERS_POOL = khronos_utils.read_server_list(server_pool_path)
    r = int(update_query_interval / query_interval)
    print("r=", r)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    file_name = timestamp + "_khronos_offsets.csv"
    #file_path = os.path.join(output_path, file_name)
    file_path = output_path + file_name
    if conf_path:
        os.system("cp %s %s" % (conf_path, file_path[:-3] + "json"))
    out = khronos_utils.open_write_file(file_path, "w")
    if start_quick:
        print("start quick")
        offset = get_offset_quick(**query_args)
        print("quick offset =", offset)
        print(_linux_adjtime_quick(offset))
        out.write("%f,%f\n" % (time.time(), offset))
        time.sleep(query_interval)

    QUERY_SERVERS = []
    old_offset, old_servers, _ = get_offset(**query_args)
    #old_offset = old_offset/4
    print("offset =", old_offset)
    print(_linux_adjtime(old_offset))
    out.write("%f,%f\n" % (time.time(), old_offset))
    time.sleep(query_interval)

    while 1:
        for i in range(r):
            if old_servers is not None:
                old_offset = khronos_utils.get_offset_simple(servers=old_servers, **query_args)
            else:
                old_offset = None
            print("old_servers_offset =", old_offset)
            new_offset, new_servers, _ = get_offset(**query_args)
            print("new_offset =", new_offset)
            if old_offset is not None and math.fabs(new_offset - old_offset) > old_distance_thresh:
                print("using new offset")
                offset = new_offset
                old_servers = new_servers
            else:
                print("using old offset")
                offset = old_offset
            print(_linux_adjtime(offset))
            out.write("%f,%f\n" % (time.time(), offset))
            time.sleep(query_interval)
        QUERY_SERVERS = []

# sudo python /media/sf_temp/khronos_d.py -m 5 -d 0.2 -p /media/sf_temp/khronos_servers_pool.json -S /media/sf_temp/current_s.json
# sudo python /media/sf_temp/khronos_d.py -m 5 -d 0.2 -p /media/sf_temp/khronos_servers_pool.json -S /media/sf_temp/current_s.json -w 0.025 -e 0.05 -o /media/sf_temp/
# sudo python /media/sf_temp/khronos_d.py -m 5 -d 0.2 -p /media/sf_temp/khronos_servers_pool_0.json -S /media/sf_temp/current_s_0.json -w 0.025 -e 0.05 -o /media/sf_temp/ -n 200 -M 300 -C -Z /media/sf_temp/zone_pools.json
# sudo service ntp stop
# sudo python khronos_d.py -m 12 -d 0.34  -w 0.025 -e 0.05 -n 500 -M 36000 -C -z usa -p khronos_servers_pool_oragon.json
# sudo python khronos_d.py -m 12 -d 0.34 -n 500 -M 36000 -C -z uk -p khronos_servers_pool_oragon.json -u 3600 -q 60
# sudo python khronos_d.py -m 12 -d 0.34 -z usa -p khronos_servers_pool_oragon.json -u 3600 -q 60
# sudo python khronos_d.py -m 12 -d 0.34 -n 500 -M 36000 -C -z germany -p khronos_servers_pool_frankfurt.json -u 3600 -q 60
# sudo python khronos_d.py -m 12 -d 0.34 -n 500 -M 36000 -C -z usa -p khronos_servers_pool_virginia.json -u 3600 -q 60
# sudo python khronos_d.py -m 12 -d 0.34 -n 500 -M 36000 -C -z uk -p khronos_servers_pool_london.json -u 3600 -q 60

def parse_arguments():
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
    parser.add_argument("-p", "--server_pool_path", default='khronos_servers_pool.json',
                        help="path for json of pool servers")
    parser.add_argument("-S", "--state", default='current_s.json',
                        help="path for json of khronos state (last queried servers)")
    parser.add_argument("-D", "--dont_start_quick", action="store_true",
                        help="dont start with full update (might lead to panic on first update)")
    parser.add_argument("-c", "--conf_path", default=None,
                        help="path for json of khronos configuration (overides all other params)")
    parser.add_argument("-C", "--save_conf_path", default="config.json",
                        help="path to save khronos configuration")
    parser.add_argument("-o", "--output_path", default="./",
                        help="path output directory")
    parser.add_argument("-n", "--pool_size", type=int, default=9,
                        help="number of servers in the pool")
    parser.add_argument("-Z", "--zone_pools_path", default='zone_pools.json',
                        help="url per state"),
    parser.add_argument("-z", "--zone", default='global',
                        help="zone for calibration (default:global) [global,europe,uk,usa,germany,syngapore,australia,japan,asia,south_america]")
    parser.add_argument("-f", "--force_calibration", default=False, action="store_true",
                        help="force calibration (generating pool file")
    parser.add_argument("-M", "--max_calibration_time", type=int, default=2 * 60 * 60,
                        help="max calibration time in seconds")
    args = parser.parse_args()

    if args.conf_path:
        config = khronos_utils.read_server_list(args.conf_path)
    else:
        config = dict(
        m=args.query_size,
        d=args.filter_bounds,
        k=args.panic_threshold,
        w=args.distance_threshold,
        err=args.local_error_bound,
        update_query_interval=args.update_query_interval,
        query_interval=args.query_interval,
        server_pool_path=args.server_pool_path,
        zone_pools_path=args.zone_pools_path,
        state_path=args.state,
        start_quick=not args.dont_start_quick,
        output_path=args.output_path,
        zone=args.zone,
        pool_size=args.pool_size,
        max_calibration_time=args.max_calibration_time,
        force_calibration=args.force_calibration
        )

        if args.save_conf_path:
            json.dump(config, khronos_utils.open_write_file(args.save_conf_path, "w"),
                      sort_keys=True, indent=4, separators=(',', ': '))

        config["err"] = None
        return config

if __name__ == "__main__":

    logger = khronos_utils.init_logging("khronos") # Start the logger
    config = parse_arguments() # get the arguments

    if not os.path.isfile(config["server_pool_path"]) or config["force_calibration"]:
        calibration_conf = dict(
            n=config["pool_size"],
            server_pool_path=config["server_pool_path"],
            zone_pools_path=config["zone_pools_path"],
            zone=config["zone"],
            max_time_secs=config["max_calibration_time"]
        )
        calibration(**calibration_conf)

    update_loop(**config)
    #update_loop2(**conf)
