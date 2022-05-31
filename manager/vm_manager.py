from fabric import Connection
from consts import Consts


def copy_files_to_vm(host, files, key):
    """
    Copies the given files to the machine of the given host.
    :param host: machine's ip
    :param files: paths to the files to be copied (list)
    :param key: ssh key for the connection
    """
    connection = Connection(host=host, user="ubuntu", connect_kwargs={"key_filename": key})
    for file in files:
        connection.put(file, '/home/ubuntu')


def run_cmd_on_vm(host, cmd, key, user='ubuntu', wait_for_res=True, sudo=True):
    """
    Runs the given command in the cmd of the given machine
    :param host: machine's ip
    :param cmd: command to run
    :param key: ssh key for the connection
    :param user: username of the machine
    :param wait_for_res: boolean variable, if true- the function waits for the command's output and returns it
    :param sudo: boolean, if true- the command runs with "sudo"
    return: The command's output if "wait_for_res" is True. Otherwise- None
    """
    if not wait_for_res:
        cmd += "2>/dev/null >/dev/null &"  # this will redirect stdout to another file and not wait for it
    connection = Connection(host=host, user=user, connect_kwargs={"key_filename": key})
    if sudo:
        output = connection.sudo(cmd, hide=True)#, hide=True, stdout=fh)
    else:
        output = connection.run(cmd, hide=True)
    if wait_for_res:
        return output.stdout
        # return connection.stdout()


def run_dns_server(dns_host, key, attack_prob, close=True):
    run_cmd_on_vm(host=dns_host,
                  cmd=f"PORT=53 CLOSE={1 if close else 0} ZONE_FILE='./zones.txt' P={attack_prob} ./dnserver.py",
                  key=key, wait_for_res=True)


def run_ntp_attacker(ntp_attacker_host, shift_params, key):
    shift_type = shift_params.get('shift_type', Consts.DEFAULT_SHIFT_TYPE)
    c_shift = shift_params.get('c_shift', Consts.DEFAULT_C_SHIFT)
    slop_t_0 = shift_params.get('slop_t_0', Consts.DEFAULT_SLOP_T_0)
    slop = shift_params.get('slop', Consts.DEFAULT_SLOP)
    run_cmd_on_vm(host=ntp_attacker_host, cmd=f'python3 ntp_adversary.py {shift_type} {c_shift} {slop_t_0} {slop}',
                  key=key, wait_for_res=True, user='ubuntu')


def load_vm_data(dns_server_host, chronos_host, ntp_attacker_host, key):
    copy_files_to_vm(dns_server_host, Consts.dns_files, key)
    copy_files_to_vm(chronos_host, Consts.chronos_files, key)
    # copy_files_to_vm(ntp_attacker_host, Consts.attacker_files, key)


def close_port(dns_ip, key):
    run_cmd_on_vm(host=dns_ip, cmd='systemctl stop systemd-resolved',
                  key=key, wait_for_res=True, user='ubuntu')
    run_cmd_on_vm(host=dns_ip, cmd='systemctl disable systemd-resolved',
                  key=key, wait_for_res=True, user='ubuntu')
    run_cmd_on_vm(host=dns_ip, cmd='systemctl mask system-resolved',
                  key=key, wait_for_res=True, user='ubuntu')
    output = ""
    try:
        output = run_cmd_on_vm(host=dns_ip, cmd='lsof -i :53', key=key, wait_for_res=True, user='ubuntu')
    except Exception as e:
        if "sudo" not in str(e):
            raise Exception
    if "COMMAND" in output:
        output = output.split("\n")
        proc = output[1].split()[1]
        run_cmd_on_vm(host=dns_ip, cmd=f'kill -9 {proc}',key=key, wait_for_res=True, user='ubuntu')

