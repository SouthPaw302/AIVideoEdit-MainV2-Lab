from __future__ import annotations

import http.client
import json
import os
import sys
import threading
from contextlib import contextmanager
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1] / "prototype" / "backend_gui"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import server as base
import stack
import studio_security


@contextmanager
def running(handler):
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield httpd.server_address[1]
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


def request(port, method, path, *, headers=None, body=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        conn.request(method, path, body=body, headers=headers or {})
        response = conn.getresponse()
        payload = response.read()
        return response.status, dict(response.getheaders()), payload
    finally:
        conn.close()


def isolated_state(monkeypatch, tmp_path):
    runtime = tmp_path / "runtime"
    monkeypatch.setattr(base, "RUNTIME", runtime)
    monkeypatch.setattr(base, "ASSET_ROOT", runtime / "assets")
    monkeypatch.setattr(base, "PROJECT_ROOT", runtime / "projects")
    monkeypatch.setattr(base, "STATE_FILE", runtime / "state.json")
    monkeypatch.setattr(base, "STATE", {"version": 1, "projects": [], "jobs": [], "assets": []})
    base.load_state()


def test_loopback_default_and_non_loopback_bind_requires_token(monkeypatch):
    monkeypatch.delenv("AIVE_STUDIO_TOKEN", raising=False)
    studio_security.validate_bind("127.0.0.1")
    studio_security.validate_bind("::1")
    with pytest.raises(RuntimeError, match="AIVE_STUDIO_TOKEN"):
        studio_security.validate_bind("0.0.0.0")
    with pytest.raises(RuntimeError, match="AIVE_STUDIO_TOKEN"):
        studio_security.validate_bind("192.0.2.20")
    monkeypatch.setenv("AIVE_STUDIO_TOKEN", "s" * 32)
    studio_security.validate_bind("0.0.0.0")


def test_untrusted_non_loopback_client_is_denied_without_token(monkeypatch):
    monkeypatch.delenv("AIVE_STUDIO_TOKEN", raising=False)
    ok, status, _, _ = studio_security.authorize(
        {"Host": "192.0.2.20:8080"}, "192.0.2.20", mutating=False
    )
    assert ok is False
    assert status == 401


def test_dns_rebinding_host_is_denied_in_loopback_mode(monkeypatch):
    monkeypatch.delenv("AIVE_STUDIO_TOKEN", raising=False)
    ok, status, _, _ = studio_security.authorize(
        {"Host": "attacker.example:8080"}, "127.0.0.1", mutating=False
    )
    assert ok is False
    assert status == 403


def test_cross_site_read_is_denied_in_loopback_mode(monkeypatch):
    monkeypatch.delenv("AIVE_STUDIO_TOKEN", raising=False)
    ok, status, _, _ = studio_security.authorize(
        {
            "Host": "127.0.0.1:8080",
            "Referer": "https://attacker.example/page",
            "Sec-Fetch-Site": "cross-site",
        },
        "127.0.0.1",
        mutating=False,
    )
    assert ok is False
    assert status == 403


def test_sensitive_studio_routes_require_auth_and_same_origin(monkeypatch, tmp_path):
    isolated_state(monkeypatch, tmp_path)
    monkeypatch.setenv("AIVE_STUDIO_TOKEN", "studio-secret")
    with running(base.Handler) as port:
        status, _, body = request(port, "GET", "/api/health")
        assert status == 200
        assert "workspace" not in json.loads(body)

        status, _, body = request(port, "GET", "/api/projects")
        assert status == 401
        assert json.loads(body)["auth_required"] is True

        bearer = {"Authorization": "Bearer studio-secret"}
        status, _, _ = request(port, "GET", "/api/projects", headers=bearer)
        assert status == 200

        status, session_headers, _ = request(
            port, "POST", "/api/auth/session", headers=bearer
        )
        assert status == 200
        cookie = session_headers["Set-Cookie"].split(";", 1)[0]

        status, _, _ = request(
            port,
            "POST",
            "/api/projects",
            headers={
                "Cookie": cookie,
                "Content-Type": "application/json",
                "Origin": "https://evil.example",
            },
            body=b'{"name":"blocked"}',
        )
        assert status == 403

        origin = f"http://127.0.0.1:{port}"
        status, _, body = request(
            port,
            "POST",
            "/api/projects",
            headers={
                "Cookie": cookie,
                "Content-Type": "application/json",
                "Origin": origin,
            },
            body=b'{"name":"authorized"}',
        )
        assert status == 201
        assert json.loads(body)["project"]["id"] == "authorized"


def test_every_sensitive_stack_entrypoint_rejects_missing_auth(monkeypatch, tmp_path):
    isolated_state(monkeypatch, tmp_path)
    monkeypatch.setenv("AIVE_STUDIO_TOKEN", "studio-secret")
    with running(stack.StackHandler) as port:
        for path in [
            "/api/system", "/api/storage", "/api/core", "/api/tools",
            "/api/projects", "/api/jobs", "/api/assets",
            "/api/projects/prototype/manifest", "/media/deadbeef/file.mp4",
        ]:
            status, _, _ = request(port, "GET", path)
            assert status == 401, path
        for method, path in [
            ("POST", "/api/core/bootstrap"),
            ("POST", "/api/tools/call"),
            ("POST", "/api/projects"),
            ("POST", "/api/assets"),
            ("POST", "/api/jobs"),
            ("POST", "/api/projects/prototype/prepare"),
            ("POST", "/api/projects/prototype/sync"),
            ("DELETE", "/api/assets/deadbeef"),
        ]:
            status, _, _ = request(port, method, path)
            assert status == 401, f"{method} {path}"


@pytest.mark.parametrize(
    "path",
    [
        "/../secret.txt",
        "/%2e%2e/secret.txt",
        "/%252e%252e/secret.txt",
        "/..%5csecret.txt",
        "/%2e%2e%2fsecret.txt",
    ],
)
def test_static_path_traversal_is_rejected(tmp_path, path):
    static = tmp_path / "static"
    static.mkdir()
    (tmp_path / "secret.txt").write_text("secret", encoding="utf-8")
    assert studio_security.static_target(static, path) is None


def test_static_symlink_escape_is_rejected(tmp_path):
    static = tmp_path / "static"
    static.mkdir()
    outside = tmp_path / "secret.txt"
    outside.write_text("secret", encoding="utf-8")
    link = static / "escape.txt"
    try:
        os.symlink(outside, link)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")
    assert studio_security.static_target(static, "/escape.txt") is None


def test_handler_rejects_encoded_static_escape(monkeypatch, tmp_path):
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("safe", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("secret", encoding="utf-8")
    monkeypatch.setattr(base, "STATIC", static)
    monkeypatch.delenv("AIVE_STUDIO_TOKEN", raising=False)
    with running(base.Handler) as port:
        status, _, _ = request(port, "GET", "/%252e%252e/secret.txt")
        assert status == 404


def test_media_asset_id_cannot_rebase_containment(monkeypatch, tmp_path):
    asset_root = tmp_path / "assets"
    asset_root.mkdir()
    monkeypatch.setattr(base, "ASSET_ROOT", asset_root)
    handler = object.__new__(base.Handler)
    assert handler.runtime_target("..", "secret.txt") is None
    assert handler.runtime_target("%2e%2e", "secret.txt") is None


def test_remote_bridge_and_studio_tokens_remain_separate(monkeypatch, tmp_path):
    isolated_state(monkeypatch, tmp_path)
    monkeypatch.setenv("AIVE_STUDIO_TOKEN", "studio-secret")
    monkeypatch.setenv("AIVE_REMOTE_ENABLED", "1")
    monkeypatch.setenv("AIVE_REMOTE_TOKEN", "remote-secret")
    monkeypatch.setattr(stack, "all_tool_schemas", lambda: [{"name": "test.echo"}])
    monkeypatch.setattr(stack, "_tool_call", lambda name, args: {"name": name, "args": args})
    body = json.dumps({"name": "test.echo", "arguments": {"value": 1}}).encode()

    with running(stack.StackHandler) as port:
        status, _, response = request(
            port,
            "POST",
            "/api/remote/call",
            headers={"Authorization": "Bearer remote-secret", "Content-Type": "application/json"},
            body=body,
        )
        assert status == 200
        assert json.loads(response)["result"]["args"] == {"value": 1}

        status, _, _ = request(
            port, "GET", "/api/tools", headers={"Authorization": "Bearer remote-secret"}
        )
        assert status == 401

        status, _, response = request(
            port,
            "POST",
            "/api/tools/call",
            headers={"Authorization": "Bearer studio-secret", "Content-Type": "application/json"},
            body=body,
        )
        assert status == 200
        assert json.loads(response)["result"]["name"] == "test.echo"
