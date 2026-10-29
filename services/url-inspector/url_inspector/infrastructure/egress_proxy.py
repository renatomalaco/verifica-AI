"""
Egress proxy: the only way the inspector's browser reaches the internet. Every request
(first page, redirects, images, scripts) is resolved here, every IP goes through the SSRF
shield, and the upstream connection uses the validated IP, so DNS rebinding cannot slip in.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable

from url_inspector.domain.proxy_request import ProxyTarget, parse_request_head
from url_inspector.domain.ssrf_shield import SsrfBlockedException
from url_inspector.infrastructure.resolver import resolve_safe_ip

logger = logging.getLogger("url_inspector.egress")

WEB_PORTS = frozenset({80, 443})
HEAD_LIMIT = 16 * 1024
TIMEOUT_SECONDS = 10.0
FORBIDDEN = b"HTTP/1.1 403 Forbidden\r\nConnection: close\r\nContent-Length: 0\r\n\r\n"
BAD_REQUEST = b"HTTP/1.1 400 Bad Request\r\nConnection: close\r\nContent-Length: 0\r\n\r\n"
TUNNEL_OPEN = b"HTTP/1.1 200 Connection Established\r\n\r\n"


class EgressProxy:
    def __init__(
        self,
        resolve: Callable[[str], Awaitable[str]] = resolve_safe_ip,
        allowed_ports: frozenset[int] | set[int] = WEB_PORTS,
    ) -> None:
        self._resolve = resolve
        self._allowed_ports = allowed_ports

    async def handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            target = parse_request_head(await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), TIMEOUT_SECONDS))
            ip = await self._authorize(target)
        except (ValueError, asyncio.LimitOverrunError, asyncio.IncompleteReadError, asyncio.TimeoutError):
            await _reply_and_close(writer, BAD_REQUEST)
            return
        except (SsrfBlockedException, RuntimeError) as exc:
            logger.warning("blocked egress: %s", exc)
            await _reply_and_close(writer, FORBIDDEN)
            return
        await self._relay(reader, writer, target, ip)

    async def _authorize(self, target: ProxyTarget) -> str:
        if target.port not in self._allowed_ports:
            raise SsrfBlockedException(f"port {target.port} is not a web port")
        return await self._resolve(target.host)

    async def _relay(self, reader, writer, target: ProxyTarget, ip: str) -> None:
        try:
            up_reader, up_writer = await asyncio.wait_for(asyncio.open_connection(ip, target.port), TIMEOUT_SECONDS)
        except (OSError, asyncio.TimeoutError):
            await _reply_and_close(writer, FORBIDDEN)
            return
        if target.is_tunnel:
            writer.write(TUNNEL_OPEN)
        else:
            up_writer.write(target.forward_head)
        await asyncio.gather(_pipe(reader, up_writer), _pipe(up_reader, writer))


async def _pipe(source: asyncio.StreamReader, sink: asyncio.StreamWriter) -> None:
    try:
        while chunk := await source.read(64 * 1024):
            sink.write(chunk)
            await sink.drain()
    except (ConnectionError, asyncio.IncompleteReadError):
        pass
    finally:
        sink.close()


async def _reply_and_close(writer: asyncio.StreamWriter, response: bytes) -> None:
    writer.write(response)
    try:
        await writer.drain()
    finally:
        writer.close()


async def serve(host: str = "0.0.0.0", port: int = 3128) -> None:
    server = await asyncio.start_server(EgressProxy().handle, host, port, limit=HEAD_LIMIT)
    async with server:
        await server.serve_forever()
