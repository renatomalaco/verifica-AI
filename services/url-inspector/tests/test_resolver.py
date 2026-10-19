import pytest
from unittest.mock import patch
import socket
from url_inspector.domain.ssrf_shield import SsrfBlockedException
from url_inspector.infrastructure.resolver import resolve_safe_ip


@pytest.mark.asyncio
async def test_resolve_safe_ip_returns_public_ip():
    with patch("socket.getaddrinfo") as mock_dns:
        mock_dns.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 80))
        ]
        ip = await resolve_safe_ip("example.com")
        assert ip == "93.184.216.34"


@pytest.mark.asyncio
async def test_resolve_safe_ip_rejects_mixed_dns_response():
    # Adversarial scenario: domain returns a public AND a private IP to attempt DNS rebinding
    with patch("socket.getaddrinfo") as mock_dns:
        mock_dns.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 80)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 80)),
        ]
        with pytest.raises(SsrfBlockedException):
            await resolve_safe_ip("adversarial-rebinding.com")
