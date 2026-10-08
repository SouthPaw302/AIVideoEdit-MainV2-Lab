#!/usr/bin/env python3
"""Minimal stdio MCP bridge exposing AIVideoEdit Studio tools to agent harnesses.

No DeepSeek SDK dependency is required here. DeepSeek Harness owns the MCP
client; AIVideoEdit remains the production authority and executes the same
Tool API used by Studio.
"""
from __future__ import annotations

import json
import sys
import traceback

import server as base
import stack
import tool_api
import operating_tools
import harness_tools

SERVER_NAME = "aivideoedit"
SERVER_VERSION = "0.1.0-prototype"
SUPPORTED_LEGACY_PROTOCOLS = ("2025-11-25", "2025-06-18", "2025-03-26")
DEFAULT_PROTOCOL = SUPPORTED_LEGACY_PROTOCOLS[0]


def _schemas():
    return tool_api.schemas() + operating_tools.schemas() + harness_tools.schemas()


def _external_name(name: str) -> str:
    return name.replace(".", "__")


SCHEMA_BY_EXTERNAL = {_external_name(s["name"]): s for s in _schemas()}
INTERNAL_BY_EXTERNAL = {_external_name(s["name"]): s["name"] for s in _schemas()}


def _initialize_runtime():
    base.load_state()
    base.dispatch_job = stack.dispatch_job
    stack.start_workers()


def _call_internal(name: str, arguments: dict):
    if name.startswith("harness."):
        return harness_tools.call(name, arguments)
    if name.startswith("operating."):
        return operating_tools.call(name, arguments)
    return tool_api.call_tool(
        name,
        arguments,
        dispatch_job=stack.dispatch_job,
        prepare_project=stack.prepare_project,
    )


def _tool_list():
    tools = []
    for external, schema in SCHEMA_BY_EXTERNAL.items():
        tools.append(
            {
                "name": external,
                "description": schema.get("description", ""),
                "inputSchema": schema.get("input_schema") or {"type": "object", "properties": {}},
            }
        )
    return tools


def _write(payload: dict):
    sys.stdout.write(json.dumps(payload, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def _result(request_id, result):
    _write({"jsonrpc": "2.0", "id": request_id, "result": result})


def _error(request_id, code: int, message: str, data=None):
    payload = {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}
    if data is not None:
        payload["error"]["data"] = data
    _write(payload)


def _handle(message: dict):
    method = message.get("method")
    request_id = message.get("id")
    params = message.get("params") if isinstance(message.get("params"), dict) else {}

    if method == "server/discover":
        return _error(
            request_id,
            -32601,
            "Method not found: server/discover (legacy stdio bridge; client may fall back to initialize)",
        )

    if method == "initialize":
        requested = params.get("protocolVersion")
        protocol = requested if requested in SUPPORTED_LEGACY_PROTOCOLS else DEFAULT_PROTOCOL
        return _result(
            request_id,
            {
                "protocolVersion": protocol,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                "instructions": (
                    "AIVideoEdit is the production authority. Call harness__context for the active "
                    "project before stage-changing work. Use the exposed production tools instead of "
                    "editing canonical state by hand. Canonical guards may reject invalid transitions. "
                    "This prototype must not mutate repository main."
                ),
            },
        )

    if method in {"notifications/initialized", "notifications/cancelled"}:
        return None

    if method == "ping":
        return _result(request_id, {})

    if method == "tools/list":
        return _result(request_id, {"tools": _tool_list()})

    if method == "tools/call":
        external = str(params.get("name") or "")
        internal = INTERNAL_BY_EXTERNAL.get(external)
        if not internal:
            return _result(
                request_id,
                {
                    "content": [{"type": "text", "text": f"Unknown AIVideoEdit tool: {external}"}],
                    "isError": True,
                },
            )
        arguments = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
        try:
            result = _call_internal(internal, arguments)
            text = json.dumps(result, indent=2, sort_keys=True, default=str)
            return _result(
                request_id,
                {
                    "content": [{"type": "text", "text": text}],
                    "isError": False,
                },
            )
        except Exception as exc:
            return _result(
                request_id,
                {
                    "content": [{"type": "text", "text": f"{type(exc).__name__}: {exc}"}],
                    "isError": True,
                },
            )

    if request_id is not None:
        return _error(request_id, -32601, f"Method not found: {method}")
    return None


def main() -> int:
    try:
        _initialize_runtime()
    except Exception as exc:
        print(f"AIVideoEdit MCP startup failed: {exc}", file=sys.stderr, flush=True)
        return 2

    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            message = json.loads(raw)
            if not isinstance(message, dict):
                raise ValueError("JSON-RPC message must be an object")
            _handle(message)
        except json.JSONDecodeError as exc:
            _error(None, -32700, "Parse error", str(exc))
        except Exception as exc:
            request_id = message.get("id") if isinstance(locals().get("message"), dict) else None
            _error(request_id, -32603, "Internal error", str(exc))
            traceback.print_exc(file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
