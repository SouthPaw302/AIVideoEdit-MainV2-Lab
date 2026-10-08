#!/usr/bin/env python3
"""Build and validate before/after refinement QC evidence.

Numbers are evidence, not directing authority. This tool deliberately does not declare
an artistic winner; it preserves comparable measurements and canon-integrity evidence.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SNAPSHOT_SCHEMA = "aivideoedit.refinement-qc-snapshot.v1"
COMPARISON_SCHEMA = "aivideoedit.refinement-qc.v1"
REQUIRED_OBJECTS = ("black_freeze", "framing_aspect", "audio_sync", "mode_aware_qc", "source_canon_integrity")


def _number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def validate_snapshot(snapshot: dict) -> list[str]:
    errors: list[str] = []
    if not isinstance(snapshot, dict) or snapshot.get("schema") != SNAPSHOT_SCHEMA:
        return [f"QC snapshot schema must be {SNAPSHOT_SCHEMA}"]
    if not _number(snapshot.get("runtime_seconds")) or snapshot.get("runtime_seconds") <= 0:
        errors.append("QC snapshot requires positive runtime_seconds")
    variety = snapshot.get("export_variety")
    if not isinstance(variety, dict):
        errors.append("QC snapshot requires export_variety")
    else:
        if variety.get("result") not in {"PASS", "REVIEW", "FAIL"}:
            errors.append("export_variety.result must be PASS, REVIEW, or FAIL")
        count = variety.get("similar_runs_count")
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            errors.append("export_variety.similar_runs_count must be a non-negative integer")
        if not isinstance(variety.get("metrics"), dict):
            errors.append("export_variety.metrics is required")
    for key in REQUIRED_OBJECTS:
        obj = snapshot.get(key)
        if not isinstance(obj, dict) or obj.get("result") not in {"PASS", "REVIEW", "FAIL"}:
            errors.append(f"QC snapshot requires {key}.result")
    warnings = snapshot.get("continuity_warnings")
    if not isinstance(warnings, list) or not all(isinstance(x, str) for x in warnings):
        errors.append("continuity_warnings must be a list of strings")
    return errors


def compare_snapshots(before: dict, after: dict) -> dict:
    be = validate_snapshot(before)
    ae = validate_snapshot(after)
    if be or ae:
        raise ValueError("invalid QC snapshot: " + "; ".join([*("before: " + e for e in be), *("after: " + e for e in ae)]))
    b_runs = before["export_variety"]["similar_runs_count"]
    a_runs = after["export_variety"]["similar_runs_count"]
    return {
        "schema": COMPARISON_SCHEMA,
        "before": before,
        "after": after,
        "comparison": {
            "similar_runs_delta": a_runs - b_runs,
            "runtime_seconds_delta": after["runtime_seconds"] - before["runtime_seconds"],
            "black_freeze_changed": after["black_freeze"]["result"] != before["black_freeze"]["result"],
            "framing_aspect_changed": after["framing_aspect"]["result"] != before["framing_aspect"]["result"],
            "audio_sync_changed": after["audio_sync"]["result"] != before["audio_sync"]["result"],
            "continuity_warning_delta": len(after["continuity_warnings"]) - len(before["continuity_warnings"]),
        },
        "metrics_are_evidence_not_direction": True,
        "artistic_decision_required": True,
    }


def validate_comparison(data: dict, expected_source_sha256: str | None = None) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict) or data.get("schema") != COMPARISON_SCHEMA:
        return [f"refinement QC schema must be {COMPARISON_SCHEMA}"]
    for key in ("before", "after"):
        snap = data.get(key)
        for e in validate_snapshot(snap if isinstance(snap, dict) else {}):
            errors.append(f"{key}: {e}")
    if not isinstance(data.get("comparison"), dict):
        errors.append("refinement QC requires comparison")
    if data.get("metrics_are_evidence_not_direction") is not True:
        errors.append("refinement QC must state metrics_are_evidence_not_direction=true")
    if data.get("artistic_decision_required") is not True:
        errors.append("refinement QC must state artistic_decision_required=true")
    if isinstance(data.get("after"), dict):
        integrity = data["after"].get("source_canon_integrity")
        if not isinstance(integrity, dict) or integrity.get("result") != "PASS":
            errors.append("post-edit source_canon_integrity must PASS")
        if expected_source_sha256 and isinstance(integrity, dict) and integrity.get("source_library_sha256") != expected_source_sha256:
            errors.append("post-edit source_canon_integrity hash does not match accepted source library")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--before", type=Path, required=True)
    ap.add_argument("--after", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    before = json.loads(args.before.read_text(encoding="utf-8"))
    after = json.loads(args.after.read_text(encoding="utf-8"))
    data = compare_snapshots(before, after)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"AIVideoEdit before/after refinement QC: PASS ({args.output})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
