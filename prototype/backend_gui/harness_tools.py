#!/usr/bin/env python3
"""Agent-harness read model for AIVideoEdit Studio.

This module deliberately adds only read-oriented orchestration helpers.
Production mutations continue to flow through the existing provider-neutral
Tool API and its canonical AIVideoEdit guards.
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import server as base
import production_project
from core_adapter import CORE
from general.reusable.tools.harness_router import harness_enabled

SCHEMAS = [
    {
        "name": "harness.status",
        "description": "Show whether the optional agent-harness bridge is available without changing production state.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "harness.context",
        "description": "Return a compact authoritative project/branch/stage/director snapshot for an agent before it acts.",
        "input_schema": {
            "type": "object",
            "required": ["project_id"],
            "properties": {"project_id": {"type": "string"}},
        },
    },
    {
        "name": "harness.specialist_fixture",
        "description": "Run one bounded provider-neutral specialist fixture when optional Harness is enabled.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {"type": "string"},
                "evidence": {"type": "object"}
            },
        },
    },
    {
        "name": "harness.fx_resolve",
        "description": "Deterministically resolve approved reusable FX and composition recipes for a batch, scene, or still from explicit semantic facts.",
        "input_schema": {
            "type": "object",
            "required": ["project_id"],
            "properties": {
                "project_id": {"type": "string"},
                "level": {"type": "string", "enum": ["batch", "scene", "still"], "default": "scene"},
                "environment": {"type": "array", "items": {"type": "string"}},
                "materials": {"type": "array", "items": {"type": "string"}},
                "objects": {"type": "array", "items": {"type": "string"}},
                "needs": {"type": "array", "items": {"type": "string"}},
                "motifs": {"type": "array", "items": {"type": "string"}},
                "tags": {"type": "array", "items": {"type": "string"}},
                "constraints": {"type": "array", "items": {"type": "string"}},
                "allow_proof_required": {"type": "boolean", "default": False},
                "max_effects": {"type": "integer", "minimum": 1, "maximum": 12}
            },
        },
    },
]


def schemas():
    return SCHEMAS


def _read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def status() -> dict:
    dsh = shutil.which("dsh")
    npx = shutil.which("npx")
    return {
        "schema": "aivideoedit.harness-status.v1",
        "ok": True,
        "bridge": "mcp-stdio",
        "bridge_ready": True,
        "enabled": harness_enabled(),
        "dsh_installed": bool(dsh),
        "npx_available": bool(npx),
        "launcher": dsh or npx,
        "canonical_core": CORE.status(),
        "policy": {
            "production_authority": "canonical-aivideoedit-core",
            "main_mutation": False,
            "guard_bypass": False,
            "project_context_required": True,
        },
    }


def context(project_id: str) -> dict:
    pid = str(project_id or "").strip()
    project = base.find_project(pid)
    if not project:
        raise ValueError("project not found")

    production = production_project.status(pid)
    project_dir_text = production.get("project_dir") or ""
    project_dir = Path(project_dir_text) if project_dir_text else None
    order = _read_json(project_dir / "OPERATING_ORDER.json", {}) if project_dir and project_dir.is_dir() else {}
    state = _read_json(project_dir / "PROJECT_STATE.json", {}) if project_dir and project_dir.is_dir() else {}

    with base.LOCK:
        assets = [
            {
                "id": a.get("id"),
                "filename": a.get("filename"),
                "status": a.get("status"),
                "sha256": a.get("sha256"),
                "qc": (a.get("qc") or {}).get("status"),
                "origin": a.get("origin"),
            }
            for a in base.STATE["assets"]
            if a.get("project") == pid
        ]
        active_jobs = [
            {
                "id": j.get("id"),
                "type": j.get("type"),
                "status": j.get("status"),
                "progress": j.get("progress"),
                "result": j.get("result"),
            }
            for j in base.STATE["jobs"]
            if j.get("project") == pid and j.get("status") in {"queued", "running"}
        ]

    return {
        "schema": "aivideoedit.harness-context.v1",
        "project": {
            "id": project.get("id"),
            "name": project.get("name"),
        },
        "production": {
            "initialized": bool(production.get("initialized")),
            "branch": production.get("branch"),
            "stage": production.get("stage"),
            "next_stage": production.get("next_stage"),
            "guard_pass": bool(production.get("guard_pass")),
            "main_commit": (production.get("core") or {}).get("main_commit") or CORE.status().get("main_commit"),
        },
        "director": {
            "director_brain_version": state.get("director_brain_version"),
            "mission": order.get("mission"),
            "direction_authority": order.get("direction_authority"),
            "production_mode": order.get("production_mode"),
            "current_user_direction": order.get("current_user_direction"),
            "exact_next_action": order.get("exact_next_action"),
            "canon_lock": order.get("canon_lock"),
            "accepted_baseline": order.get("accepted_baseline"),
            "accepted_source_library": order.get("accepted_source_library"),
            "refinement_scope": order.get("refinement_scope"),
            "recut_scope": order.get("recut_scope"),
        },
        "assets": {
            "count": len(assets),
            "ready": sum(1 for a in assets if a.get("status") == "ready"),
            "items": assets,
        },
        "active_jobs": active_jobs,
        "agent_rules": [
            "Treat the current project branch and current explicit user instruction as project authority.",
            "Run through existing AIVideoEdit tools; do not bypass canonical production guards.",
            "Harness is optional orchestration only; AIVideoEdit production state remains authoritative.",
            "Refresh harness.context after a stage-changing operation before choosing the next action.",
            "Resolve FX through harness.fx_resolve before authoring batch/scene/still FX requirements and after material scene changes.",
        ],
    }



def fx_resolve(project_id: str, request: dict) -> dict:
    pid = str(project_id or "").strip()
    project = base.find_project(pid)
    if not project:
        raise ValueError("project not found")
    production = production_project.status(pid)
    if not production.get("initialized"):
        raise RuntimeError("production workspace is not initialized")
    engine = Path(str(production.get("engine_root") or ""))
    session = _read_json(engine / ".aivideoedit" / "session.json", {})
    os_root = Path(str(session.get("os_root") or ""))
    fx_root = os_root / "general" / "reusable" / "fx_v2"
    resolver_path = fx_root / "fx_resolver.py"
    registry_path = fx_root / "registry.json"
    recipes_path = fx_root / "recipes.json"
    for required in (resolver_path, registry_path, recipes_path):
        if not required.is_file():
            raise RuntimeError(f"canonical FX resolver dependency missing: {required.name}")
    spec = importlib.util.spec_from_file_location("aivideoedit_fx_resolver", resolver_path)
    if not spec or not spec.loader:
        raise RuntimeError("cannot load canonical FX resolver")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    context_data = {
        key: request.get(key, [])
        for key in ("environment", "materials", "objects", "needs", "motifs", "tags", "constraints")
    }
    context_data["level"] = str(request.get("level") or "scene")
    resolution = module.resolve(
        context_data,
        registry_path=registry_path,
        recipes_path=recipes_path,
        allow_proof_required=bool(request.get("allow_proof_required", False)),
        max_effects=request.get("max_effects"),
    )
    return {
        "schema": "aivideoedit.harness-fx-resolution.v1",
        "project": {"id": project.get("id"), "name": project.get("name")},
        "production": {
            "branch": production.get("branch"),
            "stage": production.get("stage"),
            "main_commit": (production.get("core") or {}).get("main_commit") or CORE.status().get("main_commit"),
        },
        "resolution": resolution,
        "agent_rule": "Use this resolution before authoring FX requirements; directorial judgment may remove an effect but must not silently substitute unregistered project-local behavior.",
    }


def specialist_fixture(args: dict | None = None) -> dict:
    if not harness_enabled():
        raise RuntimeError("optional Harness is disabled; set AIVE_HARNESS_ENABLED=1 to use specialist routing")
    args = args or {}
    task = str(args.get("task") or "bounded specialist fixture").strip()
    evidence = args.get("evidence") if isinstance(args.get("evidence"), dict) else {}
    return {
        "schema": "aivideoedit.harness-specialist-fixture.v1",
        "status": "COMPLETE",
        "task": task,
        "evidence_keys": sorted(str(k) for k in evidence),
        "authority": "advisory_only",
        "production_mutation": False,
    }


def call(name: str, args: dict | None = None):
    args = args or {}
    if name == "harness.status":
        return status()
    if name == "harness.context":
        return context(str(args.get("project_id") or ""))
    if name == "harness.specialist_fixture":
        return specialist_fixture(args)
    if name == "harness.fx_resolve":
        return fx_resolve(str(args.get("project_id") or ""), args)
    raise ValueError(f"unknown harness tool: {name}")
