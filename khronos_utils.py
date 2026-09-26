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

import os
import json
import math
import logging
import time
from collections import defaultdict
from typing import Any

import colorlog
import socket

from ntplibrary import NTPClient, NTPException, NTP

_NTP_EXPECTED_VERSION = 4

tracker = defaultdict(lambda: {"no_response_count": 0, "fail_count": 0, "response_count": 0, "removed": False})
error_types = defaultdict(lambda: defaultdict(int))
server_state = defaultdict(lambda: defaultdict(Any))

last_offset = {}
LEAP_NOTINSYNC = 3
MAX_SERVER_FAILURES = 10

def init_logging(log_name, log_file = 'khronos.log'):
    global logger
    logger = colorlog.getLogger(log_name)
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)-8s - %(message)s')
    handler = colorlog.StreamHandler()
    colored_formatter = colorlog.ColoredFormatter(
        # Format string using the special %(log_color)s variable
        fmt="%(log_color)s%(asctime)s - %(name)s - %(levelname)-8s - %(message)s",
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'bold_red',
        }
    )
    handler.setFormatter(colored_formatter)
    logger = colorlog.getLogger(log_name)
    logger.addHandler(handler)
    file_handler = logging.FileHandler(filename=log_file, mode='a')  # define where the log will be written.  mode parameter will determine whether to append to log if it exists ('a') or write over file ('w').
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger

def get_logger():
    return logger

def remove_server(ip):
    tracker[ip]["removed"] = True

def add_to_no_response_count(ip):

    tracker[ip]["no_response_count"] += 1
    tracker[ip]["fail_count"] += 1
    if tracker[ip]["no_response_count"] >= MAX_SERVER_FAILURES:
        logger.error(f"Server {ip} exceeded the maximum number of failures allowed ({tracker[ip]["no_response_count"]} >= {MAX_SERVER_FAILURES}).")

def remove_from_no_response_count(ip):
    logger.info(f"Retry succeeded: {ip} server responded, failed count: {tracker[ip]["no_response_count"]}")
    tracker[ip]["no_response_count"] = 0

def add_response_count(ip):
        tracker[ip]["response_count"] += 1

def get_tracker():
    return tracker

def get_server_state():
    return server_state

def get_error_types():
    return error_types

def read_server_list(file_to_load):
    try:
        if os.path.isfile(file_to_load):
            # Open the file in read mode ('rb')
            with open(file_to_load, 'rb') as file:
                return json.load(file)
    except FileNotFoundError:
        logger.error(f"The file {file_to_load} was not found.")
    except json.JSONDecodeError:
        logger.error(f"The file {file_to_load} contains invalid JSON.")
        return None

def get_dns_names_for_zone(zone_pools_path, zone):
    dns_name_list = json.load(open(zone_pools_path, 'r'))
    return dns_name_list[zone]

def lookup_dns_addresses(dns_names):
    addresses = set()
    for dns_name in dns_names:
        try:
            addr_info = socket.getaddrinfo(dns_name, None)
            ips = set(info[4][0] for info in addr_info)
            addresses |= ips
        except socket.gaierror:
            logger.error(f"Failed to resolve {dns_name}")
            continue
    return addresses

def retrieve_server_addresses(zone_dns_names, pool_size, max_time_secs=2*60*60):

    # DNS names to retrieve ip addresses
    for dns_name in zone_dns_names:
        logger.debug(f"Lookup for {dns_name}")

    final_server_list = set()
    iterations = 1
    start = time.time()
    current_time = start
    while len(final_server_list) < pool_size and current_time - start < max_time_secs:
        final_server_list |= lookup_dns_addresses(zone_dns_names)
        logger.debug(f"iteration {iterations}, so far collected {len(final_server_list)} servers.")
        iterations += 1
        if len(final_server_list) < pool_size:
            time.sleep(60)
        current_time = time.time()

    logger.info(f"Total of {len(final_server_list)} servers collected")
    return final_server_list

def open_write_file(file_to_save, file_permissions):
    try:
        file = open(file_to_save, file_permissions)
        return file
    except PermissionError:
        print(f"Error: You do not have permission to write to this file {file_to_save}.")
    except OSError as e:
        print(f"Error: A system error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    return None

def validate_failure_checks(ip, value, condition, check_type):
    if condition:
        return True
    else:
        logger.warning(f"Invalid {check_type}: {value} from {ip}")
        return False

def validate_response_size(response, ip):
    return validate_failure_checks(ip, response.packet_size, response.packet_size >= NTP._BASE_NTP_PACKET_SIZE and response.packet_size % 4 == 0, "packet size")

def validate_response_mode(response, ip):
    match response.input_mode:
        case 3:
            return validate_failure_checks(ip, response.mode, response.mode == 4, "response mode")
        case _:
            return False

def validate_origin_timestamp(response, ip):
    match response.input_mode:
        case 3| 1| 2:
            return validate_failure_checks(ip, response.orig_timestamp, response.orig_timestamp == response.sent_timestamp, "origin timestamp")
        case _:
            return True

def valid_stratum(response, ip):
    return validate_failure_checks(ip, response.stratum, 0 < response.stratum < 16, "stratum")

def validate_synchonized(response, ip):
    return validate_failure_checks(ip, response.leap, response.leap != LEAP_NOTINSYNC, "synchonized")

def server_version_check(response, ip):
    return validate_failure_checks(ip, response.version, response.version == _NTP_EXPECTED_VERSION, "version")

def valid_response(result, ip):
    if result.has_kiss_code:
        logger.error(f"Kiss code {result.kiss_name} received from {ip}")
        return False
    return (validate_response_size(result, ip)
            and not result.has_kiss_code
            and valid_stratum(result, ip)
            and validate_synchonized(result, ip)
            and validate_response_mode(result, ip)
            and validate_origin_timestamp(result, ip))

def update_server_state(result, ip):
    server_state[ip]["Stratum"] = result.stratum
    server_state[ip]["Version"] = result.version
    server_state[ip]["KissCode"] = result.has_kiss_code
    server_state[ip]["Mode"] = result.mode
    server_state[ip]["Poll"] = result.poll
    server_state[ip]["Precision"] = result.precision
    server_state[ip]["Offset"] = result.offset
    server_state[ip]["Round_Trip_Time"] = result.Rtt
    server_state[ip]["ReferenceId"] = result.ref_id

    if result.Rtt > 5.0:
        print(f"{ip} Round trip time: {result.Rtt} > 5.0")

def process_responses(results):
    responses = dict()
    for ip, result in results.items():
        update_server_state(result, ip)
        add_response_count(ip)
        server_version_check(result, ip)
        if valid_response(result, ip):
            responses[ip] = result
            check_offset(result, ip)
        else:
            logger.warning(f"Invalid response from {ip}")
    return responses

def check_offset(response, ip):
    this_offset = response.offset
    if not ip in last_offset:
        last_offset[ip] = this_offset
    else:
        change = this_offset - last_offset[ip]
        last_offset[ip] = this_offset
        # print(f"{ip} offset changed by {change}")

def add_failure(ip, err, err_msg):
    add_to_no_response_count(ip)
    error_types[str(err)][ip] += 1
    logger.warning(f"{err_msg}{ip}: {str(err)}")

def request_packet(ip, retried):

    ntp_client = NTPClient()

    try:
        return ntp_client.request(ip, version=4, mode=3, timeout=5)

    except NTPException as err:
        add_failure(ip, err, retried)
    except socket.timeout as err:
        add_failure(ip, err, retried + "Socket timeout for ")
    except ConnectionError as err:
        add_failure(ip, err, retried + "Connection error for ")
    except OSError as err:
        add_failure(ip, err, retried + "OS error for ")
    except Exception as err:
        add_to_no_response_count(ip)
        logger.exception(f"{retried}Unexpected error from {ip}: {str(err)}")

    return None # Failed to get packet

"""
send requests to a chosen list of ips, return the offsets they return
:param servers: list of ip addresses
:return:
"""
def req_multiple_server_results(servers):

    responses = {}
    ips_failed = []
    for ip in servers:
        response = request_packet(ip, "")
        if response is not None:
            responses[ip] = response
        else:
            ips_failed.append(ip)

    """
    Retry the failed requests
    """
    for ip in ips_failed:
        response = request_packet(ip, "Retried: ")
        if response is not None:
            responses[ip] = response
            remove_from_no_response_count(ip)

    return {ip: responses[ip] for ip in servers if ip in responses}


def req_multiple_server_offsets(servers):

    results = req_multiple_server_results(servers)

    responses = process_responses(results)
    return {ip: responses[ip].offset for ip in servers if ip in responses}

def get_offset_simple(w, err, servers):
    # query chosen servers
    offset_list = req_multiple_server_offsets(servers).values()
    if offset_list is None or len(offset_list) == 0:
        return None
    # check whether all surviving samples are "close"
    avg_offset = sum(offset_list) / len(offset_list)
    if (
            (math.fabs(max(offset_list) - min(offset_list)) <= 2 * w) and
            (math.fabs(avg_offset) <= w * 2 + err)
    ):
        return avg_offset
    print("failure: %f > %f and/or %f > %f" % (
        math.fabs(max(offset_list) - min(offset_list)), 2 * w, math.fabs(avg_offset), w * 2 + err))
    return None