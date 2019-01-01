# Chronos Experiment Project
This projects provides an end-to-end experiment environment for the Chronos project.

## Usage
Given a virtual env with the required packages installed (see requirements.txt) and Python 3, run:
```
manager.py config_file_path key_path [optional -c] [optional -s]
```
where:
- *config_file_path* is the path to the configuration file, built like config_example.json
- *key_path* is the path to the public key used to communicate with the AWS EC2 virtual machines
- *-c* flag (optional) is used when a calibration of the NTP servers pool is needed
- *-s* flag (optional) is used when a manual setup has already been made

### Manual Setup Prerequisites
- 2 VPCs in the required region, on for the DNS server, the other for the rest (naive host, chronos host, ntp attacker).
- **DNS Server** machine set up on a vm on one of the VPCs, with:
    - Port 53 opened for incoming traffic
    - `dnserver.py` and `zones.txt` (found in resources dir) uploaded to vm
      (notice `zones.txt` needs to reflect the bad server config file that will also be at the chronos client vm,
      which is a mapping between some "good" NTP servers (taken from chronos servers pool) to IPs of the NTP attacker vm.
    - Python3 is installed and package dnslib is installed GLOBALLY
    - The following command should be ran to enable the machine as a functioning DNS server:
      ```
      sudo PORT=53 C=1 ZONE_FILE='./zones.txt' ./dnserver.py
      ```
    - Until all the following is preformed, the other vms will not be able to communicate. 
    - When DNS Server is running, the rest of the machines pass their DNS queries to it, which means that with 
      probability P, they will be redirected to a known host from `zones.txt` (meaning - one of the IPs of the ntp 
      attacker host). To cancel this redirection and open traffic run with C=0. 
- **NTP Attacker**
    - `ntp_adversary.py` file is uploaded to the machine
    - The following command is ran with the experiments "shift_params" (from config file):
      ```
      sudo python ntp_adversary.py [shift_type] [c_shift] [slop_t_0] [slop]
      ```
- **Chronos Client**
    - all the relevant files uploaded and python 3.6 installed
- **Naive Client** (important: this should be an ubuntu host)
    - NTP config file changed in the following manners - delete lines that start with *pool* or *server* and replace
      them with the line `server pool.ntp.org minpoll 3 maxpoll 6`
    - NTP service is restarted with `sudo service ntp restart`
