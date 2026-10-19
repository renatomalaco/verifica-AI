import asyncio
import socket
from url_inspector.domain.ssrf_shield import assert_public_ip, SsrfBlockedException


async def resolve_safe_ip(hostname: str) -> str:
    """
    Resolves every IP address (IPv4 and IPv6) for the hostname.
    Audits each returned IP against strict SSRF rules.
    If any IP is in private/reserved space, the request is aborted immediately.
    Returns the first audited public IP for pinning in the browser (DNS pinning).
    """
    loop = asyncio.get_running_loop()
    try:
        addr_info = await loop.run_in_executor(
            None,
            lambda: socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP),
        )
    except socket.gaierror as exc:
        raise RuntimeError(f"Falha de resolução DNS para o domínio '{hostname}': {exc}") from exc

    if not addr_info:
        raise RuntimeError(f"Nenhum endereço IP retornado para o domínio '{hostname}'.")

    resolved_ips: list[str] = []
    for item in addr_info:
        ip = item[4][0]
        # Strictly validate every IP returned by the lookup
        assert_public_ip(ip)
        resolved_ips.append(ip)

    return resolved_ips[0]
