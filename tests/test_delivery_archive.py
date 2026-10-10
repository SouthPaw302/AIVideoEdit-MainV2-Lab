from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "delivery_archive", ROOT / "prototype/backend_gui/delivery_archive.py"
)
delivery_archive = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(delivery_archive)


def manifest():
    return json.loads(
        (ROOT / "docs/director-case-studies/EL_CAMION_DELIVERY_ARCHIVE.json").read_text(
            encoding="utf-8"
        )
    )


def artifact(payload, artifact_id):
    return next(item for item in payload["artifacts"] if item["id"] == artifact_id)


def test_camion_content_addressed_delivery_archive_is_valid():
    assert delivery_archive.validate_manifest(manifest()) == []


def test_proxy_derived_4k_cannot_be_promoted_to_release_master():
    payload = manifest()
    artifact(payload, "local-review-upscale-4k")["release_eligible"] = True
    assert "release-eligible 4K must derive directly from the accepted master" in delivery_archive.validate_manifest(payload)


def test_transfer_parts_are_nonplayable_and_cover_exact_master_bytes():
    payload = manifest()
    master = artifact(payload, "artistic-master-1080")
    assert master["directly_playable"] is False
    assert sum(part["size_bytes"] for part in master["parts"]) == master["size_bytes"]
    master["parts"][0]["size_bytes"] -= 1
    assert any("transfer-part byte total" in error for error in delivery_archive.validate_manifest(payload))


def test_release_state_requires_authenticated_exact_hash_approval():
    payload = manifest()
    payload["lifecycle"]["history"].append({"state": "RELEASE_AUTHORIZED"})
    payload["lifecycle"]["state"] = "RELEASE_AUTHORIZED"
    assert any("authenticated approval" in error for error in delivery_archive.validate_manifest(payload))


def test_lifecycle_rejects_illegal_release_shortcut():
    payload = manifest()
    payload["lifecycle"] = {
        "state": "RELEASED",
        "history": [{"state": "DIRECTOR_RECOMMENDED"}, {"state": "RELEASED"}],
    }
    assert any("illegal lifecycle transition" in error for error in delivery_archive.validate_manifest(payload))


def test_full_duration_title_safe_area_and_audio_sync_are_fail_closed():
    for mutate, expected in (
        (lambda p: p["timeline"]["section_frames"].update({"silent_outro": 95}), "section frames"),
        (lambda p: p["title_qc"].update({"safe_area_pass": False}), "title safe-area"),
        (lambda p: p["audio_qc"].update({"best_lag_samples": 1}), "audio sync"),
    ):
        payload = copy.deepcopy(manifest())
        mutate(payload)
        assert any(expected in error for error in delivery_archive.validate_manifest(payload))


def test_archive_backend_records_lifecycle_and_content_addressed_artifacts():
    source = (ROOT / "prototype/backend_gui/production_archive.py").read_text(encoding="utf-8")
    assert '"schema":"aivideoedit.archive-manifest.v2"' in source
    assert '"delivery_lifecycle":lifecycle' in source
    assert '"artifacts":artifacts' in source
    assert '"authenticated":True' in source


def test_contract_names_every_delivery_state_and_direct_master_4k_rule():
    contract = json.loads((ROOT / "general/reusable/PRODUCTION_CONTRACT.json").read_text())
    assert contract["delivery_lifecycle_policy"]["states"] == list(delivery_archive.LIFECYCLE_STATES)
    assert contract["delivery_mastering_policy"]["release_eligible_4k_parent_must_be_exact_accepted_artistic_master"] is True
