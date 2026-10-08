#!/usr/bin/env python3
"""Runtime mutation gatekeeper for AIVideoEdit MainV2-clean.

This layer does not replace the canonical production guard. It validates that
the active mutation still matches the boot capsule/session attestation before
the existing Tool API is allowed to change production state.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Iterable


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def _sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _stable_json_sha256(value: dict) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _git_branch(engine: Path) -> str:
    p = subprocess.run(
        ["git", "-C", str(engine), "branch", "--show-current"],
        capture_output=True, text=True, check=False,
    )
    return p.stdout.strip() if p.returncode == 0 else ""


def _norm(value: str) -> str:
    return " ".join(
        value.strip().lower()
        .replace("_", " ")
        .replace("-", " ")
        .replace(".", " ")
        .split()
    )


def _scope_allows(change_tags: Iterable[str], allowed: list[str], forbidden: list[str]) -> tuple[bool, str]:
    tags = [_norm(x) for x in change_tags if str(x).strip()]
    allow = [_norm(x) for x in allowed if str(x).strip()]
    deny = [_norm(x) for x in forbidden if str(x).strip()]

    for tag in tags:
        if any(d and (d in tag or tag in d) for d in deny):
            return False, f"requested change is forbidden by active scope: {tag}"

    if allow and tags:
        for tag in tags:
            if not any(a and (a in tag or tag in a) for a in allow):
                return False, f"requested change is outside active allowed_changes: {tag}"
    return True, "scope permits requested change"


def evaluate(
    *,
    engine: Path,
    project_dir: Path,
    branch: str,
    operation: str,
    change_tags: Iterable[str] = (),
    expected_stages: Iterable[str] = (),
) -> dict:
    engine = engine.resolve()
    project_dir = project_dir.resolve()
    session_dir = engine / ".aivideoedit"
    capsule_path = session_dir / "boot_capsule.json"
    attestation_path = session_dir / "session_attestation.json"

    capsule = _read_json(capsule_path)
    attestation = _read_json(attestation_path)
    errors: list[str] = []

    if capsule.get("schema") != "aivideoedit.boot-capsule.v1":
        errors.append("valid boot capsule is required")
    if attestation.get("schema") != "aivideoedit.session-attestation.v1":
        errors.append("valid session attestation is required")
    if capsule and attestation:
        actual_capsule_hash = _stable_json_sha256(capsule)
        if attestation.get("capsule_sha256") != actual_capsule_hash:
            errors.append("session attestation does not match boot capsule")
        if attestation.get("session_id") != capsule.get("session_id"):
            errors.append("session attestation session_id mismatch")

    active = capsule.get("active") if isinstance(capsule.get("active"), dict) else {}
    if active.get("branch") != branch:
        errors.append(f"boot capsule branch mismatch: {active.get('branch')} != {branch}")

    current_branch = _git_branch(engine)
    if current_branch != branch:
        errors.append(f"working branch mismatch: {current_branch or 'unknown'} != {branch}")

    try:
        rel_project = project_dir.relative_to(engine).as_posix()
    except ValueError:
        rel_project = ""
    if active.get("project_dir") != rel_project:
        errors.append(
            f"boot capsule project mismatch: {active.get('project_dir')} != {rel_project or 'outside-engine'}"
        )

    state_path = project_dir / "PROJECT_STATE.json"
    order_path = project_dir / "OPERATING_ORDER.json"
    current_state = _read_json(state_path)
    current_order = _read_json(order_path)

    if active.get("project_state_sha256") != _sha256_file(state_path):
        errors.append("PROJECT_STATE.json changed after boot attestation")
    if active.get("operating_order_sha256") != _sha256_file(order_path):
        errors.append("OPERATING_ORDER.json changed after boot attestation")

    stage = current_state.get("stage")
    expected = [str(x) for x in expected_stages if str(x).strip()]
    if expected and stage not in expected:
        errors.append(
            f"wrong production stage for {operation}: {stage!r}; expected one of {expected}"
        )
    if active.get("stage") != stage:
        errors.append(f"boot capsule stage mismatch: {active.get('stage')!r} != {stage!r}")

    capsule_next = active.get("exact_next_action")
    live_next = (
        str(current_order.get("exact_next_action") or "").strip()
        or str(current_state.get("exact_next_action") or "").strip()
        or None
    )
    if capsule_next != live_next:
        errors.append("exact_next_action changed after boot attestation")

    canon = current_order.get("canon_lock")
    canon = canon if isinstance(canon, dict) else {}
    tags = [str(x) for x in change_tags]
    if canon.get("locked") is True and any(_norm(x) in {"canon replace", "source replace"} for x in tags):
        errors.append("protected canon replacement denied while canon_lock.locked=true")

    for scope_name in ("refinement_scope", "recut_scope"):
        scope = current_order.get(scope_name)
        if not isinstance(scope, dict) or scope.get("active") is not True:
            continue
        allowed = scope.get("allowed_changes")
        forbidden = scope.get("forbidden_changes")
        ok, reason = _scope_allows(
            tags,
            allowed if isinstance(allowed, list) else [],
            forbidden if isinstance(forbidden, list) else [],
        )
        if not ok:
            errors.append(f"{scope_name}: {reason}")

    return {
        "schema": "aivideoedit.runtime-gatekeeper.v1",
        "operation": operation,
        "branch": branch,
        "stage": stage,
        "change_tags": tags,
        "decision": "PASS" if not errors else "DENY",
        "errors": errors,
    }


def require(**kwargs) -> dict:
    result = evaluate(**kwargs)
    if result["decision"] != "PASS":
        raise RuntimeError("RUNTIME GATEKEEPER DENY: " + "; ".join(result["errors"]))
    return result
