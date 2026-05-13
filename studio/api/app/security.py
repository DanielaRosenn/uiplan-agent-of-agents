from __future__ import annotations

from collections.abc import Callable
from ipaddress import ip_address

from fastapi import Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware

LOCAL_HOSTNAMES = {"localhost", "127.0.0.1", "::1"}
LOCAL_CLIENT_HOSTNAMES = {"localhost", "127.0.0.1", "::1", "testclient"}


def _host_without_port(host_header: str | None) -> str:
    if not host_header:
        return ""
    host = host_header.strip().lower()
    if host.startswith("[") and "]" in host:
        return host[1 : host.index("]")]
    if host.count(":") == 1:
        return host.rsplit(":", 1)[0]
    return host


def is_loopback_host(host_header: str | None) -> bool:
    host = _host_without_port(host_header)
    if host in LOCAL_HOSTNAMES:
        return True
    try:
        return ip_address(host).is_loopback
    except ValueError:
        return False


def is_loopback_client(client_host: str | None) -> bool:
    if not client_host:
        return False
    host = client_host.strip().lower()
    if host in LOCAL_CLIENT_HOSTNAMES:
        return True
    try:
        return ip_address(host).is_loopback
    except ValueError:
        return False


class LocalOnlyMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> Response:
        if not is_loopback_client(request.client.host if request.client else None):
            return JSONResponse(
                status_code=403,
                content={"detail": "UiPlan Studio API is local-only."},
            )
        host_header = request.headers.get("host")
        if host_header and host_header.strip().lower() != "testserver" and not is_loopback_host(host_header):
            return JSONResponse(
                status_code=403,
                content={"detail": "UiPlan Studio API is local-only."},
            )
        return await call_next(request)
