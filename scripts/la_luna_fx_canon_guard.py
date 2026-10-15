#!/usr/bin/env python3
"""Fail-closed, branch-local FX stage canon consistency check. Not a render/release gate."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "projects" / "la-luna-de-florida"


def load(name: str) -> dict:
    return json.loads((PROJECT / name).read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def check() -> dict:
    canon = load("FX_STAGE_CANON.json")
    board = load("STORYBOARD_CANON.json")
    op = load("OPERATING_ORDER.json")
    authority = load("SOURCE_AUTHORITY.json")
    music = load("MUSIC_ANALYSIS.json")
    script = load("SCRIPT.json")
    state = load("PROJECT_STATE.json")

    require(canon["schema"] == "aivideoedit.la-luna-fx-stage-canon.v1", "FX schema mismatch")
    require(canon["status"] == "CANON_BY_EXPLICIT_USER_DIRECTION", "user FX canon missing")
    require(canon["production_id"] == "la-luna-de-florida", "wrong production")
    require(canon["branch"] == "song/la-luna-de-florida", "wrong song branch")
    ref = canon["authoritative_inputs"]
    board_ref = ref["storyboard"]
    require(board["lock"] is True and board["approval"] == "explicit_current_user_instruction",
            "50-shot storyboard not user locked")
    require(board["source"]["sha256"] == board_ref["image_sha256"],
            "canonical storyboard digest changed")
    require(board["shot_count"] == 50 and board["batch_count"] == 5 and
            board["shots_per_batch"] == 10, "unexpected storyboard layout")
    expected_batches = [f"B{i:02d}" for i in range(1, 6)]
    require([b["batch_id"] for b in board["batches"]] == expected_batches,
            "board batch order drift")
    require([s["shot_id"] for b in board["batches"] for s in b["shots"]] ==
            [f"B{b:02d}-S{s:02d}" for b in range(1, 6) for s in range(1, 11)],
            "board shot ID drift")
    require(canon["batch_structure"]["batch_ids"] == expected_batches,
            "FX batch list differs from storyboard")
    require(ref["audio"]["sha256"] == music["source_audio"]["sha256"],
            "FX input and source WAV hash disagree")
    require(music["onnx_song_analysis"]["status"] == "PASS" and
            music["onnx_song_analysis"]["run_id"] == ref["music"]["run_id"] and
            music["onnx_song_analysis"]["model_fallback_used"] is False,
            "verified full-song ONNX evidence was lost")
    require(script["locked"] is False and
            ref["script"]["frame_timing_status"] == "NOT_LOCKED",
            "lyric-script timing incorrectly promoted")
    stages = canon["stages"]
    expected = ["BATCH_LIGHT_FX", "BATCH_CHARACTER_FX", "MASTER_FX_AND_ASSEMBLY"]
    require([stage["id"] for stage in stages] == expected, "FX stage sequence drift")
    require(all(stage.get("pass_rule") and stage.get("cannot_claim") for stage in stages),
            "FX evidence or acceptance boundaries missing")
    require("camera" in stages[1]["pass_rule"].lower(), "semantic character motion standard missing")
    require(op["canon_lock"]["locked"] is True and
            op["fx_stage_canon"]["path"] == "FX_STAGE_CANON.json" and
            op["fx_stage_canon"]["sequence"] == expected, "Operating Order diverged from FX canon")
    require(op["accepted_baseline"]["status"] == "none", "unexpected accepted film baseline")
    require(canon["verified_baseline_at_policy_creation"]["B01"]["light_fx"] ==
            "TECHNICAL_PASS" and
            canon["verified_baseline_at_policy_creation"]["B02"]["light_fx"] ==
            "TECHNICAL_PASS", "historical light FX proofs unexpectedly reclassified")
    for bid in ("B01", "B02"):
        batch = canon["verified_baseline_at_policy_creation"][bid]
        require(batch["character_fx"] != "PASS" and batch["master_fx"] == "NOT_COMPLETED",
                f"{bid} technical light proof incorrectly promoted to character/master pass")
    require(authority["allow"]["unrelated_song_branches"] is False and
            authority["allow"]["prior_project_media"] is False and
            authority["allow"]["prior_project_storyboards"] is False,
            "unrelated source protections modified")
    ext = canon["external_film_reference_boundary"]
    study = authority["external_reference_process_study"]
    require(ext["unknown_source"] == "RESOLVED_REFERENCE_REPOSITORY_SouthPaw302/AIVideoEdit" and
            canon["reference_method_study"]["external_repo"] == "SouthPaw302/AIVideoEdit" and
            canon["reference_method_study"]["foreign_story_or_assets_imported"] is False and
            canon["reference_method_study"]["foreign_code_imported"] is False and
            study["content_reuse_authorized"] is False and
            study["automatic_process_import_authorized"] is False,
            "unapproved cross-project reference import")
    char = stages[1]
    require("GIF" in char["purpose"] and "video-generation requirement" in char["purpose"],
            "shot-local existing FX/loop/duplicate motion method was lost")
    require("PERFORMANCE_MOTION_GAP" in char["pass_rule"] and
            "3DGS" in char["technologies_and_existing_library"]["gaussian_terms"],
            "motion fidelity or Gaussian technology truth gate lost")
    require(state["production_complete"] is False and
            state["human_visual_approval"] is False,
            "script/FX process gate cannot release the film")
    return {
        "result": "PASS", "purpose": "FX_PROCESS_CANON_ONLY_NOT_ARTISTIC_ACCEPTANCE",
        "production": canon["production_id"], "ordered_stages": expected,
        "canonical_shots": board["shot_count"],
        "B01_light_fx": "TECHNICAL_PASS", "B02_light_fx": "TECHNICAL_PASS",
        "character_fx": "SEPARATE_UNPASSED", "master_fx": "NOT_COMPLETED",
        "cross_project_media_reuse": "FORBIDDEN"
    }


if __name__ == "__main__":
    print(json.dumps(check(), indent=2, sort_keys=True))
