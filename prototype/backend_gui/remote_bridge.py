#!/usr/bin/env python3
"""Thin authenticated remote-agent adapter for the existing AIVideoEdit Tool API.

No new production authority, execution engine, or deployment stack is introduced.
"""
from __future__ import annotations

import hmac
import os
import re
import uuid
from typing import Mapping

_REQ_RE=re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


def enabled() -> bool:
    return os.environ.get("AIVE_REMOTE_ENABLED","").strip().lower() in {"1","true","yes","on"}


def configured_token() -> str | None:
    value=os.environ.get("AIVE_REMOTE_TOKEN","").strip()
    return value or None


def request_id(headers: Mapping[str,str]) -> str:
    candidate=str(headers.get("X-Request-ID") or "").strip()
    if candidate and _REQ_RE.fullmatch(candidate):
        return candidate
    return str(uuid.uuid4())


def authorize(headers: Mapping[str,str]) -> tuple[bool,str]:
    if not enabled():
        return False,"remote bridge is disabled"
    token=configured_token()
    if not token:
        return False,"remote bridge token is not configured"
    auth=str(headers.get("Authorization") or "")
    if not auth.startswith("Bearer "):
        return False,"bearer token required"
    supplied=auth[len("Bearer "):]
    if not hmac.compare_digest(supplied,token):
        return False,"invalid bearer token"
    return True,"authorized"


def capability_document(tool_names:list[str], *, harness_enabled:bool) -> dict:
    return {
        "schema":"aivideoedit.remote-capabilities.v1",
        "remote_bridge":"existing_stack_adapter",
        "arbitrary_shell":False,
        "production_authority":"existing_aivideoedit_tool_api",
        "mutation_enforcement":[
            "boot_capsule",
            "session_attestation",
            "runtime_gatekeeper",
            "jev",
            "canonical_production_guards",
        ],
        "harness_optional":True,
        "harness_enabled":bool(harness_enabled),
        "tools":sorted(set(tool_names)),
    }
