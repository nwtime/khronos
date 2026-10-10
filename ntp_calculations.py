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
from collections import defaultdict

import numpy as np

class Calibration:
    def __init__(self, offset, delay):
        self.offset = offset
        self.delay = delay

calibrations = defaultdict(list)

def find_offset_of_min_delay(ip):
    delay_index = min(
        range(len(calibrations[ip])),
        key=lambda index: calibrations[ip][index].delay,
    )
    return calibrations[ip][delay_index].offset

def add_offset(ip, offset, delay):
    calibrations[ip].append(Calibration(offset, delay))

def clear_offsets(ip):
    calibrations[ip].clear()

def get_jitter_for_ip(ip):
    offsets = [calibration.offset for calibration in calibrations[ip]]
    if len(offsets) <= 1:
        return 0.0
    current_offset = find_offset_of_min_delay(ip)
    return calculate_jitter(current_offset, offsets)

def calculate_jitter_for_servers(tracker, server_state):

    #calculate jitter for each server and add to server_state, then clear the offsets for that server
    for ip in tracker.keys():
        jitter = get_jitter_for_ip(ip)
        server_state[ip]["jitter"] = jitter
        clear_offsets(ip)

def calculate_jitter(current_offset, offset_list :list):
    #Make sure we have at least 2 offsets to calculate jitter
    if len(offset_list) < 2:
        return 0.0

    s = np.sum([(offset - current_offset) ** 2 for offset in offset_list])
    denominator = len(offset_list) - 1
    jitter: float = float(np.sqrt(s / denominator))

    return jitter