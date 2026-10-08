#!/usr/bin/env python3
"""AIVideoEdit GitHub Releases media storage adapter.

Stores large song-production media as release assets while GitHub branches keep
the manifests and production state.

Requires the GitHub CLI (`gh`) authenticated for the repository.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

DEFAULT_REPO = "SouthPaw302/AIVideoEdit"
CATEGORIES = ("source", "generated", "proofs", "final", "qc", "archive")
MAX_ASSET_BYTES = 2 * 1024 * 1024 * 1024  # GitHub release asset limit: 2 GiB.


def fail(message: str, code: int = 2) -> "NoReturn":
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(code)


def run_gh(args: list[str], *, capture: bool = True) -> str:
    if shutil.which("gh") is None:
        fail("GitHub CLI `gh` is not installed or not on PATH.")
    proc = subprocess.run(
        ["gh", *args],
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        fail(detail or f"`gh {' '.join(args)}` failed with exit code {proc.returncode}.")
    return (proc.stdout or "").strip()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def release_tag(slug: str) -> str:
    return f"media-{slug}"


def release_url(repo: str, slug: str) -> str:
    return f"https://github.com/{repo}/releases/tag/{release_tag(slug)}"


def ensure_release(repo: str, slug: str, branch: str) -> None:
    if shutil.which("gh") is None:
        fail("GitHub CLI `gh` is not installed or not on PATH.")
    tag = release_tag(slug)
    check = subprocess.run(
        ["gh", "release", "view", tag, "--repo", repo],
        text=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if check.returncode == 0:
        return
    run_gh(
        [
            "release",
            "create",
            tag,
            "--repo",
            repo,
            "--target",
            branch,
            "--title",
            f"AIVideoEdit Media: {slug}",
            "--notes",
            (
                "Durable media storage for this AIVideoEdit song production. "
                "Production state and manifests remain on the song branch."
            ),
        ]
    )


def load_manifest(path: Path, repo: str, slug: str, branch: str) -> dict:
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("schema") != "aivideoedit.storage-manifest.v1":
            fail(f"{path} is not an AIVideoEdit storage manifest.")
        return data
    return {
        "schema": "aivideoedit.storage-manifest.v1",
        "provider": "github_releases",
        "repository": repo,
        "song_slug": slug,
        "branch": branch,
        "release_tag": release_tag(slug),
        "release_url": release_url(repo, slug),
        "assets": [],
    }


def save_manifest(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def command_init(args: argparse.Namespace) -> None:
    ensure_release(args.repo, args.slug, args.branch)
    manifest = load_manifest(args.manifest, args.repo, args.slug, args.branch)
    save_manifest(args.manifest, manifest)
    print(f"READY {release_url(args.repo, args.slug)}")
    print(f"MANIFEST {args.manifest}")


def command_upload(args: argparse.Namespace) -> None:
    src = args.file.resolve()
    if not src.is_file():
        fail(f"File not found: {src}")
    size = src.stat().st_size
    if size > MAX_ASSET_BYTES:
        fail(
            f"{src.name} is {size} bytes, over GitHub Releases' 2 GiB per-asset limit. "
            "Split/archive it before upload."
        )

    ensure_release(args.repo, args.slug, args.branch)
    asset_name = f"{args.category}__{src.name}"
    digest = sha256_file(src)

    with tempfile.TemporaryDirectory(prefix="aivideoedit-release-") as tmp:
        staged = Path(tmp) / asset_name
        try:
            os.link(src, staged)
        except OSError:
            shutil.copy2(src, staged)
        run_gh(
            [
                "release",
                "upload",
                release_tag(args.slug),
                str(staged),
                "--repo",
                args.repo,
                "--clobber",
            ]
        )

    manifest = load_manifest(args.manifest, args.repo, args.slug, args.branch)
    record = {
        "category": args.category,
        "asset_name": asset_name,
        "original_name": src.name,
        "sha256": digest,
        "bytes": size,
        "uploaded_at_utc": now_utc(),
    }
    assets = [a for a in manifest.get("assets", []) if a.get("asset_name") != asset_name]
    assets.append(record)
    assets.sort(key=lambda a: (a.get("category", ""), a.get("asset_name", "")))
    manifest["assets"] = assets
    manifest["release_url"] = release_url(args.repo, args.slug)
    save_manifest(args.manifest, manifest)

    print(f"UPLOADED {asset_name}")
    print(f"SHA256 {digest}")
    print(f"RELEASE {manifest['release_url']}")
    print(f"MANIFEST {args.manifest}")


def command_list(args: argparse.Namespace) -> None:
    output = run_gh(
        [
            "release",
            "view",
            release_tag(args.slug),
            "--repo",
            args.repo,
            "--json",
            "url,tagName,assets",
        ]
    )
    print(output)


def command_download(args: argparse.Namespace) -> None:
    args.output.mkdir(parents=True, exist_ok=True)
    pattern = args.pattern or "*"
    run_gh(
        [
            "release",
            "download",
            release_tag(args.slug),
            "--repo",
            args.repo,
            "--pattern",
            pattern,
            "--dir",
            str(args.output),
            "--clobber",
        ],
        capture=False,
    )


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Store AIVideoEdit song media in GitHub Releases.")
    p.add_argument("--repo", default=DEFAULT_REPO, help=f"GitHub repository (default: {DEFAULT_REPO})")
    sub = p.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Create the song media release and storage manifest.")
    init.add_argument("--slug", required=True)
    init.add_argument("--branch", required=True, help="Song branch, normally song/<slug>.")
    init.add_argument("--manifest", type=Path, required=True)
    init.set_defaults(func=command_init)

    upload = sub.add_parser("upload", help="Upload one categorized release asset.")
    upload.add_argument("--slug", required=True)
    upload.add_argument("--branch", required=True, help="Song branch, normally song/<slug>.")
    upload.add_argument("--category", choices=CATEGORIES, required=True)
    upload.add_argument("--file", type=Path, required=True)
    upload.add_argument("--manifest", type=Path, required=True)
    upload.set_defaults(func=command_upload)

    ls = sub.add_parser("list", help="List the remote release and assets as JSON.")
    ls.add_argument("--slug", required=True)
    ls.set_defaults(func=command_list)

    dl = sub.add_parser("download", help="Download assets from the song media release.")
    dl.add_argument("--slug", required=True)
    dl.add_argument("--pattern", help="Asset glob, e.g. 'final__*'. Defaults to all assets.")
    dl.add_argument("--output", type=Path, required=True)
    dl.set_defaults(func=command_download)

    return p


def main() -> int:
    args = parser().parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
