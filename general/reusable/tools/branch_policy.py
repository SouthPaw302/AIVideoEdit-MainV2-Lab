#!/usr/bin/env python3
"""Shared fail-closed production branch resolution for AIVideoEdit."""
from __future__ import annotations

import os
from pathlib import Path


def project_scene_parts(branch: str) -> tuple[str, str] | None:
    parts = branch.split("/")
    if len(parts) != 3 or parts[0] != "project" or not parts[1]:
        return None
    scene = parts[2]
    suffix = scene.removeprefix("scene-")
    if scene == suffix or not suffix.isdigit() or len(suffix) < 2:
        return None
    return parts[1], scene


def declared_project_scene_dir(root: Path, branch: str) -> tuple[Path | None, str | None]:
    parsed = project_scene_parts(branch)
    if parsed is None:
        return None, None
    project_slug, scene = parsed
    project_root = root / "projects" / project_slug
    policy = project_root / "PROJECT_BRANCHES.md"
    exact = project_root / "scenes" / scene
    if not policy.is_file():
        return None, f"declared project scene branch requires {policy.relative_to(root)}"
    try:
        declaration = policy.read_text(encoding="utf-8")
    except Exception as exc:
        return None, f"cannot read project branch policy: {exc}"
    if f"`{branch}`" not in declaration:
        return None, f"project scene branch is not explicitly declared in {policy.relative_to(root)}: {branch}"
    state = exact / "PROJECT_STATE.json"
    if not state.is_file():
        return None, f"declared project scene branch requires {state.relative_to(root)}"
    return exact.resolve(), None


def env_project_dir(root: Path) -> Path | None:
    value = os.environ.get("AIVIDEOEDIT_PROJECT_DIR")
    if not value:
        return None
    p = Path(value)
    return p.resolve() if p.is_absolute() else (root / p).resolve()


def resolve_production_project(root: Path, branch: str) -> tuple[Path | None, str | None]:
    """Resolve song branches or exactly declared project scene branches."""
    env_project = env_project_dir(root)
    if branch.startswith("song/"):
        if env_project is not None:
            return env_project, None
        exact = root / "projects" / branch.split("/", 1)[1]
        if (exact / "PROJECT_STATE.json").is_file():
            return exact.resolve(), None
        candidates = [p.parent.resolve() for p in (root / "projects").glob("*/PROJECT_STATE.json")]
        if len(candidates) == 1:
            return candidates[0], None
        if not candidates:
            return None, "no projects/*/PROJECT_STATE.json found for song branch"
        return None, "multiple project states found for song branch; set AIVIDEOEDIT_PROJECT_DIR"

    project_scene, error = declared_project_scene_dir(root, branch)
    if error:
        return None, error
    if project_scene is not None:
        if env_project is not None and env_project != project_scene:
            return None, f"AIVIDEOEDIT_PROJECT_DIR does not match declared scene directory: {env_project} != {project_scene}"
        return project_scene, None

    return None, f"production work must use song/<slug> or an explicitly declared project/<slug>/scene-XX branch; got {branch}"
