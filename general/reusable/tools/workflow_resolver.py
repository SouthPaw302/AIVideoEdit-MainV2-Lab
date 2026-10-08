#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DEFAULT_REGISTRY = ROOT / "general/reusable/STANDARD_WORKFLOW_REGISTRY.json"
MEDIA_MATRIX = ROOT / "general/reusable/MEDIA_CAPABILITY_MATRIX.json"
VALID_MODES = {"living_scene", "cinematic", "hybrid"}
OPTIONAL_RUNTIME_IDS = {"browser_scene_runtime"}
FORBIDDEN_KEYS = {"project", "origin_project", "source_project", "production_name"}


def load_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def walk_forbidden(obj: Any, path="root"):
    errors = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in FORBIDDEN_KEYS:
                errors.append(f"{path}.{k} is forbidden in the standard workflow registry")
            errors.extend(walk_forbidden(v, f"{path}.{k}"))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            errors.extend(walk_forbidden(v, f"{path}[{i}]"))
    return errors


def validate_registry(data: dict, media_matrix: dict | None = None):
    errors = []
    if data.get("schema") != "aivideoedit.standard-workflows.v1":
        errors.append("invalid standard workflow registry schema")
    workflows = data.get("workflows")
    if not isinstance(workflows, list) or not workflows:
        return errors + ["workflows must be a non-empty list"]
    errors.extend(walk_forbidden(data))
    ids = []
    names = []
    valid_caps = set()
    if media_matrix:
        valid_caps = {x.get("id") for x in media_matrix.get("capabilities", []) if isinstance(x, dict)}
    for i, wf in enumerate(workflows, 1):
        if not isinstance(wf, dict):
            errors.append(f"workflow {i} must be an object")
            continue
        wid = wf.get("id")
        name = wf.get("name")
        if not isinstance(wid, str) or not wid.startswith("WF-"):
            errors.append(f"workflow {i} requires neutral WF-* id")
        else:
            ids.append(wid)
        if not isinstance(name, str) or not name.strip():
            errors.append(f"workflow {i} requires name")
        else:
            names.append(name)
        if wf.get("status") != "approved":
            errors.append(f"{wid or i} must have status=approved")
        verification = wf.get("verification")
        if not isinstance(verification, dict) or verification.get("status") != "PASS":
            errors.append(f"{wid or i} requires verification.status=PASS")
        else:
            checks = verification.get("checks")
            if not isinstance(checks, list) or not checks or not all(isinstance(x, str) and x for x in checks):
                errors.append(f"{wid or i} requires non-empty verification checks")
        selection = wf.get("select_if", {})
        if not isinstance(selection, dict):
            errors.append(f"{wid or i} select_if must be an object")
            continue
        modes = selection.get("modes_any", [])
        if modes and (not isinstance(modes, list) or any(x not in VALID_MODES for x in modes)):
            errors.append(f"{wid or i} has invalid modes_any")
        for key in ("capabilities_any", "capabilities_all"):
            vals = selection.get(key, [])
            if vals and not isinstance(vals, list):
                errors.append(f"{wid or i} {key} must be a list")
            elif valid_caps:
                unknown = [x for x in vals if x not in valid_caps]
                if unknown:
                    errors.append(f"{wid or i} {key} contains unknown capabilities: {', '.join(unknown)}")
    if len(ids) != len(set(ids)):
        errors.append("workflow ids must be unique")
    if len(names) != len(set(names)):
        errors.append("workflow names must be unique")
    return errors


def matches(select_if: dict, mode: str, capabilities: set[str]):
    if select_if.get("default") is True:
        return True
    modes = set(select_if.get("modes_any", []))
    if modes and mode not in modes:
        return False
    all_caps = set(select_if.get("capabilities_all", []))
    if all_caps and not all_caps.issubset(capabilities):
        return False
    any_caps = set(select_if.get("capabilities_any", []))
    if any_caps and not any_caps.intersection(capabilities):
        return False
    if select_if.get("manual_only") is True:
        return False
    return bool(modes or all_caps or any_caps)


def resolve(data: dict, mode: str, capabilities: list[str], include: list[str] | None = None, exclude: list[str] | None = None):
    caps = set(capabilities)
    include = set(include or [])
    exclude = set(exclude or [])
    selected = []
    by_id = {wf["id"]: wf for wf in data.get("workflows", []) if isinstance(wf, dict) and wf.get("id")}
    by_name = {wf["name"]: wf for wf in data.get("workflows", []) if isinstance(wf, dict) and wf.get("name")}
    for wf in data.get("workflows", []):
        if matches(wf.get("select_if", {}), mode, caps):
            selected.append(wf)
    for token in include:
        wf = by_id.get(token) or by_name.get(token)
        if wf and wf not in selected:
            selected.append(wf)
    selected = [wf for wf in selected if wf.get("id") not in exclude and wf.get("name") not in exclude]
    return selected


def resolve_project(project: Path, registry: dict):
    plan = load_json(project / "MEDIA_PLAN.json")
    order = load_json(project / "OPERATING_ORDER.json") if (project / "OPERATING_ORDER.json").is_file() else {}
    mode = order.get("production_mode") or plan.get("production_mode")
    if mode not in VALID_MODES:
        raise ValueError(f"project production mode is missing/invalid: {mode!r}")
    caps = plan.get("selected_capabilities", [])
    if not isinstance(caps, list):
        raise ValueError("MEDIA_PLAN.selected_capabilities must be a list")

    optional_runtimes = order.get("optional_runtimes", [])
    if optional_runtimes is None:
        optional_runtimes = []
    if not isinstance(optional_runtimes, list) or any(not isinstance(x, str) or not x.strip() for x in optional_runtimes):
        raise ValueError("OPERATING_ORDER.optional_runtimes must be an array of non-empty runtime ids")
    optional_runtimes = list(dict.fromkeys(optional_runtimes))
    unknown_runtimes = sorted(set(optional_runtimes) - OPTIONAL_RUNTIME_IDS)
    if unknown_runtimes:
        raise ValueError("unknown optional runtime ids: " + ", ".join(unknown_runtimes))

    overrides = order.get("standard_workflow_overrides", {}) if isinstance(order.get("standard_workflow_overrides"), dict) else {}
    selected = resolve(registry, mode, caps, overrides.get("include"), overrides.get("exclude"))
    return {
        "mode": mode,
        "selected_capabilities": caps,
        "selected_workflows": [wf["id"] for wf in selected],
        "selected_workflow_names": [wf["name"] for wf in selected],
        "optional_runtimes": optional_runtimes,
    }


def regression_scenarios(registry: dict):
    scenarios = [
        ("living_scene", ["generated_stills", "living_painting", "living_still_fx", "loop_media", "reactive_plate"], {"WF-LIVING-SCENE-ASSEMBLY", "WF-MUSIC-DIRECTED-SECTION-ASSEMBLY", "WF-PROFILE-DRIVEN-SCENE-TREATMENT", "WF-TEMPORAL-QC"}),
        ("cinematic", ["source_video", "conventional_video"], {"WF-REAL-FOOTAGE-RESTORATION", "WF-TRACKING", "WF-STABILIZATION"}),
        ("hybrid", ["accepted_source_library", "canonical_hero_library", "source_derived_coverage", "reactive_plate", "depth_25d", "loop_media"], {"WF-SOURCE-DERIVED-LOOPS", "WF-AUDIO-REACTIVITY", "WF-SCENE-GRAPH-25D"}),
        ("cinematic", ["generated_stills", "generated_support_imagery"], {"WF-SEQUENTIAL-GENERATED-CINEMA"}),
        ("hybrid", ["true_3dgs"], {"WF-GAUSSIAN-SPLAT-PATH"}),
        ("hybrid", ["nerf"], {"WF-NERF-PATH"}),
    ]
    failures = []
    for mode, caps, expected in scenarios:
        got = {wf["id"] for wf in resolve(registry, mode, caps)}
        missing = expected - got
        if missing:
            failures.append(f"{mode}/{','.join(caps)} missing {','.join(sorted(missing))}")
    return failures


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    ap.add_argument("--project")
    ap.add_argument("--mode")
    ap.add_argument("--capability", action="append", default=[])
    ap.add_argument("--include", action="append", default=[])
    ap.add_argument("--exclude", action="append", default=[])
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    reg = load_json(Path(args.registry))
    media = load_json(MEDIA_MATRIX) if MEDIA_MATRIX.is_file() else None
    errors = validate_registry(reg, media)
    if args.verify:
        errors.extend(regression_scenarios(reg))
    if errors:
        payload = {"result": "FAIL", "errors": errors}
        print(json.dumps(payload, indent=2) if args.json else "\n".join(errors))
        return 2
    if args.project:
        result = resolve_project(Path(args.project).resolve(), reg)
    else:
        mode = args.mode or "hybrid"
        selected = resolve(reg, mode, args.capability, args.include, args.exclude)
        result = {"mode": mode, "selected_capabilities": args.capability, "selected_workflows": [x["id"] for x in selected], "selected_workflow_names": [x["name"] for x in selected], "optional_runtimes": []}
    result["result"] = "PASS"
    print(json.dumps(result, indent=2) if args.json else "\n".join(result["selected_workflow_names"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
