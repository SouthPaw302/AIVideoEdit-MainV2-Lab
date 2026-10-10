#!/usr/bin/env python3
"""Project-neutral Director scan record verifier.

Evidence presence and consistency only. Never grants visual approval, human
acceptance, or release status; the full production-release workflow is separate.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SCHEMA = "aivideoedit.director-scan.v1"
CHECKS = (
    "inventory", "duplicates_and_provenance", "source_fidelity",
    "semantic_motion", "fx_actual_and_relevance", "music_and_audio",
    "full_timeline", "baseline_comparison", "intro_outro_brand",
    "delivery_playability", "handoff_and_caveats",
)
STATUSES = {"pass", "warn", "fail", "not_applicable"}
ARTISTIC = {"pending", "repair_required", "accepted_with_caveats", "accepted"}



def _matches_type(value, wanted: str) -> bool:
    """Follow JSON Schema's primitive types (bool is not a JSON integer)."""
    if wanted == "object":
        return isinstance(value, dict)
    if wanted == "array":
        return isinstance(value, list)
    if wanted == "string":
        return isinstance(value, str)
    if wanted == "null":
        return value is None
    if wanted == "boolean":
        return isinstance(value, bool)
    if wanted == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if wanted == "number":
        return isinstance(value, (float, int)) and not isinstance(value, bool)
    raise ValueError("Unsupported Director scan schema type: " + wanted)


def _validate_schema_node(value, rule: dict, location: str) -> list[str]:
    """Validate *all keywords used by* DIRECTOR_SCAN_RECORD.schema.json.

    Fail closed if the schema grows outside this stdlib validator's supported
    vocabulary. This prevents runtime/schema drift without extra dependencies.
    """
    errs = []
    supported = {
        "$schema", "title", "description", "type", "const", "enum", "required",
        "properties", "additionalProperties", "minLength", "pattern", "items",
        "minimum", "exclusiveMinimum",
    }
    unknown = set(rule) - supported
    if unknown:
        return [f"{location}: unsupported schema keywords: {sorted(unknown)}"]
    types = rule.get("type")
    if types is not None:
        allowed = types if isinstance(types, list) else [types]
        if not any(_matches_type(value, x) for x in allowed):
            return [f"{location}: wrong JSON type; expected {types!r}"]
    if "const" in rule and value != rule["const"]:
        errs.append(f"{location}: schema constant mismatch")
    if "enum" in rule and value not in rule["enum"]:
        errs.append(f"{location}: value not in schema enum")
    if isinstance(value, dict):
        for key in rule.get("required", []):
            if key not in value:
                errs.append(f"{location}: missing required property {key}")
        properties = rule.get("properties", {})
        if rule.get("additionalProperties") is False:
            for key in value:
                if key not in properties:
                    errs.append(f"{location}: unexpected property {key}")
        for key, item in value.items():
            if key in properties:
                errs.extend(_validate_schema_node(item, properties[key], f"{location}.{key}"))
    elif isinstance(value, list):
        item_rule = rule.get("items")
        if isinstance(item_rule, dict):
            for index, item in enumerate(value):
                errs.extend(_validate_schema_node(item, item_rule, f"{location}[{index}]"))
    elif isinstance(value, str):
        if "minLength" in rule and len(value) < rule["minLength"]:
            errs.append(f"{location}: shorter than schema minLength")
        if "pattern" in rule and re.search(rule["pattern"], value) is None:
            errs.append(f"{location}: fails schema pattern")
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in rule and value < rule["minimum"]:
            errs.append(f"{location}: below schema minimum")
        if "exclusiveMinimum" in rule and value <= rule["exclusiveMinimum"]:
            errs.append(f"{location}: below schema exclusiveMinimum")
    return errs


def _validate_declared_schema(record: dict) -> list[str]:
    path = Path(__file__).resolve().parents[1] / "DIRECTOR_SCAN_RECORD.schema.json"
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        return [f"Director scan schema unavailable or invalid: {exc}"]
    return _validate_schema_node(record, schema, "$")



def verify_record(record: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(record, dict):
        return ["director scan record must be an object"]
    if record.get("schema") != SCHEMA:
        errors.append("director scan schema mismatch")
    errors.extend(_validate_declared_schema(record))
    candidate = record.get("candidate")
    candidate = candidate if isinstance(candidate, dict) else {}
    if not str(candidate.get("locator") or "").strip():
        errors.append("candidate locator missing")
    if not re.fullmatch(r"[0-9a-f]{64}", str(candidate.get("sha256") or "")):
        errors.append("candidate SHA-256 missing or invalid")
    if not re.fullmatch(r"[0-9a-f]{40}", str(candidate.get("commit_sha") or "")):
        errors.append("source commit SHA missing or invalid")
    if not str(candidate.get("branch") or "").strip():
        errors.append("candidate source branch missing")
    scope = record.get("scope")
    scope = scope if isinstance(scope, dict) else {}
    if not str(scope.get("user_instruction") or "").strip():
        errors.append("current user instruction missing")
    if scope.get("mode") not in {
        "new_production", "proof", "recovery", "baseline_refinement", "finishing", "delivery"
    }:
        errors.append("scan scope mode invalid")
    for key in ("allowed_changes", "forbidden_changes"):
        if not isinstance(scope.get(key), list):
            errors.append(f"scan scope {key} must be a list")
    if scope.get("mode") in {"baseline_refinement", "finishing"}:
        if not re.fullmatch(r"[0-9a-f]{64}", str(scope.get("accepted_baseline_sha256") or "")):
            errors.append("locked baseline SHA-256 is mandatory for refinement/finishing")
    viewing = record.get("viewing")
    viewing = viewing if isinstance(viewing, dict) else {}
    method = viewing.get("method")
    if method not in {"none", "sampled", "segments", "full_normal_speed"}:
        errors.append("viewing method invalid")
    whole = viewing.get("entire_normal_speed")
    if not isinstance(whole, bool):
        errors.append("entire_normal_speed must be boolean, not an inferred approval")
    if whole is True and (method != "full_normal_speed" or not str(viewing.get("reviewer") or "").strip()):
        errors.append("whole-film viewing claim requires full_normal_speed method and named reviewer")
    if method == "full_normal_speed" and whole is not True:
        errors.append("full_normal_speed method contradicts entire_normal_speed=false")
    checks = record.get("checks")
    checks = checks if isinstance(checks, dict) else {}
    for name in CHECKS:
        item = checks.get(name)
        if not isinstance(item, dict):
            errors.append(f"Director scan check missing: {name}")
            continue
        status = item.get("status")
        if status not in STATUSES:
            errors.append(f"{name}: status invalid")
        evidence = item.get("evidence")
        if not isinstance(evidence, list):
            errors.append(f"{name}: evidence must be a list")
        elif status in {"pass", "warn", "fail"} and (
            not evidence or not all(isinstance(x, str) and x.strip() for x in evidence)
        ):
            errors.append(f"{name}: concrete evidence required for {status}")
        if status == "not_applicable" and not str(item.get("notes") or "").strip():
            errors.append(f"{name}: not_applicable requires a rationale")
    verdict = record.get("verdict")
    verdict = verdict if isinstance(verdict, dict) else {}
    if verdict.get("technical") not in {"pass", "fail", "pending"}:
        errors.append("technical verdict invalid")
    art = verdict.get("artistic")
    if art not in ARTISTIC:
        errors.append("artistic verdict invalid")
    if verdict.get("authenticated_release") not in {"not_checked", "pending", "pass"}:
        errors.append("authenticated release status invalid")
    caveats = verdict.get("caveats")
    if not isinstance(caveats, list):
        errors.append("verdict caveats must be a list")
        caveats = []
    if art == "accepted_with_caveats" and not caveats:
        errors.append("accepted_with_caveats requires named caveats")
    if art in {"accepted", "accepted_with_caveats"}:
        if method != "full_normal_speed" or whole is not True:
            errors.append("artistic acceptance requires documented full_normal_speed viewing")
        if any(isinstance(checks.get(c), dict) and checks[c].get("status") == "fail" for c in CHECKS):
            errors.append("accepted artistic verdict contradicts a failing scan check")
        if not str(viewing.get("reviewer") or "").strip():
            errors.append("artistic acceptance needs named review authority; this validator does not authenticate it")
    if verdict.get("authenticated_release") == "pass":
        errors.append("Director scan is not the authenticated release gate; use RELEASE_GATE.json")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("record", type=Path)
    a = ap.parse_args()
    try:
        record = json.loads(a.record.read_text(encoding="utf-8"))
        errs = verify_record(record)
    except (OSError, ValueError) as e:
        errs = [str(e)]
    print(json.dumps({
        "schema": "aivideoedit.director-scan-validation.v1",
        "result": "EVIDENCE_COMPLETE" if not errs else "FAIL",
        "human_visual_approval": "NOT_GRANTED_BY_THIS_TOOL",
        "errors": errs,
    }, indent=2))
    return 0 if not errs else 2


if __name__ == "__main__":
    raise SystemExit(main())
