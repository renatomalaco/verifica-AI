import ipaddress


class SsrfBlockedException(Exception):
    """Raised when an IP address or hostname resolves to a private or restricted network."""
    pass


CGNAT_NETWORK = ipaddress.ip_network("100.64.0.0/10")
CLOUD_METADATA_V4 = ipaddress.ip_address("169.254.169.254")
CLOUD_METADATA_V6 = ipaddress.ip_address("fd00:ec2::254")


def is_literal_ip(host: str) -> bool:
    """Checks whether the string is a literal numeric IPv4 or IPv6 address."""
    try:
        ipaddress.ip_address(host.strip())
        return True
    except ValueError:
        return False


def is_ip_allowed(ip_str: str) -> bool:
    """
    Checks whether the given IP is a public IP that is safe for remote browsing.
    Rejects RFC 1918, RFC 3927 (link-local), loopback, CGNAT, cloud metadata and reserved blocks.
    """
    try:
        ip = ipaddress.ip_address(ip_str.strip())
    except ValueError:
        return False

    # For IPv4-mapped IPv6 (e.g. ::ffff:127.0.0.1), extract the inner IPv4
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped

    if ip == CLOUD_METADATA_V4 or ip == CLOUD_METADATA_V6:
        return False

    if ip.is_loopback:
        return False

    if ip.is_private:
        return False

    if ip.is_link_local:
        return False

    if ip.is_multicast or ip.is_reserved or ip.is_unspecified:
        return False

    # CGNAT check (100.64.0.0/10)
    if isinstance(ip, ipaddress.IPv4Address) and ip in CGNAT_NETWORK:
        return False

    return True


def assert_public_ip(ip_str: str) -> None:
    """Raises SsrfBlockedException if the IP is private or unsafe."""
    if not is_ip_allowed(ip_str):
        raise SsrfBlockedException(f"SSRF block: IP address '{ip_str}' belongs to a private or reserved network.")
