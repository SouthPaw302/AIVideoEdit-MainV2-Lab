#!/usr/bin/env python3
"""Director scan canon regression tests; no real production is auto-approved."""
import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TOOL = ROOT / "general/reusable/tools/director_scan_gate.py"
spec = importlib.util.spec_from_file_location("director_scan_gate", TOOL)
scan = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scan)

def sample():
    return {
        "schema": "aivideoedit.director-scan.v1",
        "candidate": {
            "locator": "durable://review/current.mp4", "sha256": "a" * 64,
            "branch": "song/example", "commit_sha": "b" * 40,
        },
        "scope": {
            "user_instruction": "Keep approved picture; repair only the named defect",
            "mode": "baseline_refinement", "accepted_baseline_sha256": "c" * 64,
            "allowed_changes": ["intro_outro"], "forbidden_changes": ["core_timeline"],
        },
        "viewing": {
            "method": "sampled", "reviewer": "sandbox_director",
            "entire_normal_speed": False,
        },
        "checks": {
            k: {"status": "pass", "evidence": [f"verified://{k}/proof"], "notes": ""}
            for k in scan.CHECKS
        },
        "verdict": {
            "technical": "pass", "artistic": "pending",
            "authenticated_release": "pending", "caveats": [],
            "notes": "Actual playthrough and human acceptance still pending",
        },
    }


class DirectorScanEvidenceTests(unittest.TestCase):
    def test_schema_contract_is_current_and_contains_every_check(self):
        schema = json.loads((ROOT / "general/reusable/DIRECTOR_SCAN_RECORD.schema.json").read_text())
        self.assertEqual(schema["properties"]["schema"]["const"], scan.SCHEMA)
        self.assertEqual(set(schema["properties"]["checks"]["required"]), set(scan.CHECKS))

    def test_complete_evidence_does_not_grant_artistic_pass(self):
        data = sample()
        self.assertEqual(scan.verify_record(data), [])
        self.assertEqual(data["verdict"]["artistic"], "pending")

    def test_missing_source_audit_fails(self):
        data = sample(); del data["checks"]["source_fidelity"]
        self.assertTrue(scan.verify_record(data))

    def test_claimed_green_fx_without_evidence_fails(self):
        data = sample(); data["checks"]["fx_actual_and_relevance"]["evidence"] = []
        self.assertTrue(any("concrete evidence" in e for e in scan.verify_record(data)))

    def test_sampled_review_cannot_claim_full_watch(self):
        data = sample(); data["viewing"]["entire_normal_speed"] = True
        self.assertTrue(any("whole-film" in e for e in scan.verify_record(data)))

    def test_accepted_with_caveats_must_name_caveats(self):
        data = sample(); data["verdict"]["artistic"] = "accepted_with_caveats"
        self.assertTrue(any("named caveats" in e for e in scan.verify_record(data)))

    def test_failing_motion_check_cannot_be_called_accepted(self):
        data = sample(); data["verdict"]["artistic"] = "accepted"
        data["checks"]["semantic_motion"]["status"] = "fail"
        self.assertTrue(any("contradicts" in e for e in scan.verify_record(data)))

    def test_not_applicable_must_explain(self):
        data = sample(); data["checks"]["baseline_comparison"] = {
            "status": "not_applicable", "evidence": [], "notes": ""}
        self.assertTrue(any("rationale" in e for e in scan.verify_record(data)))

    def test_do_not_forge_authenticated_release(self):
        data = sample(); data["verdict"]["authenticated_release"] = "pass"
        self.assertTrue(any("not the authenticated release gate" in e for e in scan.verify_record(data)))

    def test_accepted_baseline_sha_required_for_finishing(self):
        data = sample(); data["scope"]["mode"] = "finishing"
        data["scope"]["accepted_baseline_sha256"] = None
        self.assertTrue(any("locked baseline" in e for e in scan.verify_record(data)))

if __name__ == "__main__":
    unittest.main()
