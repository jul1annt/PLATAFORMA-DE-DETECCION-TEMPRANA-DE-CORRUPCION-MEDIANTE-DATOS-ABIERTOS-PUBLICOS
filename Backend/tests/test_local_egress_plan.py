import ipaddress
from scripts.prepare_local_egress import complement


def test_address_complement_blocks_only_addresses_outside_the_approved_set():
    approved = [ipaddress.ip_network('8.8.8.8/32'), ipaddress.ip_network('2606:4700:4700::1111/128')]
    blocked = [ipaddress.ip_network(value) for value in complement(approved + approved)]
    for value, expected in [('8.8.8.8', False), ('8.8.8.9', True), ('127.0.0.1', True),
                            ('2606:4700:4700::1111', False), ('2606:4700:4700::1112', True), ('::1', True)]:
        address = ipaddress.ip_address(value)
        assert any(address in network for network in blocked if network.version == address.version) == expected


def test_external_address_complement_preserves_only_loopback():
    blocked = [ipaddress.ip_network(value) for value in complement([
        ipaddress.ip_network('127.0.0.0/8'), ipaddress.ip_network('::1/128')])]
    for value, expected in [('127.0.0.1', False), ('127.5.4.3', False), ('::1', False),
                            ('192.168.1.1', True), ('1.1.1.1', True), ('::2', True)]:
        address = ipaddress.ip_address(value)
        assert any(address in network for network in blocked if network.version == address.version) == expected
