#!/usr/bin/env python3
"""Smoke-test the dependency-free AIVideoEdit MCP stdio bridge."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> int:
    requests = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "aivideoedit-selftest", "version": "1"},
            },
        },
        {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "harness__specialist_fixture",
                "arguments": {"task": "smoke specialist", "evidence": {"fixture": True}},
            },
        },
    ]
    proc = subprocess.run(
        [sys.executable, str(HERE / "aivideo_mcp.py")],
        input="\n".join(json.dumps(x) for x in requests) + "\n",
        text=True,
        capture_output=True,
        cwd=str(HERE),
        timeout=20,
        check=False,
        env={**os.environ, "AIVE_HARNESS_ENABLED": "1"},
    )
    if proc.returncode != 0:
        print(proc.stderr or proc.stdout)
        return proc.returncode or 1

    responses = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
    by_id = {x.get("id"): x for x in responses if isinstance(x, dict) and x.get("id") is not None}
    init = by_id.get(1, {}).get("result") or {}
    listed = by_id.get(2, {}).get("result") or {}
    names = {x.get("name") for x in listed.get("tools", []) if isinstance(x, dict)}

    failures = []
    if init.get("serverInfo", {}).get("name") != "aivideoedit":
        failures.append("initialize did not identify the AIVideoEdit MCP server")
    if init.get("protocolVersion") != "2025-11-25":
        failures.append("legacy MCP protocol negotiation did not settle on 2025-11-25")
    for required in {"harness__status", "harness__context", "harness__specialist_fixture", "production__status", "production__guard"}:
        if required not in names:
            failures.append(f"missing MCP tool: {required}")

    fixture = by_id.get(3, {}).get("result") or {}
    fixture_content = fixture.get("content") if isinstance(fixture, dict) else None
    if not fixture_content:
        failures.append("specialist fixture did not return MCP content")

    result = {
        "schema": "aivideoedit.harness-selftest.v1",
        "result": "PASS" if not failures else "FAIL",
        "tool_count": len(names),
        "failures": failures,
        "stderr": proc.stderr[-2000:],
    }
    print(json.dumps(result, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
