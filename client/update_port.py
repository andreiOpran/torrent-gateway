import os
import requests
from dotenv import load_dotenv

# Load environment vars
load_dotenv()

# Get credentials from environment
SERVER_URL = os.getenv("SERVER_URL")
WIREGUARD_IP = os.getenv("WIREGUARD_IP")
TORRENT_PORT = int(os.getenv("TORRENT_PORT"))
QB_URL = os.getenv("QB_URL")
QB_USER = os.getenv("QB_USER")
QB_PASS = os.getenv("QB_PASS")


# Tell VPS to forward port
response = requests.post(f'{SERVER_URL}/forward-port', json={
    'port': TORRENT_PORT,
    'client_ip': WIREGUARD_IP
})
print('VPS forwarding result:', response.json())


# Log in to qBittorrent
session = requests.Session()
login = session.post(f'{QB_URL}/api/v2/auth/login', data={
    'username': QB_USER,
    'password': QB_PASS
})
if login.status_code != 200:
    print(f'Failed to log in to qBittorrent: {login.text}')
    exit()
print('Succesfully logged in to qBittorrent')


# Set torrent port
session.post(f'{QB_URL}/api/v2/app/setPreferences', data={
    'json': f'{{"listen_port": {TORRENT_PORT}}}'
})
print(f'Updated qBittorrent to use port {TORRENT_PORT}')
