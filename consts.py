from pathlib import Path


class Consts:

    # Default experiment values
    DEFAULT_REGION = "usa"
    DEFAULT_X = 0.14
    DEFAULT_N = 50

    DEFAULT_QUERY_INTERVAL = 16
    DEFAULT_UPDATE_INTERVAL = 16
    DEFAULT_TOTAL_TIME = 3600

    DEFAULT_SHIFT_TYPE = ''
    DEFAULT_C_SHIFT = 0.2
    DEFAULT_SLOP_T_0 = 0
    DEFAULT_SLOP = 0.2

    DEFAULT_M = 12
    DEFAULT_D = 0.33
    DEFAULT_K = 3
    DEFAULT_W = 0.2
    DEFAULT_ERR = 0.2
    DEFAULT_SMOOTH = False

    # File paths
    ntp_adversary_script_path = str(Path('resources', 'ntp_adversary.py').resolve())
    chronos_client_script_path = str(Path('resources', 'chronos_client.py').resolve())
    my_ntplib_script_path = str(Path('resources', 'my_ntplib.py').resolve())
    bad_servers_path = str(Path('resources', 'bad_servers.json').resolve())
    zones_path = str(Path('resources', 'zones.txt').resolve())
    dns_server_script_path = str(Path('resources', 'dnserver.py').resolve())
    chronos_pool_path = str(Path('resources', 'chronos_servers_pool.json').resolve())
    current_s_path = str(Path('resources', 'current_s.json').resolve())

    dns_files = [zones_path, dns_server_script_path]
    chronos_files = [chronos_client_script_path, my_ntplib_script_path, chronos_pool_path, current_s_path,
                     bad_servers_path]
    attacker_files = [ntp_adversary_script_path]
