#!/usr/bin/env python3
from __future__ import annotations

import tempfile
from pathlib import Path

from branch_policy import declared_project_scene_dir, project_scene_parts, resolve_production_project


def make_declared_scene(root: Path, branch: str) -> Path:
    project_slug, scene = project_scene_parts(branch) or (None, None)
    assert project_slug and scene
    project = root / "projects" / project_slug
    target = project / "scenes" / scene
    target.mkdir(parents=True)
    (target / "PROJECT_STATE.json").write_text("{}\n", encoding="utf-8")
    (project / "PROJECT_BRANCHES.md").write_text(f"- `{branch}` — declared test scene\n", encoding="utf-8")
    return target.resolve()


def main() -> int:
    assert project_scene_parts("project/american-empire-act1/scene-03") == ("american-empire-act1", "scene-03")
    assert project_scene_parts("project/x/main") is None
    assert project_scene_parts("project/x/scene-three") is None
    assert project_scene_parts("song/x") is None

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        branch = "project/american-empire-act1/scene-03"
        expected = make_declared_scene(root, branch)
        resolved, error = declared_project_scene_dir(root, branch)
        assert error is None and resolved == expected
        resolved, error = resolve_production_project(root, branch)
        assert error is None and resolved == expected

        undeclared = "project/american-empire-act1/scene-04"
        (root / "projects/american-empire-act1/scenes/scene-04").mkdir(parents=True)
        (root / "projects/american-empire-act1/scenes/scene-04/PROJECT_STATE.json").write_text("{}\n", encoding="utf-8")
        resolved, error = resolve_production_project(root, undeclared)
        assert resolved is None and "not explicitly declared" in (error or "")

        resolved, error = resolve_production_project(root, "feature/not-production")
        assert resolved is None and "production work must use" in (error or "")

    print("project scene branch policy tests: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
