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


def run_cmd_on_vm(host, cmd, key, user='centos', wait_for_res=True):
    if not wait_for_res:
        cmd += "2>/dev/null >/dev/null &"  # this will redirect stdout to another file and not wait for it
    connection = Connection(host=host,
                            user=user,
                            connect_kwargs={"key_filename": key}
                            ).sudo(cmd, hide=True)
    if wait_for_res:
        return connection.stdout


def install_python3_centos(hostname, key):
    run_cmd_on_vm(host=hostname, cmd='yum update -y', key=key)
    run_cmd_on_vm(host=hostname, cmd='yum install yum-utils', key=key)
    run_cmd_on_vm(host=hostname, cmd='yum groupinstall development', key=key)
    run_cmd_on_vm(host=hostname, cmd='sudo yum install https://centos7.iuscommunity.org/ius-release.rpm', key=key)
    run_cmd_on_vm(host=hostname, cmd='sudo yum install python36u', key=key)


def setup_dns_server(region, key):
    # TODO
    dns_host = ""
    return dns_host


def run_dns_server(dns_host, key):
    # install python3
    # run sudo PORT=53 ZONE_FILE='./zones.txt' P=0.8 ./dnserver.py
    pass


def run_ntp_attacker(ntp_attacker_host, shift_params, key):
    shift_type = shift_params.get('shift_type', Consts.DEFAULT_SHIFT_TYPE)
    c_shift = shift_params.get('c_shift', Consts.DEFAULT_C_SHIFT)
    slop_t_0 = shift_params.get('slop_t_0', Consts.DEFAULT_SLOP_T_0)
    slop = shift_params.get('slop', Consts.DEFAULT_SLOP)
    run_cmd_on_vm(host=ntp_attacker_host, cmd=f'python ntp_adversary.py {shift_type} {c_shift} {slop_t_0} {slop}',
                  key=key, wait_for_res=False)


def setup_clients_and_ntp(num_attackers, dns_host, region):
    """
    run the following commands to set up vms using terraform - plan and apply. once plan is applied, it's stdout
    contains the ips of the vms, parse it and return the ips.
    :return: parsed output
    """
    # TODO use dns host for vpc's dhcp option set
    # TODO use region for vpc
    cwd = str(Path('terraform', 'clients_and_attacker').resolve())
    check_output(['terraform', 'init'], cwd=cwd)
    check_output(['terraform', 'plan', '-out=tfplan', '-input=false', "-var", f'num_attacker_ips={num_attackers}'],
                 cwd=cwd)
    apply_p = check_output(['terraform', 'apply', '-input=false', 'tfplan'], cwd=cwd)
    stdout = apply_p.decode('ascii')
    return _parse_tf_output(stdout)


def teardown_tf(num_attackers):
    dns_cwd = str(Path('terraform', 'dns_server').resolve())
    clients_attacker_cwd = str(Path('terraform', 'clients_and_attacker').resolve())

    check_output(['terraform', 'destroy', '-input=false', "-var", f'num_attacker_ips={num_attackers}'],
                 cwd=clients_attacker_cwd)

    check_output(['terraform', 'destroy', '-input=false', "-var", f'num_attacker_ips={num_attackers}'],
                 cwd=dns_cwd)


def _parse_tf_output(stdout):
    rows = stdout.split('\n')
    bad_ips = []
    _chronos_host = ''
    _naive_host = ''
    _ntp_attacker_host = ''
    for row in rows:
        if re.compile("^ *\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3},*$").match(row):
            bad_ips.append(row.replace(" ", "").replace(",",""))
        if 'chronos_client =' in row:
            _chronos_host = row.split(' ')[2]
        if 'naive_client =' in row:
            _naive_host = row.split(' ')[2]
        if 'ntp_attacker_eip =' in row:
            _ntp_attacker_host = row.split(' ')[2][:len(row.split(' ')[2])-4]
    return bad_ips, _chronos_host, _naive_host, _ntp_attacker_host


def load_vm_data(dns_server_host, naive_host, chronos_host, ntp_attacker_host, key):
    copy_files_to_vm(dns_server_host, Consts.dns_files, key)
    copy_files_to_vm(naive_host, Consts.naive_files, key)
    copy_files_to_vm(chronos_host, Consts.chronos_files, key)
    copy_files_to_vm(ntp_attacker_host, Consts.attacker_files, key)


