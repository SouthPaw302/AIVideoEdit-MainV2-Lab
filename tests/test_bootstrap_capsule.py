from __future__ import annotations

import json
from pathlib import Path

import bootstrap


def test_boot_capsule_is_deterministic_for_same_state(tmp_path: Path):
    repo = tmp_path
    os_root = repo / ".aivideoedit" / "os"
    project = repo / "projects" / "fixture"
    os_root.mkdir(parents=True)
    project.mkdir(parents=True)

    (project / "PROJECT_STATE.json").write_text(
        json.dumps({"stage": "INITIALIZED"}), encoding="utf-8"
    )
    (project / "OPERATING_ORDER.json").write_text(
        json.dumps({
            "exact_next_action": "analyze music",
            "accepted_baseline": {"file_or_locator": "blob://baseline"},
            "accepted_source_library": {"file_or_locator": "blob://source"},
        }),
        encoding="utf-8",
    )
    (project / "REFERENCE_MANIFEST.json").write_text("{}", encoding="utf-8")
    (project / "ASSET_MANIFEST.json").write_text("{}", encoding="utf-8")

    a = bootstrap.build_boot_capsule(
        repo, os_root, "song/fixture", project, "abc", "session-1",
        "manifest", {}, "fixture",
    )
    b = bootstrap.build_boot_capsule(
        repo, os_root, "song/fixture", project, "abc", "session-1",
        "manifest", {}, "fixture",
    )
    assert a == b
    assert a["active"]["stage"] == "INITIALIZED"
    assert a["active"]["exact_next_action"] == "analyze music"
    assert a["active"]["media_locators"] == ["blob://baseline", "blob://source"]


def test_attestation_detects_capsule_change(tmp_path: Path):
    capsule = {
        "schema": bootstrap.BOOT_CAPSULE_SCHEMA,
        "session_id": "s1",
        "authority": {"commit": "abc"},
    }
    _, attestation_path = bootstrap.write_boot_capsule(tmp_path, capsule)
    attestation = json.loads(attestation_path.read_text(encoding="utf-8"))
    original = attestation["capsule_sha256"]

    capsule["authority"]["commit"] = "def"
    assert bootstrap._stable_json_sha256(capsule) != original
