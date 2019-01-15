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

### Automated Setup
This option will only require you to build your configuration file carefully. 
For the automated setup the "vm_manager" part in not required. 
The program will build all the resources needed for the experiment from scratch in the chosen AWS region.

### Manual Setup 
Use carefully.
For this option to run smoothly, the following resources needed to built prematurally:
#####VPC #1
- **DNS Server** :
    - Port 53 opened for incoming traffic
    - Python 3.6 installed, dnslib installed (globally)  
##### VPC #2
- **DHCP configuration** DHCP options set for this VPC configured with the DNS Server vm's IP as it's DNS server. Notice you might need to reboot the vm's for this change to take place quickly.
- **NTP Attacker** (Amazon Linux)
    - Multiple network interfaces with multiple IPs
    - All traffic open on 0.0.0.0/0
    - Python 3 installed.
- **Chronos Client** (centos or anything else)
    - Python 3 installed.
- **Naive Client** (ubuntu)
    - NTP config file changed in the following manners - 
      - add the line `server pool.ntp.org minpoll 3 maxpoll 6`
      - un-comment the line `statsdir /var/log/ntpstats/`
    - NTP service is restarted with `sudo service ntp restart`
