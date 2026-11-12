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


@pytest.mark.asyncio
async def test_resolve_safe_ip_reports_a_dns_failure():
    # The egress proxy turns this into a 403: an unresolvable host is never fetched.
    with patch("socket.getaddrinfo", side_effect=socket.gaierror("Name or service not known")):
        with pytest.raises(RuntimeError, match="DNS resolution failed"):
            await resolve_safe_ip("nao-existe.invalid")


@pytest.mark.asyncio
async def test_resolve_safe_ip_reports_an_empty_answer():
    with patch("socket.getaddrinfo", return_value=[]):
        with pytest.raises(RuntimeError, match="No IP address"):
            await resolve_safe_ip("vazio.example")
