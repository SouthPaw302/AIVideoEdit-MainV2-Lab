#!/usr/bin/env python3
"""Evidence gate for music-directed, multi-pass living-scene production.

This is deliberately project-neutral.  It verifies that a selected creative
recipe was executed and proved in the project; it neither chooses imagery nor
replaces the canonical FX resolver or precompile lock.
"""
from __future__ import annotations

import json
import re
from pathlib import Path


HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")
PROFILE_ID = "music_directed_section_assembly"
PASS_NAMES = ("base", "reactive", "fill", "transition")


def _load(path: Path, errors: list[str], label: str) -> dict | None:
    if not path.is_file():
        errors.append(f"recipe execution requires {label}: {path.name}")
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"invalid {label} {path.name}: {exc}")
        return None
    if not isinstance(data, dict):
        errors.append(f"{label} {path.name} must contain an object")
        return None
    return data


def _nonempty(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _sha(value) -> bool:
    return isinstance(value, str) and bool(HEX64.fullmatch(value))


def _at(stage: str, states: list[str], target: str) -> bool:
    return states.index(stage) >= states.index(target)


def _active(state: dict, order: dict, stage: str, states: list[str]) -> bool:
    try:
        version = int(state.get("director_brain_version", 0) or 0)
    except (TypeError, ValueError):
        return False
    return (
        version >= 3
        and _at(stage, states, "APPROACH_ESTABLISHED")
        and order.get("direction_authority") == "music_led"
        and order.get("production_mode") in {"living_scene", "hybrid"}
    )


def _recipe_paths(recipe: dict, errors: list[str]) -> dict[str, Path]:
    profile = recipe.get("execution_profile")
    if not isinstance(profile, dict):
        errors.append("RENDER_RECIPE.execution_profile is required for music-directed section assembly")
        return {}
    if profile.get("id") != PROFILE_ID:
        errors.append(f"RENDER_RECIPE.execution_profile.id must be {PROFILE_ID}")
    paths = {}
    for key, name in (
        ("music_control_map", "MUSIC_CONTROL_MAP.json"),
        ("section_manifest", "SECTION_RENDER_MANIFEST.json"),
        ("application_proof", "FX_APPLICATION_PROOF.json"),
    ):
        value = profile.get(key)
        if not _nonempty(value):
            errors.append(f"RENDER_RECIPE.execution_profile.{key} must name a project artifact")
        else:
            candidate = Path(value)
            if candidate.is_absolute() or ".." in candidate.parts:
                errors.append(f"RENDER_RECIPE.execution_profile.{key} must stay inside the project")
            else:
                paths[key] = candidate
    variation = profile.get("variation_policy")
    if not isinstance(variation, dict) or not _nonempty(variation.get("intent")):
        errors.append("RENDER_RECIPE.execution_profile.variation_policy.intent is required")
    return paths


def _validate_control_map(data: dict, errors: list[str]) -> dict[str, dict]:
    if data.get("schema") != "aivideoedit.music-control-map.v1":
        errors.append("MUSIC_CONTROL_MAP.json has invalid schema")
    if not _sha(data.get("audio_sha256")):
        errors.append("MUSIC_CONTROL_MAP.audio_sha256 must be a SHA-256")
    sections = data.get("sections")
    if not isinstance(sections, list) or not sections:
        errors.append("MUSIC_CONTROL_MAP.sections must be a non-empty list")
        return {}
    result = {}
    previous_end = None
    for index, section in enumerate(sections, 1):
        if not isinstance(section, dict) or not _nonempty(section.get("id")):
            errors.append(f"MUSIC_CONTROL_MAP section {index} requires id")
            continue
        start, end = section.get("start_frame"), section.get("end_frame")
        if not isinstance(start, int) or not isinstance(end, int) or start < 0 or end <= start:
            errors.append(f"MUSIC_CONTROL_MAP section {section.get('id')} has invalid frame range")
        elif previous_end is not None and start != previous_end:
            errors.append("MUSIC_CONTROL_MAP sections must be contiguous")
        else:
            previous_end = end
        controls = section.get("controls")
        if not isinstance(controls, dict) or not any(k in controls for k in ("rms", "onset", "low", "mid", "high")):
            errors.append(f"MUSIC_CONTROL_MAP section {section.get('id')} requires declared controls")
        result[section.get("id")] = section
    return result


def _validate_section_manifest(data: dict, section_ids: set[str], stage: str, states: list[str], errors: list[str]) -> None:
    if data.get("schema") != "aivideoedit.section-render-manifest.v1":
        errors.append("SECTION_RENDER_MANIFEST.json has invalid schema")
    sections = data.get("sections")
    if not isinstance(sections, list) or not sections:
        errors.append("SECTION_RENDER_MANIFEST.sections must be a non-empty list")
        return
    found = set()
    for index, section in enumerate(sections, 1):
        if not isinstance(section, dict) or not _nonempty(section.get("id")):
            errors.append(f"SECTION_RENDER_MANIFEST section {index} requires id")
            continue
        sid = section["id"]
        found.add(sid)
        if sid not in section_ids:
            errors.append(f"SECTION_RENDER_MANIFEST section {sid} is absent from MUSIC_CONTROL_MAP")
        if not _nonempty(section.get("scene_profile")):
            errors.append(f"SECTION_RENDER_MANIFEST section {sid} requires a neutral scene_profile")
        passes = section.get("passes")
        if not isinstance(passes, dict):
            errors.append(f"SECTION_RENDER_MANIFEST section {sid} requires passes")
            continue
        for name in PASS_NAMES:
            item = passes.get(name)
            if not isinstance(item, dict) or item.get("status") not in {"planned", "rendered", "not_applicable"}:
                errors.append(f"SECTION_RENDER_MANIFEST section {sid} requires {name} pass status")
                continue
            if item.get("status") == "not_applicable" and not _nonempty(item.get("reason")):
                errors.append(f"SECTION_RENDER_MANIFEST section {sid} {name} not_applicable requires reason")
            if _at(stage, states, "SHOT_PROOFS_ACCEPTED") and item.get("status") != "not_applicable":
                proof = item.get("proof")
                if not isinstance(proof, dict) or not _nonempty(proof.get("file_or_locator")) or not _sha(proof.get("sha256")):
                    errors.append(f"SECTION_RENDER_MANIFEST section {sid} {name} requires hashed proof by SHOT_PROOFS_ACCEPTED")
    missing = section_ids - found
    if missing:
        errors.append("SECTION_RENDER_MANIFEST is missing music sections: " + ", ".join(sorted(missing)))


def _validate_application_proof(data: dict, section_ids: set[str], project: Path, stage: str, states: list[str], errors: list[str]) -> None:
    if not _at(stage, states, "FX_LOCKED"):
        return
    if data.get("schema") != "aivideoedit.fx-application-proof.v1":
        errors.append("FX_APPLICATION_PROOF.json has invalid schema")
    applications = data.get("applications")
    if not isinstance(applications, list) or not applications:
        errors.append("FX_APPLICATION_PROOF.applications must be a non-empty list by FX_LOCKED")
        return
    applied = set()
    for index, item in enumerate(applications, 1):
        if not isinstance(item, dict):
            errors.append(f"FX_APPLICATION_PROOF application {index} must be an object")
            continue
        sid, effect = item.get("section_id"), item.get("effect_id")
        if sid not in section_ids:
            errors.append(f"FX_APPLICATION_PROOF application {index} has unknown section_id")
        if not _nonempty(effect):
            errors.append(f"FX_APPLICATION_PROOF application {index} requires effect_id")
        else:
            applied.add(effect)
        output = item.get("output")
        if not isinstance(output, dict) or not _nonempty(output.get("file_or_locator")) or not _sha(output.get("sha256")):
            errors.append(f"FX_APPLICATION_PROOF application {index} requires hashed output")
        visible = item.get("visible_change")
        if not isinstance(visible, dict) or visible.get("status") != "PASS":
            errors.append(f"FX_APPLICATION_PROOF application {index} requires visible_change.status=PASS")
    lock_path = project / "fx.lock.json"
    if lock_path.is_file():
        lock = _load(lock_path, errors, "FX lock")
        required = {x.get("id") for x in (lock or {}).get("effects", []) if isinstance(x, dict) and _nonempty(x.get("id"))}
        uncovered = required - applied
        if uncovered:
            errors.append("FX_APPLICATION_PROOF does not cover locked effects: " + ", ".join(sorted(uncovered)))
    if _at(stage, states, "ASSEMBLED"):
        assembly = data.get("assembly")
        if not isinstance(assembly, dict) or assembly.get("status") != "PASS" or not _nonempty(assembly.get("file_or_locator")) or not _sha(assembly.get("sha256")):
            errors.append("FX_APPLICATION_PROOF requires PASS hashed assembly evidence by ASSEMBLED")
    if _at(stage, states, "FINAL_QC_PASSED"):
        final_qc = data.get("final_qc")
        if not isinstance(final_qc, dict) or final_qc.get("status") != "PASS" or final_qc.get("effect_coverage") != "PASS":
            errors.append("FX_APPLICATION_PROOF requires PASS final_qc/effect_coverage by FINAL_QC_PASSED")


def validate(project: Path, state: dict, order: dict, stage: str, states: list[str], errors: list[str]) -> None:
    if not _active(state, order, stage, states):
        return
    recipe = _load(project / "RENDER_RECIPE.json", errors, "RENDER_RECIPE")
    if recipe is None:
        return
    paths = _recipe_paths(recipe, errors)
    music = _load(project / paths["music_control_map"], errors, "MUSIC_CONTROL_MAP") if "music_control_map" in paths else None
    if music is None:
        return
    sections = _validate_control_map(music, errors)
    if not _at(stage, states, "STORYBOARD_LOCKED"):
        return
    manifest = _load(project / paths["section_manifest"], errors, "SECTION_RENDER_MANIFEST") if "section_manifest" in paths else None
    if manifest is None:
        return
    _validate_section_manifest(manifest, set(sections), stage, states, errors)
    proof = _load(project / paths["application_proof"], errors, "FX_APPLICATION_PROOF") if "application_proof" in paths else None
    if proof is not None:
        _validate_application_proof(proof, set(sections), project, stage, states, errors)
