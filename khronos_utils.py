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

import os
import json
import math
import logging

from ntplibrary import NTPClient

BASE_NTP_PACKET_SIZE = 48

def init_logging(log_name, log_file = 'khronos.log'):
    global logger
    logger = logging.getLogger(log_name)
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    file_handler = logging.FileHandler(filename=log_file, mode='a')  # define where the log will be written.  mode parameter will determine whether to append to log if it exists ('a') or write over file ('w').
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


def read_server_list(file_to_load):
    try:
        if os.path.isfile(file_to_load):
            # Open the file in read mode ('rb')
            with open(file_to_load, 'rb') as file:
                return json.load(file)
    except FileNotFoundError:
        print(f"The file {file_to_load} was not found.")
    except json.JSONDecodeError:
        print(f"The file {file_to_load} contains invalid JSON.")
        return None

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

def validate_response_size(response, ip):
    if response.packet_size >= BASE_NTP_PACKET_SIZE and response.packet_size % 4 == 0:
        return True
    else:
        logger.warning(f"Invalid packet size {response.packet_size} from {ip}")
        return False

def validate_response_mode(response):
    match response.input_mode:
        case 3:
            return response.mode == 4
        case _:
            return True

def validate_origin_timestamp(response, ip):
    match response.input_mode:
        case 3| 1| 2:
            return response.orig_timestamp == response.sent_timestamp
        case _:
            return True

def valid_stratum(response):
    return response.stratum > 0 and response.stratum < 16

def validate_responses(results):

    responses = dict()
    for ip, result in results.items():
        # logger.debug(f"Validating response from {ip}")
        if result.has_kiss_code:
            logger.error(f"Kiss code {result.kiss_name} received from {ip}")
        if (validate_response_size(result, ip)
                and not result.has_kiss_code
                and valid_stratum(result)
                and validate_response_mode(result)
                and validate_origin_timestamp(result, ip)):
            responses[ip] = result
        else:
            logger.warning(f"Invalid response from {ip}")
    return responses

def req_multiple_server_results(servers):
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
            responses[ip] = ntp_client.request(ip, version=4, mode=3)
        except Exception as err:
            ips_failed.append(ip)
            print(ip, err)
    for ip in ips_failed:
        try:
            responses[ip] = ntp_client.request(ip)
        except Exception as err:
            print(ip, err)
    return {ip: responses[ip] for ip in servers if ip in responses}


def req_multiple_server_offsets(servers):

    results = req_multiple_server_results(servers)

    responses = validate_responses(results)
    return {ip: responses[ip].offset for ip in servers if ip in responses}

def get_offset_simple(m, d, k, w, err, servers):
    # query chosen servers
    offset_list = req_multiple_server_offsets(servers).values()
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