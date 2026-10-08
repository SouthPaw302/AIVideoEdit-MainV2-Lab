#!/usr/bin/env python3
"""Deterministic bounded decision hook for AIVideoEdit."""
from __future__ import annotations

from typing import Any

ALLOWED = {"PASS", "FAIL", "RETRY", "CONTINUE", "ESCALATE"}


def _result(decision: str, reason: str) -> dict[str, Any]:
    if decision not in ALLOWED:
        raise ValueError("invalid Jev decision")
    return {
        "schema": "aivideoedit.jev-decision.v1",
        "decision": decision,
        "reason": reason,
    }


def decide(evidence: dict[str, Any]) -> dict[str, Any]:
    gate = str(evidence.get("gate") or "").upper()
    if gate not in {"PASS", "DENY"}:
        return _result("ESCALATE", "missing or ambiguous gatekeeper evidence")
    if gate == "DENY":
        return _result("FAIL", "runtime gatekeeper denied the action")

    checks = evidence.get("checks") if isinstance(evidence.get("checks"), dict) else {}
    failed = sorted(str(k) for k, v in checks.items() if v is False)
    unknown = sorted(str(k) for k, v in checks.items() if v is None)
    if failed:
        return _result("FAIL", "required checks failed: " + ", ".join(failed))

    observations = evidence.get("model_observations")
    observations = observations if isinstance(observations, list) else []
    for index, obs in enumerate(observations, start=1):
        if not isinstance(obs, dict):
            return _result("ESCALATE", f"model observation {index} is malformed")
        if obs.get("authority") != "evidence_only":
            return _result("ESCALATE", f"model observation {index} has invalid authority")
        if obs.get("ambiguous") is True:
            return _result("ESCALATE", f"model observation {index} is ambiguous")
        confidence = obs.get("confidence")
        if confidence is not None:
            try:
                confidence = float(confidence)
            except (TypeError, ValueError):
                return _result("ESCALATE", f"model observation {index} confidence is invalid")
            if confidence < 0.5:
                return _result("ESCALATE", f"model observation {index} confidence is below bounded threshold")

    if evidence.get("retryable_error") is True:
        return _result("RETRY", "bounded retryable error reported")
    if evidence.get("ambiguous") is True or unknown:
        return _result("ESCALATE", "ambiguous evidence requires authorized-agent review")
    if evidence.get("next_action_permitted") is True:
        return _result("CONTINUE", "all declared evidence passes and next action is permitted")
    return _result("PASS", "all declared checks pass")
