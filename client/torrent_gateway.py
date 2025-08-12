import wireguard_setup
import requests
from dotenv import load_dotenv
import os

# Load environment vars
load_dotenv()

# Get credentials from environment
SERVER_URL = os.getenv("SERVER_URL")
WIREGUARD_IP = os.getenv("WIREGUARD_IP")
TORRENT_PORT = int(os.getenv("TORRENT_PORT"))
QB_URL = os.getenv("QB_URL")
QB_USER = os.getenv("QB_USER")
QB_PASS = os.getenv("QB_PASS")


def update_port_on_vps():
    response = requests.post(f'{SERVER_URL}/forward-port', json={
        'port': TORRENT_PORT,
        'client_ip': WIREGUARD_IP
    })
    print('[VPS] Port forwarding result:', response.json())


def update_qbittorrent_port():
    # Log in to qBittorrent
    session = requests.Session()
    login = session.post(f'{QB_URL}/api/v2/auth/login', data={
        'username': QB_USER,
        'password': QB_PASS
    })
    if login.status_code != 200:
        raise Exception(f'[qBit] Failed to log in to qBittorrent: {login.text}')
    print('[qBit] Succesfully logged in to qBittorrent')

    session.post(f'{QB_URL}/api/v2/app/setPreferences', data={
        'json': f'{{"listen_port": {TORRENT_PORT}}}'
    })
    print(f'[qBit] Updated qBittorrent to use port {TORRENT_PORT}')


def check_port_open():
    try:
        response = requests.get(f'https://api.canyouseeme.org/port/{TORRENT_PORT}')
        print(f'[Check] Port ({TORRENT_PORT}) open:', response.text)
    except Exception as e:
        raise Exception('Error checking port:', e)


if __name__ == '__main__':
    try:
        # Optional: call wireguard setup
        wireguard_setup.main_setup()

        update_port_on_vps()
        update_qbittorrent_port()
        check_port_open()

    except Exception as e:
        print(f'Error in main function: {e}')
        exit(1)

