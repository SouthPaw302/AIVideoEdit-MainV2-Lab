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
