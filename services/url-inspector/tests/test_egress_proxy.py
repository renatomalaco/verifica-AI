import asyncio

import pytest

from url_inspector.domain.proxy_request import parse_request_head
from url_inspector.domain.ssrf_shield import SsrfBlockedException, assert_public_ip
from url_inspector.infrastructure.egress_proxy import EgressProxy


# --- Parsing (pure) ---

def test_connect_is_a_tunnel_to_host_and_port():
    target = parse_request_head(b"CONNECT banco.example:443 HTTP/1.1\r\nHost: banco.example:443\r\n\r\n")
    assert (target.host, target.port, target.is_tunnel) == ("banco.example", 443, True)


def test_absolute_http_request_becomes_origin_form_and_closes_the_connection():
    head = b"GET http://site.example/promo?x=1 HTTP/1.1\r\nHost: site.example\r\nProxy-Connection: keep-alive\r\n\r\n"
    target = parse_request_head(head)
    assert (target.host, target.port, target.is_tunnel) == ("site.example", 80, False)
    assert target.forward_head.startswith(b"GET /promo?x=1 HTTP/1.1\r\n")
    assert b"Connection: close\r\n" in target.forward_head
    assert b"Proxy-Connection" not in target.forward_head


@pytest.mark.parametrize("head", [b"GET /relative HTTP/1.1\r\n\r\n", b"lixo\r\n\r\n", b"CONNECT semporta HTTP/1.1\r\n\r\n"])
def test_malformed_requests_are_rejected(head):
    with pytest.raises(ValueError):
        parse_request_head(head)


# --- Proxy behaviour (local sockets only) ---

async def fake_resolve(host: str) -> str:
    """'ok.test' points to a local upstream; anything else resolves to the cloud metadata IP."""
    if host == "ok.test":
        return "127.0.0.1"
    assert_public_ip("169.254.169.254")
    return "169.254.169.254"


async def start_upstream():
    async def handle(reader, writer):
        await reader.readuntil(b"\r\n\r\n")
        writer.write(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nok")
        await writer.drain()
        writer.close()

    server = await asyncio.start_server(handle, "127.0.0.1", 0)
    return server, server.sockets[0].getsockname()[1]


async def start_proxy(upstream_port: int):
    proxy = EgressProxy(resolve=fake_resolve, allowed_ports={443, upstream_port})
    server = await asyncio.start_server(proxy.handle, "127.0.0.1", 0)
    return server, server.sockets[0].getsockname()[1]


async def send(proxy_port: int, request: bytes) -> bytes:
    reader, writer = await asyncio.open_connection("127.0.0.1", proxy_port)
    writer.write(request)
    await writer.drain()
    response = await asyncio.wait_for(reader.read(4096), timeout=5)
    writer.close()
    return response


async def test_request_to_a_validated_host_is_forwarded():
    upstream, upstream_port = await start_upstream()
    proxy, proxy_port = await start_proxy(upstream_port)
    async with upstream, proxy:
        response = await send(proxy_port, f"GET http://ok.test:{upstream_port}/ HTTP/1.1\r\nHost: ok.test\r\n\r\n".encode())
    assert response.startswith(b"HTTP/1.1 200 OK")
    assert response.endswith(b"ok")


async def test_redirect_target_on_cloud_metadata_is_blocked():
    # A phishing page that redirects (or loads an <img>) to the metadata service hits the proxy like any request.
    upstream, upstream_port = await start_upstream()
    proxy, proxy_port = await start_proxy(upstream_port)
    async with upstream, proxy:
        response = await send(proxy_port, b"CONNECT metadata.test:443 HTTP/1.1\r\nHost: metadata.test:443\r\n\r\n")
    assert response.startswith(b"HTTP/1.1 403")


async def test_ports_other_than_web_are_blocked():
    upstream, upstream_port = await start_upstream()
    proxy, proxy_port = await start_proxy(upstream_port)
    async with upstream, proxy:
        response = await send(proxy_port, b"CONNECT ok.test:22 HTTP/1.1\r\nHost: ok.test:22\r\n\r\n")
    assert response.startswith(b"HTTP/1.1 403")


def test_the_real_resolver_is_the_default():
    from url_inspector.infrastructure.resolver import resolve_safe_ip

    assert EgressProxy()._resolve is resolve_safe_ip
    assert SsrfBlockedException  # the proxy reports blocks as 403
