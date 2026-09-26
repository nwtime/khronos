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
from collections import defaultdict, Counter

import khronos_utils

excluded_offset_analysis = {}
removals = defaultdict()

''' Removal Processing'''

def add_removal(ip, removal_type):
    removals[ip] = removal_type

def delete_removals():
    removals.clear()


def get_removals():
    return removals

''' Statistics Tracking '''

def recommend_server_removals(tracker, min_attempts=15, failure_rate_threshold=0.20):

    """Return IPs with enough samples and an excessive request failure rate."""
    recommendations = []
    for ip, value in tracker.items():
        if value["removed"]:
            continue
        attempts = value["response_count"] + value["fail_count"]
        if attempts < min_attempts:
            continue

        failure_rate = value["fail_count"] / attempts
        if failure_rate >= failure_rate_threshold:
            recommendations.append({
                "ip": ip,
                "attempts": attempts,
                "failures": value["fail_count"],
                "successful_requests": value["response_count"],
                "failure_rate": round(failure_rate * 100, 2),
            })
            add_removal(ip, "failure")

    return sorted(
        recommendations,
        key=lambda recommendation: (
            recommendation["failure_rate"],
            recommendation["failures"],
        ),
        reverse=True,
    )


def report_statistics():

    logger  = khronos_utils.get_logger()
    tracker = khronos_utils.get_tracker()
    error_types = khronos_utils.get_error_types()
    server_state = khronos_utils.get_server_state()

    logger.info(f"Larger Failure Statistics:")
    for ip, value in tracker.items():
        attempts = value["response_count"] + value["fail_count"]
        if attempts:
            fail_percent = round(value["fail_count"] / attempts * 100, 2)
        else:
            fail_percent = 0
        if fail_percent > 10.0:
            logger.info(f"{ip}: {value} ({fail_percent}% failed) Stratum: {server_state[ip]["Stratum"]} RefId: {server_state[ip]["ReferenceId"]}")

    recommendations = recommend_server_removals(tracker, 15, .20)
    if recommendations:
        logger.info("Recommended Server Removals:")
        for recommendation in recommendations:
            logger.info(
                f"\t{recommendation['ip']}: "
                f"{recommendation['failure_rate']}% failed "
                f"({recommendation['failures']}/"
                f"{recommendation['attempts']} attempts)")

    '''Report errors'''
    logger.info(f"Errors Reported:")
    for err, value in error_types.items():
        logger.info(f"\t{err}")
        for ip, count in value.items():
            logger.info(f"\t\tIP: {ip} count: {count}")

    '''Report error type counts'''
    logger.info(f"Error Types Reported:")
    for err, value in error_types.items():
        logger.info(f"\t{err}: {sum(value.values())}")

    ''' Report removals'''
    logger.info(f"Removals Reported:")
    if len(removals) == 0:
        logger.info(f"\tNo Removals Reported")
    else:
        for ip, value in removals.items():
            logger.info(f"\t{ip}: {value}")

    ''' Report server stratum'''
    logger.info(f"Server Stratum Reported:")
    stratum_list = Counter(info["Stratum"] for info in server_state.values() if "Stratum" in info)
    for stratum, count in sorted(stratum_list.items()):
        logger.info(f"\tStratum {stratum}: count: {count}")

    logger.info(f"Stratum 1 Servers:")
    for ip, value in server_state.items():
        if value["Stratum"] == 1:
            logger.info(f"\tIP: {ip} Stratum 1: Reference: {value['ReferenceId']}")

''' Analyze Excluded Offsets '''

def analyze_excluded_offsets(offsets_dict, trimmed_servers, trim_count):
    """Accumulate why servers were excluded from the trimmed offset range."""
    if not trimmed_servers:
        return

    sorted_servers = sorted(offsets_dict, key=offsets_dict.get)
    lower_trimmed_servers = set(sorted_servers[:trim_count])
    upper_trimmed_servers = set(sorted_servers[-trim_count:]) if trim_count else set()
    trimmed_offsets = [offsets_dict[server] for server in trimmed_servers]
    lower_bound = min(trimmed_offsets)
    upper_bound = max(trimmed_offsets)

    for server, offset in offsets_dict.items():
        if server in trimmed_servers:
            continue

        stats = excluded_offset_analysis.setdefault(server, {
            "excluded_count": 0,
            "lower_trimmed_outlier": 0,
            "upper_trimmed_outlier": 0,
            "below_range": 0,
            "above_range": 0,
            "at_range_boundary": 0,
            "offset_sum": 0.0,
            "minimum_offset": offset,
            "maximum_offset": offset,
            "range_distance_sum": 0.0,
            "maximum_range_distance": 0.0,
        })
        stats["excluded_count"] += 1
        if server in lower_trimmed_servers:
            stats["lower_trimmed_outlier"] += 1
        if server in upper_trimmed_servers:
            stats["upper_trimmed_outlier"] += 1
        if offset < lower_bound:
            range_distance = lower_bound - offset
            stats["below_range"] += 1
        elif offset > upper_bound:
            range_distance = offset - upper_bound
            stats["above_range"] += 1
        else:
            range_distance = 0.0
            stats["at_range_boundary"] += 1
        stats["offset_sum"] += offset
        stats["minimum_offset"] = min(stats["minimum_offset"], offset)
        stats["maximum_offset"] = max(stats["maximum_offset"], offset)
        stats["range_distance_sum"] += range_distance
        stats["maximum_range_distance"] = max(stats["maximum_range_distance"], range_distance)

def explain_excluded_offset_stats(stats):
    """Explain the dominant reason a server was excluded from valid ranges."""
    excluded_count = stats["excluded_count"]
    average_offset = stats["offset_sum"] / excluded_count
    outside_count = stats["below_range"] + stats["above_range"]
    average_range_distance = stats["range_distance_sum"] / excluded_count

    if stats["lower_trimmed_outlier"] > stats["upper_trimmed_outlier"]:
        trim_explanation = "it was usually in the lowest offsets selected for trimming"
    elif stats["upper_trimmed_outlier"] > stats["lower_trimmed_outlier"]:
        trim_explanation = "it was usually in the highest offsets selected for trimming"
    else:
        trim_explanation = "it was selected for trimming from both sides equally"

    if stats["below_range"] > stats["above_range"]:
        range_explanation = "most violations were below the retained valid range"
    elif stats["above_range"] > stats["below_range"]:
        range_explanation = "most violations were above the retained valid range"
    elif outside_count:
        range_explanation = "violations were split between both sides of the retained range"
    else:
        range_explanation = "its offset matched the retained range boundary"

    return (
        f"{trim_explanation}; {range_explanation}; "
        f"outside={outside_count}/{excluded_count}, "
        f"average_distance_from_range={average_range_distance}, "
        f"maximum_distance_from_range={stats['maximum_range_distance']}, "
        f"observed_offset_range=[{stats['minimum_offset']}, "
        f"{stats['maximum_offset']}], average_offset={average_offset}"
    )

def report_excluded_offset_analysis(reset=True):

    logger = khronos_utils.get_logger()

    """Report accumulated exclusions and optionally start a new analysis window."""
    if not excluded_offset_analysis:
        return

    logger.info("Excluded Offset Analysis (lowest/highest offsets are trimmed):")
    for server, stats in sorted(
            excluded_offset_analysis.items(),
            key=lambda item: item[1]["excluded_count"],
            reverse=True):
        logger.info(f"\t{server}: {explain_excluded_offset_stats(stats)}")

    if reset:
        excluded_offset_analysis.clear()

