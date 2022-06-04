# Chronos Experiment Project
This projects provides a Chronos_d, a Chronos client which is used as a watchdog for safer NTPv4 ([see details in the paper](https://www.ndss-symposium.org/wp-content/uploads/2018/02/ndss2018_02A-2_Deutsch_paper.pdf)).

Moreover, an end-to-end experiment environment is provided.

This repository consists of two Chronos client implementations: (i) python implementation (in the master branch), and (ii) C implementation (in the ''final project'') branch. 
Next, the python implementation is presented.

# Usage

Given a virtual env with the required packages installed (matplotlib, fabric), run:
```
chronos_d.py [-h] [-m QUERY_SIZE] [-d FILTER_BOUNDS]
                      [-k PANIC_THRESHOLD] [-w DISTANCE_THRESHOLD]
                      [-e LOCAL_ERROR_BOUND] [-u UPDATE_QUERY_INTERVAL]
                      [-q QUERY_INTERVAL] [-p SERVER_POOL_PATH] [-S STATE]
                      [-D] [-c CONF_PATH] [-o OUTPUT_PATH] [-n POOL_SIZE]
                      [-Z ZONE_POOLS_PATH] [-z ZONE] [-C]
                      [-M MAX_CALIBRATION_TIME]
```
For example:
```
sudo python chronos_d.py -m 12 -d 0.34 -n 500 -M 36000 -C -z uk -p chronos_servers_pool_london.json -u 3600 -q 60
```
where the optional arguments are as follows:
- *-h, --help*  show this help message and exit
- *-m QUERY_SIZE, --query_size QUERY_SIZE* is the number of servers to query
- *-d FILTER_BOUNDS, --filter_bounds FILTER_BOUNDS* the ratio of m to filter from each side
- *-k PANIC_THRESHOLD, --panic_threshold PANIC_THRESHOLD* the number of update failure before panic
- *-w DISTANCE_THRESHOLD, --distance_threshold DISTANCE_THRESHOLD* the offsets distance threshold
 - *-e LOCAL_ERROR_BOUND, --local_error_bound LOCAL_ERROR_BOUND* the offsets distance threshold
- *-u UPDATE_QUERY_INTERVAL, --update_query_interval UPDATE_QUERY_INTERVAL* the time interval between choosing new m servers
- *-q QUERY_INTERVAL, --query_interval QUERY_INTERVAL* the time interval between queries
 - *-p SERVER_POOL_PATH, --server_pool_path SERVER_POOL_PATH* the path for json of pool servers
 - *-S STATE, --state STATE* is the path for json of chronos state (last queried servers)
 - *-D, --dont_start_quick* don't start with full update (might lead to panic on first update)
 - *-c CONF_PATH, --conf_path CONF_PATH* the path for json of chronos configuration (overides all other params)
 - *-o OUTPUT_PATH, --output_path OUTPUT_PATH* the path output directory
- *-n POOL_SIZE, --pool_size POOL_SIZE* the number of servers in the pool
- *-Z ZONE_POOLS_PATH, --zone_pools_path ZONE_POOLS_PATH* url per state
- *-z ZONE, --zone ZONE  zone for calibration (default:global) [global,europe,uk,usa,germany,syngapore,australia,japan,asia,south_ame
                        rica]*
- *-C, --force_calibration* is used for force calibration (and generating pool file)
- *-M MAX_CALIBRATION_TIME, --max_calibration_time MAX_CALIBRATION_TIME* the max calibration time (in seconds).


### Test environment setup 
Use carefully.
For this option to run smoothly, the following resources needed to built prematurely. You can build them manually, or use 
the terraform files (build dns_attack_server and ntp_multi_attack_server, stop and install what needs to be installed, then build dhcp_settings)
#####VPC #1
- **DNS Server** :
    - Port 53 opened for incoming traffic
    - Python 2.7 installed, dnslib installed (globally)  
##### VPC #2
- **DHCP configuration** DHCP options set for this VPC configured with the DNS Server vm's IP as it's DNS server. Notice you might need to reboot the vm's for this change to take place quickly.
- **NTP Attacker** (Amazon Linux)
    - Multiple network interfaces with multiple IPs
    - All traffic open on 0.0.0.0/0
    - Python 2.7 installed.
- **Chronos_d** (centos or anything else)
    - Python 2.7 installed.
- **NTPd** (ubuntu)
    - run:
    ```
    ntpd.py [-c conf_path] 
            [-o output_path] 
            [-r read_state_interval] 
            [-Z zone_pools_path] 
            [-z zone] 
            [-C configure_ntpd] 
            [-M maxpoll_param] 
            [-m minpoll_param]
            [-a addr_command]
    ```
    - For example
    ```
    sudo python ntpd.py -C -z uk -a server
    ```
    where the optional arguments are as follows:
    - *-h, --help*  show this help message and exit
    - *-c* the path for json of ntpd configuration (overrides  all other params)
    - *-o --output_path* path output directory (default="./")
    - *-r --read_state_interval* is the interval between reading ntpd state
    - *-Z --zone_pools_path* is the url per state (default='zone_pools.json')
    - *-z --zone* is the zone for calibration (default:global) [global,europe,uk,usa,germany,syngapore,australia,japan,asia,south_america]
    - *-C --configure_ntpd* for reconfigure ntpd service and restart it (default=False, action="store_true")
    - *-M --maxpoll_param* is the max polling interval (in seconds).
    - *-m --minpoll_param* is min polling interval (in seconds).
    - *-a --addr_command* addres configuration command (default:pool) [pool, server, ...]
   
