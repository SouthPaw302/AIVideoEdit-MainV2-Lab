#!/usr/bin/env python3
"""Build and verify one immutable media/engine/source lineage for a render run.

The staging job is the only job allowed to resolve production refs or fetch
media.  Fan-out workers consume the content-addressed bundle and this record;
they never reinterpret moving branches or download alternate source bytes.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit


SCHEMA = "aivideoedit.render-lineage.v1"
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
TOOLCHAIN_PATHS = (
    "scripts/render_lineage.py",
    "scripts/director_harness_gate.py",
    "scripts/prepare_render_shard.py",
    "scripts/plan_render_shards.py",
    "scripts/render_real_music_film.py",
    "scripts/render_real_music_film_shard.py",
    "scripts/assemble_parallel_music_film.py",
    "scripts/release_gate.py",
    ".github/workflows/mainv2-director-parallel-real-render.yml",
    ".github/requirements/render-runner.lock.txt",
    "general/reusable/fx_v2/requirements-runtime.txt",
)


class LineageError(ValueError):
    pass


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fd:
        for block in iter(lambda: fd.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def canonical_sha(value) -> str:
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _git(root: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=False
    )
    if proc.returncode:
        raise LineageError("git identity unavailable: " + (proc.stderr or proc.stdout)[-600:])
    return proc.stdout.strip()


def git_commit(root: Path) -> str:
    value = _git(root, "rev-parse", "HEAD")
    if not HEX40.fullmatch(value):
        raise LineageError("checkout does not have an immutable SHA-1 commit")
    return value


def git_tree(root: Path, project: Path) -> str:
    root = root.resolve()
    project = project.resolve()
    try:
        relative = project.relative_to(root).as_posix()
    except ValueError as exc:
        raise LineageError("project directory escapes source checkout") from exc
    value = _git(root, "rev-parse", "HEAD:" + relative)
    if not HEX40.fullmatch(value):
        raise LineageError("project package is not an immutable tracked git tree")
    return value


def _toolchain(engine: Path) -> tuple[dict[str, str], str]:
    files = {}
    for relative in TOOLCHAIN_PATHS:
        path = engine / relative
        if not path.is_file():
            raise LineageError("required render toolchain file missing: " + relative)
        files[relative] = sha(path)
    return files, canonical_sha(files)


def _runtime_toolchain() -> tuple[dict[str, str], str]:
    proc = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, check=False)
    if proc.returncode or not proc.stdout.strip():
        raise LineageError("pinned FFmpeg runtime is unavailable")
    runtime = {
        "runner_image_os": os.getenv("ImageOS", platform.system()),
        "runner_image_version": os.getenv("ImageVersion", "local"),
        "python": platform.python_version(),
        "ffmpeg": proc.stdout.splitlines()[0].strip(),
    }
    return runtime, canonical_sha(runtime)


def _media_entries(manifest: dict):
    yield "audio", manifest.get("audio")
    for shot in manifest.get("shots") or []:
        yield "shot:" + str(shot.get("id") or ""), shot.get("source")


def _suffix(spec: dict, staged: Path) -> str:
    candidate = Path(urlsplit(str(spec.get("url") or "")).path).suffix or staged.suffix
    candidate = candidate.lower()
    if not re.fullmatch(r"\.[a-z0-9]{1,8}", candidate):
        return ".media"
    return candidate


def _replace_media(manifest: dict, media: dict[str, dict]) -> dict:
    staged = copy.deepcopy(manifest)
    staged["audio"] = {
        **staged["audio"],
        "path": media["audio"]["bundle_path"],
    }
    staged["audio"].pop("url", None)
    for shot in staged["shots"]:
        key = "shot:" + shot["id"]
        shot["source"] = {**shot["source"], "path": media[key]["bundle_path"]}
        shot["source"].pop("url", None)
    return staged


def build_bundle(
    manifest_path: Path,
    input_root: Path,
    engine_root: Path,
    project: Path,
    output: Path,
) -> dict:
    manifest_path = manifest_path.resolve()
    input_root = input_root.resolve()
    engine_root = engine_root.resolve()
    project = project.resolve()
    output = output.resolve()
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise LineageError("render manifest is unavailable or invalid") from exc

    sys.path.insert(0, str(engine_root))
    from scripts.render_real_music_film import stage, validate_manifest

    validate_manifest(manifest)
    source_commit = git_commit(input_root)
    engine_commit = git_commit(engine_root)
    project_tree = git_tree(input_root, project)
    toolchain, toolchain_sha = _toolchain(engine_root)
    runtime, runtime_sha = _runtime_toolchain()
    output.mkdir(parents=True, exist_ok=True)
    objects = output / "objects"
    objects.mkdir(parents=True, exist_ok=True)
    fetch_cache = output / ".fetch-cache"

    media = {}
    for key, spec in _media_entries(manifest):
        if not key or not isinstance(spec, dict):
            raise LineageError("manifest contains a missing media specification")
        expected = str(spec.get("sha256") or "").lower()
        if not HEX64.fullmatch(expected):
            raise LineageError("media is not SHA-256 pinned: " + key)
        source = stage(spec, input_root=input_root, cache=fetch_cache)
        extension = _suffix(spec, source)
        relative = Path("objects") / (expected + extension)
        target = output / relative
        if target.exists() and sha(target) != expected:
            raise LineageError("content-addressed bundle collision: " + key)
        if not target.exists():
            shutil.copyfile(source, target)
        if sha(target) != expected:
            raise LineageError("staged media bytes changed: " + key)
        media[key] = {
            "sha256": expected,
            "bytes": target.stat().st_size,
            "bundle_path": relative.as_posix(),
        }

    staged_manifest = _replace_media(manifest, media)
    staged_manifest["run_lineage"] = {
        "schema": SCHEMA,
        "source_commit_sha": source_commit,
        "engine_commit_sha": engine_commit,
        "source_manifest_sha256": sha(manifest_path),
        "project_tree_git_sha": project_tree,
        "toolchain_sha256": toolchain_sha,
        "runtime_toolchain_sha256": runtime_sha,
    }
    staged_path = output / "STAGED_MANIFEST.json"
    staged_path.write_text(json.dumps(staged_manifest, indent=2) + "\n", encoding="utf-8")
    bundle_identity = [
        {"key": key, **media[key]} for key in sorted(media)
    ]
    lineage = {
        "schema": SCHEMA,
        "production_id": manifest.get("production_id"),
        "source_commit_sha": source_commit,
        "engine_commit_sha": engine_commit,
        "project_tree_git_sha": project_tree,
        "manifest_sha256": sha(manifest_path),
        "staged_manifest_sha256": sha(staged_path),
        "toolchain": toolchain,
        "toolchain_sha256": toolchain_sha,
        "runtime_toolchain": runtime,
        "runtime_toolchain_sha256": runtime_sha,
        "media": media,
        "media_bundle_sha256": canonical_sha(bundle_identity),
        "audio_sha256": media["audio"]["sha256"],
        "clip_sha256": {
            key.removeprefix("shot:"): value["sha256"]
            for key, value in media.items() if key.startswith("shot:")
        },
    }
    (output / "RUN_LINEAGE.json").write_text(
        json.dumps(lineage, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    shutil.rmtree(fetch_cache, ignore_errors=True)
    return lineage


def verify_bundle(
    lineage_path: Path,
    staged_manifest_path: Path,
    media_root: Path,
    *,
    source_root: Path | None = None,
    engine_root: Path | None = None,
    project: Path | None = None,
    original_manifest: Path | None = None,
) -> dict:
    lineage_path = lineage_path.resolve()
    staged_manifest_path = staged_manifest_path.resolve()
    media_root = media_root.resolve()
    try:
        lineage = json.loads(lineage_path.read_text(encoding="utf-8"))
        manifest = json.loads(staged_manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise LineageError("lineage or staged manifest is unavailable") from exc
    if lineage.get("schema") != SCHEMA:
        raise LineageError("unknown render lineage schema")
    for name in ("manifest_sha256", "staged_manifest_sha256", "toolchain_sha256",
                 "media_bundle_sha256", "audio_sha256", "runtime_toolchain_sha256"):
        if not HEX64.fullmatch(str(lineage.get(name) or "")):
            raise LineageError("invalid lineage digest: " + name)
    for name in ("source_commit_sha", "engine_commit_sha", "project_tree_git_sha"):
        if not HEX40.fullmatch(str(lineage.get(name) or "")):
            raise LineageError("invalid immutable git identity: " + name)
    if sha(staged_manifest_path) != lineage["staged_manifest_sha256"]:
        raise LineageError("staged manifest changed after lineage lock")
    declared = manifest.get("run_lineage") or {}
    expected_declared = {
        "schema": SCHEMA,
        "source_commit_sha": lineage["source_commit_sha"],
        "engine_commit_sha": lineage["engine_commit_sha"],
        "source_manifest_sha256": lineage["manifest_sha256"],
        "project_tree_git_sha": lineage["project_tree_git_sha"],
        "toolchain_sha256": lineage["toolchain_sha256"],
        "runtime_toolchain_sha256": lineage["runtime_toolchain_sha256"],
    }
    if declared != expected_declared:
        raise LineageError("staged manifest lineage fields conflict")
    if original_manifest is not None and sha(original_manifest) != lineage["manifest_sha256"]:
        raise LineageError("source manifest changed after lineage lock")
    if source_root is not None and git_commit(source_root) != lineage["source_commit_sha"]:
        raise LineageError("source checkout commit differs from run lineage")
    if engine_root is not None:
        if git_commit(engine_root) != lineage["engine_commit_sha"]:
            raise LineageError("engine checkout commit differs from run lineage")
        toolchain, digest = _toolchain(engine_root.resolve())
        if toolchain != lineage.get("toolchain") or digest != lineage["toolchain_sha256"]:
            raise LineageError("render toolchain differs from run lineage")
        runtime, runtime_digest = _runtime_toolchain()
        if runtime != lineage.get("runtime_toolchain") or runtime_digest != lineage["runtime_toolchain_sha256"]:
            raise LineageError("runner/Python/FFmpeg runtime differs from run lineage")
    if project is not None:
        if source_root is None:
            raise LineageError("project verification requires source checkout")
        if git_tree(source_root, project) != lineage["project_tree_git_sha"]:
            raise LineageError("project package differs from run lineage")

    media = lineage.get("media")
    if not isinstance(media, dict) or not media:
        raise LineageError("lineage has no staged media map")
    identity = []
    for key in sorted(media):
        record = media[key]
        relative = Path(str(record.get("bundle_path") or ""))
        target = (media_root / relative).resolve()
        if relative.is_absolute() or media_root not in target.parents:
            raise LineageError("media bundle path escapes root: " + key)
        if not target.is_file() or sha(target) != record.get("sha256"):
            raise LineageError("missing or wrong-hash staged media: " + key)
        if target.stat().st_size != record.get("bytes"):
            raise LineageError("staged media size changed: " + key)
        identity.append({"key": key, **record})
    if canonical_sha(identity) != lineage["media_bundle_sha256"]:
        raise LineageError("media bundle identity digest conflict")

    manifest_media = dict(_media_entries(manifest))
    if set(manifest_media) != set(media):
        raise LineageError("staged manifest/media map coverage differs")
    for key, spec in manifest_media.items():
        if spec.get("sha256") != media[key]["sha256"] or spec.get("path") != media[key]["bundle_path"]:
            raise LineageError("staged manifest media identity conflict: " + key)
        if spec.get("url"):
            raise LineageError("staged manifest may not re-download media: " + key)
    if lineage["audio_sha256"] != media["audio"]["sha256"]:
        raise LineageError("audio byte identity conflict")
    clips = {
        key.removeprefix("shot:"): value["sha256"]
        for key, value in media.items() if key.startswith("shot:")
    }
    if lineage.get("clip_sha256") != clips:
        raise LineageError("clip byte identity conflict")
    return lineage


def receipt_identity(lineage: dict, lineage_path: Path) -> dict:
    return {
        "lineage_schema": SCHEMA,
        "lineage_sha256": sha(lineage_path),
        "source_commit_sha": lineage["source_commit_sha"],
        "engine_commit_sha": lineage["engine_commit_sha"],
        "project_tree_git_sha": lineage["project_tree_git_sha"],
        "manifest_sha256": lineage["manifest_sha256"],
        "staged_manifest_sha256": lineage["staged_manifest_sha256"],
        "toolchain_sha256": lineage["toolchain_sha256"],
        "runtime_toolchain_sha256": lineage["runtime_toolchain_sha256"],
        "media_bundle_sha256": lineage["media_bundle_sha256"],
    }


def require_receipt_identity(receipt: dict, lineage: dict, lineage_path: Path) -> None:
    for name, expected in receipt_identity(lineage, lineage_path).items():
        if receipt.get(name) != expected:
            raise LineageError("receipt lineage mismatch: " + name)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    stage_parser = sub.add_parser("stage")
    stage_parser.add_argument("--manifest", type=Path, required=True)
    stage_parser.add_argument("--input-root", type=Path, required=True)
    stage_parser.add_argument("--engine-root", type=Path, required=True)
    stage_parser.add_argument("--project", type=Path, required=True)
    stage_parser.add_argument("--out", type=Path, required=True)
    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("--lineage", type=Path, required=True)
    verify_parser.add_argument("--manifest", type=Path, required=True)
    verify_parser.add_argument("--media-root", type=Path, required=True)
    verify_parser.add_argument("--source-root", type=Path)
    verify_parser.add_argument("--engine-root", type=Path)
    verify_parser.add_argument("--project", type=Path)
    verify_parser.add_argument("--original-manifest", type=Path)
    args = parser.parse_args()
    if args.command == "stage":
        result = build_bundle(args.manifest, args.input_root, args.engine_root, args.project, args.out)
        summary = {"result": "PASS", **receipt_identity(result, args.out / "RUN_LINEAGE.json")}
    else:
        result = verify_bundle(
            args.lineage, args.manifest, args.media_root,
            source_root=args.source_root, engine_root=args.engine_root,
            project=args.project, original_manifest=args.original_manifest,
        )
        summary = {"result": "PASS", "lineage": result["media_bundle_sha256"]}
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
