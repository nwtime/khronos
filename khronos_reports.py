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
from collections import Counter

import khronos_analysis
import khronos_utils

def report_statistics():

    report_server_states()
    report_jitter_statistics()
    report_server_removal_recommendations()
    report_errors()
    report_removals()
    report_stratum_statistics()
    report_stratum_1_servers()

''''Report Details Here'''

''' Report Jitter Statistics '''
def report_jitter_statistics():

    logger  = khronos_utils.get_logger()
    server_state = khronos_utils.get_server_state()

    logger.info(f"Jitter Statistics:")
    for ip, value in server_state.items():
        if value["jitter"] is None or value["jitter"] <= 0:
            logger.info(f"\t{ip}: No Jitter Information")
        elif value["Stratum"] is None:
            logger.info(f"\t{ip}: No Stratum Information")
        elif "jitter" in value:
            logger.info(f"\t{ip}: Stratum: {value['Stratum']} Jitter: {value['jitter']:.5f} ")
        else:
            logger.info(f"\t{ip}: Stratum: {value['Stratum']} Jitter: No Jitter Information")

def report_server_states():
    logger  = khronos_utils.get_logger()
    server_state = khronos_utils.get_server_state()
    tracker = khronos_utils.get_tracker()

    logger.info(f"Report Server State:")
    for ip, value in tracker.items():
        attempts = value["response_count"] + value["fail_count"]
        if attempts:
            fail_percent = round(value["fail_count"] / attempts * 100, 2)
        else:
            fail_percent = 0
        if value["response_count"] == 0:
            logger.info(f"{ip}: (0% successful) {value} No Stratum or ReferenceId Information")
        elif fail_percent > 10.0:
            if server_state[ip]["Stratum"] is not None and server_state[ip]["ReferenceId"] is not None:
                logger.info(f"{ip}: ({fail_percent}% failed) {value} Stratum: {server_state[ip]["Stratum"]} Jitter: {server_state[ip]["jitter"]:.5f} RefId: {server_state[ip]["ReferenceId"]}")
            else:
                logger.info(f"{ip}: ({fail_percent}% failed) {value} ")

def report_server_removal_recommendations():
    logger  = khronos_utils.get_logger()
    tracker = khronos_utils.get_tracker()

    recommendations = khronos_analysis.recommend_server_removals(tracker, 15, .20)
    if recommendations:
        logger.info("Recommended Server Removals:")
        for recommendation in recommendations:
            logger.info(
                f"\t{recommendation['ip']}: "
                f"{recommendation['failure_rate']}% failed "
                f"({recommendation['failures']}/"
                f"{recommendation['attempts']} attempts)")

def report_errors():
    logger  = khronos_utils.get_logger()
    error_types = khronos_utils.get_error_types()

    logger.info(f"Errors Reported:")
    for err, value in error_types.items():
        logger.info(f"\t{err}")
        for ip, count in value.items():
            logger.info(f"\t\tIP: {ip} count: {count}")

    '''Report error type counts'''
    logger.info(f"Error Types Reported:")
    for err, value in error_types.items():
        logger.info(f"\t{err}: {sum(value.values())}")

def report_removals():
    logger  = khronos_utils.get_logger()
    removals = khronos_analysis.get_removals()

    logger.info(f"Removals Reported:")
    if len(removals) == 0:
        logger.info(f"\tNo Removals Reported")
    else:
        for ip, value in removals.items():
            logger.info(f"\t{ip}: {value}")

def report_stratum_statistics():
    logger  = khronos_utils.get_logger()
    server_state = khronos_utils.get_server_state()

    logger.info(f"Server Stratum Statistics:")
    stratum_list = Counter(info["Stratum"] for info in server_state.values() if "Stratum" in info)
    for stratum, count in sorted(stratum_list.items()):
        logger.info(f"\tStratum {stratum}: count: {count}")

def report_stratum_1_servers():
    logger  = khronos_utils.get_logger()
    server_state = khronos_utils.get_server_state()

    logger.info(f"Stratum 1 Servers:")
    for ip, value in server_state.items():
        if value["Stratum"] is not None and value["Stratum"] == 1:
            logger.info(f"\tIP: {ip} Stratum 1: Reference: {value['ReferenceId']}")