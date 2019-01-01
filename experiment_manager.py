import csv
import datetime
import json
import os
import random
import sys
import time
from pathlib import Path
import matplotlib.pyplot as plt
from server_search import collect_ntp_servers, NTPservers
import logging

from consts import Consts
import vm_manager
# logger:
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
handler.setFormatter(logging.Formatter('%(asctime)s: %(message)s', datefmt='%H:%M:%S'))

logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def get_naive_offset():
    """
    Send an NTP request from the naive client to the region's ntp host, return the offset.
    The Query is sent using ntpd unix commands on the remote host.
    :return: offset
    rtype: float
    """
    # get system peer
    _ = vm_manager.run_cmd_on_vm(host=naive_host, user='ubuntu', cmd='ntpdc -c sysinfo', key=key_file_path)
    # get peers ntp responses
    stdout = vm_manager.run_cmd_on_vm(host=naive_host, user='ubuntu', cmd='ntpq -p', key=key_file_path)
    # parse output - search for a row starts with "*" that represents the ntp stats of the system peer. get offset.
    offset = ""
    for row in stdout.split("\n"):
        if row.startswith("*"):
            splitted = [val for val in row.split(" ") if val]
            offset = splitted[-2]
    return offset


def get_chronos_offset(update_flag, prev_chronos_offset):
    """
    Send an NTP request from the chronos client to the region's ntp host, return the offset.
    The Query is sent using the script found in the remote chronos client machine.
    USAGE chronos_client.py [m] [d] [k] [w] [err] [attack_prob] [truth] [optional: update] [optional: smooth]
    [attack_prob] [truth] [optional: update]
    notice truth is prev_chronos_offset
    :return: offset
    rtype: float
    """
    update = '-u' if update_flag else ''
    m = chronos_params.get('m', Consts.DEFAULT_M)
    d = chronos_params.get('d', Consts.DEFAULT_D)
    k = chronos_params.get('k', Consts.DEFAULT_K)
    w = chronos_params.get('w', Consts.DEFAULT_W)
    err = chronos_params.get('err', Consts.DEFAULT_ERR)
    smooth = '-s' if chronos_params.get('smooth', Consts.DEFAULT_SMOOTH) else ''
    return vm_manager.run_cmd_on_vm(host=chronos_host,
                                    cmd=f'python chronos_client.py {m} {d} {k} {w} {err} {attack_ratio} '
                                        f'{prev_chronos_offset} {update} {smooth}',
                                    key=key_file_path)


def create_bad_server_configuration(ntp_attacker_ips):
    """
    given the good servers pool written in chronos_servers_pool.json, create the bad servers configuration by replacing
    a portion of them in one of the adversary ips. the portion is determined by the given attack ratio parameter in the
    config file.
    Write the mapping to the bad servers json (meant for chronos machine) and zones text file (meant for the dns)
    """
    idx_to_replace = random.sample(range(len(chronos_servers_pool)), num_attackers)
    new_pool = {}
    adversary_idx = 0
    for i, ip in enumerate(chronos_servers_pool):
        if i in idx_to_replace:
            new_pool[ip] = ntp_attacker_ips[adversary_idx]
            adversary_idx += 1
        else:
            new_pool[ip] = chronos_servers_pool[i]
    with open(Consts.bad_servers_path, 'w') as bad_servers_f:
        bad_servers_f.write(json.dumps(new_pool))
    with open(Consts.zones_path, 'w') as zones_f:
        for good_ip, bad_ip in new_pool.items():
            line = f"{good_ip} A {bad_ip}"
            zones_f.write(line)


def create_good_servers_pool(calibrate):
    """
    read the chronos_servers_pool file contents.
    Run calibration process again if one of the option holds:
    1. The file is empty
    2. Calibration flag was passed on expereiment init
    3. The pool's size is smaller than the N param given at experiment init
    :return: the pool as list of ips
    """
    with open(Consts.chronos_pool_path, 'r') as pool_f:
        pool = json.loads(pool_f.read())
    if not pool or calibrate or len(pool) < n:
        start = time.time()
        logger.info("Starting to calibrate servers pool.")
        pool = collect_ntp_servers(region, n=n)
        with open(Consts.chronos_pool_path, 'w') as pool_f:
            pool_f.write(json.dumps(pool))
        logger.info(f"Servers pool calibration complete, took {start - time.time()} seconds.")
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
    plt.plot(range(1, len(offsets)+1), naive_offsets)
    plt.plot(range(1, len(offsets)+1), chronos_offset)
    plt.legend(['Naive Client', 'Chronos Client'], loc='upper left')
    plt.title(f"Chronos experiment - {now}")
    plt.xlabel("Queries")
    plt.ylabel("Offsets")
    plt.ylim([-0.2, 0.2])
    plt.savefig(str(Path(logs_dir,f"chronos_offsets_{now}")))


def setup():
    """
    Prepare all machines from scratch by the correct order.
    :return:
    """
    start = time.time()

    logger.info("Started VM setup")
    _dns_host = vm_manager.setup_dns_server(region, key_file_path)
    _bad_ips, _chronos_host, _naive_host, _ntp_attacker_host = vm_manager.setup_clients_and_ntp(num_attackers,
                                                                                            dns_host, region)
    logger.info("VMs are up")
    create_bad_server_configuration(_bad_ips)
    vm_manager.load_vm_data(dns_host, naive_host, chronos_host, ntp_attacker_host, key_file_path)
    vm_manager.run_dns_server(dns_host, key_file_path)
    vm_manager.run_ntp_attacker(ntp_attacker_host, shift_params, key_file_path)
    logger.info(f"All vms are up and ready to use, took {time.time() - start} seconds")
    return _dns_host, _chronos_host, _naive_host, _ntp_attacker_host


def run_experiment():
    """
    Run the chronos experiment!
    Query the Chronos Client and the Naive Client for offsets.
    Querying occurse every "query_interval" for "total_time" (params taken from config).
    If chronos needs to be updated (every "update_interval" loops) update the relevant flags.
    Print the results (and timings) to the logger and return a list of offsets.
    :return: List of tuples [(naive_offset,chronos_offset)] where every tuple is one query loop.
    """
    start_time = time.time()
    logger.info(f"Starting experiment at {datetime.datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')}")
    update_counter = 0
    update_flag = True
    panic_flag = False
    prev_chronos_offset = 0
    offsets = []
    cur_time = time.time()
    while cur_time - start_time < total_time:

        # check if chronos needs to update it's server's sample group
        if update_counter == update_interval:
            update_flag = True
            update_counter = 0

        # get chronos offset (usually around 3s, can get to 35s if PANIC)
        chronos_time = time.time()
        chronos_offset = get_chronos_offset(update_flag, prev_chronos_offset)
        if "PANIC" in chronos_offset:
            chronos_offset = chronos_offset.split("\n")[1]
            panic_flag = True
        chronos_offset = chronos_offset.strip("\n")
        logger.info(f"chronos took {time.time() - chronos_time} secs " + (" | update" if update_flag else "") +
                    (" | panic" if panic_flag else ""))

        # get naive offset (usually around 6s)
        naive_time = time.time()
        naive_client_offset = get_naive_offset()
        logger.info(f"naive took {time.time() - naive_time} secs")

        # log and save results
        logger.info(f"Queries succeed, Naive offset: {naive_client_offset}, Chronos offset: {chronos_offset}")
        result = (naive_client_offset, chronos_offset, "panic" if panic_flag else "", "update" if update_flag else "")
        offsets.append(result)

        # wait for the remaining time of the query interval
        took = time.time() - chronos_time
        waiting_time = query_interval - took if query_interval - took > 0 else 0
        time.sleep(waiting_time)

        # update loop variables
        update_counter += 1
        update_flag = False
        panic_flag = False
        prev_chronos_offset = chronos_offset.strip("\n")
        cur_time = time.time()
    return offsets


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.stdout("Missing params. Usage: experiment_manager.py config_file_path ec2_key_path "
                   "[optional (calibration) -c] [optional (manual setup) -s]")
        exit()

    with open(sys.argv[1], 'r') as f:
        config = json.loads(f.read())

    key_file_path = sys.argv[2]

    chronos_params = config.get('chronos_params')
    n = chronos_params.get('n', Consts.DEFAULT_N)

    attack_ratio = config.get('adversary_ratio', Consts.DEFAULT_X)
    num_attackers = int(attack_ratio * n)

    query_interval = config.get('query_interval', Consts.DEFAULT_QUERY_INTERVAL)
    update_interval = config.get('update_interval', Consts.DEFAULT_UPDATE_INTERVAL)
    total_time = config.get('total_time', Consts.DEFAULT_TOTAL_TIME)

    calibrate = True if '-c' in sys.argv else False
    manual_setup = True if '-s' in sys.argv else False

    region = config.get('region', Consts.DEFAULT_REGION)
    if region not in NTPservers.keys():
        sys.stdout("Invalid state. Options are " + ", ".join(list(NTPservers.keys())))
        exit()
    ntp_region_host = NTPservers[region][0]

    if not manual_setup:
        try:
            # create chronos_servers_pool or take it from chronos_servers_pool.json
            shift_params = config.get('shift_params')
            chronos_servers_pool = create_good_servers_pool(calibrate)
            dns_host, chronos_host, naive_host, ntp_attacker_host = setup()
        except BaseException as err:
            vm_manager.teardown_tf(num_attackers)
            logger.info(err)
            exit()
    else:
        vm_params = config.get('vm_params')
        if not vm_params:
            logger.info("ERROR: can't use -s for manual setup without specifying vm params in config")
            exit()
        dns_host = vm_params.get('dns_host')
        chronos_host = vm_params.get('chronos_host')
        naive_host = vm_params.get('naive_host')
        ntp_attacker_host = vm_params.get('ntp_attacker_host')
        logger.info("No setup needed, taking host names from config file.")
        logger.info("WARNING: USE THIS OPTION CAREFULLY. For the experiment to run successfully the given hosts needed "
                    "to be set according to the experiment's prerequisites listed in README")

    offsets = run_experiment()
    logger.info("Experiment completed.")
    log_experiment()


