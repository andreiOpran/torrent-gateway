import subprocess
import ipaddress
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator

app = FastAPI()


class PortRequest(BaseModel):
    port: int
    client_ip: str

    @field_validator('client_ip')
    def validate_ip(self, value):
        try:
            ipaddress.ip_address(value)
        except ValueError:
            raise ValueError('Invalid IP address')
        return value

    @field_validator('port')
    def validate_port(self, value):
        if not 1 <= value <= 65535:
            raise ValueError('Port must be between 1 and 65535')
        return value


@app.post('/forward-port')
def forward_port(req: PortRequest):
    try:
        # iptables rules for WireGuard interface 'wg0'
        for protocol in ['tcp', 'udp']:
            # DNAT rules
            subprocess.run([
                'sudo', 'iptables', '-t', 'nat', '-A', 'PREROUTING',
                '-p', protocol, '--dport', str(req.port),
                '-j', 'DNAT', '--to-destination', f'{req.client_ip}:{req.port}'
            ], check=True)

            # Forward rules to allow the traffic
            subprocess.run([
                'sudo', 'iptables', '-A', 'FORWARD',
                '-p', protocol, '-d', req.client_ip, '--dport', str(req.port),
                '-j', 'ACCEPT'
            ], check=True)

        return {'status': 'ok', 'port': req.port}
    except subprocess.CalledProcessError as e:
        raise HTTPException(500, f'iptables error: {e}')


@app.get('/health')
def health():
    return {'status': 'server running'}
