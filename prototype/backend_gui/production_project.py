#!/usr/bin/env python3
"""Bridge browser projects into isolated canonical AIVideoEdit production repos.

Each workstation project gets its own local checkout and `song/<slug>` branch.
The compatibility scaffold only creates the minimum INITIALIZED project files;
the current-main production guard remains the authority for validity and all
later stage advancement.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import server as base
from core_adapter import CORE


def _run(cmd: list[str], cwd: Path, timeout: int = 300, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout, check=False, env=env)


def _engine_root(project_id: str) -> Path:
    return base.PROJECT_ROOT / project_id / "engine"


def _song_slug(project_id: str) -> str:
    return base.slugify(project_id)


def _branch(project_id: str) -> str:
    return f"song/{_song_slug(project_id)}"


def _canonical_project_dir(engine: Path, project_id: str) -> Path:
    return engine / "projects" / _song_slug(project_id)


def _read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {} if default is None else default


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _parse_fps(value) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value or "").strip()
    if not text:
        return 0.0
    try:
        if "/" in text:
            left, right = text.split("/", 1)
            denom = float(right)
            return float(left) / denom if denom else 0.0
        return float(text)
    except Exception:
        return 0.0


def _git_commit_paths(engine: Path, paths: list[Path], message: str) -> str | None:
    rels = []
    for path in paths:
        try:
            rels.append(path.resolve().relative_to(engine.resolve()).as_posix())
        except Exception:
            continue
    if not rels:
        return None
    add = _run(["git", "add", "--", *rels], engine, timeout=60)
    if add.returncode != 0:
        raise RuntimeError((add.stderr or add.stdout or "git add failed")[-1200:])
    diff = _run(["git", "diff", "--cached", "--quiet"], engine, timeout=30)
    if diff.returncode == 0:
        return None
    commit = _run(["git", "commit", "-m", message], engine, timeout=60)
    if commit.returncode != 0:
        raise RuntimeError((commit.stderr or commit.stdout or "git commit failed")[-1200:])
    sha = _run(["git", "rev-parse", "HEAD"], engine, timeout=20)
    return sha.stdout.strip() if sha.returncode == 0 else None


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _head(engine: Path) -> str | None:
    proc = _run(["git", "rev-parse", "HEAD"], engine, timeout=20)
    return proc.stdout.strip() if proc.returncode == 0 and proc.stdout.strip() else None


def _guard_marker_path(engine: Path) -> Path:
    return engine / ".aivideoedit" / "workstation_guard.json"


def _clear_guard_marker(engine: Path) -> None:
    try:
        _guard_marker_path(engine).unlink()
    except FileNotFoundError:
        pass


def _write_guard_marker(project_id: str) -> None:
    engine = _engine_root(project_id)
    project_dir = _canonical_project_dir(engine, project_id)
    state_path = project_dir / "PROJECT_STATE.json"
    if not engine.is_dir() or not state_path.is_file():
        return
    marker = {
        "schema": "aivideoedit.workstation-guard.v1",
        "project_id": project_id,
        "branch": _branch(project_id),
        "verified_head": _head(engine),
        "verified_state_sha256": _sha256_file(state_path),
        "verified_at": base.now(),
    }
    path = _guard_marker_path(engine)
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(path, marker)


def _scaffold(project_id: str, name: str, engine: Path) -> Path:
    project_dir = _canonical_project_dir(engine, project_id)
    project_dir.mkdir(parents=True, exist_ok=True)
    branch = _branch(project_id)
    contract = CORE.production_contract()
    denied = contract.get("default_denied_sources", [])

    text_files = {
        "PROJECT.md": f"# {name}\n\nAIVideoEdit production workspace.\n",
        "STATUS.md": "# Status\n\nStage: INITIALIZED\n",
        "HANDOFF.md": "# Handoff\n\nProduction initialized; no creative direction is implied by this scaffold.\n",
        "SCRIPT.md": "# Script\n\nNot locked.\n",
        "VISUAL_DNA.md": "# Visual DNA\n\nNot established.\n",
        "SHOT_LIST.md": "# Shot List\n\nNot established.\n",
        "RENDER_HISTORY.md": "# Render History\n\nNo accepted renders.\n",
        "QC.md": "# QC\n\nNo final QC has been performed.\n",
    }
    for filename, content in text_files.items():
        (project_dir / filename).write_text(content, encoding="utf-8")

    _write_json(project_dir / "PROJECT_STATE.json", {
        "schema": "aivideoedit.project-state.v1",
        "branch": branch,
        "stage": "INITIALIZED",
        "source_ingest_complete": False,
        "reference_analysis_complete": False,
        "music_analysis_complete": False,
        "lyrics_status_resolved": False,
        "genre_authority_resolved": False,
        "visual_approach_established": False,
        "storyboard_locked": False,
        "script_locked": False,
        "shot_packages_built": False,
        "shot_proofs_accepted": False,
        "fx_lock_verified": False,
        "assembly_complete": False,
        "final_qc_passed": False,
        "archive_complete": False,
    })
    _write_json(project_dir / "SOURCE_AUTHORITY.json", {
        "schema": "aivideoedit.source-authority.v1",
        "allow": {key: False for key in denied},
        "explicit_user_authorizations": [],
    })
    _write_json(project_dir / "REFERENCE_MANIFEST.json", {"schema": "aivideoedit.reference-manifest.v1", "videos": [], "images": [], "audio": []})
    _write_json(project_dir / "MEDIA_PLAN.json", {
        "schema": "aivideoedit.media-plan.v1",
        "selected_capabilities": [],
        "user_approach_established": False,
        "production_mode": "hybrid",
        "production_mode_authority": "bootstrap_compatibility_only",
        "production_mode_locked": False,
        "bootstrap_note": "Provisional resolver input only; no creative direction is implied. Replace through Director Brain after current-production analysis.",
    })
    _write_json(project_dir / "ASSET_MANIFEST.json", {"schema": "aivideoedit.asset-manifest.v1", "assets": []})
    _write_json(project_dir / "MUSIC_ANALYSIS.json", {})
    _write_json(project_dir / "SCRIPT.json", {"entries": []})
    return project_dir


def initialize(project_id: str) -> dict:
    project = base.find_project(project_id)
    if not project:
        raise ValueError("project not found")
    if not CORE.status().get("bootstrapped"):
        raise RuntimeError("canonical core is not loaded")

    engine = _engine_root(project_id)
    if engine.exists():
        return status(project_id)
    engine.parent.mkdir(parents=True, exist_ok=True)

    proc = _run(["git", "clone", "--no-hardlinks", str(CORE.core_repo), str(engine)], CORE.core_repo)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "local core clone failed")[-1200:])

    branch = _branch(project_id)
    base_commit = str(CORE.status().get("main_commit") or "").strip()
    checkout = _run(["git", "checkout", "-b", branch, base_commit or "main"], engine, timeout=60)
    if checkout.returncode != 0:
        checkout = _run(["git", "checkout", "-b", branch, "main"], engine, timeout=60)
    if checkout.returncode != 0:
        checkout = _run(["git", "checkout", "-b", branch, "origin/main"], engine, timeout=60)
    if checkout.returncode != 0:
        shutil.rmtree(engine, ignore_errors=True)
        raise RuntimeError((checkout.stderr or checkout.stdout or "song branch creation failed")[-1200:])

    project_dir = _scaffold(project_id, project.get("name") or project_id, engine)
    _run(["git", "config", "user.name", "AIVideoEdit Workstation"], engine, timeout=20)
    _run(["git", "config", "user.email", "workstation@aivideoedit.local"], engine, timeout=20)
    _run(["git", "add", f"projects/{project_dir.name}"], engine, timeout=30)
    commit = _run(["git", "commit", "-m", "Initialize AIVideoEdit production workspace"], engine, timeout=60)
    if commit.returncode != 0:
        raise RuntimeError((commit.stderr or commit.stdout or "initial project commit failed")[-1200:])

    boot_env = dict(os.environ)
    core_ref = os.environ.get("AIVE_CORE_REF", "main").strip() or "main"
    if core_ref != "main":
        boot_env["AIVIDEOEDIT_AUTHORITY_REF"] = core_ref
        boot_env["AIVIDEOEDIT_VALIDATION_MODE"] = "1"
    boot_cmd = [
        sys.executable, str(engine / "bootstrap.py"), "boot",
        "--repo-root", str(engine),
        "--branch", branch,
        "--project-dir", f"projects/{project_dir.name}",
    ]
    if os.environ.get("AIVE_OFFLINE", "").strip().lower() in {"1", "true", "yes", "on"}:
        boot_cmd.append("--offline")
    boot = _run(boot_cmd, engine, timeout=300, env=boot_env)
    if boot.returncode != 0:
        return {
            "ok": False,
            "initialized": True,
            "guard_pass": False,
            "branch": branch,
            "engine_root": str(engine),
            "project_dir": str(project_dir),
            "stdout": (boot.stdout or "")[-4000:],
            "stderr": (boot.stderr or "")[-4000:],
        }
    _write_guard_marker(project_id)
    return status(project_id)


def _manifest_records(project_id: str) -> tuple[list[dict], dict]:
    with base.LOCK:
        assets = [dict(a) for a in base.STATE["assets"] if a.get("project") == project_id]

    asset_records: list[dict] = []
    refs = {"schema": "aivideoedit.reference-manifest.v1", "videos": [], "images": [], "audio": []}
    for asset in assets:
        meta = asset.get("metadata") or {}
        content_type = str(asset.get("content_type") or "application/octet-stream")
        record = {
            "id": asset.get("id"),
            "name": asset.get("filename"),
            "uri": f"aive://asset/{asset.get('id')}",
            "sha256": asset.get("sha256"),
            "content_type": content_type,
            "size_bytes": asset.get("size_bytes"),
            "status": asset.get("status"),
            "created_at": asset.get("created_at"),
            "updated_at": asset.get("updated_at"),
            "metadata": meta,
            "derivatives": {
                "thumbnail": bool(asset.get("thumbnail_url")),
                "proxy": bool(asset.get("proxy_url")),
                "review_frames": len(asset.get("review_frames") or []),
            },
            "qc": asset.get("qc") or {"status": "unchecked"},
            "authority": "current_project_user_supplied",
        }
        asset_records.append(record)

        common = {
            "asset_id": asset.get("id"),
            "name": asset.get("filename"),
            "uri": record["uri"],
            "sha256": asset.get("sha256"),
            "authorized_role": "current_project_source_media",
            "content_reuse_authorized": True,
            "analysis_complete": False,
        }
        if content_type.startswith("image/"):
            refs["images"].append({**common, "width": meta.get("width"), "height": meta.get("height")})
        # MIME authority wins over incidental embedded streams. An MP3 may carry
        # album art that FFprobe reports as a video stream; it is still source
        # audio and must not become a visual reference.
        elif content_type.startswith("audio/"):
            refs["audio"].append({
                **common,
                "duration_seconds": float(meta.get("duration_seconds") or 0),
                "audio_codec": meta.get("audio_codec"),
            })
        elif content_type.startswith("video/") or meta.get("video_codec"):
            fps = _parse_fps(meta.get("fps"))
            duration = float(meta.get("duration_seconds") or 0)
            total_frames = int(round(duration * fps)) if duration > 0 and fps > 0 else 0
            refs["videos"].append({
                **common,
                "duration_seconds": duration,
                "total_frames": total_frames,
                "extracted_frames": len(asset.get("review_frames") or []),
                "extraction_policy": "workstation_preview_only",
                "sampling_description": "Preview-only review snapshots; canonical reference analysis not yet complete.",
                "coverage": [],
            })
        elif meta.get("audio_codec"):
            refs["audio"].append({
                **common,
                "duration_seconds": float(meta.get("duration_seconds") or 0),
                "audio_codec": meta.get("audio_codec"),
            })
    return asset_records, refs


def sync_assets(project_id: str) -> dict:
    current = status(project_id)
    if not current.get("initialized"):
        raise RuntimeError("production workspace is not initialized")
    engine = Path(current["engine_root"])
    project_dir = Path(current["project_dir"])
    records, refs = _manifest_records(project_id)
    manifest = {
        "schema": "aivideoedit.asset-manifest.v1",
        "source": "aivideoedit-workstation",
        "project_id": project_id,
        "synced_at": base.now(),
        "assets": records,
    }
    _write_json(project_dir / "ASSET_MANIFEST.json", manifest)
    _write_json(project_dir / "REFERENCE_MANIFEST.json", refs)

    state_path = project_dir / "PROJECT_STATE.json"
    state = _read_json(state_path, {})
    state["workstation_asset_sync_complete"] = True
    state["workstation_asset_count"] = len(records)
    state["workstation_ready_asset_count"] = sum(1 for r in records if r.get("status") == "ready")
    state["workstation_asset_manifest_synced_at"] = manifest["synced_at"]
    _write_json(state_path, state)

    commit = _git_commit_paths(
        engine,
        [project_dir / "ASSET_MANIFEST.json", project_dir / "REFERENCE_MANIFEST.json", state_path],
        "Sync workstation media into production manifests",
    )
    _clear_guard_marker(engine)
    return {
        **status(project_id),
        "asset_count": len(records),
        "ready_asset_count": sum(1 for r in records if r.get("status") == "ready"),
        "video_count": len(refs["videos"]),
        "image_count": len(refs["images"]),
        "audio_count": len(refs["audio"]),
        "commit": commit,
    }


def status(project_id: str) -> dict:
    project = base.find_project(project_id)
    if not project:
        raise ValueError("project not found")
    engine = _engine_root(project_id)
    project_dir = _canonical_project_dir(engine, project_id)
    session_path = engine / ".aivideoedit" / "session.json"
    state_path = project_dir / "PROJECT_STATE.json"
    session = _read_json(session_path, {})
    state = _read_json(state_path, {})
    marker = _read_json(_guard_marker_path(engine), {})
    current_head = _head(engine) if engine.is_dir() else None
    state_hash = _sha256_file(state_path) if state_path.is_file() else None
    verified = bool(
        marker
        and marker.get("branch") == _branch(project_id)
        and marker.get("verified_head") == current_head
        and marker.get("verified_state_sha256") == state_hash
    )
    contract = CORE.production_contract()
    states = contract.get("states", [])
    stage = state.get("stage")
    next_stage = None
    if stage in states:
        index = states.index(stage)
        next_stage = states[index + 1] if index + 1 < len(states) else None
    return {
        "ok": True,
        "initialized": engine.is_dir() and project_dir.is_dir(),
        "guard_pass": verified and session.get("guard_result") == "PASS" and session.get("branch") == _branch(project_id),
        "branch": _branch(project_id),
        "stage": stage,
        "next_stage": next_stage,
        "engine_root": str(engine) if engine.is_dir() else None,
        "project_dir": str(project_dir) if project_dir.is_dir() else None,
        "main_commit": session.get("os_main_commit"),
        "session_id": session.get("session_id"),
        "workstation_asset_sync_complete": bool(state.get("workstation_asset_sync_complete")),
        "workstation_asset_count": int(state.get("workstation_asset_count") or 0),
        "workstation_ready_asset_count": int(state.get("workstation_ready_asset_count") or 0),
    }


def run_guard(project_id: str) -> dict:
    current = status(project_id)
    if not current.get("initialized"):
        raise RuntimeError("production workspace is not initialized")
    engine = Path(current["engine_root"])
    session = engine / ".aivideoedit" / "session.json"
    rec = _read_json(session, {})
    if not rec:
        raise RuntimeError("production bootstrap session is missing")
    os_root = Path(rec.get("os_root") or "")
    guard = os_root / "general/reusable/tools/production_guard.py"
    if not guard.is_file():
        raise RuntimeError("bootstrapped production guard is missing")
    env = dict(os.environ)
    env["AIVIDEOEDIT_REPO_ROOT"] = str(engine)
    env["AIVIDEOEDIT_OS_ROOT"] = str(os_root)
    env["AIVIDEOEDIT_PROJECT_DIR"] = f"projects/{_song_slug(project_id)}"
    proc = subprocess.run(
        [sys.executable, str(guard), "--branch", _branch(project_id)],
        cwd=str(engine), env=env, capture_output=True, text=True, timeout=120, check=False,
    )
    if proc.returncode == 0:
        _write_guard_marker(project_id)
    else:
        _clear_guard_marker(engine)
    latest = status(project_id)
    latest.update({
        "ok": proc.returncode == 0,
        "guard_pass": proc.returncode == 0,
        "stdout": (proc.stdout or "")[-4000:],
        "stderr": (proc.stderr or "")[-4000:],
    })
    return latest


def advance(project_id: str, target_stage: str) -> dict:
    current = status(project_id)
    if not current.get("initialized"):
        raise RuntimeError("production workspace is not initialized")
    contract = CORE.production_contract()
    states = contract.get("states", [])
    current_stage = current.get("stage")
    target_stage = str(target_stage or "").strip()
    if current_stage not in states:
        raise RuntimeError(f"current production stage is invalid: {current_stage}")
    if target_stage not in states:
        raise ValueError(f"unknown production stage: {target_stage}")
    current_index = states.index(current_stage)
    if current_index + 1 >= len(states) or states[current_index + 1] != target_stage:
        expected = states[current_index + 1] if current_index + 1 < len(states) else None
        raise ValueError(f"only the next stage may be requested; expected {expected or 'none'}")

    sync = sync_assets(project_id)
    engine = Path(sync["engine_root"])
    project_dir = Path(sync["project_dir"])
    state_path = project_dir / "PROJECT_STATE.json"
    status_path = project_dir / "STATUS.md"
    old_state = state_path.read_text(encoding="utf-8")
    old_status = status_path.read_text(encoding="utf-8") if status_path.is_file() else ""
    state = _read_json(state_path, {})

    if target_stage == "SOURCE_INGESTED":
        with base.LOCK:
            assets = [dict(a) for a in base.STATE["assets"] if a.get("project") == project_id]
        if not assets:
            raise RuntimeError("cannot mark source ingest complete without media")
        incomplete = [a.get("filename") for a in assets if a.get("status") != "ready" or not a.get("sha256")]
        if incomplete:
            raise RuntimeError("source ingest is not complete; media still needs analysis: " + ", ".join(str(x) for x in incomplete[:8]))
        state["source_ingest_complete"] = True

    state["stage"] = target_stage
    state["stage_requested_by"] = "aivideoedit-workstation"
    state["stage_requested_at"] = base.now()
    _write_json(state_path, state)
    status_path.write_text(f"# Status\n\nStage: {target_stage}\n\nPending canonical guard verification.\n", encoding="utf-8")

    guard = run_guard(project_id)
    if not guard.get("guard_pass"):
        state_path.write_text(old_state, encoding="utf-8")
        status_path.write_text(old_status, encoding="utf-8")
        _clear_guard_marker(engine)
        return {
            **status(project_id),
            "ok": False,
            "advanced": False,
            "requested_stage": target_stage,
            "guard_stdout": guard.get("stdout", ""),
            "guard_stderr": guard.get("stderr", ""),
            "error": "canonical production guard rejected the requested stage",
        }

    status_path.write_text(f"# Status\n\nStage: {target_stage}\n\nCanonical production guard: PASS.\n", encoding="utf-8")
    commit = _git_commit_paths(engine, [state_path, status_path], f"Advance production to {target_stage}")
    _write_guard_marker(project_id)
    return {
        **status(project_id),
        "ok": True,
        "advanced": True,
        "requested_stage": target_stage,
        "commit": commit,
        "guard_stdout": guard.get("stdout", ""),
    }
