#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
MODULE_PATH = HERE / "recipe_execution_guard.py"
spec = importlib.util.spec_from_file_location("aivideoedit_recipe_execution_guard", MODULE_PATH)
if spec is None or spec.loader is None:
    raise SystemExit("TEST FAIL: cannot load recipe execution guard")
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

STATES = [
    "INITIALIZED", "SOURCE_INGESTED", "REFERENCES_ANALYZED", "APPROACH_ESTABLISHED",
    "STORYBOARD_LOCKED", "SHOT_PACKAGES_BUILT", "SHOT_PROOFS_ACCEPTED", "FX_LOCKED",
    "ASSEMBLED", "FINAL_QC_PASSED", "ARCHIVED",
]
SHA = "a" * 64
ORDER = {"direction_authority": "music_led", "production_mode": "living_scene"}
STATE = {"director_brain_version": 3}


def write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def fixture(project: Path) -> None:
    write(project / "RENDER_RECIPE.json", {
        "execution_profile": {
            "id": "music_directed_section_assembly",
            "music_control_map": "MUSIC_CONTROL_MAP.json",
            "section_manifest": "SECTION_RENDER_MANIFEST.json",
            "application_proof": "FX_APPLICATION_PROOF.json",
            "variation_policy": {"intent": "Vary internal motion and light with the music."},
        }
    })
    write(project / "MUSIC_CONTROL_MAP.json", {
        "schema": "aivideoedit.music-control-map.v1", "audio_sha256": SHA,
        "sections": [{"id": "S01", "start_frame": 0, "end_frame": 240, "controls": {"rms": "bounded"}}],
    })
    proof = {"file_or_locator": "artifact://proof", "sha256": SHA}
    write(project / "SECTION_RENDER_MANIFEST.json", {
        "schema": "aivideoedit.section-render-manifest.v1",
        "sections": [{"id": "S01", "scene_profile": "reflection_drift", "passes": {
            "base": {"status": "rendered", "proof": proof},
            "reactive": {"status": "rendered", "proof": proof},
            "fill": {"status": "not_applicable", "reason": "The restrained opening needs no detail overlay."},
            "transition": {"status": "not_applicable", "reason": "Single-section proof has no outgoing join."},
        }}],
    })
    write(project / "fx.lock.json", {"effects": [{"id": "FX2-MOTION-002"}]})
    write(project / "FX_APPLICATION_PROOF.json", {
        "schema": "aivideoedit.fx-application-proof.v1",
        "applications": [{
            "section_id": "S01", "effect_id": "FX2-MOTION-002",
            "output": {"file_or_locator": "artifact://section", "sha256": SHA},
            "visible_change": {"status": "PASS", "source_delta": 1.2},
        }],
        "assembly": {"status": "PASS", "file_or_locator": "artifact://assembly", "sha256": SHA},
        "final_qc": {"status": "PASS", "effect_coverage": "PASS"},
    })


def validate(project: Path, stage: str) -> list[str]:
    errors: list[str] = []
    guard.validate(project, STATE, ORDER, stage, STATES, errors)
    return errors


def test_missing_recipe_fails() -> None:
    with tempfile.TemporaryDirectory() as td:
        errors = validate(Path(td), "APPROACH_ESTABLISHED")
        assert any("RENDER_RECIPE" in error for error in errors), errors


def test_complete_recipe_passes() -> None:
    with tempfile.TemporaryDirectory() as td:
        project = Path(td)
        fixture(project)
        assert not validate(project, "FINAL_QC_PASSED"), validate(project, "FINAL_QC_PASSED")


def test_uncovered_lock_fails() -> None:
    with tempfile.TemporaryDirectory() as td:
        project = Path(td)
        fixture(project)
        write(project / "fx.lock.json", {"effects": [{"id": "FX2-LIGHT-001"}]})
        errors = validate(project, "FX_LOCKED")
        assert any("does not cover locked effects" in error for error in errors), errors


def main() -> int:
    tests = [test_missing_recipe_fails, test_complete_recipe_passes, test_uncovered_lock_fails]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"Recipe execution guard tests: PASS ({len(tests)} tests)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
