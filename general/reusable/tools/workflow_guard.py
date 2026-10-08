#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path

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

REGISTRY = OS_ROOT / "general/reusable/STANDARD_WORKFLOW_REGISTRY.json"
RESOLVER = OS_ROOT / "general/reusable/tools/workflow_resolver.py"
MEDIA = OS_ROOT / "general/reusable/MEDIA_CAPABILITY_MATRIX.json"
CONTRACT = OS_ROOT / "general/reusable/PRODUCTION_CONTRACT.json"

# Optional execution engines may extend an already-resolved AIVideoEdit workflow,
# but they may never register themselves as workflow authority. This protects the
# existing director/bootstrap/guard machinery from being silently replaced by an
# implementation-specific renderer, transition package, or audio bridge.
OPTIONAL_RUNTIME_MARKERS = {
    "render_runtime",
    "render_scene.mjs",
    "aivideoedit-render-core",
    "aivideoedit-render-cli",
    "transition_bridge.js",
    "audio_mix_bridge.js",
}


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("aivideoedit_workflow_resolver_guard", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate_optional_runtime_boundary(registry: dict):
    serialized = json.dumps(registry, sort_keys=True).lower()
    errors = []
    for marker in sorted(OPTIONAL_RUNTIME_MARKERS):
        if marker.lower() in serialized:
            errors.append(
                f"optional runtime implementation marker {marker!r} is forbidden in STANDARD_WORKFLOW_REGISTRY; "
                "resolve the AIVideoEdit workflow first, then invoke optional runtime tools as subordinate capabilities"
            )
    return errors


def validate(branch: str):
    errors = []
    if not REGISTRY.is_file():
        return [f"missing standard workflow registry: {REGISTRY}"]
    if not RESOLVER.is_file():
        return [f"missing standard workflow resolver: {RESOLVER}"]
    mod = load_module(RESOLVER)
    registry = load_json(REGISTRY)
    media = load_json(MEDIA) if MEDIA.is_file() else None
    errors.extend(mod.validate_registry(registry, media))
    errors.extend(mod.regression_scenarios(registry))
    errors.extend(validate_optional_runtime_boundary(registry))
    if errors or branch == "main":
        return errors

    project, branch_error = resolve_production_project(ROOT, branch)
    if branch_error:
        return [branch_error]
    if project is None:
        return [f"production project could not be resolved for {branch}"]
    try:
        resolved = mod.resolve_project(project, registry)
    except Exception as exc:
        return [f"standard workflow selection failed: {exc}"]
    selected = resolved.get("selected_workflows", [])
    mandatory = {"WF-PROJECT-STATE", "WF-RENDER-DELIVERY", "WF-MACHINE-QC", "WF-CACHE-INVALIDATION"}
    state = load_json(project / "PROJECT_STATE.json")
    order = load_json(project / "OPERATING_ORDER.json") if (project / "OPERATING_ORDER.json").is_file() else {}
    contract = load_json(CONTRACT)
    try:
        version = int(state.get("director_brain_version", 0) or 0)
    except (TypeError, ValueError):
        version = 0
    stage = state.get("stage")
    states = contract.get("states", [])
    if (
        version >= 3
        and stage in states
        and states.index(stage) >= states.index("APPROACH_ESTABLISHED")
        and order.get("direction_authority") == "music_led"
        and order.get("production_mode") in {"living_scene", "hybrid"}
    ):
        mandatory.update({"WF-MUSIC-DIRECTED-SECTION-ASSEMBLY", "WF-PROFILE-DRIVEN-SCENE-TREATMENT"})
    missing = mandatory - set(selected)
    if missing:
        errors.append("standard workflow selection missing mandatory defaults: " + ", ".join(sorted(missing)))
    return errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--branch", default=os.environ.get("GITHUB_REF_NAME") or os.environ.get("AIVIDEOEDIT_BRANCH") or "")
    args = ap.parse_args()
    if not args.branch:
        print("AIVideoEdit standard workflow contract: FAIL\n- branch required")
        return 2
    errors = validate(args.branch)
    if errors:
        print("AIVideoEdit standard workflow contract: FAIL")
        for e in errors:
            print("- " + e)
        return 2
    print("AIVideoEdit standard workflow contract: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
