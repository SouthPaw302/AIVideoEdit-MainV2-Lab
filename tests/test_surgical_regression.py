from __future__ import annotations

import json
import subprocess
from pathlib import Path

import bootstrap
from general.reusable.tools.harness_router import route_jev
from general.reusable.tools.jev_decision import decide
from prototype.backend_gui import runtime_gatekeeper as gate


FIXTURE = Path("tests/fixtures/surgical/golden_project_state.json")


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def materialize(tmp_path: Path):
    doc=json.loads(FIXTURE.read_text(encoding="utf-8"))
    engine=tmp_path/"engine"
    project=engine/doc["project"]["project_dir"]
    project.mkdir(parents=True)
    subprocess.run(["git","init","-b",doc["project"]["branch"],str(engine)],check=True,capture_output=True)

    write_json(project/"PROJECT_STATE.json",doc["project"]["state"])
    write_json(project/"OPERATING_ORDER.json",doc["project"]["operating_order"])
    write_json(project/"REFERENCE_MANIFEST.json",{"schema":"fixture"})
    write_json(project/"ASSET_MANIFEST.json",{"schema":"fixture"})

    capsule=bootstrap.build_boot_capsule(
        engine,
        engine/".aivideoedit"/"os",
        doc["project"]["branch"],
        project,
        "golden-main-commit",
        "golden-session",
        "golden-manifest",
        {},
        "fixture",
    )
    session=engine/".aivideoedit"
    write_json(session/"boot_capsule.json",capsule)
    write_json(session/"session_attestation.json",{
        "schema":"aivideoedit.session-attestation.v1",
        "session_id":"golden-session",
        "capsule_sha256":bootstrap._stable_json_sha256(capsule),
        "authority_commit":"golden-main-commit",
    })
    return doc,engine,project,capsule


def test_golden_allowed_change_replays_to_continue(tmp_path: Path, monkeypatch):
    doc,engine,project,_=materialize(tmp_path)
    result=gate.evaluate(
        engine=engine,
        project_dir=project,
        branch=doc["project"]["branch"],
        operation="proof.refine",
        change_tags=["camera amplitude"],
    )
    assert result["decision"]==doc["expected"]["allowed_gate"]
    jev=decide({
        "gate":result["decision"],
        "checks":{"attestation":True,"scope":True},
        "next_action_permitted":True,
    })
    assert jev["decision"]==doc["expected"]["jev_after_allowed_gate"]

    monkeypatch.delenv("AIVE_HARNESS_ENABLED",raising=False)
    escalated=route_jev({"decision":"ESCALATE"})
    assert escalated["route"]==doc["expected"]["harness_route_when_disabled"]


def test_golden_forbidden_change_is_denied(tmp_path: Path):
    doc,engine,project,_=materialize(tmp_path)
    result=gate.evaluate(
        engine=engine,
        project_dir=project,
        branch=doc["project"]["branch"],
        operation="proof.replace",
        change_tags=["hero imagery"],
    )
    assert result["decision"]==doc["expected"]["forbidden_gate"]


def test_negative_drift_changes_state_hash_and_denies(tmp_path: Path):
    doc,engine,project,_=materialize(tmp_path)
    state=json.loads((project/"PROJECT_STATE.json").read_text(encoding="utf-8"))
    state["stage"]="FX_LOCKED"
    write_json(project/"PROJECT_STATE.json",state)
    result=gate.evaluate(
        engine=engine,
        project_dir=project,
        branch=doc["project"]["branch"],
        operation="proof.refine",
        change_tags=["camera amplitude"],
    )
    assert result["decision"]=="DENY"
    assert any("changed after boot attestation" in x for x in result["errors"])


def test_boot_capsule_replay_hash_is_stable(tmp_path: Path):
    _,_,_,capsule=materialize(tmp_path)
    first=bootstrap._stable_json_sha256(capsule)
    second=bootstrap._stable_json_sha256(json.loads(json.dumps(capsule)))
    assert first==second
