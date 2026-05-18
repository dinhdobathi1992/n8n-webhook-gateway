import fnmatch
import ipaddress
import socket
from urllib.parse import urlparse

from app.config import settings
from app.security import csv_values


def _allowed_hosts() -> list[str]:
    return csv_values(settings.allowed_internal_hosts)


def _host_matches(pattern: str, host: str) -> bool:
    pattern = pattern.lower()
    host = host.lower()
    return host == pattern or fnmatch.fnmatch(host, pattern)


def _is_allowed_host(host: str) -> bool:
    return any(_host_matches(pattern, host) for pattern in _allowed_hosts())


def _is_blocked_ip(value: str) -> bool:
    ip = ipaddress.ip_address(value)
    return any(
        (
            ip.is_private,
            ip.is_loopback,
            ip.is_link_local,
            ip.is_multicast,
            ip.is_reserved,
            ip.is_unspecified,
        )
    )


def validate_http_url(value: str | None, *, field_name: str, destination: bool) -> str | None:
    if value is None:
        return None
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(f"{field_name} must start with http:// or https://")
    if not parsed.hostname:
        raise ValueError(f"{field_name} must include a hostname")
    if parsed.username or parsed.password:
        raise ValueError(f"{field_name} must not include credentials")
    if destination and settings.block_private_destination_ips and not _is_allowed_host(parsed.hostname):
        try:
            if _is_blocked_ip(parsed.hostname):
                raise ValueError(f"{field_name} points to a blocked private/internal address")
        except ValueError as exc:
            if "blocked private/internal" in str(exc):
                raise
    return value


def assert_destination_allowed(value: str) -> None:
    validate_http_url(value, field_name="destination_url", destination=True)
    if not settings.block_private_destination_ips:
        return

    parsed = urlparse(value)
    host = parsed.hostname
    if not host or _is_allowed_host(host):
        return

    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValueError(f"destination_url hostname could not be resolved: {host}") from exc

    checked: set[str] = set()
    for info in infos:
        ip = info[4][0]
        if ip in checked:
            continue
        checked.add(ip)
        if _is_blocked_ip(ip):
            raise ValueError(f"destination_url resolves to blocked private/internal address: {ip}")
