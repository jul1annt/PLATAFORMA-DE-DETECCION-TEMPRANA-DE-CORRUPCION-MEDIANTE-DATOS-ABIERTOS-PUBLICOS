"""Prepare scoped Windows Firewall rules for the dedicated integration Python."""
import argparse
import hashlib
import ipaddress
import json
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.local_integration import inside, read_json, atomic_json

HOSTS = ('www.datos.gov.co', 'datos.gov.co')


def complement(allowed):
    """Return CIDRs outside the given IPv4/IPv6 networks, without overlaps."""
    result = []
    for version, universe in ((4, '0.0.0.0/0'), (6, '::/0')):
        remaining = [ipaddress.ip_network(universe)]
        for accepted in ipaddress.collapse_addresses(net for net in allowed if net.version == version):
            next_remaining = []
            for network in remaining:
                if accepted.subnet_of(network):
                    next_remaining.extend(network.address_exclude(accepted))
                else:
                    next_remaining.append(network)
            remaining = next_remaining
        result.extend(str(net) for net in sorted(remaining))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1] / '.codex-integration-postgres')
    args = parser.parse_args(); root = args.root.resolve()
    runtime = read_json(root / 'runtime.json')
    programs = [inside(root / 'runtime', runtime[name]) for name in ('python', 'base_python')]
    assert len(set(programs)) == 2 and all(path.is_file() for path in programs)
    resolved = {}
    for host in HOSTS:
        addresses = sorted({info[4][0] for info in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)})
        if not addresses or not all(ipaddress.ip_address(address).is_global for address in addresses):
            raise RuntimeError('La resolución de una fuente no contiene únicamente direcciones públicas')
        resolved[host] = addresses
    networks = [ipaddress.ip_network(address) for addresses in resolved.values() for address in addresses]
    https_blocked = complement(networks)
    external = complement([ipaddress.ip_network('127.0.0.0/8'), ipaddress.ip_network('::1/128')])
    rules = []
    for number, program in enumerate(programs):
        for kind, protocol, ports, addresses in (
            ('https-destinations', 'TCP', '443', https_blocked),
            ('other-external-tcp', 'TCP', '1-442,444-65535', external),
            ('external-udp', 'UDP', None, external),
        ):
            rules.append({'name': f'PDTC-Local-{number}-{kind}', 'program': str(program),
                          'protocol': protocol, 'ports': ports, 'addresses': addresses})
    atomic_json(root / 'egress-plan.json', {
        'scope': 'Dedicated integration Python only; no global profile changes',
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'dns_snapshot': resolved,
        'program_sha256': {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in programs},
        'rules': rules,
    })
    print(json.dumps({'plan_prepared': True, 'rules': len(rules), 'hosts': list(resolved)}))


if __name__ == '__main__':
    main()
