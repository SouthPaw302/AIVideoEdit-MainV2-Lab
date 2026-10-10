"""Packet 04: generic shard planning, isolated workflow and atomic rebuilds."""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys

import pytest

from scripts.plan_render_shards import plan_shards, validate_plan


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "prototype" / "backend_gui"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
import production_shots  # noqa: E402


@pytest.mark.parametrize(("count", "expected"), [
    (1, [(0, 1)]),
    (9, [(0, 8), (8, 9)]),
    (30, [(0, 8), (8, 16), (16, 24), (24, 30)]),
    (32, [(0, 8), (8, 16), (16, 24), (24, 32)]),
    (33, [(0, 8), (8, 16), (16, 24), (24, 32), (32, 33)]),
])
def test_manifest_size_plans_every_shot_exactly_once(count, expected):
    plan = plan_shards(count, 8)
    validate_plan(plan, count)
    assert [(row["start"], row["end"]) for row in plan["include"]] == expected
    covered = [index for row in plan["include"] for index in range(row["start"], row["end"])]
    assert covered == list(range(count))


@pytest.mark.parametrize(("count", "size"), [(0, 8), (-1, 8), (1, 0), (1, 65)])
def test_invalid_shard_plans_fail_closed(count, size):
    with pytest.raises(ValueError):
        plan_shards(count, size)


@pytest.fixture()
def package_workspace(tmp_path, monkeypatch):
    engine = tmp_path / "engine"
    project = tmp_path / "project"
    engine.mkdir()
    project.mkdir()
    script = {
        "locked": True,
        "entries": [
            {"shot_id": "shot-1", "start_frame": 0, "end_frame": 24},
            {"shot_id": "shot-2", "start_frame": 24, "end_frame": 48},
        ],
    }
    (project / "SCRIPT.json").write_text(json.dumps(script), encoding="utf-8")
    state_path = project / "PROJECT_STATE.json"
    state_path.write_text('{"stage":"STORYBOARD_LOCKED","marker":"old"}\n', encoding="utf-8")
    old_package = project / "shot_packages" / "old-shot" / "package.json"
    old_package.parent.mkdir(parents=True)
    old_package.write_text('{"shot_id":"old-shot","marker":"preserve"}\n', encoding="utf-8")
    current = {"initialized": True, "stage": "STORYBOARD_LOCKED", "project_id": "demo"}
    assets = {
        "asset-1": {"id": "asset-1", "status": "ready", "sha256": "a" * 64,
                    "filename": "one.mp4", "content_type": "video/mp4"},
        "asset-2": {"id": "asset-2", "status": "ready", "sha256": "b" * 64,
                    "filename": "two.mp4", "content_type": "video/mp4"},
    }
    commits = []
    monkeypatch.setattr(production_shots, "_project", lambda _pid: (current, engine, project))
    monkeypatch.setattr(production_shots, "_assets", lambda _pid: assets)
    monkeypatch.setattr(production_shots.base, "now", lambda: "2026-10-10T00:00:00Z")
    monkeypatch.setattr(production_shots.production_project, "_git_commit_paths",
                        lambda _engine, paths, message: commits.append((list(paths), message)) or "c" * 40)
    monkeypatch.setattr(production_shots.production_project, "_clear_guard_marker", lambda _engine: None)
    assignments = [
        {"shot_id": "shot-1", "asset_ids": ["asset-1"]},
        {"shot_id": "shot-2", "asset_ids": ["asset-2"]},
    ]
    return project, state_path, old_package, assignments, commits


def temporary_package_dirs(project):
    return list(project.glob(".shot_packages.*-*"))


def test_validation_failure_preserves_previous_packages(package_workspace, monkeypatch):
    project, state_path, old_package, assignments, commits = package_workspace
    before_state = state_path.read_bytes()
    before_package = old_package.read_bytes()
    monkeypatch.setattr(production_shots.production_storyboard, "run_narrative_guard", lambda _pid: {"ok": True})
    with pytest.raises(ValueError, match="requires at least one"):
        production_shots.build_packages("demo", assignments[:1])
    assert state_path.read_bytes() == before_state
    assert old_package.read_bytes() == before_package
    assert not commits
    assert not temporary_package_dirs(project)


def test_guard_rejection_rolls_back_complete_previous_tree(package_workspace, monkeypatch):
    project, state_path, old_package, assignments, commits = package_workspace
    before_state = state_path.read_bytes()
    before_package = old_package.read_bytes()
    monkeypatch.setattr(production_shots.production_storyboard, "run_narrative_guard",
                        lambda _pid: {"ok": False, "stdout": "rejected"})
    with pytest.raises(RuntimeError, match="narrative guard rejected"):
        production_shots.build_packages("demo", assignments)
    assert state_path.read_bytes() == before_state
    assert old_package.read_bytes() == before_package
    assert not commits
    assert not temporary_package_dirs(project)


def test_success_atomically_replaces_and_commits_complete_tree(package_workspace, monkeypatch):
    project, state_path, old_package, assignments, commits = package_workspace
    monkeypatch.setattr(production_shots.production_storyboard, "run_narrative_guard", lambda _pid: {"ok": True})
    result = production_shots.build_packages("demo", assignments)
    assert not old_package.exists()
    assert (project / "shot_packages" / "shot-1" / "package.json").is_file()
    assert (project / "shot_packages" / "shot-2" / "package.json").is_file()
    state = json.loads(state_path.read_text())
    assert state["shot_package_count"] == 2
    assert state["shot_packages_built"] is True
    assert state["media_evidence_verified"] is True
    assert len(commits) == 1
    assert result["narrative_guard"] == "PASS"
    assert not temporary_package_dirs(project)


def test_canonical_workflow_is_dynamic_isolated_and_least_privilege():
    workflow = (ROOT / ".github/workflows/mainv2-director-parallel-real-render.yml").read_text()
    assert "Canonical Production Candidate" in workflow
    assert "fromJSON(needs.director-gate.outputs.matrix)" in workflow
    assert "start: 24\n            end: 32" not in workflow
    assert "github.ref" not in workflow
    assert "cancel-in-progress: false" in workflow
    assert "permissions:\n  contents: read" in workflow
    assert "publish-review-proof:" in workflow
    assert "contents: write" in workflow
    assert "runs-on: ubuntu-24.04" in workflow
    assert "song/camion" not in workflow.lower()


def test_all_active_github_actions_are_commit_pinned():
    seen = 0
    for path in (ROOT / ".github" / "workflows").glob("*.yml"):
        for line in path.read_text(encoding="utf-8").splitlines():
            if "uses: actions/" not in line:
                continue
            seen += 1
            assert re.search(r"uses: actions/[A-Za-z0-9_.-]+@[0-9a-f]{40}(?:\s|$)", line), (path, line)
    assert seen >= 20


def test_director_gate_has_no_song_specific_creative_requirements():
    source = (ROOT / "scripts/director_harness_gate.py").read_text(encoding="utf-8").lower()
    for forbidden in ("camion", "spanish", "mountain-noir", "truck", "wet asphalt"):
        assert forbidden not in source
