import os
import sys
my_ntplib_path = './my_ntplib.py'
sys.path.append(os.path.abspath(my_ntplib_path))


import random
import math
from my_ntplib import NTPClient
import sys
import json


def req_multiple_servers(server_indices, servers_pool):
    """
    send requests to a chosen list of ips, return the offsets they return
    :param server_indices:
    :return:
    """
    ntp_client = NTPClient(attack_prob)
    ips_to_query = [servers_pool[idx] for idx in server_indices]
    responses = []
    ips_failed = []
    for ip in ips_to_query:
        try:
            responses.append(ntp_client.request(ip))
        except BaseException as err:
            ips_failed.append(ip)
            pass
    for ip in ips_failed:
        try:
            responses.append(ntp_client.request(ip))
        except BaseException as err:
            pass
    return [res.offset for res in responses if res]


def time_update(S):
    """
    Chronos Time Update Algorithm
    :param S: a list of indexes of the servers pool to query
    :type S: List[int]
    :return: the chosen offset
    """
    panic_counter = 0
    while panic_counter < k:

        # query chosen servers
        offsets = req_multiple_servers(S, servers_pool)
        offsets.sort()

        # trim d from each side of the server responses (offsets)
        t = int(d * m)
        T = offsets[t:m - t]

        # check wether all surviving samples are "close"
        avg_offset = sum(T) / float(len(T))*2 if smooth else sum(T) / float(len(T))
        if (math.fabs(max(T) - min(T)) <= 2 * w) and (math.fabs(avg_offset - truth) <= w * 2 + err):
                return avg_offset
        panic_counter += 1
    print("PANIC")
    # PANIC
    S = list(range(len(servers_pool)))
    offsets = req_multiple_servers(S, servers_pool)
    offsets.sort()
    t = int(d * m)
    T = offsets[t:m - t]
    avg_offset = sum(T) / float(len(T))
    return avg_offset


if __name__ == "__main__":
    # USAGE chronos_client.py [m] [d] [k] [w] [err] [attack_prob] [truth] [optional: update] [optional: smooth]
    # Files needed to be on machine: 'chronos_servers_pool.json' 'current_s.json'
    m = int(sys.argv[1])
    d = float(sys.argv[2])
    k = int(sys.argv[3])
    w = float(sys.argv[4])
    err = float(sys.argv[5])
    smooth = True if '-s' in sys.argv else False
    update = True if '-u' in sys.argv else False

    attack_prob = float(sys.argv[6])
    truth = float(sys.argv[7])

    servers_pool = json.load(open('chronos_servers_pool.json'))   # [ip1, ip2..]
    current_S = json.load(open('current_s.json'))  # [idx1, idx2..]
    # if update, S is drawn again from the pool and saved for next rounds, else it's the previously chosen S
    if update:
        S = random.sample(range(len(servers_pool)), m)
        with open('current_s.json', 'w') as f:
            f.write(json.dumps(S))
    else:
        S = current_S
    offset = time_update(S)
    print(offset)




