#!/usr/bin/env python3
"""Security boundary shared by the browser Studio and workstation server."""
from __future__ import annotations

import hashlib
import hmac
import ipaddress
import os
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Mapping
from urllib.parse import unquote, urlparse

STUDIO_TOKEN_ENV = "AIVE_STUDIO_TOKEN"
SESSION_COOKIE = "aive_studio_session"
_SESSION_CONTEXT = b"aivideoedit-studio-session-v1"


def configured_token() -> str | None:
    value = os.environ.get(STUDIO_TOKEN_ENV, "").strip()
    return value or None


def is_loopback(value: str) -> bool:
    host = str(value or "").strip().strip("[]").lower()
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def validate_bind(host: str) -> None:
    if not is_loopback(host):
        token = configured_token()
        if not token or len(token.encode("utf-8")) < 32:
            raise RuntimeError(
                f"Refusing non-loopback bind {host!r} without a strong "
                f"{STUDIO_TOKEN_ENV} (minimum 32 bytes). Use 127.0.0.1 or "
                "configure a strong Studio token."
            )


def session_value(token: str) -> str:
    return hmac.new(token.encode("utf-8"), _SESSION_CONTEXT, hashlib.sha256).hexdigest()


def session_cookie(token: str) -> str:
    return f"{SESSION_COOKIE}={session_value(token)}; Path=/; HttpOnly; SameSite=Strict"


def _header(headers: Mapping[str, str], name: str) -> str:
    return str(headers.get(name) or "").strip()


def _valid_bearer(headers: Mapping[str, str], token: str) -> bool:
    auth = _header(headers, "Authorization")
    if not auth.startswith("Bearer "):
        return False
    return hmac.compare_digest(auth[len("Bearer "):], token)


def _valid_session(headers: Mapping[str, str], token: str) -> bool:
    raw = _header(headers, "Cookie")
    if not raw:
        return False
    try:
        cookies = SimpleCookie(raw)
        supplied = cookies.get(SESSION_COOKIE)
        return bool(supplied) and hmac.compare_digest(supplied.value, session_value(token))
    except Exception:
        return False


def _same_origin(headers: Mapping[str, str]) -> bool:
    host = _header(headers, "Host").lower()
    source = _header(headers, "Origin") or _header(headers, "Referer")
    if not host or not source:
        return False
    try:
        return urlparse(source).netloc.lower() == host
    except Exception:
        return False


def _request_host_is_loopback(headers: Mapping[str, str]) -> bool:
    raw = _header(headers, "Host")
    if not raw:
        return False
    try:
        parsed = urlparse(f"//{raw}")
        return is_loopback(parsed.hostname or "")
    except Exception:
        return False


def authorize(
    headers: Mapping[str, str],
    client_ip: str,
    *,
    mutating: bool,
) -> tuple[bool, int, str, str]:
    """Return allowed, HTTP status, reason and authorization mode."""
    token = configured_token()
    origin_present = bool(_header(headers, "Origin") or _header(headers, "Referer"))
    fetch_site = _header(headers, "Sec-Fetch-Site").lower()
    if fetch_site in {"cross-site", "same-site"}:
        return False, 403, "cross-origin Studio request denied", "none"

    if token:
        bearer = _valid_bearer(headers, token)
        cookie = _valid_session(headers, token)
        if not bearer and not cookie:
            return False, 401, "Studio authorization required", "none"
        if origin_present and not _same_origin(headers):
            return False, 403, "cross-origin Studio request denied", "none"
        if mutating and cookie and not bearer and not _same_origin(headers):
            return False, 403, "same-origin Studio session required", "none"
        return True, 200, "authorized", "bearer" if bearer else "session"

    if not is_loopback(client_ip):
        return False, 401, "Studio is restricted to the local workstation", "none"
    if not _request_host_is_loopback(headers):
        return False, 403, "non-loopback Host denied in local Studio mode", "none"
    if origin_present and not _same_origin(headers):
        return False, 403, "cross-origin Studio request denied", "none"
    return True, 200, "authorized", "loopback"


def authorize_session(headers: Mapping[str, str], client_ip: str) -> tuple[bool, int, str]:
    token = configured_token()
    if token:
        if _valid_bearer(headers, token):
            return True, 200, "authorized"
        return False, 401, "valid Studio bearer token required"
    if is_loopback(client_ip):
        return True, 200, "loopback mode"
    return False, 401, "Studio is restricted to the local workstation"


def decode_path(value: str) -> str:
    decoded = str(value or "")
    for _ in range(8):
        candidate = unquote(decoded)
        if candidate == decoded:
            break
        decoded = candidate
    return decoded.replace("\\", "/")


def contained_path(root: Path, relative: str) -> Path | None:
    root = root.resolve()
    decoded = decode_path(relative)
    if "\x00" in decoded:
        return None
    parts = [part for part in decoded.split("/") if part]
    if any(part in {".", ".."} or ":" in part for part in parts):
        return None
    try:
        target = (root / decoded.lstrip("/")).resolve()
        target.relative_to(root)
    except (OSError, RuntimeError, ValueError):
        return None
    return target


def static_target(root: Path, request_path: str) -> Path | None:
    parsed = urlparse(request_path).path
    decoded = decode_path(parsed)
    if decoded == "/":
        decoded = "/index.html"
    return contained_path(root, decoded)
