#!/usr/bin/env python3
"""Regression tests for canonical source-library recovery/recut support."""
from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


hero = load("test_hero", HERE / "hero_library_extract.py")
qc = load("test_qc", HERE / "refinement_qc_compare.py")
recut = load("test_recut_guard", HERE / "recut_guard.py")
fx = load("test_project_local_fx", HERE.parent / "fx_v2" / "project_local_fx_gate.py")
bootstrap = load("test_bootstrap", ROOT / "bootstrap.py")


def assert_true(value, message):
    if not value:
        raise AssertionError(message)


def source_library(**overrides):
    value = {
        "status": "accepted",
        "role": "hero_library",
        "file_or_locator": "source.mp4",
        "sha256": "a" * 64,
        "user_acceptance_statement": "Use these approved pixels as canon.",
        "content_reuse_authorized": True,
        "timeline_locked": False,
    }
    value.update(overrides)
    return value


def test_accepted_source_library_valid_and_timeline_editable():
    errors = []
    recut.validate_source_library({"accepted_source_library": source_library()}, errors)
    assert_true(not errors, str(errors))
    errors = []
    recut.validate_source_library({"accepted_source_library": source_library(timeline_locked=True)}, errors)
    assert_true(any("timeline_locked=false" in e for e in errors), str(errors))


def test_source_library_hash_and_reuse_authorization_required():
    errors = []
    recut.validate_source_library({"accepted_source_library": source_library(sha256="bad", content_reuse_authorized=False)}, errors)
    assert_true(any("64 hexadecimal" in e for e in errors), str(errors))
    assert_true(any("content_reuse_authorized=true" in e for e in errors), str(errors))


def test_source_library_local_hash_verification():
    with tempfile.TemporaryDirectory() as td:
        project = Path(td)
        (project / "source.mp4").write_bytes(b"actual source")
        errors = []
        recut.validate_source_library({"accepted_source_library": source_library(sha256="a" * 64)}, errors, project)
        assert_true(any("local file hash" in e for e in errors), str(errors))


def test_baseline_semantics_are_separate():
    order = {"accepted_baseline": {"status": "accepted"}, "accepted_source_library": source_library()}
    errors = []
    recut.validate_source_library(order, errors)
    assert_true(not errors and order["accepted_baseline"]["status"] == "accepted", str(errors))


def test_recut_scope_blocks_source_replacement():
    with tempfile.TemporaryDirectory() as td:
        project = Path(td)
        (project / "ASSET_MANIFEST.json").write_text(json.dumps({"assets": [{
            "origin": "source_derived",
            "replaces_source_library": True,
            "provenance": {
                "kind": "source_derived",
                "source_library_sha256": "a" * 64,
                "derivation": "crop/reframe",
                "source_time_seconds": 1.2,
            },
        }]}), encoding="utf-8")
        errors = []
        recut.validate_source_derived_provenance(project, source_library(), {"active": True, "source_replacement_authorized": False}, errors)
        assert_true(any("cannot silently replace" in e for e in errors), str(errors))


def test_source_derived_provenance_matches_canon():
    with tempfile.TemporaryDirectory() as td:
        project = Path(td)
        (project / "ASSET_MANIFEST.json").write_text(json.dumps({"assets": [{
            "origin": "source_derived",
            "provenance": {
                "kind": "source_derived",
                "source_library_sha256": "b" * 64,
                "derivation": "detail extraction",
                "source_range_seconds": [1.0, 1.5],
            },
        }]}), encoding="utf-8")
        errors = []
        recut.validate_source_derived_provenance(project, source_library(), {"active": False}, errors)
        assert_true(any("does not derive" in e for e in errors), str(errors))


def test_backend_substitution_requires_equivalence():
    with tempfile.TemporaryDirectory() as td:
        project = Path(td)
        (project / "RENDER_RECIPE.json").write_text(json.dumps({
            "schema": "aivideoedit.render-recipe.v1",
            "recipe_identity": "r1",
            "proof_backend": "python_opencv",
            "production_backend": "ffmpeg",
            "render_implementation": {"file_or_locator": "render.py", "sha256": "c" * 64},
        }), encoding="utf-8")
        errors = []
        recut.validate_render_recipe(project, errors)
        assert_true(any("equivalence_proof" in e for e in errors), str(errors))


def test_backend_substitution_with_equivalence_passes():
    with tempfile.TemporaryDirectory() as td:
        project = Path(td)
        (project / "RENDER_RECIPE.json").write_text(json.dumps({
            "schema": "aivideoedit.render-recipe.v1",
            "recipe_identity": "r1",
            "proof_backend": "python_opencv",
            "production_backend": "ffmpeg",
            "backend_mapping": {"zoom": "scale expression"},
            "render_implementation": {"file_or_locator": "render.py", "sha256": "c" * 64},
            "equivalence_proof": {
                "status": "PASS",
                "behavior_preserved": True,
                "effects_visible": True,
                "traceable": True,
                "representative_proof": {"file_or_locator": "proof.mp4", "sha256": "d" * 64},
            },
        }), encoding="utf-8")
        errors = []
        recut.validate_render_recipe(project, errors)
        assert_true(not errors, str(errors))


def hero_manifest(source_sha="a" * 64):
    return {
        "schema": hero.SCHEMA,
        "source": {"identity": "source.mp4", "sha256": source_sha},
        "selection": {"candidate_count": 8, "near_duplicate_rejections": 1},
        "entries": [{
            "frame_index": 10,
            "time_seconds": 0.4,
            "frame_sha256": "b" * 64,
            "lifecycle_status": "candidate",
            "source_range_seconds": [0.2, 0.6],
            "visual_signature": {"vector": [0.1, 0.2]},
            "diversity_evidence": {"min_distance_to_selected": 0.2},
        }],
    }


def test_hero_manifest_valid_and_nonempty():
    errors = hero.validate_library_manifest(hero_manifest())
    assert_true(not errors, str(errors))


def test_empty_hero_library_fails():
    manifest = {"schema": hero.SCHEMA, "source": {"identity": "x", "sha256": "a" * 64}, "entries": []}
    errors = hero.validate_library_manifest(manifest)
    assert_true(any("at least one" in e for e in errors), str(errors))


def test_duplicate_heavy_library_warns():
    manifest = {"entries": [{}, {}, {}], "selection": {"candidate_count": 10, "near_duplicate_rejections": 7}}
    warnings = hero.library_warnings(manifest)
    assert_true(any("duplicate-heavy" in w for w in warnings), str(warnings))


def snapshot(result="PASS", runs=0, source_sha="a" * 64):
    return {
        "schema": qc.SNAPSHOT_SCHEMA,
        "runtime_seconds": 120.0,
        "export_variety": {"result": result, "similar_runs_count": runs, "metrics": {"mean_adjacent_similarity": 0.8}},
        "black_freeze": {"result": "PASS"},
        "framing_aspect": {"result": "PASS"},
        "audio_sync": {"result": "PASS"},
        "continuity_warnings": [],
        "mode_aware_qc": {"result": "PASS"},
        "source_canon_integrity": {"result": "PASS", "source_library_sha256": source_sha},
    }


def test_before_after_qc_evidence():
    data = qc.compare_snapshots(snapshot("REVIEW", 3), snapshot("PASS", 0))
    assert_true(data["comparison"]["similar_runs_delta"] == -3, str(data))
    errors = qc.validate_comparison(data, "a" * 64)
    assert_true(not errors, str(errors))


def test_canon_integrity_hash_required():
    data = qc.compare_snapshots(snapshot("REVIEW", 1), snapshot("PASS", 0, "b" * 64))
    errors = qc.validate_comparison(data, "a" * 64)
    assert_true(any("hash does not match" in e for e in errors), str(errors))


def test_project_local_fx_requires_proof_and_lock():
    with tempfile.TemporaryDirectory() as td:
        project = Path(td)
        impl = project / "impl.py"; impl.write_text("print('fx')\n", encoding="utf-8")
        inp = project / "input.dat"; inp.write_text("input", encoding="utf-8")
        proof = project / "proof.dat"; proof.write_text("changed pixels", encoding="utf-8")
        manifest = {
            "schema": fx.SCHEMA,
            "scope": "project_local",
            "effect_id": "local_fx",
            "technology_label": "project-local image transform",
            "truthful_naming": True,
            "placeholder": False,
            "promoted_to_canonical": False,
            "implementation": {"path": "impl.py", "sha256": fx.sha256_file(impl)},
            "render_inputs": [{"path": "input.dat", "sha256": fx.sha256_file(inp)}],
            "deterministic_applicable": True,
            "parameters": {"amount": 0.2},
            "deterministic_parameters": True,
            "proof": {"path": "proof.dat", "sha256": fx.sha256_file(proof), "visible_pixel_change": True},
            "qc": {"status": "PASS", "reviewer": "agent:test"},
        }
        path = project / "local.json"; path.write_text(json.dumps(manifest), encoding="utf-8")
        assert_true(not fx.validate_manifest(manifest, project), str(fx.validate_manifest(manifest, project)))
        lock = fx.make_lock(path, project); lock_path = project / "local.lock.json"; lock_path.write_text(json.dumps(lock), encoding="utf-8")
        assert_true(not fx.validate_lock(path, lock_path, project), str(fx.validate_lock(path, lock_path, project)))
        manifest["proof"]["visible_pixel_change"] = False
        assert_true(any("visible_pixel_change" in e for e in fx.validate_manifest(manifest, project)), "missing proof failure")


def test_second_brain_surfaces_baseline_and_source_library():
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        project = repo / "projects" / "fixture"
        os_root = repo / "os"
        project.mkdir(parents=True)
        (os_root / "general/reusable").mkdir(parents=True)
        (os_root / "general/reusable/PRODUCTION_CONTRACT.json").write_text(json.dumps({"states": ["INITIALIZED", "SOURCE_INGESTED"]}), encoding="utf-8")
        (os_root / "PRIME_DIRECTIVE.md").write_text("Prime", encoding="utf-8")
        (project / "PROJECT_STATE.json").write_text(json.dumps({"director_brain_version": 2, "stage": "INITIALIZED"}), encoding="utf-8")
        (project / "SOURCE_AUTHORITY.json").write_text(json.dumps({"allow": {}}), encoding="utf-8")
        (project / "MEDIA_PLAN.json").write_text(json.dumps({"selected_capabilities": ["canonical_hero_library"]}), encoding="utf-8")
        (project / "REFERENCE_MANIFEST.json").write_text(json.dumps({"videos": [], "images": []}), encoding="utf-8")
        (project / "OPERATING_ORDER.json").write_text(json.dumps({
            "mission": "recut",
            "direction_authority": "user_directed",
            "production_mode": "hybrid",
            "canon_lock": {"locked": True, "picture_language": "approved world", "items": ["world"]},
            "accepted_baseline": {"status": "accepted", "file_or_locator": "master.mp4", "sha256": "b" * 64, "user_acceptance_statement": "keep edit baseline"},
            "accepted_source_library": source_library(),
            "refinement_scope": {"active": False},
            "recut_scope": {"active": True, "named_defects": ["composition repetition"], "allowed_changes": ["coverage"], "forbidden_changes": ["source canon"], "source_replacement_authorized": False},
            "current_user_direction": "recut",
            "exact_next_action": "extract coverage",
        }), encoding="utf-8")
        text = bootstrap.build_second_brain(repo, os_root, "song/fixture", project, "f" * 40, "session")
        assert_true("### Accepted baseline" in text, text)
        assert_true("### Accepted source library" in text, text)
        assert_true("### Source-library recut scope" in text, text)
        assert_true("Content reuse authorized: `True`" in text, text)


def main() -> int:
    tests = [
        test_accepted_source_library_valid_and_timeline_editable,
        test_source_library_hash_and_reuse_authorization_required,
        test_source_library_local_hash_verification,
        test_baseline_semantics_are_separate,
        test_recut_scope_blocks_source_replacement,
        test_source_derived_provenance_matches_canon,
        test_backend_substitution_requires_equivalence,
        test_backend_substitution_with_equivalence_passes,
        test_hero_manifest_valid_and_nonempty,
        test_empty_hero_library_fails,
        test_duplicate_heavy_library_warns,
        test_before_after_qc_evidence,
        test_canon_integrity_hash_required,
        test_project_local_fx_requires_proof_and_lock,
        test_second_brain_surfaces_baseline_and_source_library,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"Recut system regression tests: PASS ({len(tests)} tests)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
