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
import json
import random
import socket
import time
from logging import Logger

import khronos_analysis
import khronos_utils

dns_name_list = []
logger: Logger
server_pool = set()
query_servers = []
CURRENT_PATH = 'current_s.json'
SERVER_POOL_PATH = 'server_pool.json'
ZONE = ''

def init_dns(logger_output, state_path, server_pool_path):
    global logger
    global CURRENT_PATH
    global SERVER_POOL_PATH
    logger = logger_output
    CURRENT_PATH = state_path
    SERVER_POOL_PATH = server_pool_path

def get_dns_names_for_zone(zone):
    global ZONE
    ZONE = zone
    if zone == "global":
        name = "pool.ntp.org"
    else:
        name = zone + ".pool.ntp.org"
    for i in range(4):  # Pool Zones have 4 DNS names
        dns_name = str(i) + "." + name
        dns_name_list.append(dns_name)
    return dns_name_list

def lookup_dns_addresses():
    addresses = set()
    for dns_name in dns_name_list:
        try:
            addr_info = socket.getaddrinfo(dns_name, None)
            ips = set(info[4][0] for info in addr_info)
            addresses |= ips
        except socket.gaierror:
            logger.error(f"Failed to resolve {dns_name}")
            continue
    return addresses

def retrieve_server_addresses(pool_size, max_time_secs=2*60*60):
    global server_pool

    # DNS names to retrieve ip addresses
    for dns_name in dns_name_list:
        logger.debug(f"Lookup for {dns_name}")

    iterations = 1
    start = time.time()
    current_time = start
    while len(server_pool) < pool_size and current_time - start < max_time_secs:
        server_pool |= lookup_dns_addresses()
        logger.debug(f"iteration {iterations}, so far collected {len(server_pool)} servers.")
        iterations += 1
        if len(server_pool) < pool_size:
            time.sleep(60)
        current_time = time.time()

    json.dump(list(server_pool), open(ZONE + "_" + SERVER_POOL_PATH, 'w'), indent=4, separators=(',', ': '))

    logger.info(f"Total of {len(server_pool)} servers collected")
    return server_pool

def remove_failed_servers():
    removals = khronos_analysis.get_removals()
    for ip in removals:
        if ip in server_pool:
            server_pool.remove(ip)
        if ip  in query_servers:
            query_servers.remove(ip)
        logger.info(f"Removed {ip} from server list")
        khronos_utils.remove_server(ip)

def get_random_server_list_from_pool(total_servers_needed):
    global query_servers
    if total_servers_needed <= len(query_servers):
        return query_servers

    ''' Make sure to remove servers that have proven to be unreliable sources '''
    remove_failed_servers()

    ''' If we don't have enough ask DNS for more servers '''
    if total_servers_needed > len(server_pool):
        retrieve_server_addresses(total_servers_needed)

    server_indices = random.sample(range(len(server_pool)), total_servers_needed)
    server_list = list(server_pool)
    query_servers = [server_list[idx] for idx in server_indices]
    json.dump(query_servers, open(ZONE + "_" + CURRENT_PATH, 'w'), indent=4, separators=(',', ': '))
    return query_servers
