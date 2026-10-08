#!/usr/bin/env python3
"""Small regression suite for Director Brain v3 guard behavior."""
from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
GUARD_PATH = HERE / "production_guard.py"
MODES_PATH = HERE.parent / "PRODUCTION_MODES.json"
CONTRACT_PATH = HERE.parent / "PRODUCTION_CONTRACT.json"

spec = importlib.util.spec_from_file_location("aivideoedit_production_guard", GUARD_PATH)
if spec is None or spec.loader is None:
    raise SystemExit("TEST FAIL: cannot import production_guard.py")
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

MODES = json.loads(MODES_PATH.read_text(encoding="utf-8"))
CONTRACT = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
STATES = CONTRACT["states"]


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def base_order(mode: str = "living_scene") -> dict:
    return {
        "schema": "aivideoedit.operating-order.v1",
        "mission": "Create the selected visual experience and preserve approved work.",
        "direction_authority": "music_led",
        "production_mode": mode,
        "canon_lock": {
            "locked": False,
            "picture_language": "Not locked yet.",
            "items": []
        },
        "accepted_baseline": {
            "status": "none",
            "file_or_locator": None,
            "sha256": None,
            "user_acceptance_statement": None
        },
        "refinement_scope": {
            "active": False,
            "goal": None,
            "allowed_changes": [],
            "forbidden_changes": [],
            "restart_authorized": False
        },
        "current_user_direction": "Continue the selected route.",
        "exact_next_action": "Build the next required proof.",
        "updated_at_utc": None
    }


def validate_order(project: Path, state: dict, stage: str) -> list[str]:
    errors: list[str] = []
    guard.validate_operating_order(project, state, stage, STATES, MODES, errors)
    return errors


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_missing_order_fails() -> None:
    with tempfile.TemporaryDirectory() as td:
        project = Path(td)
        errors = validate_order(project, {"director_brain_version": 2}, "INITIALIZED")
        assert_true(any("requires OPERATING_ORDER.json" in e for e in errors), str(errors))


def test_valid_initial_order_passes() -> None:
    with tempfile.TemporaryDirectory() as td:
        project = Path(td)
        write_json(project / "OPERATING_ORDER.json", base_order())
        errors = validate_order(project, {"director_brain_version": 2}, "INITIALIZED")
        assert_true(not errors, str(errors))


def test_invalid_mode_fails() -> None:
    with tempfile.TemporaryDirectory() as td:
        project = Path(td)
        order = base_order("generic_ai_video")
        write_json(project / "OPERATING_ORDER.json", order)
        errors = validate_order(project, {"director_brain_version": 2}, "INITIALIZED")
        assert_true(any("production_mode" in e for e in errors), str(errors))


def test_accepted_refinement_passes() -> None:
    with tempfile.TemporaryDirectory() as td:
        project = Path(td)
        order = base_order()
        order["canon_lock"] = {
            "locked": True,
            "picture_language": "Stable authored world with internal material motion.",
            "items": ["hero_01", "shot timing"]
        }
        order["accepted_baseline"] = {
            "status": "accepted",
            "file_or_locator": "remote://accepted-master",
            "sha256": "a" * 64,
            "user_acceptance_statement": "Keep this baseline and improve the named defect."
        }
        order["refinement_scope"] = {
            "active": True,
            "goal": "Reduce camera shake while preserving the picture.",
            "allowed_changes": ["camera amplitude"],
            "forbidden_changes": ["hero imagery", "timing", "picture language"],
            "restart_authorized": False
        }
        write_json(project / "OPERATING_ORDER.json", order)
        errors = validate_order(project, {"director_brain_version": 2}, "INITIALIZED")
        assert_true(not errors, str(errors))


def test_refinement_without_baseline_fails() -> None:
    with tempfile.TemporaryDirectory() as td:
        project = Path(td)
        order = base_order()
        order["refinement_scope"] = {
            "active": True,
            "goal": "Repair one defect.",
            "allowed_changes": ["defect"],
            "forbidden_changes": ["everything else"],
            "restart_authorized": False
        }
        write_json(project / "OPERATING_ORDER.json", order)
        errors = validate_order(project, {"director_brain_version": 2}, "INITIALIZED")
        assert_true(any("accepted_baseline.status=accepted" in e for e in errors), str(errors))


def test_living_scene_requires_semantic_regions() -> None:
    with tempfile.TemporaryDirectory() as td:
        project = Path(td)
        write_json(project / "OPERATING_ORDER.json", base_order("living_scene"))
        write_json(project / "SCRIPT.json", {
            "entries": [{
                "shot_id": "S01",
                "start_frame": 0,
                "end_frame": 23,
                "visual_media": "hero plate",
                "animation_behavior": "animate",
                "music_cues": ["pulse"],
                "transition": "cut"
            }]
        })
        state = {"director_brain_version": 2}
        errors = validate_order(project, state, "STORYBOARD_LOCKED")
        assert_true(any("motion_regions" in e for e in errors), str(errors))
        assert_true(any("protected_regions" in e for e in errors), str(errors))


def test_mode_aware_acceptance_flags_required() -> None:
    with tempfile.TemporaryDirectory() as td:
        project = Path(td)
        write_json(project / "OPERATING_ORDER.json", base_order("cinematic"))
        errors = validate_order(project, {"director_brain_version": 2}, "SHOT_PROOFS_ACCEPTED")
        assert_true(any("mode_aware_proofs_accepted" in e for e in errors), str(errors))


def main() -> int:
    tests = [
        test_missing_order_fails,
        test_valid_initial_order_passes,
        test_invalid_mode_fails,
        test_accepted_refinement_passes,
        test_refinement_without_baseline_fails,
        test_living_scene_requires_semantic_regions,
        test_mode_aware_acceptance_flags_required,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"Director Brain regression tests: PASS ({len(tests)} tests)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
