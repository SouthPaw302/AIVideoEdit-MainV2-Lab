#!/usr/bin/env python3
"""Fail-closed sanity check for the independent MainV2 lab."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
lock = json.loads((ROOT / "SOURCE_LOCK.json").read_text(encoding="utf-8"))
assert lock["source_repository"] == "SouthPaw302/AIVideoEdit", "Unexpected authority repository"
assert lock["source_branch"] == "MainV2", "Source branch must be explicit"
assert re.fullmatch(r"[0-9a-f]{40}", lock["source_sha"]), "Source SHA must be pinned"
assert lock["promotion_to_production"] == "FORBIDDEN", "No production writes permitted"
assert lock["synthetic_smoke_is_creative_acceptance"] is False, "Synthetic smoke is not visual acceptance"
assert lock["visual_acceptance"] == "HUMAN_REQUIRED", "Require independent visual approval"
assert lock["baseline_status"] == "UNPROVEN_VISUALLY", "Do not pre-approve a production"
print("LAB_CONTRACT: PASS — scope and source lock are valid; visual approval remains PENDING")

# Production authority is fail-closed even when technical smoke/render checks pass.
production = json.loads((ROOT / "general/reusable/PRODUCTION_CONTRACT.json").read_text(encoding="utf-8"))
policy = production.get("release_gate_policy", {})
for key in ("fail_closed", "full_song_required", "real_source_required",
            "human_verified_comment_required", "actual_export_inspection_required",
            "measured_time_varying_audio_controls_required", "visible_locked_fx_evidence_required",
            "temporal_motion_evidence_required", "transition_continuity_evidence_required",
            "numeric_qc_cannot_grant_artistic_approval",
            "production_contract_is_top_level_authority", "final_master_archive_4k_blocked_without_pass"):
    assert policy.get(key) is True, f"Missing production release policy: {key}"
assert (ROOT / "scripts/release_gate.py").is_file(), "missing release implementation"
assert (ROOT / ".github/workflows/production-final-release.yml").is_file(), "missing gated final delivery"
for flow in (ROOT / ".github/workflows").glob("*.yml"):
    content = flow.read_text(encoding="utf-8")
    if flow.name == "production-final-release.yml":
        assert "scripts/release_gate.py" in content and "gh release create" in content, "ungated final release"
    else:
        # Each technical proof release MUST remain an explicitly marked prerelease.
        for match in re.finditer(r"gh release create\b", content):
            following = content[match.start():match.start() + 1100]
            assert "--prerelease" in following, f"Unprotected release publishing in {flow.name}"
print("PRODUCTION_RELEASE_POLICY: PASS — final/master/archive/4K paths require release authority")
