import pytest
from url_inspector.domain.ssrf_shield import is_ip_allowed, assert_public_ip, SsrfBlockedException


@pytest.mark.parametrize(
    "forbidden_ip",
    [
        "127.0.0.1",
        "127.255.255.255",
        "10.0.0.1",
        "10.255.255.254",
        "172.16.0.1",
        "172.31.255.255",
        "192.168.0.1",
        "192.168.100.200",
        "169.254.1.1",
        "169.254.169.254",  # AWS/OCI metadata endpoint
        "100.64.0.1",       # CGNAT
        "0.0.0.0",
        "255.255.255.255",
        "::1",
        "fc00::1",          # IPv6 ULA
        "fd00:ec2::254",    # AWS IPv6 metadata
        "fe80::1",          # IPv6 Link-local
        "::ffff:127.0.0.1", # IPv4-mapped loopback
        "::ffff:169.254.169.254", # IPv4-mapped metadata
    ],
)
def test_ssrf_shield_rejects_private_ips(forbidden_ip: str):
    assert is_ip_allowed(forbidden_ip) is False
    with pytest.raises(SsrfBlockedException):
        assert_public_ip(forbidden_ip)


@pytest.mark.parametrize(
    "public_ip",
    [
        "8.8.8.8",
        "1.1.1.1",
        "142.250.190.46",
        "200.147.3.157",
        "2606:4700:4700::1111",
    ],
)
def test_ssrf_shield_allows_public_ips(public_ip: str):
    assert is_ip_allowed(public_ip) is True
    # Must not raise
    assert_public_ip(public_ip)
