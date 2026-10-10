#!/usr/bin/env python3
"""Run the live Director/Harness gate before a real film render.

The canonical MainV2 checkout is supplied separately by the workflow.  This
gate reads the branch director package, boots the isolated main core through
the AIVideoEdit MCP bridge, exercises the Harness surface, resolves FX, runs
the pinned music model, and writes a receipt consumed by every render shard.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def call(proc, request_id: int, method: str, params: dict):
    proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}) + "\n")
    proc.stdin.flush()
    while True:
        line = proc.stdout.readline()
        if not line:
            raise RuntimeError("AIVideoEdit MCP bridge exited before replying")
        value = json.loads(line)
        if value.get("id") == request_id:
            if "error" in value:
                raise RuntimeError(str(value["error"]))
            return value.get("result") or {}


def tool(proc, request_id: int, name: str, arguments: dict):
    result = call(proc, request_id, "tools/call", {"name": name.replace(".", "__"), "arguments": arguments})
    if result.get("isError"):
        content = result.get("content") or []
        message = content[0].get("text") if content and isinstance(content[0], dict) else str(result)
        raise RuntimeError(f"{name}: {message}")
    content = result.get("content") or []
    text = content[0].get("text") if content and isinstance(content[0], dict) else "{}"
    return json.loads(text)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-root", type=Path, required=True)
    ap.add_argument("--engine-root", type=Path, required=True)
    ap.add_argument("--project", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--lineage", type=Path, required=True)
    ap.add_argument("--media-root", type=Path, required=True)
    ap.add_argument("--shard-plan", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    source = args.source_root.resolve()
    engine = args.engine_root.resolve()
    project = args.project.resolve()
    manifest_path = args.manifest.resolve()
    lineage_path = args.lineage.resolve()
    media_root = args.media_root.resolve()
    shard_plan_path = args.shard_plan.resolve()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)

    order = read(project / "OPERATING_ORDER.json", {})
    plan = read(project / "MEDIA_PLAN.json", {})
    music = read(project / "MUSIC_ANALYSIS.json", {})
    manifest = read(manifest_path, {})
    required = [order, plan, music, manifest]
    if any(not isinstance(x, dict) or not x for x in required):
        raise RuntimeError("director package, music analysis, or render manifest is missing")
    direction = str(order.get("current_user_direction") or "")
    if not direction.strip():
        raise RuntimeError("live Director gate did not receive current user direction")
    if order.get("direction_authority") != "user_directed" or order.get("production_mode") not in {"living_scene", "cinematic", "hybrid"}:
        raise RuntimeError("unexpected Director authority or production mode")
    if manifest.get("render_authorization") != "explicit_user_render_request":
        raise RuntimeError("render authorization is not explicit")

    sys.path.insert(0, str(engine))
    from scripts.render_lineage import receipt_identity, verify_bundle
    staged_manifest_path = media_root / "STAGED_MANIFEST.json"
    lineage = verify_bundle(
        lineage_path, staged_manifest_path, media_root,
        source_root=source, engine_root=engine, project=project,
        original_manifest=manifest_path,
    )
    staged_manifest = read(staged_manifest_path, {})
    shard_plan = read(shard_plan_path, {})
    from scripts.plan_render_shards import validate_plan
    validate_plan(shard_plan, len(manifest["shots"]))

    context_spec = plan.get("director_context") if isinstance(plan.get("director_context"), dict) else {}

    def context_list(name: str, fallback: list[str]) -> list[str]:
        value = context_spec.get(name)
        if isinstance(value, list):
            cleaned = [str(item).strip() for item in value if str(item).strip()]
            if cleaned:
                return cleaned[:24]
        return fallback

    route_name = str((plan.get("visual_direction_gate") or {}).get("user_selection", {}).get("route_name") or "authored production")
    production_id = str(manifest.get("production_id") or project.name)

    # Use the exact main checkout as the authority for model, JEV, FX, and the
    # live MCP bridge.  The bridge's runtime is isolated and never writes main.
    runtime = out / "harness-runtime"
    env = dict(os.environ)
    env.update({
        "AIVE_RUNTIME": str(runtime),
        "AIVE_CORE_REF": "main",
        "AIVE_OFFLINE": "1",
        "AIVE_HARNESS_ENABLED": "1",
    })
    bridge = engine / "prototype" / "backend_gui" / "aivideo_mcp.py"
    proc = subprocess.Popen(
        [sys.executable, str(bridge)], cwd=str(engine / "prototype" / "backend_gui"),
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, env=env, bufsize=1,
    )
    try:
        init = call(proc, 1, "initialize", {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "aivideoedit-director-gate", "version": "1"}})
        proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}) + "\n")
        proc.stdin.flush()
        listed = call(proc, 3, "tools/list", {})
        names = {x.get("name") for x in listed.get("tools", []) if isinstance(x, dict)}
        required_tools = {"harness__status", "harness__context", "harness__specialist_fixture", "harness__fx_resolve", "core__bootstrap", "production__initialize"}
        missing = sorted(required_tools - names)
        if missing:
            raise RuntimeError("live Harness surface missing: " + ", ".join(missing))

        core = tool(proc, 4, "core.status", {})
        boot = tool(proc, 5, "core.bootstrap", {"offline": True})
        if not boot.get("bootstrapped") or boot.get("requested_core_ref") != "main":
            raise RuntimeError("isolated canonical main core did not boot: " + json.dumps(boot)[-2400:])
        project_result = tool(proc, 6, "project.create", {"name": production_id + " — Director Gate"})
        project_id = str((project_result.get("project") or {}).get("id") or "")
        if not project_id:
            raise RuntimeError("live Tool API did not create a director-gate project")
        production = tool(proc, 7, "production.initialize", {"project_id": project_id})
        # The live bridge project is an isolated Harness workspace. Creative
        # direction remains authoritative in the already locked branch package;
        # configuring a second provisional project would violate the stage gate.
        harness_status = tool(proc, 8, "harness.status", {})
        context = tool(proc, 9, "harness.context", {"project_id": project_id})
        specialist = tool(proc, 10, "harness.specialist_fixture", {
            "task": "Director review: enforce the current user direction, shot continuity, authored motion/transitions, source fidelity, and no release promotion before visual approval. Direction: " + direction,
            "evidence": {
                "user_direction": direction,
                "route": route_name,
                "production_mode": order["production_mode"],
                "manifest_sha256": sha(manifest_path),
            },
        })
        fx_resolution = tool(proc, 11, "harness.fx_resolve", {
            "project_id": project_id,
            "level": "scene",
            "environment": context_list("environment", [route_name]),
            "materials": context_list("materials", ["source-defined materials"]),
            "objects": context_list("objects", ["manifest-authorized subjects"]),
            "needs": context_list("needs", ["authored camera motion", "continuity", "authored transitions"]),
            "motifs": context_list("motifs", [production_id]),
            "tags": context_list("tags", [order["production_mode"], "user-directed"]),
            "constraints": context_list("constraints", ["preserve subject identity", "preserve source fidelity", "no unregistered FX"]),
            "max_effects": 12,
        })

        # Provision and execute the pinned music model once.  Shards consume
        # this evidence instead of independently inventing editorial timing.
        provision = subprocess.run([sys.executable, "-m", "general.reusable.tools.model_provision", "music-beat-onnx-v1"], cwd=str(engine), env=env, capture_output=True, text=True, timeout=600)
        if provision.returncode:
            raise RuntimeError("pinned ONNX provision failed: " + (provision.stderr or provision.stdout)[-1800:])
        from scripts.render_real_music_film import stage
        from general.reusable.tools.music_beat_worker import analyze_music
        audio = stage(staged_manifest["audio"], input_root=media_root, cache=out / "verified_inputs")
        if sha(audio) != lineage["audio_sha256"]:
            raise RuntimeError("staged audio differs from immutable run lineage")
        music_evidence = analyze_music(audio)
        if music_evidence.get("engine") != "beat_this_onnx" or music_evidence.get("model_resolution", {}).get("used_fallback"):
            raise RuntimeError("pinned Beat This ONNX evidence is missing or used fallback")
        (out / "MUSIC_BEAT_EVIDENCE.json").write_text(json.dumps(music_evidence, indent=2) + "\n", encoding="utf-8")

        from general.reusable.tools.jev_decision import decide
        from general.reusable.tools.harness_router import route_jev
        evidence = {
            "gate": "PASS",
            "checks": {
                "director_input_present": bool(direction),
                "canonical_main_booted": bool(boot.get("bootstrapped")),
                "live_harness_available": bool(harness_status.get("bridge_ready")),
                "harness_director_review_consumed": specialist.get("status") == "COMPLETE",
                "canonical_fx_resolution_present": bool(fx_resolution.get("resolution")),
                "onnx_evidence_available": True,
                "parallel_render_authorized": True,
            },
            "model_observations": [{"authority": "evidence_only", "confidence": float(music_evidence.get("confidence") or 0.9)}],
            "next_action_permitted": True,
        }
        jev = decide(evidence)
        route = route_jev(jev)
        if jev.get("decision") not in {"PASS", "CONTINUE"}:
            raise RuntimeError("JEV denied the director-gated render: " + json.dumps(jev))

        from scripts.render_real_music_film import fx_lock
        lock, effects, transitions = fx_lock(manifest, out)
        if not lock:
            raise RuntimeError("canonical FX lock is empty")
        receipt = {
            "schema": "aivideoedit.director-harness-receipt.v1",
            "branch": os.environ.get("SOURCE_REF") or os.environ.get("GITHUB_REF_NAME") or "production/unknown",
            "source_project": str(project),
            "manifest_sha256": sha(manifest_path),
            "director_input": direction,
            "route_name": route_name,
            "core": {"boot": boot, "main_commit": boot.get("main_commit") or core.get("main_commit")},
            "harness": {"status": harness_status, "context": context, "specialist": specialist, "fx_resolution": fx_resolution},
            "jev": jev,
            "harness_route": route,
            "music_evidence_sha256": sha(out / "MUSIC_BEAT_EVIDENCE.json"),
            "fx_lock_sha256": sha(lock),
            "effects": effects,
            "transitions": transitions,
            "parallel_shards": len(shard_plan["include"]),
            "shard_plan": shard_plan["include"],
            "shard_plan_sha256": sha(shard_plan_path),
            "human_visual_approval": False,
            "production_complete": False,
            **receipt_identity(lineage, lineage_path),
        }
        (out / "DIRECTOR_HARNESS_RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"result": "PASS", "decision": jev, "route": route, "main_commit": receipt["core"]["main_commit"], "fx_lock_sha256": receipt["fx_lock_sha256"]}, indent=2))
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=10)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
