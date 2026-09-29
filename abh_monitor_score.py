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
import math

def no_response_score():
    return -5, 0

def invalid_response_score():
    return -2, 5

def calculate_score(server):
    score = 0
    step = 0.0
    if server.has_kiss_code:
        if server.kiss_name == "RATE":
            step = -3.5
        elif server.kiss_name == "RSTR" or server.kiss_name == "DENY":
            step = -10
            score = -50
    elif server.stratum == 0:
        step = -2
        score = 5
    elif server.offset is None:
        step = -4
    else:
        offset_abs = math.fabs(server.offset)
        if offset_abs > 3 or server.stratum > 8:
            step = -4
            if offset_abs > 3:
                score = -20
        elif offset_abs > 0.75:
            step = -2
        elif offset_abs > 0.025:
            if offset_abs > 0.1:
                step = -6.667 * offset_abs + 1.167
            else:
                step = -2.308 * offset_abs + 0.731
            if step > 1:
                step = 1
        else:
            step = 1

    return score, step

