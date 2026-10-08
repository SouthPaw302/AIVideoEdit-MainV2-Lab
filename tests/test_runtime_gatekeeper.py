from __future__ import annotations

import json
import subprocess
from pathlib import Path

from prototype.backend_gui import runtime_gatekeeper as gate


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def fixture(tmp_path: Path, *, stage="INITIALIZED", canon_locked=False, scope=None):
    engine = tmp_path / "engine"
    project = engine / "projects" / "fixture"
    project.mkdir(parents=True)
    subprocess.run(["git", "init", "-b", "song/fixture", str(engine)], check=True, capture_output=True)

    state = {"stage": stage}
    order = {
        "exact_next_action": "continue fixture",
        "canon_lock": {"locked": canon_locked},
        "refinement_scope": {"active": False},
        "recut_scope": {"active": False},
    }
    if scope:
        order["refinement_scope"] = scope
    write_json(project / "PROJECT_STATE.json", state)
    write_json(project / "OPERATING_ORDER.json", order)

    active = {
        "branch": "song/fixture",
        "project_dir": "projects/fixture",
        "stage": stage,
        "exact_next_action": "continue fixture",
        "project_state_sha256": gate._sha256_file(project / "PROJECT_STATE.json"),
        "operating_order_sha256": gate._sha256_file(project / "OPERATING_ORDER.json"),
    }
    capsule = {
        "schema": "aivideoedit.boot-capsule.v1",
        "session_id": "s1",
        "active": active,
    }
    session = engine / ".aivideoedit"
    write_json(session / "boot_capsule.json", capsule)
    write_json(session / "session_attestation.json", {
        "schema": "aivideoedit.session-attestation.v1",
        "session_id": "s1",
        "capsule_sha256": gate._stable_json_sha256(capsule),
    })
    return engine, project


def test_valid_action_passes(tmp_path: Path):
    engine, project = fixture(tmp_path)
    result = gate.evaluate(
        engine=engine, project_dir=project, branch="song/fixture",
        operation="fixture.mutate", change_tags=["metadata update"],
        expected_stages=["INITIALIZED"],
    )
    assert result["decision"] == "PASS", result


def test_wrong_stage_denied(tmp_path: Path):
    engine, project = fixture(tmp_path, stage="INITIALIZED")
    result = gate.evaluate(
        engine=engine, project_dir=project, branch="song/fixture",
        operation="fixture.mutate", expected_stages=["FX_LOCKED"],
    )
    assert result["decision"] == "DENY"
    assert any("wrong production stage" in x for x in result["errors"])


def test_protected_canon_replacement_denied(tmp_path: Path):
    engine, project = fixture(tmp_path, canon_locked=True)
    result = gate.evaluate(
        engine=engine, project_dir=project, branch="song/fixture",
        operation="fixture.replace", change_tags=["canon.replace"],
    )
    assert result["decision"] == "DENY"
    assert any("protected canon replacement" in x for x in result["errors"])


def test_branch_mismatch_denied(tmp_path: Path):
    engine, project = fixture(tmp_path)
    result = gate.evaluate(
        engine=engine, project_dir=project, branch="song/not-fixture",
        operation="fixture.mutate",
    )
    assert result["decision"] == "DENY"
    assert any("branch mismatch" in x for x in result["errors"])


def test_stale_state_denied(tmp_path: Path):
    engine, project = fixture(tmp_path)
    write_json(project / "PROJECT_STATE.json", {"stage": "SOURCE_INGESTED"})
    result = gate.evaluate(
        engine=engine, project_dir=project, branch="song/fixture",
        operation="fixture.mutate",
    )
    assert result["decision"] == "DENY"
    assert any("changed after boot attestation" in x for x in result["errors"])


def test_active_scope_denies_unlisted_change(tmp_path: Path):
    scope = {
        "active": True,
        "allowed_changes": ["camera amplitude"],
        "forbidden_changes": ["hero imagery"],
    }
    engine, project = fixture(tmp_path, scope=scope)
    result = gate.evaluate(
        engine=engine, project_dir=project, branch="song/fixture",
        operation="fixture.mutate", change_tags=["hero imagery"],
    )
    assert result["decision"] == "DENY"
    assert any("refinement_scope" in x for x in result["errors"])
