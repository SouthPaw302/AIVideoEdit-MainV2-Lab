#!/usr/bin/env python3
"""Storage adapter for the AIVideoEdit alpha stack.

Local workspace is always authoritative during alpha. An optional rclone
remote can mirror project media to R2, B2, S3 or any other rclone-supported
object store without adding a Python cloud SDK dependency.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path


def remote_name() -> str | None:
    value = os.environ.get("AIVE_RCLONE_REMOTE", "").strip().rstrip("/")
    return value or None


def status() -> dict:
    remote = remote_name()
    rclone = shutil.which("rclone")
    return {
        "mode": "rclone" if remote else "local",
        "configured": bool(remote and rclone),
        "remote": remote,
        "rclone_available": bool(rclone),
        "detail": (
            "External mirror ready" if remote and rclone
            else "Set AIVE_RCLONE_REMOTE and install rclone to enable external storage"
            if remote or rclone
            else "Local workspace only"
        ),
    }


def _copy(local: Path, destination: str) -> None:
    rclone = shutil.which("rclone")
    if not rclone:
        raise RuntimeError("rclone is not installed")
    proc = subprocess.run(
        [rclone, "copyto", str(local), destination, "--no-traverse"],
        capture_output=True,
        text=True,
        timeout=7200,
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "rclone copy failed")[-1200:])


def sync_project(project_id: str, assets: list[dict], project_root: Path, progress=None) -> dict:
    remote = remote_name()
    if not remote:
        raise RuntimeError("AIVE_RCLONE_REMOTE is not configured")
    if not shutil.which("rclone"):
        raise RuntimeError("rclone is not installed")

    candidates: list[tuple[Path, str, str]] = []
    for asset in assets:
        folder = Path(asset["folder"])
        asset_id = asset["id"]
        for key, relative in [
            ("source", Path(asset["local_path"]).name),
            ("thumbnail", "thumbnail.jpg"),
            ("proxy", "proxy.mp4"),
        ]:
            local = folder / relative
            if local.is_file():
                candidates.append((local, f"{remote}/{project_id}/assets/{asset_id}/{relative}", key))
        frames = folder / "review_frames"
        if frames.is_dir():
            for local in sorted(frames.glob("*.jpg")):
                candidates.append((local, f"{remote}/{project_id}/assets/{asset_id}/review_frames/{local.name}", "review_frame"))

    total = len(candidates)
    uploaded = []
    for index, (local, destination, kind) in enumerate(candidates, start=1):
        _copy(local, destination)
        uploaded.append({
            "kind": kind,
            "local": str(local),
            "remote": destination,
            "size_bytes": local.stat().st_size,
        })
        if progress:
            progress(index, total, local.name)

    manifest = {
        "schema": "aivideoedit.external-storage.v1",
        "project": project_id,
        "remote": remote,
        "synced_at": time.time(),
        "objects": uploaded,
    }
    project_dir = project_root / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = project_dir / "external_storage_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    _copy(manifest_path, f"{remote}/{project_id}/external_storage_manifest.json")
    return manifest
