#!/usr/bin/env python3
"""Provider-neutral routing for optional specialist-agent escalation."""
from __future__ import annotations

import os
import shutil
from typing import Any


def harness_enabled() -> bool:
    return os.environ.get("AIVE_HARNESS_ENABLED", "").strip().lower() in {"1","true","yes","on"}


def launcher() -> str | None:
    return shutil.which("dsh") or shutil.which("npx")


def route_jev(decision: dict[str, Any]) -> dict[str, Any]:
    value=str(decision.get("decision") or "").upper()
    if value != "ESCALATE":
        return {
            "schema":"aivideoedit.harness-route.v1",
            "route":"none",
            "reason":"Jev did not request escalation",
        }
    if harness_enabled():
        return {
            "schema":"aivideoedit.harness-route.v1",
            "route":"optional_harness_specialist",
            "reason":"Jev escalated and optional Harness is enabled",
            "launcher":launcher(),
        }
    return {
        "schema":"aivideoedit.harness-route.v1",
        "route":"authorized_sandbox_agent",
        "reason":"Jev escalated but optional Harness is disabled",
    }
