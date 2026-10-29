"""Parses what the browser asks the egress proxy for: a CONNECT tunnel or an absolute-form HTTP request."""

from dataclasses import dataclass
from urllib.parse import urlsplit

HOP_BY_HOP = (b"proxy-connection", b"connection", b"keep-alive", b"proxy-authorization")


@dataclass(frozen=True)
class ProxyTarget:
    host: str
    port: int
    is_tunnel: bool
    forward_head: bytes = b""  # origin-form request sent upstream (plain HTTP only)


def parse_request_head(head: bytes) -> ProxyTarget:
    lines = head.split(b"\r\n")
    parts = lines[0].split(b" ")
    if len(parts) != 3:
        raise ValueError("malformed request line")
    method, target, version = parts
    if method == b"CONNECT":
        return _tunnel(target.decode("ascii"))
    return _plain_http(method, target.decode("ascii"), version, lines[1:])


def _tunnel(authority: str) -> ProxyTarget:
    host, sep, port = authority.rpartition(":")
    if not (sep and host and port.isdigit()):
        raise ValueError("CONNECT needs host:port")
    return ProxyTarget(host=host.strip("[]").lower(), port=int(port), is_tunnel=True)


def _plain_http(method: bytes, target: str, version: bytes, headers: list[bytes]) -> ProxyTarget:
    url = urlsplit(target)
    if url.scheme != "http" or not url.hostname:
        raise ValueError("only absolute http:// requests are proxied in plain text")
    path = (url.path or "/") + (f"?{url.query}" if url.query else "")
    kept = [h for h in headers if h and h.split(b":", 1)[0].strip().lower() not in HOP_BY_HOP]
    # One request per connection, so a kept-alive socket can never be reused for another host.
    head = b"\r\n".join([method + b" " + path.encode("ascii") + b" " + version, *kept, b"Connection: close", b"", b""])
    return ProxyTarget(host=url.hostname.lower(), port=url.port or 80, is_tunnel=False, forward_head=head)
