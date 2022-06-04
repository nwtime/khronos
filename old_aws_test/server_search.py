__author__ = 'T8165122'

# from time import ctime
import socket
import time
import datetime
import sys
import json
CHECK_ALL = False


NTPservers = {

    "global": [
        '0.pool.ntp.org',
        '1.pool.ntp.org',
        '2.pool.ntp.org',
        '3.pool.ntp.org'
    ],

    "europe": [
        '0.europe.pool.ntp.org',
        '1.europe.pool.ntp.org',
        '2.europe.pool.ntp.org',
        '3.europe.pool.ntp.org'
    ],

    "uk": [
        '0.uk.pool.ntp.org',
        '1.uk.pool.ntp.org',
        '2.uk.pool.ntp.org',
        '3.uk.pool.ntp.org'
    ],

    "usa": [
        '0.us.pool.ntp.org',
        '1.us.pool.ntp.org',
        '2.us.pool.ntp.org',
        '3.us.pool.ntp.org',

        '0.ca.pool.ntp.org',
        '1.ca.pool.ntp.org',
        '2.ca.pool.ntp.org',
        '3.ca.pool.ntp.org',
    ],

    "germany": [
        '0.de.pool.ntp.org',
        '1.de.pool.ntp.org',
        '2.de.pool.ntp.org',
        '3.de.pool.ntp.org',
    ],

    "syngapore": [
        '0.sg.pool.ntp.org',
        '1.sg.pool.ntp.org',
        '2.sg.pool.ntp.org',
        '3.sg.pool.ntp.org',
    ],

    "australia": [
        '0.oceania.pool.ntp.org',
        '1.oceania.pool.ntp.org',
        '2.oceania.pool.ntp.org',
        '3.oceania.pool.ntp.org',
    ],

    "japan" : [
        '0.jp.pool.ntp.org',
        '1.jp.pool.ntp.org',
        '2.jp.pool.ntp.org',
        '3.jp.pool.ntp.org',
    ],

    "asia": [  # korea, india
        '0.asia.pool.ntp.org',
        '1.asia.pool.ntp.org',
        '2.asia.pool.ntp.org',
        '3.asia.pool.ntp.org',
    ],

    "south_america": [  # use in addition to global
        '0.south-america.pool.ntp.org',
        '1.south-america.pool.ntp.org',
        '2.south-america.pool.ntp.org',
        '3.south-america.pool.ntp.org',
    ]
}

REPEAT = 50
previousfileName = ''


def simple_get_ntp_servers(location, repeat):
    ip_list = NTPservers.get(location)
    if ip_list:
        final_server_list = []
        for i in range(repeat):
            for url in ip_list:
                addrinfo = socket.getaddrinfo(url, 'ntp')[0]
                final_server_list.append(addrinfo[4][0])
        return list(set(final_server_list))
    return "ERROR: wrong location"
temp = ['204.2.134.163', '107.174.70.24', '68.96.20.178', '206.248.144.166', '67.215.197.149', '4.53.160.75', '103.105.51.156', '66.135.44.92', '50.76.34.188', '206.248.188.245', '66.96.99.10', '45.77.78.241', '174.136.103.130', '198.98.50.212', '52.6.191.28', '185.144.157.134', '199.180.255.17', '69.165.173.93', '38.229.71.1', '198.50.139.209', '107.190.68.13', '63.211.239.58', '137.190.2.4', '192.73.248.134', '98.152.165.38', '198.50.238.156', '199.233.217.27', '184.105.182.15', '184.105.182.16', '108.161.151.187', '216.229.0.50', '69.164.202.202', '199.223.248.99', '199.223.248.98', '149.56.111.74', '162.221.74.15', '45.32.199.189', '23.31.21.163', '104.168.88.15', '206.55.191.142', '208.81.1.197', '144.217.65.184', '144.217.65.183', '144.217.65.182', '144.217.242.233', '128.10.19.24', '23.239.26.89', '64.62.142.222', '208.76.53.137', '199.182.221.110', '66.228.42.59', '199.102.46.77', '76.10.149.44', '138.236.128.112', '66.220.10.2', '54.39.13.155', '205.166.121.31', '45.32.225.67', '206.163.231.209', '198.100.149.122', '52.53.178.201', '173.0.156.209', '208.67.72.50', '69.64.225.2', '66.172.10.184', '195.21.137.209', '104.131.53.252', '13.84.173.66', '192.241.146.233', '97.107.128.165', '69.17.158.101', '207.244.103.95', '199.223.248.100', '52.6.160.3', '66.151.147.38', '173.255.215.209', '216.218.254.202', '204.9.54.119', '158.69.2.23', '45.63.111.145', '65.182.224.39', '23.239.24.67', '138.197.135.239', '216.93.242.12', '207.210.46.249', '45.79.1.70', '66.96.98.9', '192.207.62.39', '104.238.179.228', '69.197.188.178', '174.94.155.224', '54.39.173.225', '96.245.170.99', '208.88.126.235', '65.223.27.156', '144.217.181.221', '138.236.128.36', '142.137.247.90', '192.99.34.87', '66.70.234.51', '206.55.65.229', '64.251.10.152', '208.69.120.241', '69.196.158.106', '199.223.248.101', '69.89.207.199', '72.38.129.202', '208.75.89.4', '107.191.50.162', '66.7.96.2', '198.211.103.209', '74.208.235.60', '45.79.111.167', '206.55.65.228', '98.143.85.249', '199.180.133.100', '66.180.171.114', '128.100.100.128', '159.203.158.197', '50.116.52.97', '173.71.69.215', '50.18.44.198', '50.21.181.14', '66.70.172.17', '23.131.160.7', '69.164.203.231', '18.222.40.121', '144.202.41.122', '216.75.56.132', '107.172.97.205', '195.21.152.161', '192.3.29.143', '108.61.73.244', '108.61.73.243', '45.79.109.111', '45.127.113.2', '199.188.64.12', '69.36.182.57', '206.108.0.134', '206.108.0.132', '206.108.0.133', '206.108.0.131', '192.138.210.214', '68.112.4.227', '108.59.2.24', '184.60.28.49', '50.116.38.157', '104.236.114.203', '104.236.116.147', '173.255.206.154', '216.229.4.69', '216.229.4.66', '50.126.194.190', '104.131.139.195', '66.175.211.68', '108.61.194.85', '144.217.240.204', '74.117.214.3', '74.117.214.2', '50.112.150.45', '198.199.120.223', '107.191.112.226', '146.71.77.36', '167.114.156.48', '64.6.144.6', '45.33.84.208', '45.76.244.202', '54.242.183.158', '107.181.191.189', '198.71.81.66', '204.17.205.24', '108.170.151.8', '172.98.193.44', '208.67.75.242', '69.89.207.99', '216.6.2.70', '167.99.20.98', '66.79.136.240', '207.34.48.31', '142.4.208.200', '45.63.11.93', '64.62.190.177', '69.10.161.7', '158.69.226.90', '99.224.45.6', '142.147.92.5', '66.228.48.38', '199.204.32.4', '23.92.29.245', '38.110.92.248', '64.62.206.99', '44.190.6.254', '158.69.254.196', '141.193.21.6', '199.101.100.221', '45.33.103.94', '208.79.89.249', '192.111.144.114', '208.73.56.29', '162.213.2.253', '128.100.56.135', '74.122.204.3', '173.161.33.165', '69.195.142.11', '192.99.2.8', '184.105.182.7', '47.190.36.230', '199.102.46.80', '173.95.72.34', '74.82.59.149', '148.167.132.200', '158.69.247.184', '204.11.201.12', '173.230.144.79', '96.126.122.39', '64.113.44.54', '64.113.44.55', '69.164.198.192', '72.87.88.202', '75.188.231.119', '12.167.151.1', '12.167.151.2', '161.129.154.50', '192.241.211.46', '198.58.105.63', '173.255.140.30', '173.203.211.73', '192.73.243.97', '149.56.47.60', '66.241.101.63', '65.19.142.137', '199.38.183.232', '69.195.159.158', '199.19.167.36', '204.11.201.10', '209.115.181.108', '209.115.181.107', '209.115.181.102', '96.244.96.19', '71.252.219.43', '71.19.144.130', '129.250.35.250', '129.250.35.251', '138.197.114.122', '138.68.201.49', '144.217.252.208', '66.70.166.200', '108.61.56.35', '107.155.79.3', '67.169.140.139', '74.207.240.206', '171.66.97.126', '174.142.39.145', '54.39.20.247', '162.220.9.203', '192.95.27.155', '45.76.244.193', '45.79.11.217', '173.255.192.10', '198.50.135.212', '198.60.22.240', '198.84.61.242', '129.128.12.20', '167.99.179.124', '45.33.41.203', '162.248.241.94', '208.75.88.4', '71.17.253.178', '172.98.77.203', '74.6.168.72', '74.6.168.73', '206.210.192.32', '66.228.58.20', '162.243.194.203', '138.68.46.177', '107.175.144.206', '45.55.217.50', '104.225.103.41', '104.248.104.92', '140.82.7.153', '192.73.244.251', '173.230.144.109', '72.5.72.15', '155.94.164.121', '64.79.100.196', '107.155.79.108', '204.2.134.162', '162.248.221.109', '204.2.134.164', '208.81.1.244', '45.33.106.180', '192.73.242.152', '216.228.192.52', '216.228.192.51', '155.94.238.29', '199.102.46.73', '199.102.46.74', '199.102.46.75', '199.102.46.76', '174.123.154.242', '199.102.46.78', '199.102.46.79', '198.46.223.227', '69.87.223.252', '52.206.70.54', '138.68.19.10', '50.205.244.25', '50.205.244.23', '50.205.244.20', '69.164.213.136', '45.32.75.249', '45.79.111.114', '45.79.187.10', '74.82.59.150', '104.155.144.4', '69.114.173.217', '173.230.149.23', '45.63.20.61', '159.203.8.72', '72.14.183.239', '216.229.0.49', '173.230.235.13', '98.191.213.2', '154.16.245.246', '208.67.72.43', '104.236.167.15', '45.56.118.161', '64.79.100.197', '149.56.121.16', '96.8.121.205', '158.69.125.231', '72.249.38.88', '67.217.112.181', '209.177.145.40', '45.127.112.2', '72.30.35.89', '72.30.35.88', '199.188.48.60', '66.228.59.187', '209.87.233.53', '216.230.228.242', '159.89.241.143', '198.55.111.50', '144.217.75.74', '45.33.48.4', '104.236.52.16', '52.0.56.137']

def collect_ntp_servers(location, n):
    ip_list = NTPservers.get(location)

    if ip_list:
        final_server_list = temp
        iterations = 1
        while len(final_server_list) < n:
            final_server_list.extend(query(ip_list, repeat=50))
            final_server_list = list(set(final_server_list))
            print(f'iteration {iterations}, so far collected {len(final_server_list)} servers.')
            print(final_server_list)
            iterations += 1
            time.sleep(60)
        return final_server_list
    return "ERROR: wrong location"


def query(ip_list, repeat):
    global previousfileName

    currTime = datetime.datetime.now()
    filename = 'temp_server_lists/serverList-' + str(currTime.hour) + ':' + str(currTime.minute)
    newList = []

    # get previous ip's to remove duplicates
    if previousfileName != '':
        prevFile = open(previousfileName + '.txt', 'r')
        newList = prevFile.readlines()
        prevFile.close()
    previousfileName = filename
    oldLength = len(newList)

    for i in range(repeat):
        for url in ip_list:
            addrinfo = socket.getaddrinfo(url, 'ntp')[0]
            # print(addrinfo[4][0])
            ip = addrinfo[4][0].strip('\n')
            if ip:
                newList.append(ip)

    # choose only set
    newSet = list(set(newList))

    # createList
    listFile = open(filename + '.txt', 'w')

    for s in newSet:
        listFile.write(s)
        listFile.write('\n')
    listFile.close()

    with open('temp_server_lists/Server24hSearch-log.txt', 'w') as logFile:
        logFile.write('new srvers in ' + filename + ': ' + str(len(newSet) - oldLength) + '\n')

    print('collected: ' + str(len(newSet)))
    print(newSet)
    return newSet


if __name__ == "__main__":
    n = sys.argv[1]
    if len(sys.argv) < 2:
        exit()
    start = time.time()
    print("START")
    ips = collect_ntp_servers('usa', int(n))
    print(f"DONE, took {time.time() - start}")
    with open('resources/temp_servers.json', 'w') as f:
        f.write(json.dumps(ips))