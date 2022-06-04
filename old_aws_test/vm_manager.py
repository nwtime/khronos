from fabric import Connection
from subprocess import check_output
from pathlib import Path
import re
from consts import Consts


def copy_files_to_vm(host, files, key):
    connection = Connection(host=host,
                            user="centos",

                            connect_kwargs={"key_filename": key})
    for file in files:
        connection.put(file, '/home/centos')


def run_cmd_on_vm(host, cmd, key, user='centos', wait_for_res=True, sudo=True):
    if not wait_for_res:
        cmd += "2>/dev/null >/dev/null &"  # this will redirect stdout to another file and not wait for it
    connection = Connection(host=host,
                                user=user,
                                connect_kwargs={"key_filename": key}
                                )
    if sudo:
        connection.sudo(cmd, hide=True)
    else:
        connection.run(cmd, hide=True)
    if wait_for_res:
        return connection.stdout


def install_python36_ubuntu(hostname, key, pip=False):
    run_cmd_on_vm(host=hostname, cmd="add-apt-repository ppa:jonathonf/python-3.6", key=key, user='ubuntu')
    run_cmd_on_vm(host=hostname, cmd="apt-get update", key=key, user='ubuntu')
    run_cmd_on_vm(host=hostname, cmd="apt-get install python3.6", key=key, user='ubuntu')
    if pip:
        run_cmd_on_vm(host=hostname, cmd="apt-get install python3-pip", key=key, user='ubuntu')


def install_python36_centos(hostname, key, pip=False):
    run_cmd_on_vm(host=hostname, cmd='yum update -y', key=key)
    run_cmd_on_vm(host=hostname, cmd='yum install yum-utils', key=key)
    run_cmd_on_vm(host=hostname, cmd='yum groupinstall development', key=key)
    run_cmd_on_vm(host=hostname, cmd='yum install https://centos7.iuscommunity.org/ius-release.rpm', key=key)
    run_cmd_on_vm(host=hostname, cmd='yum install python36u', key=key)
    if pip:
        run_cmd_on_vm(host=hostname, cmd='yum install python36u-pip', key=key)


def install_python3_amazon_linux(hostname, key, pip=False):
    """
    required for ntp_attacker and chronos_client vms
    :param hostname:
    :param key:
    :param pip:
    :return:
    """
    run_cmd_on_vm(host=hostname, cmd='yum update -y', key=key, user='ec2-user')
    run_cmd_on_vm(host=hostname, cmd='yum install python3', key=key, user='ec2-user')
    if pip:
        run_cmd_on_vm(host=hostname, cmd='curl -O https://bootstrap.pypa.io/get-pip.py', key=key, user='ec2-user')
        run_cmd_on_vm(host=hostname, cmd='python3 get-pip.py --user', key=key, user='ec2-user', sudo=False)
        run_cmd_on_vm(host=hostname, cmd="pip3 install dnslib --user", key=key, user='ec2-user', sudo=False)


def install_python36_amazon_linux(hostname,key):
    """
    required for dns server vm
    :param hostname:
    :param key:
    :return:
    """
    cmds = ["yum update -y", "yum install gcc openssl-devel bzip2-devel", "yum -y groupinstall development",
            "wget https://www.python.org/ftp/python/3.6.0/Python-3.6.0.tar.xz", "tar xJf Python-3.6.0.tar.xz",
            "cd Python-3.6.0", "./configure", "make", "make install", "ln -s /usr/local/bin/pip3.6 /usr/bin/pip3.6",
            "sudo ln -s /usr/local/bin/python3.6 /usr/bin/python3.6"]
    for cmd in cmds:
        run_cmd_on_vm(host=hostname, cmd=cmd, key=key, user='ec2-user')


def setup_dns_server(region, dns_subnet_id, key):
    """
    build machine on given region+subnet, install python3.6 and dnslib globally
    :return dns ip
    """
    dns_host = build_dns_server(region, dns_subnet_id)
    install_python36_amazon_linux(dns_host, key)
    run_cmd_on_vm(host=dns_host, cmd='pip3.6 install dnslib', key=key, user='ubuntu')
    return dns_host


def build_dns_server(region, subnet_id):
    cwd = str(Path('terraform', 'dns_server').resolve())
    check_output(['terraform', 'init'], cwd=cwd)
    check_output(['terraform', 'plan', '-out=tfplan', '-input=false', "-var", f'region={region}'
                  '-var', f'subnet_id={subnet_id}'], cwd=cwd)
    apply_p = check_output(['terraform', 'apply', '-input=false', 'tfplan'], cwd=cwd)

    stdout = apply_p.decode('ascii')
    dns_host = _parse_tf_output_dns(stdout)
    return dns_host


def build_dhcp_settings(dns_ip, vpc_id):
    # build dhcp settings
    cwd = str(Path('terraform', 'dhcp_settings').resolve())
    check_output(['terraform', 'init'], cwd=cwd)
    check_output(['terraform', 'plan', '-out=tfplan', '-input=false', "-var", f'dns_server_ip={dns_ip}', '-var',
                  f'vpc_id={vpc_id}'], cwd=cwd)
    apply_p = check_output(['terraform', 'apply', '-input=false', 'tfplan'], cwd=cwd)
    # TODO REBOOT
    # reboot machines in clients vpc
    pass


def run_dns_server(dns_host, key, attack_prob, close=True):
    run_cmd_on_vm(host=dns_host,
                  cmd=f"PORT=53 CLOSE={1 if close else 0} ZONE_FILE='./zones.txt' P={attack_prob} ./dnserver.py",
                  key=key)


def run_ntp_attacker(ntp_attacker_host, shift_params, key):
    shift_type = shift_params.get('shift_type', Consts.DEFAULT_SHIFT_TYPE)
    c_shift = shift_params.get('c_shift', Consts.DEFAULT_C_SHIFT)
    slop_t_0 = shift_params.get('slop_t_0', Consts.DEFAULT_SLOP_T_0)
    slop = shift_params.get('slop', Consts.DEFAULT_SLOP)
    run_cmd_on_vm(host=ntp_attacker_host, cmd=f'python3 ntp_adversary.py {shift_type} {c_shift} {slop_t_0} {slop}',
                  key=key, wait_for_res=False, user='ec2-user')


def setup_clients_and_ntp(num_attackers, dns_host, region, vpc_id, subnet_id, sg_id, key):
    """
    run the following commands to set up vms using terraform - plan and apply. once plan is applied, it's stdout
    contains the ips of the vms, parse it and return the ips.
    :return: parsed output
    """
    # build machines (this is done with default dhcp configuration!)
    cwd = str(Path('terraform', 'clients_and_attacker').resolve())
    check_output(['terraform', 'init'], cwd=cwd)
    check_output(['terraform', 'plan', '-out=tfplan', '-input=false', "-var", f'num_attacker_ips={num_attackers}'
                  '-var', f'region={region}', '-var', f'vpc_id={vpc_id}', '-var', f'subnet_id={subnet_id}',
                  'var', f'sg_id={sg_id}', '-var', f'dns_server_ip={dns_host}'],
                 cwd=cwd)
    apply_p = check_output(['terraform', 'apply', '-input=false', 'tfplan'], cwd=cwd)
    stdout = apply_p.decode('ascii')
    bad_ips, chronos_host, naive_host, ntp_attacker_host = _parse_tf_output_ntp_clients(stdout)
    install_python36_centos(chronos_host, key)
    return [bad_ips, chronos_host, naive_host, ntp_attacker_host]


def setup_all_vms(key, region, clients_vpc_id, dns_subnet_id, clients_subnet_id, sg_id, num_attackers):
    # set up dns and get hostname (build, install python+dnslib)
    dns_host = setup_dns_server(region, dns_subnet_id, key)

    # set up clients (build all, install python3 on chronos and on ntp)
    ips = setup_clients_and_ntp(num_attackers, dns_host, region, clients_vpc_id, clients_subnet_id, sg_id, key)

    return ips.extend(dns_host)


def edit_ntp_config(naive_host):
    # TODO
    pass


def teardown_tf(num_attackers):
    dns_cwd = str(Path('terraform', 'dns_server').resolve())
    clients_attacker_cwd = str(Path('terraform', 'clients_and_attacker').resolve())

    check_output(['terraform', 'destroy', '-input=false', "-var", f'num_attacker_ips={num_attackers}'],
                 cwd=clients_attacker_cwd)

    check_output(['terraform', 'destroy', '-input=false', "-var", f'num_attacker_ips={num_attackers}'],
                 cwd=dns_cwd)


def _parse_tf_output_ntp_clients(stdout):
    rows = stdout.split('\n')
    bad_ips = []
    _chronos_host = ''
    _naive_host = ''
    _ntp_attacker_host = ''
    for row in rows:
        if re.compile("^ *\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3},*$").match(row):
            bad_ips.append(row.replace(" ", "").replace(",", ""))
        if 'chronos_client =' in row:
            _chronos_host = row.split(' ')[2]
        if 'naive_client =' in row:
            _naive_host = row.split(' ')[2]
        if 'ntp_attacker_eip =' in row:
            _ntp_attacker_host = row.split(' ')[2][:len(row.split(' ')[2])-4]
    return bad_ips, _chronos_host, _naive_host, _ntp_attacker_host


def _parse_tf_output_dns(stdout):
    rows = stdout.split('\n')
    dns_host = rows[len(rows-1)].split(' ')[2]
    return dns_host


def load_vm_data(dns_server_host, chronos_host, ntp_attacker_host, key):
    copy_files_to_vm(dns_server_host, Consts.dns_files, key)
    copy_files_to_vm(chronos_host, Consts.chronos_files, key)
    copy_files_to_vm(ntp_attacker_host, Consts.attacker_files, key)


