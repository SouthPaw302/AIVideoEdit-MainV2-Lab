#!/usr/bin/env python3
"""Fail-closed directing/music/media evidence validator for AIVideoEdit."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from branch_policy import resolve_production_project

SCRIPT_ROOT = Path(__file__).resolve().parents[3]
if os.environ.get("AIVIDEOEDIT_REPO_ROOT"):
    ROOT = Path(os.environ["AIVIDEOEDIT_REPO_ROOT"]).resolve()
elif SCRIPT_ROOT.name == "os" and SCRIPT_ROOT.parent.name == ".aivideoedit":
    ROOT = SCRIPT_ROOT.parent.parent.resolve()
else:
    ROOT = SCRIPT_ROOT.resolve()


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"FAIL: missing {path.relative_to(ROOT)}")
    except Exception as e:
        raise SystemExit(f"FAIL: invalid JSON {path.relative_to(ROOT)}: {e}")


def truthy(v):
    return v is True


def fail(msg, errors):
    errors.append(msg)


def discover_project(branch: str):
    project, error = resolve_production_project(ROOT, branch)
    if error:
        raise SystemExit(f"FAIL: {error}")
    if project is None:
        raise SystemExit("FAIL: production project could not be resolved")
    return project


def validate_music_analysis(project: Path, state: dict, errors: list[str]):
    music_path = project / "MUSIC_ANALYSIS.json"
    if not music_path.is_file():
        fail("missing MUSIC_ANALYSIS.json", errors)
        return None
    music = load_json(music_path)

    if music.get("schema") != "aivideoedit.music-analysis.v1":
        fail("MUSIC_ANALYSIS.json schema must be aivideoedit.music-analysis.v1", errors)
    if not truthy(music.get("analysis_complete")):
        fail("MUSIC_ANALYSIS.analysis_complete must be true before REFERENCES_ANALYZED", errors)

    lyrics = music.get("lyrics")
    if not isinstance(lyrics, dict):
        fail("MUSIC_ANALYSIS.lyrics is required", errors)
    else:
        status = lyrics.get("status")
        if status not in {"present", "instrumental", "none_confirmed"}:
            fail("lyrics.status must be present, instrumental, or none_confirmed", errors)
        if status == "present":
            lyrics_file = lyrics.get("text_file") or "LYRICS.md"
            if not (project / lyrics_file).is_file():
                fail(f"lyrics.status=present requires {lyrics_file}", errors)
            directing_use = lyrics.get("directing_use", "required")
            if directing_use not in {"required", "excluded_by_current_user"}:
                fail("lyrics.directing_use must be required or excluded_by_current_user", errors)
            if directing_use == "excluded_by_current_user":
                if lyrics.get("exclusion_source") != "current_user_instruction":
                    fail("lyrics excluded from directing require exclusion_source=current_user_instruction", errors)
                instruction = lyrics.get("exclusion_instruction")
                if not isinstance(instruction, str) or not instruction.strip():
                    fail("lyrics excluded from directing require exclusion_instruction", errors)

    genre = music.get("genre")
    if not isinstance(genre, dict):
        fail("MUSIC_ANALYSIS.genre is required", errors)
    else:
        status = genre.get("status")
        label = genre.get("label")
        if status not in {"confident", "user_confirmed"}:
            fail(
                "genre is unresolved; if the agent cannot confidently identify the song type, "
                "ask the user and record status=user_confirmed",
                errors,
            )
        if not isinstance(label, str) or not label.strip():
            fail("genre.label is required", errors)
        if status == "confident":
            confidence = genre.get("confidence")
            if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or confidence < 0.65:
                fail("genre.status=confident requires confidence >= 0.65", errors)
        if status == "user_confirmed":
            if genre.get("source") != "current_user_instruction":
                fail("user-confirmed genre must use source=current_user_instruction", errors)
            declaration = genre.get("user_declaration")
            if not isinstance(declaration, str) or not declaration.strip():
                fail("user-confirmed genre requires user_declaration", errors)

    rhythm = music.get("rhythm")
    if not isinstance(rhythm, dict):
        fail("MUSIC_ANALYSIS.rhythm is required", errors)
    else:
        tempo_status = rhythm.get("tempo_status")
        if tempo_status not in {"measured", "approximate", "non_metric"}:
            fail("rhythm.tempo_status must be measured, approximate, or non_metric", errors)
        bpm = rhythm.get("tempo_bpm")
        if tempo_status in {"measured", "approximate"}:
            if not isinstance(bpm, (int, float)) or isinstance(bpm, bool) or bpm <= 0:
                fail("metric music requires positive rhythm.tempo_bpm", errors)
        if not isinstance(rhythm.get("pulse_description"), str) or not rhythm.get("pulse_description", "").strip():
            fail("rhythm.pulse_description is required", errors)
        if not isinstance(rhythm.get("meter_or_groove"), str) or not rhythm.get("meter_or_groove", "").strip():
            fail("rhythm.meter_or_groove is required", errors)

    sections = music.get("sections")
    if not isinstance(sections, list) or len(sections) < 2:
        fail("MUSIC_ANALYSIS.sections requires at least two analyzed sections", errors)
    else:
        prev_end = None
        for i, section in enumerate(sections, 1):
            if not isinstance(section, dict):
                fail(f"music section {i} must be an object", errors)
                continue
            start = section.get("start_seconds")
            end = section.get("end_seconds")
            if not isinstance(start, (int, float)) or not isinstance(end, (int, float)) or end <= start:
                fail(f"music section {i} requires valid start_seconds/end_seconds", errors)
            if prev_end is not None and isinstance(start, (int, float)) and start < prev_end - 0.02:
                fail(f"music section {i} overlaps prior section unexpectedly", errors)
            if isinstance(end, (int, float)):
                prev_end = end
            cues = section.get("musical_cues")
            if not isinstance(cues, list) or not cues or not all(isinstance(x, str) and x.strip() for x in cues):
                fail(f"music section {i} requires non-empty musical_cues", errors)
            if not isinstance(section.get("energy"), str) or not section.get("energy", "").strip():
                fail(f"music section {i} requires energy description", errors)

            directing_function = section.get("visual_function")
            if not isinstance(directing_function, str) or not directing_function.strip():
                directing_function = section.get("narrative_function")
            if not isinstance(directing_function, str) or not directing_function.strip():
                fail(
                    f"music section {i} requires visual_function or narrative_function",
                    errors,
                )

    for key in ("music_analysis_complete", "lyrics_status_resolved", "genre_authority_resolved"):
        if not truthy(state.get(key)):
            fail(f"REFERENCES_ANALYZED requires {key}=true", errors)

    return music


def validate_script(project: Path, state: dict, music: dict | None, errors: list[str]):
    md = project / "SCRIPT.md"
    js = project / "SCRIPT.json"
    if not md.is_file():
        fail("STORYBOARD_LOCKED requires SCRIPT.md", errors)
    if not js.is_file():
        fail("STORYBOARD_LOCKED requires SCRIPT.json", errors)
        return
    script = load_json(js)
    if script.get("schema") != "aivideoedit.video-script.v1":
        fail("SCRIPT.json schema must be aivideoedit.video-script.v1", errors)
    if not truthy(script.get("locked")) or not truthy(state.get("script_locked")):
        fail("storyboard/script stage requires locked script evidence", errors)
    if not truthy(script.get("based_on_storyboard")):
        fail("SCRIPT.json must be based_on_storyboard=true", errors)

    fps = script.get("target_fps")
    total = script.get("total_frames")
    duration = script.get("duration_seconds")
    if not isinstance(fps, (int, float)) or isinstance(fps, bool) or fps <= 0:
        fail("SCRIPT.target_fps must be positive", errors)
    if not isinstance(total, int) or isinstance(total, bool) or total <= 0:
        fail("SCRIPT.total_frames must be a positive integer", errors)
    if not isinstance(duration, (int, float)) or isinstance(duration, bool) or duration <= 0:
        fail("SCRIPT.duration_seconds must be positive", errors)

    basis = script.get("basis")
    if not isinstance(basis, list):
        basis = []
    if "storyboard" not in basis or "music_analysis" not in basis:
        fail("SCRIPT.basis must include storyboard and music_analysis", errors)

    lyrics_status = None
    lyrics_directing_use = "required"
    if music and isinstance(music.get("lyrics"), dict):
        lyrics_status = music["lyrics"].get("status")
        lyrics_directing_use = music["lyrics"].get("directing_use", "required")
        if lyrics_status == "present" and lyrics_directing_use != "excluded_by_current_user" and "lyrics" not in basis:
            fail("lyrics are present and active, so SCRIPT.basis must include lyrics", errors)
        if lyrics_status == "present" and lyrics_directing_use == "excluded_by_current_user" and "lyrics" in basis:
            fail("lyrics are explicitly excluded by the current user, so SCRIPT.basis must not include lyrics", errors)

    entries = script.get("entries")
    if not isinstance(entries, list) or not entries:
        fail("SCRIPT.entries must contain the frame-followable video script", errors)
        return

    expected_start = 0
    lyric_cue_count = 0
    for i, entry in enumerate(entries, 1):
        if not isinstance(entry, dict):
            fail(f"script entry {i} must be an object", errors)
            continue
        start = entry.get("start_frame")
        end = entry.get("end_frame")
        if not isinstance(start, int) or isinstance(start, bool) or not isinstance(end, int) or isinstance(end, bool):
            fail(f"script entry {i} requires integer start_frame/end_frame", errors)
        else:
            if start != expected_start:
                fail(f"script entry {i} must start at frame {expected_start}; got {start}", errors)
            if end < start:
                fail(f"script entry {i} has end_frame before start_frame", errors)
            expected_start = end + 1

        for key in ("shot_id", "visual_media", "animation_behavior", "transition"):
            if not isinstance(entry.get(key), str) or not entry.get(key, "").strip():
                fail(f"script entry {i} requires {key}", errors)

        action = entry.get("visual_action")
        if not isinstance(action, str) or not action.strip():
            action = entry.get("story_action")
        if not isinstance(action, str) or not action.strip():
            fail(f"script entry {i} requires visual_action or story_action", errors)

        cues = entry.get("music_cues")
        if not isinstance(cues, list) or not cues or not all(isinstance(x, str) and x.strip() for x in cues):
            fail(f"script entry {i} requires music_cues", errors)
        lyric_cue = entry.get("lyric_cue")
        if isinstance(lyric_cue, str) and lyric_cue.strip():
            lyric_cue_count += 1

    if isinstance(total, int) and expected_start != total:
        fail(f"SCRIPT frame coverage must end at total_frames-1 ({total-1}); got {expected_start-1}", errors)
    if lyrics_status == "present" and lyrics_directing_use != "excluded_by_current_user" and lyric_cue_count == 0:
        fail("lyrics are present and active but SCRIPT contains no lyric_cue entries", errors)
    if lyrics_status == "present" and lyrics_directing_use == "excluded_by_current_user" and lyric_cue_count != 0:
        fail("lyrics are explicitly excluded by the current user but SCRIPT still contains lyric_cue entries", errors)


def generated_assets_present(asset_manifest: dict) -> bool:
    assets = asset_manifest.get("assets", [])
    for asset in assets if isinstance(assets, list) else []:
        if not isinstance(asset, dict):
            continue
        origin = str(asset.get("origin", "")).casefold()
        kind = str(asset.get("kind", "")).casefold()
        role = str(asset.get("role", "")).casefold()
        if origin == "generated" or "generated" in kind or "generated" in role:
            return True
    return False


def validate_shot_packages(project: Path, plan: dict, errors: list[str]):
    sp = project / "shot_packages"
    packages = [p for p in sp.iterdir() if p.is_dir()] if sp.is_dir() else []
    if not packages:
        fail("SHOT_PACKAGES_BUILT requires at least one shot package", errors)
        return

    for pkg in packages:
        package_json = pkg / "package.json"
        if not package_json.is_file():
            fail(f"{pkg.name} missing package.json", errors)
            continue
        data = load_json(package_json)
        evidence = data.get("media_evidence")
        if not isinstance(evidence, list) or not evidence:
            fail(
                f"{pkg.name} requires non-empty media_evidence; metadata-only shot packages are forbidden",
                errors,
            )
            continue
        for j, item in enumerate(evidence, 1):
            if not isinstance(item, dict):
                fail(f"{pkg.name} media_evidence {j} must be an object", errors)
                continue
            locator = item.get("path") or item.get("uri")
            if not isinstance(locator, str) or not locator.strip():
                fail(f"{pkg.name} media_evidence {j} requires path or uri", errors)
            sha = item.get("sha256")
            if not isinstance(sha, str) or len(sha) < 16:
                fail(f"{pkg.name} media_evidence {j} requires a content hash", errors)
            if item.get("status") not in {"generated", "ingested", "derived", "accepted"}:
                fail(f"{pkg.name} media_evidence {j} requires a valid status", errors)

    selected = plan.get("selected_capabilities", [])
    generated_caps = {"generated_stills", "generated_support_imagery", "living_painting"}
    if any(cap in generated_caps for cap in selected if isinstance(cap, str)):
        assets = load_json(project / "ASSET_MANIFEST.json")
        if not generated_assets_present(assets):
            fail(
                "MEDIA_PLAN selects generated visual media but ASSET_MANIFEST contains no generated visual asset evidence",
                errors,
            )


def validate(branch: str):
    errors: list[str] = []
    if branch == "main":
        required = [
            "general/reusable/NARRATIVE_CONTRACT.md",
            "general/reusable/tools/narrative_guard.py",
        ]
        for rel in required:
            if not (ROOT / rel).is_file():
                fail(f"missing directing system file: {rel}", errors)
        return errors

    project, branch_error = resolve_production_project(ROOT, branch)
    if branch_error:
        return [branch_error]
    if project is None:
        return [f"production project could not be resolved for {branch}"]

    state = load_json(project / "PROJECT_STATE.json")
    plan = load_json(project / "MEDIA_PLAN.json")
    stage = state.get("stage")
    states = [
        "INITIALIZED",
        "SOURCE_INGESTED",
        "REFERENCES_ANALYZED",
        "APPROACH_ESTABLISHED",
        "STORYBOARD_LOCKED",
        "SHOT_PACKAGES_BUILT",
        "SHOT_PROOFS_ACCEPTED",
        "FX_LOCKED",
        "ASSEMBLED",
        "FINAL_QC_PASSED",
        "ARCHIVED",
    ]
    if stage not in states:
        return [f"invalid production stage: {stage}"]
    idx = states.index(stage)

    def at(name):
        return idx >= states.index(name)

    music = None
    if at("REFERENCES_ANALYZED"):
        music = validate_music_analysis(project, state, errors)
    if at("STORYBOARD_LOCKED"):
        validate_script(project, state, music, errors)
    if at("SHOT_PACKAGES_BUILT"):
        validate_shot_packages(project, plan, errors)
        if not truthy(state.get("media_evidence_verified")):
            fail("SHOT_PACKAGES_BUILT requires media_evidence_verified=true", errors)

    return errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--branch",
        default=os.environ.get("GITHUB_REF_NAME") or os.environ.get("AIVIDEOEDIT_BRANCH") or "",
    )
    args = ap.parse_args()
    if not args.branch:
        raise SystemExit("FAIL: branch required (--branch or GITHUB_REF_NAME)")
    errors = validate(args.branch)
    if errors:
        print("AIVideoEdit directing contract: FAIL")
        for e in errors:
            print("- " + e)
        raise SystemExit(1)
    print("AIVideoEdit directing contract: PASS")


if __name__ == "__main__":
    main()
