import os
import json
import time


QUERY_SERVERS = []
SERVERS_POOL = []
STATE_PATH = 'current_s.json'
# to do:
# change the configuration file: /etc/ntp.conf
# find how to run on th estate machine



"""net@net-VirtualBox:~$ ntpdc -pn
     remote           local      st poll reach  delay   offset    disp
=======================================================================
=188.93.95.200   10.0.2.15        3    8  377 0.14160  0.357146 0.02036
=202.90.132.242  10.0.2.15        2    8  377 0.26527  0.347226 0.02122
*202.156.0.34    10.0.2.15        1    8  267 0.22197  0.361743 0.01924
=129.250.35.251  10.0.2.15        2    8  377 0.07390  0.362315 0.01744
"""

def get_ntpd_offset():
    """
    Send an NTP request from the naive client to the region's ntp host, return the offset.
    The Query is sent using ntpd unix commands on the remote host.
    :return: offset
    rtype: float
    """
    import subprocess
    p = subprocess.Popen(["ntpdc", "-pn"], stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
    stdout, stderr = p.communicate()
    print stdout
    for row in stdout.split("\n"):
        if row.startswith("*"):
            splitted = [val for val in row.split(" ") if val]
            offset = splitted[-2]
            return float(offset)
    return None



def read_loop(read_interval, output_path, conf_path=None):
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    file_name = timestamp + "_ntpd_offsets.csv"
    #file_path = os.path.join(output_path, file_name)
    file_path = output_path + file_name
    os.system("cp /etc/ntp.conf %s" % (file_path[:-3]+"conf") )
    if conf_path:
        os.system("cp %s %s" % (conf_path, file_path[:-3]+"json") )
    out = file(file_path, "w")
    while 1:
        offset = get_ntpd_offset()
        print "offset =", offset
        if offset is not None:
            out.write("%f,%f\n" % (time.time(), offset))
        time.sleep(read_interval)


def configure_ntpd(zone, minpoll, maxpoll, zone_pools_path):
    urls = json.load(open(zone_pools_path, 'r'))
    zone_urls = urls[zone]
    old_conf = file("/etc/ntp.conf").readlines()
    new_conf = []
    wrote_servers = False
    set_statsdir  = False
    for line in old_conf:
        if line.startswith("#server ") or line.startswith("server "):
            if not wrote_servers:
                for url in zone_urls:
                    new_line = "server %s minpoll %d maxpoll %d\n" %(url, minpoll, maxpoll)
                    new_conf.append(new_line)
                wrote_servers = True
        elif "statsdir " in line:
            if line.startswith("#"):
                new_line = line[1:]
            else:
                new_line = line
            new_conf.append(new_line)
            set_statsdir = True
        else:
            new_conf.append(line)
    if not set_statsdir:
        new_conf.append("statsdir /var/log/ntpstats/\n")
    if not wrote_servers:
        for url in zone_urls:
            new_line = "server %s minpoll %d maxpoll %d\n" % (url, minpoll, maxpoll)
            new_conf.append(new_line)
    file("/etc/ntp.conf","w").writelines(new_conf)
    res = os.system("sudo service ntp restart")
    time.sleep(2**maxpoll+1)
    return res



def install_ntpd():
    os.system('sudo apt - get install ntp')

# sudo python /media/sf_temp/ntpd.py -o /media/sf_temp/
# sudo python /media/sf_temp/ntpd.py -o /media/sf_temp/ -C -Z /media/sf_temp/zone_pools.json
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--conf_path", default=None,
                        help="path for json of ntpd configuration (overides all other params)")
    parser.add_argument("-o", "--output_path", default="./",
                        help="path output directory")
    parser.add_argument("-r", "--read_state_interval", type=float, default=2**4,
                        help="interval between reading ntpd state")
    parser.add_argument("-Z", "--zone_pools_path", default='zone_pools.json',
                        help="url per state"),
    parser.add_argument("-z", "--zone", default='global',
                        help="zone for calibration (default:global) [global,europe,uk,usa,germany,syngapore,australia,japan,asia,south_america]")
    parser.add_argument("-C", "--configure_ntpd", default=False, action="store_true",
                        help="reconfigure ntpd service and restart it")
    parser.add_argument("-M", "--maxpoll_param", type=int, default=4,
                        help="max calibration time in seconds")
    parser.add_argument("-m", "--minpoll_param", type=int, default=3,
                        help="max calibration time in seconds")
    args = parser.parse_args()

    if args.configure_ntpd:
        conf = dict(
            zone_pools_path=args.zone_pools_path,
            zone=args.zone,
            maxpoll=args.maxpoll_param,
            minpoll=args.minpoll_param
        )
        if args.conf_path:
            fconf = json.load(file(args.conf_path))
            conf.update(fconf)
            json.dump(conf, file(args.conf_path, "wb"),
                sort_keys=True, indent=4, separators=(',', ': '))
        configure_ntpd(**conf)

    read_loop(read_interval=args.read_state_interval, output_path=args.output_path, conf_path=args.conf_path)



