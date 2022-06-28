# Chronos - protected NTP client - Test Environment Guide 

## Target
Simulate NTP naïve client VS Chronos client, under Man-in-the-Middle attack 

## Overview
In our test environment, we have 4 machines:
* Naïve Client – basic NTP client 
* Chronos Client – basic NTP client with Chronos as a watchdog 
* Malicious server – attacker with two attack strategies: constant-shift and cumulative-shift
* DNS server

## Architecture

![image](https://user-images.githubusercontent.com/84453420/176244989-e847d9a8-f906-433c-8afa-f3a9c784d3f3.png)

 

## Setup

### VPC #1
 * DNS Server:
   - Port 53 opened for incoming traffic
   - Python 3 installed, dnslib installed (globally)

 * NTP Attacker (ubuntu):
   - Multiple network interfaces with multiple IPs
   - All traffic open on 0.0.0.0/0
   - Python 3 installed

### VPC #2
**DHCP configuration:** DHCP options set for this VPC configured with the DNS Server VM's IP as its DNS server.\
Notice you might need to reboot the VM's for this change to take place quickly.

 * Chronos client (ubuntu):
   - ntpd installed
 * Naïve client (ubuntu)
   - ntpd installed 

## Configuration Files
### Chronos Client:
  - chronos_config.txt -  chronos algorithm configuration. (Fields: m, d, k, w, drift, d_chronos, pool_size)
  - watchdog_config.txt - chronos watchdog configuration. (Fields: chronosDivert, deltaChronos, deltaNTP)
### Naïve Client:
  - naive_config.txt - naive client configuration. (Fields: deltaNTP)


## Calibration
Before you start, notice your Chronos calibration pool is legit (in the range of two weeks for the last time activated). If not- go to Chronos machine and start calibration stage by:
```
gcc calibration.c tools.c -o calibration
./calibration [zone] [poolsize] [timelimit]
```
## Operate
The first step is to activate the DNS server with a wanted attack ratio

```
sudo python3 dnsserver.py [optional]
```

when the optional parameters are:
```
-p=[listening port],
-u=[upstream DNS server],
-i=[current ips state file path],
-b=[path for bad server pool],
-r=[bad server ratio],
-P=[upsrteam DNS server port],
[-d]
```
The second step is to activate the malicious server
```
sudo python3 ntp_attack_server.py [shift type] [c_shift] [slop_t] [slop] [interfaces file]
```
The third step is to activate the naïve client
```
gcc naive_client.c logger.c -o naiveC
./naiveC [time (minutes)]
```
The fourth step is to activate the Chronos client
```
gcc chronos_watchdog.c logger.c tools.c chronos.c -o chronosC
./chronosC [time (minutes)]
```
## Example
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
# Thanks :robot:
