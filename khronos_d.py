"""********************************************************************
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
"""

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
import random
import math
import json
import argparse
from pathlib import Path

import khronos_analysis
import khronos_utils
import time

DNS_ZONE_NAMES = []
QUERY_SERVERS = []
SERVERS_POOL = []
STATE_PATH = 'current_s.json'
servers_available = True

def initialize_server_pool(pool_size, server_pool_path, zone_pools_path, zone, max_time_secs=2 * 60 * 60):
    global SERVERS_POOL
    global DNS_ZONE_NAMES

    logger.info(f"Starting to retrieve server pool ip addresses from {zone} zone list")
    DNS_ZONE_NAMES = khronos_utils.get_dns_names_for_zone(zone_pools_path, zone)

    ''' Set up the server pool '''
    SERVERS_POOL = khronos_utils.retrieve_server_addresses(DNS_ZONE_NAMES, pool_size, max_time_secs)

    json.dump(list(SERVERS_POOL), open(server_pool_path, 'w'),
            indent=4, separators=(',', ': '))

def remove_failed_servers(pool_list, query_list):
    removals = khronos_analysis.get_removals()
    for ip in removals:
        if ip in pool_list:
            pool_list.remove(ip)
        if ip  in query_list:
            query_list.remove(ip)
        logger.info(f"Removed {ip} from server list")
        khronos_utils.remove_server(ip)
    khronos_analysis.delete_removals()


def get_random_server_list_from_pool(total_servers_needed):
    global QUERY_SERVERS
    global SERVERS_POOL

    ''' Make sure to remove servers that have proven to be not reliable sources '''
    remove_failed_servers(SERVERS_POOL, QUERY_SERVERS)

    ''' If we don't have enough ask DNS for more servers '''
    if total_servers_needed > len(SERVERS_POOL):
        SERVERS_POOL = khronos_utils.retrieve_server_addresses(DNS_ZONE_NAMES, total_servers_needed)

    server_indices = random.sample(range(len(SERVERS_POOL)), total_servers_needed)
    server_list = list(SERVERS_POOL)
    QUERY_SERVERS = [server_list[idx] for idx in server_indices]
    json.dump(QUERY_SERVERS, open(STATE_PATH, 'w'), indent=4, separators=(',', ': '))


def get_offset_list_from_pool(server_list, fraction_to_use, err=0.0):
    global servers_available
    # query chosen servers
    offsets_dict = khronos_utils.req_multiple_server_offsets(server_list)
    if len(offsets_dict) == 0:
        logger.error("No servers available")
        servers_available = False
        return None, None

    servers_available = True
    sorted_servers = sorted(offsets_dict.keys(), key=offsets_dict.get)
    offset_list_size = len(offsets_dict)

    # trim d from each side of the server responses (offsets)
    needed_size = int(fraction_to_use * offset_list_size)
    trimmed_servers = sorted_servers[needed_size:offset_list_size - needed_size]

    khronos_analysis.analyze_excluded_offsets(offsets_dict, trimmed_servers, needed_size)
    offset_list = [offsets_dict[s] for s in trimmed_servers]
    return offset_list, trimmed_servers

def panic_threshold_reached(k, len_list, len_servers):
    logger.error(f"Panic threshold of {k} attempts reached with {len_list} offsets from {len_servers} servers in pool")

def get_offset(total_servers_needed, fraction_to_use, max_retries, spread_limit, err=0.0):
    if len(QUERY_SERVERS) < total_servers_needed:
        get_random_server_list_from_pool(total_servers_needed)

    retries = 0
    while retries < max_retries:
        offset_list, trimmed_servers = get_offset_list_from_pool(QUERY_SERVERS, fraction_to_use, err)
        #Make sure we have offsets to work with
        if offset_list is None or len(offset_list) == 0:
            return None, None, None

        min_offset = min(offset_list, key=math.fabs)
        offset_range = max(offset_list) - min(offset_list)

        # check whether all surviving samples are "close"
        avg_offset = sum(offset_list) / len(offset_list)
        if (
                (offset_range <= 2 * spread_limit) and
                (math.fabs(avg_offset) <= spread_limit * 2 + err)
        ):
            return avg_offset, trimmed_servers, min_offset
        retries += 1
        print(")failure %d: %f > %f and/or %f > %f" % (
            retries, offset_range, 2 * spread_limit, math.fabs(avg_offset), spread_limit * 2 + err))
        get_random_server_list_from_pool(total_servers_needed)
    # PANIC
    panic_threshold_reached(max_retries, len(offset_list), len(trimmed_servers))

    # The randomly selected servers failed to get a good response
    # so we try again with the whole pool and try and get a good selected average
    # unlike the range limit check above it is not checked for the limits

    offset_dict, trimmed_servers = get_offset_list_from_pool(SERVERS_POOL, fraction_to_use, err)
    if offset_dict is None or len(offset_dict) == 0:
        return None, None, None

    avg_offset = sum(offset_list) / float(len(offset_list))
    return avg_offset, trimmed_servers, None


def get_offset_quick(total_servers_needed, fraction_to_use, max_retries, spread_limit):
    if len(QUERY_SERVERS) != total_servers_needed:
        get_random_server_list_from_pool(total_servers_needed)

    retries = 0
    while retries < max_retries:
        # query chosen servers
        offset_list, trimmed_servers = get_offset_list_from_pool(QUERY_SERVERS, fraction_to_use, 0)
        if offset_list is not None and len(offset_list) > 0:
        # check whether all surviving samples are "close"
            avg_offset = sum(offset_list) / len(offset_list)
            offset_range = max(offset_list) - min(offset_list)
            if offset_range <= 2 * spread_limit:
                return avg_offset
        else:
            offset_range = 0.0

        # Failed so we need to try again
        retries += 1
        print("failure %d: %f > %f" % (retries, offset_range, 2 * spread_limit))
        get_random_server_list_from_pool(total_servers_needed)
    # PANIC
    panic_threshold_reached(max_retries, len(offset_list), len(trimmed_servers))

    offset_list, _ = get_offset_list_from_pool(SERVERS_POOL, fraction_to_use, 0)
    if offset_list == None or len(offset_list) == 0:
        return None
    avg_offset = sum(offset_list) / float(len(offset_list))
    return avg_offset

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

    r = int(update_query_interval / query_interval)
    print("r=", r)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    file_name = timestamp + "_khronos_offsets.csv"
    file_path = Path(output_path) / file_name
    out = khronos_utils.open_write_file(file_path, "w")
    if start_quick:
        print("start quick")
        offset = get_offset_quick(query_args["total_servers_needed"], query_args["fraction_to_use"], query_args["max_tries"], query_args["spread_limit"])
        print("quick offset =", offset)
        out.write("%f,%f\n" % (time.time(), offset))
        time.sleep(query_interval)

    while True:
        QUERY_SERVERS = []
        for i in range(r):
            loop_count += 1
            offset, _, min_offset = get_offset(query_args["total_servers_needed"], query_args["fraction_to_use"], query_args["max_tries"], query_args["spread_limit"], query_args["err"])
            if offset is None:
                logger.error("offset not available")
            else:
                if min_offset is not None and math.fabs(delta) < 0.001:
                    delta = offset - min_offset
                    offset = min_offset
                if math.fabs(offset) < thresh:
                    offset = 0
                    print("offset set to 0")
                elif offset < 0:
                    offset += thresh
                    print(f"offset increased by {thresh}")
                else:
                    offset -= thresh
                    print(f"offset decreased by {thresh}")
                change = offset - last_offset
                print(f"count = {loop_count}, ind = {i}, last offset = {last_offset}, offset = {offset}, changed = {change} delta = {delta}, min_offset = {min_offset}")
                out.write("%f,%f\n" % (time.time(), offset))
                last_offset = offset

            if loop_count % 10 == 0:
                khronos_analysis.report_statistics()
                # khronos_analysis.report_excluded_offset_analysis()
                ''' If we have servers that are not providing valid response, remove them'''
                remove_failed_servers(SERVERS_POOL, QUERY_SERVERS)

            time.sleep(query_interval)

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
                        help="path for json of khronos configuration (overrides all other params)")
    parser.add_argument("-C", "--save_conf_path", default="config.json",
                        help="path to save khronos configuration")
    parser.add_argument("-o", "--output_path", default="./",
                        help="path output directory")
    parser.add_argument("-n", "--pool_size", type=int, default=9,
                        help="number of servers needed for the pool")
    parser.add_argument("-Z", "--zone_pools_path", default='zone_pools.json',
                        help="file name of the list for the zone pools"),
    parser.add_argument("-z", "--zone", default='global',
                        help="zone for calibration (default:global) [global,europe,uk,usa,germany,singapore,australia,japan,asia,south_america]")
    parser.add_argument("-f", "--force_calibration", default=False, action="store_true",
                        help="force calibration (generating pool file")
    parser.add_argument("-M", "--max_calibration_time", type=int, default=2 * 60 * 60,
                        help="max calibration time in seconds")
    args = parser.parse_args()

    if args.conf_path:
        config = khronos_utils.read_server_list(args.conf_path)
    else:
        config = dict(
        total_servers_needed=args.query_size,
        fraction_to_use=args.filter_bounds,
        max_tries=args.panic_threshold,
        spread_limit=args.distance_threshold,
        err=args.local_error_bound,
        update_query_interval=args.update_query_interval,
        query_interval=args.query_interval,
        server_pool_path=args.server_pool_path,
        zone_pools_path=args.zone_pools_path,
        conf_path=args.conf_path,
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

        return config

if __name__ == "__main__":

    config = parse_arguments() # get the arguments
    logger = khronos_utils.init_logging("khronos", "khronos_" + config["zone"] + ".log") # Start the logger

    if not os.path.isfile(config["server_pool_path"]) or config["force_calibration"]:
        calibration_conf = dict(
            pool_size=config["pool_size"],
            server_pool_path=config["server_pool_path"],
            zone_pools_path=config["zone_pools_path"],
            zone=config["zone"],
            max_time_secs=config["max_calibration_time"]
        )
        initialize_server_pool(**calibration_conf)

    update_loop(**config)
