import os
import subprocess
import paramiko
from dotenv import load_dotenv

# Load environment vars
load_dotenv()

# VPS connection credentials
VPS_IP = os.getenv('VPS_IP')
VPS_USER = 'root'
VPS_SSH_KEY = '.ssh-key'

# WireGuard config
WG_PORT = os.getenv('WG_PORT')
SERVER_WG_IP = '10.0.0.1/24'
CLIENT_WG_IP = '10.0.0.2/24'


# Generate WireGuard keys
def generate_keys(prefix):
    private_key = subprocess.check_output("wg genkey", shell=True).decode().strip()
    public_key = subprocess.check_output(f'echo {private_key} | wg pubkey', shell=True).decode().strip()
    with open(f'{prefix}_private.key', 'w') as f:
        f.write(private_key)
    with open(f'{prefix}_public.key', 'w') as f:
        f.write(public_key)

    return private_key, public_key


def write_server_config(server_private, client_public):
    return f'''
[Interface]
Address = {SERVER_WG_IP}
ListenPort = {WG_PORT}
PrivateKey = {server_private}
PostUp = echo 1 > /proc/sys/net/ipv4/ip_forward; iptables -A FORWARD -i wg0 -j ACCEPT; iptables -A FORWARD -o wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o ens3 -j MASQUERADE
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT; iptables -D FORWARD -o wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o ens3 -j MASQUERADE

[Peer]
PublicKey = {client_public}
AllowedIPs = {CLIENT_WG_IP.split('/')[0]}/32
'''


def write_client_config(client_private, server_public):
    return f'''
[Interface]
Address = {CLIENT_WG_IP}
PrivateKey = {client_private}
DNS = 8.8.8.8

[Peer]
PublicKey = {server_public}
Endpoint = {VPS_IP}:{WG_PORT}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
'''


# Upload server config to VPS
def upload_and_start_server(server_config):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VPS_IP, username=VPS_USER, key_filename=VPS_SSH_KEY)

    ssh.exec_command('mkdir -p /etc/wireguard')

    sftp = ssh.open_sftp()
    with sftp.file('/tmp/wg0.conf', 'w') as f:
        f.write(server_config)
    sftp.close()

    commands = [
        'mv /tmp/wg0.conf /etc/wireguard/wg0.conf',
        'chmod 600 /etc/wireguard/wg0.conf',
        'wg-quick down wg0 2>/dev/null || true',
        'wg-quick up wg0'
    ]

    for command in commands:
        stdin, stdout, stderr = ssh.exec_command(command)
        exit_status = stdout.channel.recv_exit_status()  # wait for command completion
        if exit_status != 0 and 'down wg0' not in command:
            error = stderr.read().decode()
            print(f"Error executing '{command}': {error}")
    ssh.close()


def start_local_wireguard():
    # Stop any existing connection
    subprocess.run(['sudo', 'wg-quick', 'down', 'wg0'],
                   capture_output=True, check=False)

    # Copy config to system location
    subprocess.run(['sudo', 'cp', 'wg0.conf', '/etc/wireguard/wg0.conf'],
                   check=True)
    subprocess.run(['sudo', 'chmod', '600', '/etc/wireguard/wg0.conf'],
                   check=True)

    # Start new connection
    result = subprocess.run(['sudo', 'wg-quick', 'up', 'wg0'],
                            capture_output=True, text=True, check=True)


def main_setup():
    server_private, server_public = generate_keys('server')
    client_private, client_public = generate_keys('client')

    server_config = write_server_config(server_private, client_public)
    client_config = write_client_config(client_private, server_public)

    # Save local client config
    with open('wg0.conf', 'w') as f:
        f.write(client_config)

    # Upload server config and start
    upload_and_start_server(server_config)

    # Start local connection
    start_local_wireguard()

    print('VPN tunnel established.')


if __name__ == '__main__':
    server_private, server_public = generate_keys('server')
    client_private, client_public = generate_keys('client')

    server_config = write_server_config(server_private, client_public)
    client_config = write_client_config(client_private, server_public)

    # Save local client config
    with open('wg0.conf', 'w') as f:
        f.write(client_config)

    # Upload server config and start
    upload_and_start_server(server_config)

    # Start local connection
    start_local_wireguard()

    print('VPN tunnel established.')

