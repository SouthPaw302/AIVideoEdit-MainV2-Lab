#!/usr/bin/env python3
"""Fail-closed validation for canonical-source recovery/recut workflows.

This companion guard extends Director Brain without changing accepted-baseline
semantics. Existing Operating Orders that do not use source-library/recut fields
remain valid; once those fields or artifacts are used, their evidence fails closed.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
from pathlib import Path
from typing import Any

from branch_policy import resolve_production_project

SCRIPT_ROOT = Path(__file__).resolve().parents[3]
if os.environ.get("AIVIDEOEDIT_REPO_ROOT"):
    ROOT = Path(os.environ["AIVIDEOEDIT_REPO_ROOT"]).resolve()
elif SCRIPT_ROOT.name == "os" and SCRIPT_ROOT.parent.name == ".aivideoedit":
    ROOT = SCRIPT_ROOT.parent.parent.resolve()
else:
    ROOT = SCRIPT_ROOT.resolve()
if os.environ.get("AIVIDEOEDIT_OS_ROOT"):
    OS_ROOT = Path(os.environ["AIVIDEOEDIT_OS_ROOT"]).resolve()
elif SCRIPT_ROOT.name == "os" and SCRIPT_ROOT.parent.name == ".aivideoedit":
    OS_ROOT = SCRIPT_ROOT.resolve()
else:
    OS_ROOT = ROOT

CONTRACT_PATH = OS_ROOT / "general/reusable/PRODUCTION_CONTRACT.json"
TOOLS = OS_ROOT / "general/reusable/tools"
FX = OS_ROOT / "general/reusable/fx_v2"
SOURCE_ROLES = {"hero_library", "shot_library", "visual_world", "reference_content"}
SOURCE_STATUSES = {"none", "accepted", "retired"}


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"missing {path}")
    except Exception as exc:
        raise ValueError(f"invalid JSON {path}: {exc}")


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def valid_sha(value: Any) -> bool:
    return nonempty(value) and bool(re.fullmatch(r"[0-9a-fA-F]{64}", value.strip()))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def discover_project(branch: str) -> Path | None:
    project, error = resolve_production_project(ROOT, branch)
    if error:
        return None
    return project


def import_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_source_library(order: dict, errors: list[str], project: Path | None = None) -> dict:
    source = order.get("accepted_source_library")
    if source is None:
        return {"status": "none"}
    if not isinstance(source, dict):
        errors.append("OPERATING_ORDER.accepted_source_library must be an object")
        return {"status": "none"}
    status = source.get("status")
    if status not in SOURCE_STATUSES:
        errors.append("accepted_source_library.status must be none, accepted, or retired")
        return source
    if status == "accepted":
        if source.get("role") not in SOURCE_ROLES:
            errors.append("accepted source library requires a supported role")
        if not nonempty(source.get("file_or_locator")):
            errors.append("accepted source library requires file_or_locator")
        if not valid_sha(source.get("sha256")):
            errors.append("accepted source library sha256 must contain 64 hexadecimal characters")
        if not nonempty(source.get("user_acceptance_statement")):
            errors.append("accepted source library requires user_acceptance_statement")
        if source.get("content_reuse_authorized") is not True:
            errors.append("accepted source library requires content_reuse_authorized=true")
        if source.get("timeline_locked") is not False:
            errors.append("accepted source library requires timeline_locked=false so the edit remains editable")
        locator = source.get("file_or_locator")
        if project is not None and nonempty(locator) and valid_sha(source.get("sha256")):
            candidate = Path(locator)
            if not candidate.is_absolute():
                candidate = project / candidate
            if candidate.is_file() and sha256_file(candidate).lower() != source["sha256"].strip().lower():
                errors.append("accepted source library local file hash does not match OPERATING_ORDER")
    return source


def validate_recut_scope(order: dict, source: dict, errors: list[str]) -> dict:
    scope = order.get("recut_scope")
    if scope is None:
        return {"active": False}
    if not isinstance(scope, dict):
        errors.append("OPERATING_ORDER.recut_scope must be an object")
        return {"active": False}
    if not isinstance(scope.get("active"), bool):
        errors.append("recut_scope.active must be boolean")
        return scope
    if scope.get("active") is True:
        if source.get("status") != "accepted":
            errors.append("active recut_scope requires accepted_source_library.status=accepted")
        defects = scope.get("named_defects")
        if not isinstance(defects, list) or not defects or not all(nonempty(x) for x in defects):
            errors.append("active recut_scope requires non-empty named_defects")
        for key in ("allowed_changes", "forbidden_changes"):
            value = scope.get(key)
            if not isinstance(value, list) or not value or not all(nonempty(x) for x in value):
                errors.append(f"active recut_scope requires non-empty {key}")
        if scope.get("source_replacement_authorized") is not False:
            errors.append("recut_scope.source_replacement_authorized must be false unless user explicitly chooses a different workflow")
    return scope


def validate_render_recipe(project: Path, errors: list[str]) -> None:
    path = project / "RENDER_RECIPE.json"
    if not path.is_file():
        return
    try:
        recipe = load_json(path)
    except ValueError as exc:
        errors.append(str(exc))
        return
    if recipe.get("schema") != "aivideoedit.render-recipe.v1":
        errors.append("RENDER_RECIPE.json has invalid schema")
    for key in ("recipe_identity", "proof_backend", "production_backend"):
        if not nonempty(recipe.get(key)):
            errors.append(f"RENDER_RECIPE.{key} is required")
    impl = recipe.get("render_implementation")
    if not isinstance(impl, dict) or not nonempty(impl.get("file_or_locator")) or not valid_sha(impl.get("sha256")):
        errors.append("RENDER_RECIPE.render_implementation requires locator and sha256")
    if recipe.get("proof_backend") == recipe.get("production_backend"):
        return
    mapping = recipe.get("backend_mapping")
    if not isinstance(mapping, dict) or not mapping:
        errors.append("backend substitution requires non-empty backend_mapping")
    proof = recipe.get("equivalence_proof")
    if not isinstance(proof, dict):
        errors.append("backend substitution requires equivalence_proof")
        return
    if proof.get("status") != "PASS":
        errors.append("backend substitution requires equivalence_proof.status=PASS")
    if proof.get("behavior_preserved") is not True:
        errors.append("equivalence proof requires behavior_preserved=true")
    if proof.get("effects_visible") is not True:
        errors.append("equivalence proof requires effects_visible=true")
    if proof.get("traceable") is not True:
        errors.append("equivalence proof requires traceable=true")
    representative = proof.get("representative_proof")
    if not isinstance(representative, dict) or not nonempty(representative.get("file_or_locator")) or not valid_sha(representative.get("sha256")):
        errors.append("equivalence proof requires representative proof locator and sha256")


def asset_entries(project: Path) -> list[dict]:
    path = project / "ASSET_MANIFEST.json"
    if not path.is_file():
        return []
    try:
        data = load_json(path)
    except ValueError:
        return []
    entries = data.get("assets") if isinstance(data.get("assets"), list) else data.get("entries")
    return [x for x in entries if isinstance(x, dict)] if isinstance(entries, list) else []


def validate_source_derived_provenance(project: Path, source: dict, scope: dict, errors: list[str]) -> None:
    accepted_sha = source.get("sha256") if source.get("status") == "accepted" else None
    for index, asset in enumerate(asset_entries(project), 1):
        provenance = asset.get("provenance") if isinstance(asset.get("provenance"), dict) else {}
        source_derived = asset.get("origin") == "source_derived" or provenance.get("kind") == "source_derived"
        if not source_derived:
            continue
        derived_sha = provenance.get("source_library_sha256")
        if not valid_sha(derived_sha):
            errors.append(f"ASSET_MANIFEST source-derived entry {index} requires provenance.source_library_sha256")
        elif accepted_sha and derived_sha.lower() != accepted_sha.lower():
            errors.append(f"ASSET_MANIFEST source-derived entry {index} does not derive from the accepted source library")
        if not nonempty(provenance.get("derivation")):
            errors.append(f"ASSET_MANIFEST source-derived entry {index} requires provenance.derivation")
        has_time = isinstance(provenance.get("source_time_seconds"), (int, float)) and not isinstance(provenance.get("source_time_seconds"), bool)
        source_range = provenance.get("source_range_seconds")
        has_range = isinstance(source_range, list) and len(source_range) == 2 and all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in source_range)
        if not (has_time or has_range):
            errors.append(f"ASSET_MANIFEST source-derived entry {index} requires source time or range evidence")
        if scope.get("active") is True and scope.get("source_replacement_authorized") is False and asset.get("replaces_source_library") is True:
            errors.append(f"ASSET_MANIFEST source-derived entry {index} cannot silently replace locked source canon")


def validate_hero_library(project: Path, plan: dict, scope: dict, source: dict, errors: list[str], warnings: list[str]) -> None:
    selected = plan.get("selected_capabilities", []) if isinstance(plan, dict) else []
    required = "canonical_hero_library" in selected or scope.get("active") is True
    path = project / "HERO_LIBRARY.json"
    if not required and not path.is_file():
        return
    if required and not path.is_file():
        errors.append("canonical hero-library workflow requires HERO_LIBRARY.json")
        return
    try:
        module = import_module(TOOLS / "hero_library_extract.py", "aivideoedit_hero_library_extract")
        manifest = load_json(path)
        errors.extend("HERO_LIBRARY: " + e for e in module.validate_library_manifest(manifest))
        warnings.extend("HERO_LIBRARY: " + w for w in module.library_warnings(manifest))
        accepted_sha = source.get("sha256") if source.get("status") == "accepted" else None
        hero_source = manifest.get("source", {}) if isinstance(manifest.get("source"), dict) else {}
        if accepted_sha and valid_sha(hero_source.get("sha256")) and hero_source.get("sha256").lower() != accepted_sha.lower():
            errors.append("HERO_LIBRARY source sha256 does not match accepted source library")
    except Exception as exc:
        errors.append(f"cannot validate HERO_LIBRARY.json: {exc}")


def validate_project_local_fx(project: Path, errors: list[str]) -> None:
    root = project / "project_fx"
    if not root.is_dir():
        return
    try:
        gate = import_module(FX / "project_local_fx_gate.py", "aivideoedit_project_local_fx_gate")
    except Exception as exc:
        errors.append(f"cannot load project-local FX gate: {exc}")
        return
    for manifest_path in sorted(root.glob("*.json")):
        if manifest_path.name.endswith(".lock.json"):
            continue
        try:
            manifest = load_json(manifest_path)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        errors.extend(f"{manifest_path.name}: {e}" for e in gate.validate_manifest(manifest, project))
        lock_path = manifest_path.with_suffix(".lock.json")
        errors.extend(f"{manifest_path.name}: {e}" for e in gate.validate_lock(manifest_path, lock_path, project))


def validate_refinement_qc(project: Path, source: dict, scope: dict, stage: str, states: list[str], errors: list[str]) -> None:
    if scope.get("active") is not True or source.get("status") != "accepted":
        return
    if stage not in states or states.index(stage) < states.index("FINAL_QC_PASSED"):
        return
    path = project / "REFINEMENT_QC.json"
    if not path.is_file():
        errors.append("recut FINAL_QC_PASSED requires REFINEMENT_QC.json with before/after evidence")
        return
    try:
        tool = import_module(TOOLS / "refinement_qc_compare.py", "aivideoedit_refinement_qc_compare")
        data = load_json(path)
        errors.extend("REFINEMENT_QC: " + e for e in tool.validate_comparison(data, source.get("sha256")))
    except Exception as exc:
        errors.append(f"cannot validate REFINEMENT_QC.json: {exc}")


def validate(branch: str) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if branch == "main":
        for rel in (
            "general/reusable/RECUT_REFINEMENT.md",
            "general/reusable/tools/hero_library_extract.py",
            "general/reusable/tools/refinement_qc_compare.py",
            "general/reusable/tools/recut_guard.py",
            "general/reusable/fx_v2/project_local_fx_gate.py",
        ):
            if not (OS_ROOT / rel).is_file():
                errors.append(f"missing recut system file: {rel}")
        return errors, warnings

    project, branch_error = resolve_production_project(ROOT, branch)
    if branch_error:
        return [branch_error], warnings
    if project is None:
        return [f"production project could not be resolved for {branch}"], warnings

    try:
        state = load_json(project / "PROJECT_STATE.json")
        order = load_json(project / "OPERATING_ORDER.json") if (project / "OPERATING_ORDER.json").is_file() else {}
        plan = load_json(project / "MEDIA_PLAN.json") if (project / "MEDIA_PLAN.json").is_file() else {}
        contract = load_json(CONTRACT_PATH)
    except ValueError as exc:
        return [str(exc)], warnings
    try:
        version = int(state.get("director_brain_version", 0) or 0)
    except (TypeError, ValueError):
        version = 0
    if version < 2 or not order:
        return errors, warnings
    source = validate_source_library(order, errors, project)
    scope = validate_recut_scope(order, source, errors)
    validate_render_recipe(project, errors)
    validate_source_derived_provenance(project, source, scope, errors)
    validate_hero_library(project, plan, scope, source, errors, warnings)
    validate_project_local_fx(project, errors)
    validate_refinement_qc(project, source, scope, state.get("stage", ""), contract.get("states", []), errors)
    return errors, warnings


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--branch", default=os.environ.get("GITHUB_REF_NAME") or os.environ.get("AIVIDEOEDIT_BRANCH") or "")
    args = ap.parse_args()
    if not args.branch:
        print("AIVideoEdit recut contract: FAIL\n- branch required")
        return 1
    errors, warnings = validate(args.branch)
    for warning in warnings:
        print("AIVideoEdit recut contract: WARN - " + warning)
    if errors:
        print("AIVideoEdit recut contract: FAIL")
        for error in errors:
            print("- " + error)
        return 1
    print("AIVideoEdit recut contract: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
