import csv
import datetime
import json
import os
import random
import sys
import time
from pathlib import Path
import matplotlib.pyplot as plt
import logging
import threading

from consts import Consts
import vm_manager

# logger:
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
handler.setFormatter(logging.Formatter('%(asctime)s: %(message)s', datefmt='%H:%M:%S'))

logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def get_naive_offset(prev_offset):
    """
    Send an NTP request from the naive client to the region's ntp host, return the offset.
    The Query is sent using ntpd unix commands on the remote host.
    :return: offset
    """
    # get peers ntp responses
    stdout = vm_manager.run_cmd_on_vm(host=naive_host, user='ubuntu', cmd='ntpq -p', key=key_file_path)  # i [ms]
    # parse output - search for a row starts with "*" that represents the ntp stats of the system peer. get offset.
    offset = ""
    for row in stdout.split("\n"):
        if row.startswith("*"):
            splitted = [val for val in row.split(" ") if val]
            offset = splitted[-2]
    if offset == '':
        print(stdout)
        return prev_offset
    return offset


def get_chronos_offset():
    """
    Send an NTP request from the chronos client, return the offset.
    The Query is sent using the script found in the remote chronos client machine.
    :return: offset
    """
    offset = vm_manager.run_cmd_on_vm(host=chronos_host,
                                      cmd=f'./run_chronos',
                                      key=key_file_path)
    return offset.split()[-1].strip()


def create_bad_server_configuration(ntp_attacker_ip):
    """
    given the good servers pool written in chronos_servers_pool.json, create the bad servers configuration by replacing
    a portion of them with the adversary ips. the portion is determined by the given attack ratio parameter in the
    config file.
    Write the mapping to the bad servers file (meant for chronos machine) and zones text file (meant for the dns)
    """
    num_attackers_in_pool = int(attack_ratio * n)
    idx_to_replace = random.sample(range(len(chronos_servers_pool)), num_attackers_in_pool)
    new_pool = {}
    for i, ip in enumerate(chronos_servers_pool):
        if i in idx_to_replace:
            new_pool[ip] = ntp_attacker_ip
        else:
            new_pool[ip] = chronos_servers_pool[i]
    with open(Consts.chronos_pool_path, 'w') as bad_servers_f:
        counter = 0
        for cur_ip in new_pool:
            counter += 1
            if counter == n:
                bad_servers_f.write(f"{new_pool[cur_ip]}")
            else:
                bad_servers_f.write(f"{new_pool[cur_ip]}\n")
    with open(Consts.zones_path, 'w') as zones_f:
        for good_ip, bad_ip in new_pool.items():
            line = f"{good_ip} A {bad_ip}\n"
            zones_f.write(line)


def create_good_servers_pool():
    """
    read the chronos_servers_pool file contents.
    :return: the pool as list of ips
    """
    with open(Consts.calibration_pool_path, 'r') as pool_f:
        pool = pool_f.readlines()
        for i in range(len(pool)):
            pool[i] = pool[i].replace('\n', '')
    return pool


def log_experiment():
    now = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M")
    logs_dir = str(Path(f"chronos_experiment_{now}").resolve())
    os.mkdir(logs_dir)
    with open(str(Path(logs_dir, 'logs.csv')), 'w') as log_file:
        writer = csv.writer(log_file)
        params = [f"{key}={val}" for key, val in chronos_params.items()]
        writer.writerow(params)
        writer.writerow(('naive', 'chronos', 'panic', 'update'))
        for offset_pair in offsets:
            writer.writerow(offset_pair)

    fig = plt.figure()
    fig.add_subplot(111)
    naive_offsets = [a[0] for a in offsets]
    chronos_offset = [a[1] for a in offsets]
    plt.plot(range(1, len(offsets) + 1), naive_offsets)
    plt.plot(range(1, len(offsets) + 1), chronos_offset)
    plt.legend(['Naive Client', 'Chronos Client'], loc='upper left')
    plt.title(f"Chronos experiment - {now}")
    plt.xlabel("Queries")
    plt.ylabel("Offsets")
    plt.ylim([-0.2, 0.2])
    plt.savefig(str(Path(logs_dir, f"chronos_offsets_{now}")))


def set_time(host, offset):
    """
    Changes the local clock of the machine, according to the given offset
    """
    offset = float(offset)
    if abs(offset) < 0.0001:
        offset = 0.0001
    if float(offset) >= 0:
        to_add = f'+{offset}'
    else:
        to_add = f'{-offset} ago'
    vm_manager.run_cmd_on_vm(host=host, cmd=f"timedatectl set-time '{to_add}'",
                             key=key_file_path)


def run_experiment():
    """
    Run the chronos experiment for "total time" seconds:
    Query the Naive Client for offset every "delta_ntp" seconds.
    Query the Chronos Client for offset every "delta_chronos" iterations.
    Print the results (and timings) to the logger and return a list of offsets.
    :return: List of tuples [(naive_offset,chronos_offset)] where every tuple is one query loop.
    """
    # compile the chronos code
    vm_manager.run_cmd_on_vm(host=chronos_host, cmd=f'gcc chronos.c tools.c -o run_chronos', key=key_file_path)
    # turn on the ntpd
    vm_manager.run_cmd_on_vm(host=naive_host, cmd="ntpd", key=key_file_path)
    # disable time update by ntp
    vm_manager.run_cmd_on_vm(host=chronos_host, cmd=f'timedatectl set-ntp 0', key=key_file_path)
    vm_manager.run_cmd_on_vm(host=naive_host, cmd=f'timedatectl set-ntp 0', key=key_file_path)
    
    start_time = time.time()
    logger.info(f"Starting experiment at {datetime.datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')}")
    update_counter = 0
    update_flag = True
    panic_flag = False
    prev_chronos_offset = '0'
    naive_client_offset = '0'
    offset_lst = []
    cur_time = time.time()
    while cur_time - start_time < total_time:

        # check if chronos needs to be queried
        chronos_time = time.time()
        if update_counter == delta_chronos:
            update_flag = True
            update_counter = 0

            # get chronos offset
            logger.info("before_chronos")
            chronos_offset = get_chronos_offset()
            set_time(chronos_host, chronos_offset)
            logger.info("after_chronos")
            if "PANIC" in chronos_offset:
                chronos_offset = chronos_offset.split("\n")[1]
                panic_flag = True
            chronos_offset = chronos_offset.strip("\n")
            logger.info(f"chronos took {time.time() - chronos_time} secs " + (" | update" if update_flag else "") +
                        (" | panic" if panic_flag else ""))
        else:
            chronos_offset = prev_chronos_offset

        # get naive offset
        naive_time = time.time()
        naive_client_offset = get_naive_offset(naive_client_offset)
        naive_client_offset = str(float(naive_client_offset) / 1000)
        set_time(naive_host, naive_client_offset)
        logger.info(f"naive took {time.time() - naive_time} secs")

        # log and save results
        logger.info(f"Queries succeed, Naive offset: {naive_client_offset}, Chronos offset: {chronos_offset}")
        result = (naive_client_offset, chronos_offset, "panic" if panic_flag else "", "update" if update_flag else "")
        offset_lst.append(result)

        # wait for the remaining time of the query interval
        took = time.time() - chronos_time
        waiting_time = delta_ntp - took if delta_ntp - took > 0 else 0
        time.sleep(waiting_time)

        # update loop variables
        update_counter += 1
        update_flag = False
        panic_flag = False
        prev_chronos_offset = chronos_offset.strip("\n")
        cur_time = time.time()

    vm_manager.run_cmd_on_vm(host=chronos_host, cmd=f'timedatectl set-ntp 1', key=key_file_path)
    vm_manager.run_cmd_on_vm(host=naive_host, cmd=f'timedatectl set-ntp 1', key=key_file_path)
    return offset_lst


def create_config_chronos(params, d_chronos, pool_size):
    """
    Creates config file for Chronos, containing the relevant parameters
    """
    m = params.get('m', Consts.DEFAULT_M)
    d = params.get('d', Consts.DEFAULT_D)
    k = params.get('k', Consts.DEFAULT_K)
    w = params.get('w', Consts.DEFAULT_W)
    drift = params.get('drift', Consts.DEFAULT_DRIFT)
    with open(Consts.chronos_config_path, 'w') as config_file:
        config_file.write(f"{m} {d} {k} {w} {drift} {d_chronos} {pool_size}")




if __name__ == "__main__":
    if len(sys.argv) < 3:
        logger.error("Missing params. Usage: experiment_manager.py config_file_path ec2_key_path "
                     "[optional (calibration) -c] [optional (manual setup) -s]")
        exit()

    # read config file:
    with open(sys.argv[1], 'r') as f:
        config = json.loads(f.read())

    key_file_path = sys.argv[2]
    chronos_params = config.get('chronos_params')

    # test duration params:
    delta_ntp = config.get('delta_ntp', Consts.DEFAULT_DELTA_NTP)
    delta_chronos = config.get('delta_chronos', Consts.DEFAULT_DELTA_CHRONOS)
    total_time = config.get('total_time', Consts.DEFAULT_TOTAL_TIME)

    shift_params = config.get('shift_params')
    attack_ratio = config.get('attack_ratio', Consts.DEFAULT_ATTACK_RATIO)

    vm_params = config.get('vm_params')

    # VM's params
    dns_host = vm_params.get('dns_host')
    chronos_host = vm_params.get('chronos_host')
    naive_host = vm_params.get('naive_host')
    ntp_attacker_host = vm_params.get('ntp_attacker_host')
    ntp_attacker_private = vm_params.get('ntp_attacker_private')

    chronos_servers_pool = create_good_servers_pool()
    n = len(chronos_servers_pool)
    create_config_chronos(chronos_params, delta_chronos * delta_ntp, n)
    num_attackers = int(attack_ratio * n)

    create_bad_server_configuration(ntp_attacker_private)
    vm_manager.load_vm_data(dns_host, chronos_host, ntp_attacker_host, key_file_path)
#    x1 = threading.Thread(target=vm_manager.run_dns_server, args=(dns_host, key_file_path, attack_ratio))
#    vm_manager.run_dns_server(dns_host, key_file_path, attack_ratio)
#    x2 = threading.Thread(target=vm_manager.run_ntp_attacker, args=(ntp_attacker_host, shift_params, key_file_path))
#    vm_manager.run_ntp_attacker(ntp_attacker_host, shift_params, key_file_path)
#    x1.start()
#    x2.start()
    input("run dns and attacker and press enter")
    offsets = run_experiment()
    logger.info("Experiment completed.")
    log_experiment()
