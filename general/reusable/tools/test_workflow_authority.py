#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
GUARD = HERE / "workflow_guard.py"
RESOLVER = HERE / "workflow_resolver.py"
REGISTRY = ROOT / "general/reusable/STANDARD_WORKFLOW_REGISTRY.json"
RUNTIME_DIR = ROOT / "general/reusable/render_runtime"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_guard():
    return load_module(GUARD, "aivideoedit_workflow_guard_test")


def load_resolver():
    return load_module(RESOLVER, "aivideoedit_workflow_resolver_test")


def test_optional_runtime_cannot_become_workflow_authority():
    mod = load_guard()
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    assert mod.validate_optional_runtime_boundary(registry) == []

    poisoned = json.loads(json.dumps(registry))
    poisoned["workflows"][0]["implementation"]["backend_options"].append("render_runtime")
    errors = mod.validate_optional_runtime_boundary(poisoned)
    assert errors
    assert "forbidden in STANDARD_WORKFLOW_REGISTRY" in errors[0]


def test_existing_aivideoedit_defaults_remain_mandatory():
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    default_ids = {
        wf["id"]
        for wf in registry.get("workflows", [])
        if isinstance(wf, dict) and wf.get("select_if", {}).get("default") is True
    }
    required = {"WF-PROJECT-STATE", "WF-RENDER-DELIVERY", "WF-MACHINE-QC", "WF-CACHE-INVALIDATION"}
    assert required.issubset(default_ids)


def test_optional_runtime_requires_explicit_project_opt_in():
    mod = load_resolver()
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as td:
        project = Path(td)
        (project / "MEDIA_PLAN.json").write_text(
            json.dumps({"production_mode": "hybrid", "selected_capabilities": []}),
            encoding="utf-8",
        )
        (project / "OPERATING_ORDER.json").write_text(
            json.dumps({"production_mode": "hybrid"}),
            encoding="utf-8",
        )
        baseline = mod.resolve_project(project, registry)
        assert baseline["optional_runtimes"] == []

        (project / "OPERATING_ORDER.json").write_text(
            json.dumps({"production_mode": "hybrid", "optional_runtimes": ["browser_scene_runtime"]}),
            encoding="utf-8",
        )
        opted_in = mod.resolve_project(project, registry)
        assert opted_in["optional_runtimes"] == ["browser_scene_runtime"]
        assert opted_in["selected_workflows"] == baseline["selected_workflows"]

        (project / "OPERATING_ORDER.json").write_text(
            json.dumps({"production_mode": "hybrid", "optional_runtimes": ["render_runtime"]}),
            encoding="utf-8",
        )
        try:
            mod.resolve_project(project, registry)
        except ValueError as exc:
            assert "unknown optional runtime ids" in str(exc)
        else:
            raise AssertionError("unknown runtime id must fail closed")


def test_runtime_entry_points_are_gated():
    for name in ("render_scene.mjs", "scene_qc.mjs", "stage_runtime_assets.mjs"):
        text = (RUNTIME_DIR / name).read_text(encoding="utf-8")
        assert "assertRuntimeOptIn" in text, f"{name} must enforce explicit runtime opt-in"
    gate = (RUNTIME_DIR / "runtime_opt_in.mjs").read_text(encoding="utf-8")
    assert "browser_scene_runtime" in gate
    assert "optional_runtimes" in gate


if __name__ == "__main__":
    test_optional_runtime_cannot_become_workflow_authority()
    test_existing_aivideoedit_defaults_remain_mandatory()
    test_optional_runtime_requires_explicit_project_opt_in()
    test_runtime_entry_points_are_gated()
    print("workflow authority regression: PASS")
