#!/usr/bin/env python3
"""AIVideoEdit portable OS bootstrap.

Every session materializes the entire exact current `main` commit into
`.aivideoedit/os/`, runs current-main fail-closed guards against the active
workspace, attests critical OS hashes, and generates the session Second Brain.
GitHub `main` remains the operating-system authority.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import uuid
from pathlib import Path

REPOSITORY = "SouthPaw302/AIVideoEdit"
DEFAULT_REF = "main"
API_MAIN = f"https://api.github.com/repos/{REPOSITORY}/commits/{DEFAULT_REF}"
SESSION_DIRNAME = ".aivideoedit"
SESSION_SCHEMA = "aivideoedit.session.v1"
BOOT_CAPSULE_SCHEMA = "aivideoedit.boot-capsule.v1"
ATTESTATION_SCHEMA = "aivideoedit.session-attestation.v1"
MANIFEST_PATH = "general/reusable/AIVIDEOEDIT_OS_MANIFEST.json"
CACHE_ARCHIVE = "cache/main.tar.gz"
CACHE_META = "cache/main.json"


def authority_ref() -> str:
    ref = os.environ.get("AIVIDEOEDIT_AUTHORITY_REF", DEFAULT_REF).strip() or DEFAULT_REF
    if ref != DEFAULT_REF and os.environ.get("AIVIDEOEDIT_VALIDATION_MODE") != "1":
        raise SystemExit("BOOTSTRAP FAIL: non-main authority ref requires explicit validation mode.")
    return ref


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def http_bytes(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers={
        "User-Agent": "AIVideoEdit-bootstrap/3",
        "Accept": "application/vnd.github+json, application/octet-stream;q=0.9, */*;q=0.8",
    })
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def git(repo: Path, *args: str) -> str:
    try:
        p = subprocess.run(["git", "-C", str(repo), *args], text=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    except FileNotFoundError:
        return ""
    return p.stdout.strip() if p.returncode == 0 else ""


def find_repo_root(start: Path | None = None) -> Path:
    env = os.environ.get("AIVIDEOEDIT_REPO_ROOT")
    if env:
        p = Path(env).expanduser().resolve()
        if p.is_dir():
            return p
    p = (start or Path.cwd()).expanduser().resolve()
    for cur in [p, *p.parents]:
        if (cur / "README.md").is_file() and (cur / "general/reusable").is_dir():
            return cur
    raise SystemExit("BOOTSTRAP FAIL: AIVideoEdit repository root not found. Use --repo-root.")


def detect_branch(repo: Path, explicit: str | None) -> str:
    if explicit:
        return explicit
    for key in ("AIVIDEOEDIT_BRANCH", "GITHUB_HEAD_REF", "GITHUB_REF_NAME"):
        if os.environ.get(key):
            return os.environ[key]
    branch = git(repo, "branch", "--show-current")
    if branch:
        return branch
    raise SystemExit("BOOTSTRAP FAIL: branch cannot be determined. Use --branch.")


def declared_project_scene_dir(repo: Path, branch: str) -> Path | None:
    """Resolve only explicitly declared project/<slug>/scene-XX production branches."""
    parts = branch.split("/")
    if len(parts) != 3 or parts[0] != "project" or not parts[1]:
        return None
    scene = parts[2]
    suffix = scene.removeprefix("scene-")
    if scene == suffix or not suffix.isdigit() or len(suffix) < 2:
        return None
    project_root = repo / "projects" / parts[1]
    policy = project_root / "PROJECT_BRANCHES.md"
    exact = project_root / "scenes" / scene
    if not policy.is_file() or not (exact / "PROJECT_STATE.json").is_file():
        return None
    try:
        declared = policy.read_text(encoding="utf-8")
    except Exception:
        return None
    if f"`{branch}`" not in declared:
        return None
    return exact.resolve()


def detect_project_dir(repo: Path, branch: str, explicit: str | None) -> Path | None:
    if explicit:
        p = Path(explicit)
        return p.resolve() if p.is_absolute() else (repo / p).resolve()
    env = os.environ.get("AIVIDEOEDIT_PROJECT_DIR")
    if env:
        p = Path(env)
        return p.resolve() if p.is_absolute() else (repo / p).resolve()
    if branch.startswith("song/"):
        exact = repo / "projects" / branch.split("/", 1)[1]
        if (exact / "PROJECT_STATE.json").is_file():
            return exact
    project_scene = declared_project_scene_dir(repo, branch)
    if project_scene is not None:
        return project_scene
    candidates = [p.parent for p in (repo / "projects").glob("*/PROJECT_STATE.json")]
    candidates += [p.parent for p in (repo / "projects").glob("*/scenes/*/PROJECT_STATE.json")]
    return candidates[0] if len(candidates) == 1 else None


def fetch_main_sha(offline: bool, repo: Path) -> tuple[str, str]:
    ref = authority_ref()
    if ref != DEFAULT_REF:
        sha = git(repo, "rev-parse", f"origin/{ref}") or git(repo, "rev-parse", ref) or git(repo, "rev-parse", "HEAD")
        if sha:
            return sha, f"validation-ref:{ref}"
        raise SystemExit(f"BOOTSTRAP FAIL: cannot establish validation authority ref {ref}.")
    if not offline:
        try:
            data = json.loads(http_bytes(API_MAIN).decode("utf-8"))
            sha = str(data.get("sha") or "")
            if sha:
                return sha, "github-main"
        except Exception as exc:
            print(f"BOOTSTRAP: GitHub main lookup unavailable ({exc}); trying local origin/main.", file=sys.stderr)
    sha = git(repo, "rev-parse", "origin/main") or git(repo, "rev-parse", "main")
    if sha:
        return sha, "local-git-main"
    cache_meta = repo / SESSION_DIRNAME / CACHE_META
    cached = read_json_if(cache_meta)
    cached_sha = str(cached.get("main_commit") or "")
    archive = repo / SESSION_DIRNAME / CACHE_ARCHIVE
    if offline and cached_sha and archive.is_file():
        return cached_sha, "cached-main"
    raise SystemExit("BOOTSTRAP FAIL: cannot establish authoritative main commit.")


def safe_extract_tar(tf: tarfile.TarFile, dest: Path, strip_first_component: bool) -> None:
    dest = dest.resolve()
    for member in tf.getmembers():
        parts = Path(member.name).parts
        if strip_first_component:
            if len(parts) <= 1:
                continue
            rel = Path(*parts[1:])
        else:
            rel = Path(*parts)
        if not rel.parts:
            continue
        target = (dest / rel).resolve()
        if target != dest and dest not in target.parents:
            raise SystemExit(f"BOOTSTRAP FAIL: unsafe archive member: {member.name}")
        if member.isdir():
            target.mkdir(parents=True, exist_ok=True)
        elif member.isfile():
            target.parent.mkdir(parents=True, exist_ok=True)
            src = tf.extractfile(member)
            if src is not None:
                target.write_bytes(src.read())


def _cache_paths(repo: Path) -> tuple[Path, Path]:
    root = repo / SESSION_DIRNAME
    return root / CACHE_ARCHIVE, root / CACHE_META


def _write_main_cache(repo: Path, main_sha: str, data: bytes) -> None:
    archive, meta = _cache_paths(repo)
    archive.parent.mkdir(parents=True, exist_ok=True)
    archive.write_bytes(data)
    meta.write_text(json.dumps({
        "schema": "aivideoedit.main-cache.v1",
        "main_commit": main_sha,
        "archive_sha256": sha256_bytes(data),
        "cached_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def materialize_entire_main(repo: Path, os_root: Path, main_sha: str, offline: bool) -> str:
    if offline:
        try:
            p = subprocess.run(["git", "-C", str(repo), "archive", "--format=tar", main_sha],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        except FileNotFoundError:
            p = None
        if p is not None and p.returncode == 0:
            with tarfile.open(fileobj=io.BytesIO(p.stdout), mode="r:") as tf:
                safe_extract_tar(tf, os_root, False)
            return "git-archive"

        archive, meta = _cache_paths(repo)
        cached = read_json_if(meta)
        if archive.is_file() and str(cached.get("main_commit") or "") == main_sha:
            data = archive.read_bytes()
            expected = str(cached.get("archive_sha256") or "")
            if expected and sha256_bytes(data) != expected:
                raise SystemExit("BOOTSTRAP FAIL: cached main archive hash mismatch.")
            with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
                safe_extract_tar(tf, os_root, True)
            return "cached-github-archive"
        raise SystemExit("BOOTSTRAP FAIL: offline boot needs local git main or a verified cached main archive.")

    try:
        data = http_bytes(f"https://codeload.github.com/{REPOSITORY}/tar.gz/{main_sha}", timeout=90)
    except Exception as exc:
        archive, meta = _cache_paths(repo)
        cached = read_json_if(meta)
        if archive.is_file() and str(cached.get("main_commit") or "") == main_sha:
            data = archive.read_bytes()
            expected = str(cached.get("archive_sha256") or "")
            if expected and sha256_bytes(data) != expected:
                raise SystemExit("BOOTSTRAP FAIL: cached main archive hash mismatch.")
            with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
                safe_extract_tar(tf, os_root, True)
            return "cached-github-archive"
        raise SystemExit(f"BOOTSTRAP FAIL: exact current-main OS download failed: {exc}.")
    _write_main_cache(repo, main_sha, data)
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
        safe_extract_tar(tf, os_root, True)
    return "github-archive"


def load_os_manifest(os_root: Path) -> tuple[dict, bytes]:
    path = os_root / MANIFEST_PATH
    if not path.is_file():
        raise SystemExit(f"BOOTSTRAP FAIL: current main lacks {MANIFEST_PATH}")
    raw = path.read_bytes()
    try:
        return json.loads(raw.decode("utf-8")), raw
    except Exception as exc:
        raise SystemExit(f"BOOTSTRAP FAIL: invalid OS manifest: {exc}")


def attest_manifest_files(os_root: Path, manifest: dict) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for rec in manifest.get("files", []):
        rel = rec["path"] if isinstance(rec, dict) else rec
        p = os_root / rel
        if not p.is_file():
            raise SystemExit(f"BOOTSTRAP FAIL: OS manifest file missing from main snapshot: {rel}")
        hashes[rel] = sha256_file(p)
    return hashes


def run_guard(path: Path, args: list[str], env: dict[str, str], label: str) -> None:
    if not path.is_file():
        raise SystemExit(f"BOOTSTRAP FAIL: {label} missing from current main.")
    p = subprocess.run([sys.executable, str(path), *args], env=env, text=True, check=False)
    if p.returncode != 0:
        raise SystemExit(f"BOOTSTRAP FAIL: current-main {label} rejected this workspace.")


def run_bootstrap_guards(repo: Path, os_root: Path, branch: str, project: Path | None) -> None:
    env = os.environ.copy()
    env["AIVIDEOEDIT_REPO_ROOT"] = str(repo)
    env["AIVIDEOEDIT_OS_ROOT"] = str(os_root)
    env["AIVIDEOEDIT_BOOTSTRAP_PHASE"] = "1"
    if project:
        env["AIVIDEOEDIT_PROJECT_DIR"] = str(project.relative_to(repo))
    run_guard(os_root / "general/reusable/tools/production_guard.py",
              ["--branch", branch, "--bootstrap-phase"], env, "production contract")
    recut = os_root / "general/reusable/tools/recut_guard.py"
    if recut.is_file():
        run_guard(recut, ["--branch", branch], env, "recut contract")
    workflow = os_root / "general/reusable/tools/workflow_guard.py"
    if workflow.is_file():
        run_guard(workflow, ["--branch", branch], env, "standard workflow contract")


def handoff_to_current_main_bootstrap(repo: Path, os_root: Path, branch: str, args: argparse.Namespace) -> None:
    if branch == "main" or os.environ.get("AIVIDEOEDIT_BOOTSTRAP_REEXEC") == "1":
        return
    canonical = os_root / "bootstrap.py"
    if not canonical.is_file():
        raise SystemExit("BOOTSTRAP FAIL: current-main snapshot lacks bootstrap.py")
    try:
        same = Path(__file__).resolve().is_file() and sha256_file(Path(__file__).resolve()) == sha256_file(canonical)
    except Exception:
        same = False
    if same:
        return
    cmd = [sys.executable, str(canonical), "boot", "--repo-root", str(repo), "--branch", branch]
    if args.project_dir:
        cmd += ["--project-dir", str(args.project_dir)]
    if args.offline:
        cmd.append("--offline")
    env = os.environ.copy()
    env["AIVIDEOEDIT_BOOTSTRAP_REEXEC"] = "1"
    os.execve(sys.executable, cmd, env)


def read_json_if(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def read_text_if(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def next_stage(contract: dict, stage: str | None) -> str:
    states = contract.get("states", [])
    if stage in states:
        i = states.index(stage)
        return states[i + 1] if i + 1 < len(states) else "COMPLETE"
    return states[0] if states else "UNKNOWN"


def fmt_list(value) -> str:
    return "; ".join(str(x) for x in value) if isinstance(value, list) and value else "none recorded"


def resolve_standard_workflows(os_root: Path, project: Path | None) -> list[str]:
    if project is None:
        return []
    tool = os_root / "general/reusable/tools/workflow_resolver.py"
    if not tool.is_file():
        return []
    p = subprocess.run([sys.executable, str(tool), "--project", str(project), "--json"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if p.returncode != 0:
        return ["ERROR: standard workflow resolution failed"]
    try:
        data = json.loads(p.stdout)
    except Exception:
        return ["ERROR: standard workflow resolver returned invalid JSON"]
    vals = data.get("selected_workflow_names", [])
    return [str(x) for x in vals] if isinstance(vals, list) else []


def build_second_brain(repo: Path, os_root: Path, branch: str, project: Path | None, main_sha: str, session_id: str) -> str:
    contract = read_json_if(os_root / "general/reusable/PRODUCTION_CONTRACT.json")
    prime = read_text_if(os_root / "PRIME_DIRECTIVE.md")
    lines = [
        "# AIVideoEdit Session Second Brain", "",
        "> Generated by `bootstrap.py`. Ephemeral working context; never a separate authority.", "",
        f"- Session: `{session_id}`", f"- Current-main OS commit: `{main_sha}`", f"- Active branch: `{branch}`", "",
        "## PRIME DIRECTIVE", prime or "ERROR: PRIME_DIRECTIVE.md was not readable.", "",
    ]
    if not project:
        lines += ["- Active production: none detected", "", "## Authority",
                  "Current explicit user instruction -> current-main AIVideoEdit OS.",
                  "Do not infer production identity, story, media, or continuity from history."]
        return "\n".join(lines) + "\n"

    state = read_json_if(project / "PROJECT_STATE.json")
    auth = read_json_if(project / "SOURCE_AUTHORITY.json")
    plan = read_json_if(project / "MEDIA_PLAN.json")
    refs = read_json_if(project / "REFERENCE_MANIFEST.json")
    order = read_json_if(project / "OPERATING_ORDER.json")
    stage = state.get("stage")
    allow = [k for k, v in auth.get("allow", {}).items() if v is True]
    deny = [k for k, v in auth.get("allow", {}).items() if v is False]
    lines += ["## ACTIVE PRODUCTION", f"- Project directory: `{project.relative_to(repo).as_posix()}`",
              f"- Director Brain version: `{state.get('director_brain_version', 'legacy')}`",
              f"- Production stage: `{stage or 'UNKNOWN'}`", f"- Next contract stage: `{next_stage(contract, stage)}`", "",
              "## DIRECTOR OPERATING ORDER"]
    if order:
        canon = order.get("canon_lock", {}) if isinstance(order.get("canon_lock"), dict) else {}
        baseline = order.get("accepted_baseline", {}) if isinstance(order.get("accepted_baseline"), dict) else {}
        source = order.get("accepted_source_library", {}) if isinstance(order.get("accepted_source_library"), dict) else {}
        refine = order.get("refinement_scope", {}) if isinstance(order.get("refinement_scope"), dict) else {}
        recut = order.get("recut_scope", {}) if isinstance(order.get("recut_scope"), dict) else {}
        lines += [
            f"- Mission: {order.get('mission') or 'MISSING'}",
            f"- Direction authority: `{order.get('direction_authority') or 'MISSING'}`",
            f"- Production mode: `{order.get('production_mode') or 'MISSING'}`",
            f"- Current user direction: {order.get('current_user_direction') or 'MISSING'}", "",
            "### Canon", f"- Locked: `{canon.get('locked')}`", f"- Picture language: {canon.get('picture_language') or 'none recorded'}",
            f"- Canon items: {fmt_list(canon.get('items'))}", "",
            "### Accepted baseline", f"- Status: `{baseline.get('status') or 'none'}`", f"- File/locator: {baseline.get('file_or_locator') or 'none'}",
            f"- SHA-256: {baseline.get('sha256') or 'none'}", f"- User acceptance: {baseline.get('user_acceptance_statement') or 'none'}", "",
            "### Accepted source library", f"- Status: `{source.get('status') or 'none'}`", f"- Role: `{source.get('role') or 'none'}`",
            f"- File/locator: {source.get('file_or_locator') or 'none'}", f"- SHA-256: {source.get('sha256') or 'none'}",
            f"- User acceptance: {source.get('user_acceptance_statement') or 'none'}",
            f"- Content reuse authorized: `{source.get('content_reuse_authorized')}`", f"- Timeline locked: `{source.get('timeline_locked')}`", "",
            "### Baseline refinement scope", f"- Active: `{refine.get('active')}`", f"- Goal: {refine.get('goal') or 'none'}",
            f"- Allowed changes: {fmt_list(refine.get('allowed_changes'))}", f"- Forbidden changes: {fmt_list(refine.get('forbidden_changes'))}",
            f"- Restart authorized: `{refine.get('restart_authorized')}`", "",
            "### Source-library recut scope", f"- Active: `{recut.get('active')}`", f"- Named defects: {fmt_list(recut.get('named_defects'))}",
            f"- Allowed changes: {fmt_list(recut.get('allowed_changes'))}", f"- Forbidden changes: {fmt_list(recut.get('forbidden_changes'))}",
            f"- Source replacement authorized: `{recut.get('source_replacement_authorized')}`", "",
            "### EXACT NEXT ACTION", order.get("exact_next_action") or "MISSING", "",
        ]
        if refine.get("active") is True and refine.get("restart_authorized") is False:
            lines += ["## DO NOT RESTART", "An accepted baseline is under active refinement. Preserve canon and the baseline. Perform only the allowed changes above unless the current user changes authorization.", ""]
        if recut.get("active") is True and recut.get("source_replacement_authorized") is False:
            lines += ["## PRESERVE SOURCE CANON", "A canonical source library is under defect-first recut. Preserve its approved pixels/world and repair only named defects with traceable source-derived coverage unless the current user changes authorization.", ""]
    else:
        lines += ["OPERATING_ORDER.json not present. This is permitted only for an unmigrated legacy project. Do not invent canon/baseline/source-library/refinement state from history.", ""]
    standard_workflows = resolve_standard_workflows(os_root, project)
    lines += [
        "## Source authority snapshot", "Allowed: " + (", ".join(allow) if allow else "none recorded"), "",
        "Denied: " + (", ".join(deny) if deny else "none recorded"), "",
        "Explicit historical authorizations: " + (", ".join(auth.get("explicit_user_authorizations", [])) or "none"), "",
        "## Media plan", "Selected capabilities: " + (", ".join(plan.get("selected_capabilities", [])) or "not established"), "",
        "## Standard workflow selection", "Selected workflows: " + (", ".join(standard_workflows) or "none resolved"), "",
        "## Reference inventory", f"- Videos: {len(refs.get('videos', []))}", f"- Images: {len(refs.get('images', []))}", "",
        "## Session rule", "Do not advance stage, generate media, select FX, assemble, or claim QC from memory. Use the Prime Directive, active Operating Order, active branch evidence, and current-main OS. Re-run the bootstrapped production, narrative, and recut guards before stage-changing work.",
    ]
    return "\n".join(lines) + "\n"


def _sha256_optional(path: Path) -> str | None:
    return sha256_file(path) if path.is_file() else None


def _stable_json_sha256(value: dict) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256_bytes(raw)


def _project_snapshot(repo: Path, project: Path | None) -> dict:
    if project is None:
        return {
            "project_dir": None,
            "stage": None,
            "exact_next_action": None,
            "project_state_sha256": None,
            "operating_order_sha256": None,
            "reference_manifest_sha256": None,
            "asset_manifest_sha256": None,
            "media_locators": [],
        }

    state_path = project / "PROJECT_STATE.json"
    order_path = project / "OPERATING_ORDER.json"
    refs_path = project / "REFERENCE_MANIFEST.json"
    assets_path = project / "ASSET_MANIFEST.json"
    state = read_json_if(state_path)
    order = read_json_if(order_path)
    exact_next_action = (
        str(order.get("exact_next_action") or "").strip()
        or str(state.get("exact_next_action") or "").strip()
        or None
    )
    media_locators: list[str] = []
    for section in ("accepted_baseline", "accepted_source_library"):
        rec = order.get(section)
        if isinstance(rec, dict):
            locator = str(rec.get("file_or_locator") or "").strip()
            if locator:
                media_locators.append(locator)

    return {
        "project_dir": project.relative_to(repo).as_posix(),
        "stage": state.get("stage"),
        "exact_next_action": exact_next_action,
        "project_state_sha256": _sha256_optional(state_path),
        "operating_order_sha256": _sha256_optional(order_path),
        "reference_manifest_sha256": _sha256_optional(refs_path),
        "asset_manifest_sha256": _sha256_optional(assets_path),
        "media_locators": sorted(set(media_locators)),
    }


def build_boot_capsule(repo: Path, os_root: Path, branch: str, project: Path | None,
                       main_sha: str, session_id: str, manifest_hash: str,
                       file_hashes: dict[str, str], archive_source: str) -> dict:
    project_snapshot = _project_snapshot(repo, project)
    guards = {}
    registries = {}
    for rel in (
        "general/reusable/tools/production_guard.py",
        "general/reusable/tools/narrative_guard.py",
        "general/reusable/tools/recut_guard.py",
        "general/reusable/tools/workflow_guard.py",
    ):
        if rel in file_hashes:
            guards[rel] = file_hashes[rel]
        else:
            digest = _sha256_optional(os_root / rel)
            if digest:
                guards[rel] = digest
    for rel in (
        "general/reusable/PRODUCTION_CONTRACT.json",
        "general/reusable/STANDARD_WORKFLOW_REGISTRY.json",
        "general/reusable/CANONICAL_EFFECT_REGISTRY.json",
        "general/reusable/fx_v2/registry.json",
        "general/reusable/intelligence/MODEL_REGISTRY.json",
    ):
        if rel in file_hashes:
            registries[rel] = file_hashes[rel]
        else:
            digest = _sha256_optional(os_root / rel)
            if digest:
                registries[rel] = digest

    return {
        "schema": BOOT_CAPSULE_SCHEMA,
        "session_id": session_id,
        "repository": REPOSITORY,
        "authority": {
            "ref": authority_ref(),
            "commit": main_sha,
            "manifest_sha256": manifest_hash,
            "archive_source": archive_source,
        },
        "active": {
            "branch": branch,
            **project_snapshot,
        },
        "guards": guards,
        "registries": registries,
    }


def write_boot_capsule(session_dir: Path, capsule: dict) -> tuple[Path, Path]:
    capsule_path = session_dir / "boot_capsule.json"
    capsule_path.write_text(json.dumps(capsule, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    attestation = {
        "schema": ATTESTATION_SCHEMA,
        "session_id": capsule.get("session_id"),
        "capsule_sha256": _stable_json_sha256(capsule),
        "authority_commit": capsule.get("authority", {}).get("commit"),
    }
    attestation_path = session_dir / "session_attestation.json"
    attestation_path.write_text(json.dumps(attestation, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return capsule_path, attestation_path


def write_session(repo: Path, os_root: Path, branch: str, project: Path | None, main_sha: str,
                  os_source: str, archive_source: str, manifest_hash: str, file_hashes: dict[str, str]) -> Path:
    session_dir = repo / SESSION_DIRNAME
    session_id = str(uuid.uuid4())
    order = read_json_if(project / "OPERATING_ORDER.json") if project else {}
    state = read_json_if(project / "PROJECT_STATE.json") if project else {}
    baseline = order.get("accepted_baseline", {}) if isinstance(order.get("accepted_baseline"), dict) else {}
    source = order.get("accepted_source_library", {}) if isinstance(order.get("accepted_source_library"), dict) else {}
    refine = order.get("refinement_scope", {}) if isinstance(order.get("refinement_scope"), dict) else {}
    recut = order.get("recut_scope", {}) if isinstance(order.get("recut_scope"), dict) else {}
    standard_workflows = resolve_standard_workflows(os_root, project) if project else []
    rec = {
        "schema": SESSION_SCHEMA, "session_id": session_id,
        "started_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "repository": REPOSITORY,
        "branch": branch, "project_dir": project.relative_to(repo).as_posix() if project else None,
        "os_main_commit": main_sha, "os_source": os_source, "archive_source": archive_source,
        "os_root": str(os_root), "manifest_sha256": manifest_hash, "os_files": file_hashes, "guard_result": "PASS",
        "director_brain_version": state.get("director_brain_version") if project else None,
        "direction_authority": order.get("direction_authority") if order else None,
        "production_mode": order.get("production_mode") if order else None,
        "accepted_baseline_status": baseline.get("status"), "accepted_source_library_status": source.get("status"),
        "refinement_active": refine.get("active"), "recut_active": recut.get("active"),
        "standard_workflows": standard_workflows,
    }
    path = session_dir / "session.json"
    path.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (session_dir / "SECOND_BRAIN.md").write_text(build_second_brain(repo, os_root, branch, project, main_sha, session_id), encoding="utf-8")
    capsule = build_boot_capsule(
        repo, os_root, branch, project, main_sha, session_id,
        manifest_hash, file_hashes, archive_source,
    )
    capsule_path, attestation_path = write_boot_capsule(session_dir, capsule)
    return path, capsule_path, attestation_path


def clear_volatile_session_state(session_dir: Path) -> None:
    """Keep pinned model cache and downloaded archive intact across bootstrap.

    Model integrity is validated by the model provisioner, not by this helper.
    """
    for child in list(session_dir.iterdir()):
        if child.name in {"cache", "models"}:
            continue
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink()


def boot(args: argparse.Namespace) -> int:
    repo = find_repo_root(Path(args.repo_root) if args.repo_root else None)
    branch = detect_branch(repo, args.branch)
    project = detect_project_dir(repo, branch, args.project_dir)
    session_dir = repo / SESSION_DIRNAME
    os_root = session_dir / "os"
    session_dir.mkdir(parents=True, exist_ok=True)
    clear_volatile_session_state(session_dir)
    os_root.mkdir(parents=True, exist_ok=True)
    main_sha, os_source = fetch_main_sha(args.offline, repo)
    archive_source = materialize_entire_main(repo, os_root, main_sha, args.offline)
    handoff_to_current_main_bootstrap(repo, os_root, branch, args)
    manifest, manifest_bytes = load_os_manifest(os_root)
    file_hashes = attest_manifest_files(os_root, manifest)
    run_bootstrap_guards(repo, os_root, branch, project)
    session_path, capsule_path, attestation_path = write_session(
        repo, os_root, branch, project, main_sha, os_source, archive_source,
        sha256_bytes(manifest_bytes), file_hashes,
    )
    print("AIVideoEdit OS BOOTSTRAP: PASS")
    print(f"main={main_sha}")
    print(f"branch={branch}")
    print(f"os={os_root}")
    print(f"session={session_path}")
    print(f"boot_capsule={capsule_path}")
    print(f"session_attestation={attestation_path}")
    print(f"second_brain={session_dir / 'SECOND_BRAIN.md'}")
    if project:
        print(f"project={project.relative_to(repo)}")
    return 0


def status(args: argparse.Namespace) -> int:
    repo = find_repo_root(Path(args.repo_root) if args.repo_root else None)
    path = repo / SESSION_DIRNAME / "session.json"
    if not path.is_file():
        raise SystemExit("AIVideoEdit OS SESSION: MISSING — run `python bootstrap.py boot`.")
    print(path.read_text(encoding="utf-8"))
    return 0


def install(args: argparse.Namespace) -> int:
    dst = Path(args.workspace).expanduser().resolve()
    if dst.exists() and any(dst.iterdir()):
        raise SystemExit(f"INSTALL FAIL: workspace is not empty: {dst}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    if shutil.which("git"):
        p = subprocess.run(["git", "clone", "--branch", DEFAULT_REF, "--single-branch", f"https://github.com/{REPOSITORY}.git", str(dst)], check=False)
        if p.returncode != 0:
            raise SystemExit("INSTALL FAIL: git clone failed.")
    else:
        data = http_bytes(f"https://codeload.github.com/{REPOSITORY}/tar.gz/refs/heads/{DEFAULT_REF}", timeout=90)
        dst.mkdir(parents=True, exist_ok=True)
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
            safe_extract_tar(tf, dst, True)
    print(f"AIVideoEdit installed at {dst}")
    print(f"Next: {sys.executable} {dst/'bootstrap.py'} boot --repo-root {dst}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="AIVideoEdit portable OS bootstrap")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("boot", help="load exact current-main OS and attest this session")
    b.add_argument("--repo-root"); b.add_argument("--branch"); b.add_argument("--project-dir")
    b.add_argument("--offline", action="store_true", help="materialize exact local origin/main via git archive instead of GitHub")
    b.set_defaults(func=boot)
    s = sub.add_parser("status", help="show current session attestation"); s.add_argument("--repo-root"); s.set_defaults(func=status)
    i = sub.add_parser("install", help="install AIVideoEdit main into an empty sandbox"); i.add_argument("--workspace", required=True); i.set_defaults(func=install)
    args = ap.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
