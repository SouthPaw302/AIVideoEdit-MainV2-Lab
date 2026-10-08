#!/usr/bin/env python3
"""Fail-closed gate for branch-local experimental FX.

This gate does not register or promote effects into canonical fx_v2. It only proves
that a project-local adapter is real, traceable, locked, and visibly pixel-altering.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA = "aivideoedit.project-local-fx.v1"
LOCK_SCHEMA = "aivideoedit.project-local-fx-lock.v1"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _valid_sha(v: Any) -> bool:
    return isinstance(v, str) and len(v) == 64 and all(c in "0123456789abcdefABCDEF" for c in v)


def _resolve(project_root: Path, value: str) -> Path:
    p = Path(value)
    p = p.resolve() if p.is_absolute() else (project_root / p).resolve()
    root = project_root.resolve()
    if p != root and root not in p.parents:
        raise ValueError(f"path escapes project root: {value}")
    return p


def _verify_file_record(project_root: Path, rec: Any, label: str, errors: list[str]) -> None:
    if not isinstance(rec, dict):
        errors.append(f"{label} must be an object")
        return
    locator = rec.get("path") or rec.get("file_or_locator")
    if not isinstance(locator, str) or not locator.strip():
        errors.append(f"{label} requires path/file_or_locator")
        return
    if not _valid_sha(rec.get("sha256")):
        errors.append(f"{label}.sha256 must be 64 hexadecimal characters")
    try:
        p = _resolve(project_root, locator)
    except ValueError as e:
        errors.append(str(e))
        return
    if p.is_file() and _valid_sha(rec.get("sha256")) and sha256_file(p).lower() != rec["sha256"].lower():
        errors.append(f"{label} local file hash mismatch")


def validate_manifest(manifest: dict, project_root: Path) -> list[str]:
    errors: list[str] = []
    if not isinstance(manifest, dict) or manifest.get("schema") != SCHEMA:
        return [f"project-local FX schema must be {SCHEMA}"]
    if manifest.get("scope") != "project_local":
        errors.append("project-local FX scope must be project_local")
    for key in ("effect_id", "technology_label"):
        if not isinstance(manifest.get(key), str) or not manifest.get(key, "").strip():
            errors.append(f"project-local FX requires {key}")
    if manifest.get("truthful_naming") is not True:
        errors.append("project-local FX requires truthful_naming=true")
    if manifest.get("placeholder") is not False:
        errors.append("project-local FX must explicitly set placeholder=false")
    if manifest.get("promoted_to_canonical") is True:
        errors.append("project-local FX gate cannot promote an effect into canonical fx_v2")
    _verify_file_record(project_root, manifest.get("implementation"), "implementation", errors)
    inputs = manifest.get("render_inputs")
    if not isinstance(inputs, list) or not inputs:
        errors.append("project-local FX requires non-empty render_inputs")
    else:
        for i, rec in enumerate(inputs, 1):
            _verify_file_record(project_root, rec, f"render_inputs[{i}]", errors)
    if manifest.get("deterministic_applicable") is True:
        if not isinstance(manifest.get("parameters"), dict) or not manifest.get("parameters"):
            errors.append("deterministic project-local FX requires recorded parameters")
        if manifest.get("deterministic_parameters") is not True:
            errors.append("deterministic project-local FX requires deterministic_parameters=true")
    proof = manifest.get("proof")
    _verify_file_record(project_root, proof, "proof", errors)
    if not isinstance(proof, dict) or proof.get("visible_pixel_change") is not True:
        errors.append("project-local FX proof requires visible_pixel_change=true")
    qc = manifest.get("qc")
    if not isinstance(qc, dict) or qc.get("status") != "PASS":
        errors.append("project-local FX requires qc.status=PASS")
    elif not isinstance(qc.get("reviewer"), str) or not qc.get("reviewer", "").strip():
        errors.append("project-local FX QC requires reviewer")
    return errors


def make_lock(manifest_path: Path, project_root: Path) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors = validate_manifest(manifest, project_root)
    if errors:
        raise ValueError("; ".join(errors))
    implementation = manifest["implementation"]
    proof = manifest["proof"]
    return {
        "schema": LOCK_SCHEMA,
        "locked": True,
        "manifest": manifest_path.relative_to(project_root).as_posix(),
        "manifest_sha256": sha256_file(manifest_path),
        "implementation_sha256": implementation["sha256"],
        "proof_sha256": proof["sha256"],
        "render_input_sha256": [r["sha256"] for r in manifest["render_inputs"]],
        "canonical_promotion": False,
    }


def validate_lock(manifest_path: Path, lock_path: Path, project_root: Path) -> list[str]:
    errors: list[str] = []
    if not lock_path.is_file():
        return [f"missing project-local FX precompile lock: {lock_path.name}"]
    try:
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
    except Exception as e:
        return [f"invalid project-local FX lock: {e}"]
    if lock.get("schema") != LOCK_SCHEMA or lock.get("locked") is not True:
        errors.append("project-local FX lock must be locked and use the current schema")
    if lock.get("canonical_promotion") is not False:
        errors.append("project-local FX lock must state canonical_promotion=false")
    current = sha256_file(manifest_path)
    if lock.get("manifest_sha256") != current:
        errors.append("project-local FX lock is stale: manifest hash changed")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("verify")
    v.add_argument("manifest", type=Path)
    v.add_argument("--project-root", type=Path, required=True)
    l = sub.add_parser("lock")
    l.add_argument("manifest", type=Path)
    l.add_argument("--project-root", type=Path, required=True)
    l.add_argument("--output", type=Path)
    args = ap.parse_args()
    root = args.project_root.resolve()
    manifest_path = args.manifest.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors = validate_manifest(manifest, root)
    if errors:
        print("AIVideoEdit project-local FX gate: FAIL")
        for e in errors:
            print("- " + e)
        return 1
    if args.cmd == "lock":
        lock = make_lock(manifest_path, root)
        out = args.output or manifest_path.with_suffix(".lock.json")
        out.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
        print(f"AIVideoEdit project-local FX lock: PASS ({out})")
        return 0
    lock_path = manifest_path.with_suffix(".lock.json")
    lock_errors = validate_lock(manifest_path, lock_path, root)
    if lock_errors:
        print("AIVideoEdit project-local FX gate: FAIL")
        for e in lock_errors:
            print("- " + e)
        return 1
    print("AIVideoEdit project-local FX gate: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
