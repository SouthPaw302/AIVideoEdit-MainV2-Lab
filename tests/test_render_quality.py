"""Packet 05: audio-reactive FX, real motion, source quality, and seam evidence."""
from __future__ import annotations

import copy
from pathlib import Path

import numpy as np
import pytest

from scripts.render_quality import (
    AudioControls,
    QualityCollector,
    QualityError,
    bundle_fx_proofs,
    combine_visual_evidence,
    inspect_source_media,
    transition_prerolls,
)

ROOT = Path(__file__).resolve().parents[1]


def controls():
    return {
        "audio_controls": {
            "source": "decoded_pcm_rms_flux",
            "points": [
                {"seconds": 0, "energy": 0.1, "transient": 0.0},
                {"seconds": 0.5, "energy": 0.9, "transient": 1.0},
                {"seconds": 1.0, "energy": 0.3, "transient": 0.1},
            ],
        }
    }


def test_measured_controls_interpolate_and_constant_controls_fail_closed():
    track = AudioControls(controls())
    assert track.at(0.25) == pytest.approx((0.5, 0.5))
    assert track.summary(24)["time_varying"] is True
    flat = controls()
    for point in flat["audio_controls"]["points"]:
        point.update(energy=0.2, transient=0.2)
    with pytest.raises(QualityError, match="constant"):
        AudioControls(flat)


def test_transition_preroll_consumes_preview_instead_of_restarting_source():
    shots = [
        {"id": "a", "duration_seconds": 2, "transition_out": "wipe", "transition_seconds": 0.5},
        {"id": "b", "duration_seconds": 2},
    ]
    assert transition_prerolls(shots) == [0.0, 0.5]
    assert transition_prerolls([shots[1]], first_preroll=0.5) == [0.5]


def test_visible_fx_motion_and_transition_seam_produce_evidence_only_pass(tmp_path):
    shots = [
        {"id": "a", "source": {"path": "a.mp4"}, "duration_seconds": 1,
         "transition_out": "tr", "transition_seconds": 0.5},
        {"id": "b", "source": {"path": "b.mp4"}, "duration_seconds": 1},
    ]
    proof_dir = tmp_path / "proofs"
    collector = QualityCollector(4, shots, proof_dir=proof_dir)
    last = None
    for shot_id in ("a", "b"):
        for index in range(4):
            frame = np.zeros((90, 160, 3), np.uint8)
            x = index * 8 if shot_id == "a" else 24 + index * 8
            frame[30:55, x:x + 20] = 120
            if shot_id == "b" and index == 0:
                frame = last.copy()
            collector.observe_source(shot_id, frame, index)
            before = frame.copy()
            after = frame.copy()
            after[10:25, 10:25, 2] = 220
            collector.effect("fx", before, after, index, kind="effect",
                             params={"protected_roi": [.5, .5, 1, 1]})
            if shot_id == "a" and index >= 2:
                transitioned = after.copy()
                transitioned[60:75, 60:75, 1] = 180
                collector.effect("tr", after, transitioned, index, kind="transition")
                after = transitioned
            if shot_id == "b" and index == 0:
                after = last.copy()
            collector.observe_output(shot_id, after, index)
            last = after
    summary = collector.summary()
    gate = {
        "effects": [{"id": "fx"}], "transitions": [{"id": "tr"}],
        "source_media_qc": {"status": "PASS"},
        "director_fx_disposition": [
            {"id": "fx", "protected_roi": [.5, .5, 1, 1],
             "status": "DIRECTOR_RECOMMENDED_FOR_HUMAN_REVIEW"},
            {"id": "tr", "status": "DIRECTOR_RECOMMENDED_FOR_HUMAN_REVIEW"},
        ],
    }
    manifest = {"output": {"fps": 4}, "shots": shots}
    receipt = {"technical_visual_evidence": summary, "music_controls": AudioControls(controls()).summary(8)}
    proof_sha = bundle_fx_proofs([("test", proof_dir)], tmp_path / "FX_VISIBILITY_PROOF.zip")
    qc = combine_visual_evidence(manifest, [receipt], gate, "a" * 64, proof_sha)
    assert qc["status"] == "PASS"
    assert qc["checks"]["all_locked_fx_visibly_changed_frames"] is True
    assert qc["checks"]["temporal_motion_measured"] is True
    assert qc["checks"]["transition_seams_continuous"] is True
    assert qc["checks"]["paired_fx_proof_bundle_present"] is True
    assert qc["checks"]["declared_protected_rois_preserved"] is True
    assert any(item["roi_comparisons"] for item in qc["effects"] if item["id"] == "fx")
    assert qc["human_visual_approval"] is False
    assert qc["artistic_approval"] is False
    assert qc["release_authority"] is False

    restarted = copy.deepcopy(receipt)
    restarted["technical_visual_evidence"]["shots"][1]["entry_preroll_seconds"] = 0
    assert combine_visual_evidence(manifest, [restarted], gate, "a" * 64, proof_sha)["status"] == "FAIL"


def test_low_resolution_and_loop_substitution_fail_closed(tmp_path):
    import cv2
    tiny = tmp_path / "tiny.png"
    cv2.imwrite(str(tiny), np.zeros((20, 20, 3), np.uint8))
    manifest = {
        "shots": [{"id": "still", "source": {"path": "tiny.png"}, "media_role": "real_source",
                   "duration_seconds": 1}],
    }
    with pytest.raises(QualityError, match="low-resolution"):
        inspect_source_media(manifest, [tiny], 160, 90)
    manifest["shots"][0]["loop"] = True
    with pytest.raises(QualityError, match="loop"):
        inspect_source_media(manifest, [tiny], 160, 90)

    large = tmp_path / "large.png"
    cv2.imwrite(str(large), np.zeros((180, 320, 3), np.uint8))
    manifest["shots"][0].pop("loop")
    assert inspect_source_media(manifest, [large], 160, 90)["status"] == "PASS"


def test_production_workflows_require_visual_and_paired_fx_evidence():
    candidate = (ROOT / ".github/workflows/mainv2-director-parallel-real-render.yml").read_text()
    release = (ROOT / ".github/workflows/production-final-release.yml").read_text()
    assert "VISUAL_QC_EVIDENCE.json" in candidate
    assert "FX_VISIBILITY_PROOF.zip" in candidate
    assert "--visual-qc" in release and "--fx-proof" in release
    assert "energy=0.35" not in (ROOT / "scripts/render_real_music_film.py").read_text()
    assert "energy=0.35" not in (ROOT / "scripts/render_real_music_film_shard.py").read_text()
