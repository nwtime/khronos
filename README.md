# Chronos NTP protected client – test environment guide 

## Target –
Simulate NTP naïve client VS Chronos client, under man in the middle attack 

## Overview -
In our test environment program, we have 4 machines 
Naïve Client – basic NTP client 
Chronos Client – basic NTp client with the Chronos as watch dog 
Malicious server – attacker with two attack option: constant and cumulative
DNS server

## Architecture -

![image](https://user-images.githubusercontent.com/84452715/175526803-b7b906bd-9932-4959-8325-2d1763d9cc15.png)

 

## Setup –

### VPC #1
DNS Server :
Port 53 opened for incoming traffic
Python 3 installed, dnslib installed (globally)

NTP Attacker (ubuntu Linux):
Multiple network interfaces with multiple IPs
All traffic open on 0.0.0.0/0
Python 3 installed.

### VPC #2
DHCP configuration DHCP options set for this VPC configured with the DNS Server vm's IP as it's DNS server. Notice you might need to reboot the vm's for this change to take place quickly.
Chronos client (ubuntu)
Naïve client (ubuntu)

## configuration
### Chronos Client:
  - chronos_config.txt -  chronos algorithm configuration. (fields: m, d, k, w, drift, d_chronos, pool_size)
  - watchdog_config.txt - chronos watch dog configuration. (fields: chronosDivert, deltaChronos, deltaNTP)
### Naïve Client:
  - naive_config.txt - naive client configuration.  (fields: delta NTP)


## Calibration –
Before you start notice your Chronos calibration pool is legit (in the range of two weeks for the last time activated), if not go to Chronos machine and Start calibration stage by 
```
gcc calibration.c tools.c -o calibration
./calibration [zone] [poolsize] [timelimit]
```
## Operate – 
The first step Is to activate the DNS server with wanted attack ratio

```
#p=[listening port], -u=[upstream DNS server], -i=[current ips state file path], -b=[path for bad server pool], -r=[bad server ratio], -P=[upsrteam DNS server port], [-d]

sudo python3 dnsserver.py [optional]
```
The second step in to activate the malicious server
```
sudo python3 ntp_attack_server.py [shift type] [c_shift] [slop_t] [slop] [interfaces file]
```
The third stage in to activate the naïve client 
```
gcc naive_client.c logger.c -o naiveC
./naiveC [time (minutes)]
```
The forth stage is to activate the Chronos client  
```
gcc chronos_watchdog.c logger.c tools.c chronos.c -o chronosC
./chronosC [time (minutes)]
```
## example -
DNS
```
sudo python3 dnsserver.py -r=0.2
```
ATTACKER
```
sudo python3 ntp_attack_server.py CONSTANT 0.5 0 0 bad_ips_pool.json
```
NAIVE
```
gcc naive_client.c logger.c -o naiveC
./naiveC 150
```
CHRONOS
```
gcc chronos_watchdog.c logger.c tools.c chronos.c -o chronosC
./chronosC 150
```
# thanks :robot:
