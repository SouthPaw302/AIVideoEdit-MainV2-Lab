#!/usr/bin/env python3
"""Fail-closed validation for delivery lifecycle and content-addressed lineage."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SCHEMA = "aivideoedit.delivery-archive.v1"
LIFECYCLE_STATES = (
    "DIRECTOR_REJECTED",
    "REVISION_REQUIRED",
    "DIRECTOR_RECOMMENDED",
    "HUMAN_ACCEPTED",
    "RELEASE_AUTHORIZED",
    "RELEASED",
    "SUPERSEDED",
    "WITHDRAWN",
)
_TRANSITIONS = {
    "DIRECTOR_REJECTED": {"REVISION_REQUIRED"},
    "REVISION_REQUIRED": {"DIRECTOR_REJECTED", "DIRECTOR_RECOMMENDED"},
    "DIRECTOR_RECOMMENDED": {"DIRECTOR_REJECTED", "REVISION_REQUIRED", "HUMAN_ACCEPTED"},
    "HUMAN_ACCEPTED": {"REVISION_REQUIRED", "RELEASE_AUTHORIZED", "WITHDRAWN"},
    "RELEASE_AUTHORIZED": {"REVISION_REQUIRED", "RELEASED", "WITHDRAWN"},
    "RELEASED": {"SUPERSEDED", "WITHDRAWN"},
    "SUPERSEDED": set(),
    "WITHDRAWN": set(),
}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
_ACCESS = {"directly_playable", "lossless_transfer_parts", "local_only", "evidence"}


def _close(a, b, tolerance=1e-5):
    return abs(float(a) - float(b)) <= tolerance


def validate_lifecycle(lifecycle):
    errors = []
    state = lifecycle.get("state")
    history = lifecycle.get("history")
    if state not in LIFECYCLE_STATES:
        errors.append("invalid lifecycle state")
        return errors
    if not isinstance(history, list) or not history:
        return ["lifecycle history is required"]
    states = [entry.get("state") for entry in history if isinstance(entry, dict)]
    if len(states) != len(history) or any(item not in LIFECYCLE_STATES for item in states):
        errors.append("lifecycle history contains an invalid state")
    else:
        for before, after in zip(states, states[1:]):
            if after not in _TRANSITIONS[before]:
                errors.append(f"illegal lifecycle transition {before}->{after}")
        if states[-1] != state:
            errors.append("current lifecycle state differs from history")
    return errors


def validate_manifest(payload):
    errors = []
    if payload.get("schema") != SCHEMA:
        errors.append(f"schema must be {SCHEMA}")
    errors.extend(validate_lifecycle(payload.get("lifecycle") or {}))

    authority = payload.get("authority") or {}
    for key in ("source_commit", "engine_commit"):
        if not _GIT_SHA.fullmatch(str(authority.get(key) or "")):
            errors.append(f"authority.{key} must be a full Git SHA")

    timeline = payload.get("timeline") or {}
    fps = timeline.get("fps")
    frames = timeline.get("frame_count")
    duration = timeline.get("duration_seconds")
    sections = timeline.get("section_frames") or {}
    if not fps or not frames or not duration or not _close(frames / fps, duration):
        errors.append("timeline frame count, fps, and duration disagree")
    if sum(sections.values()) != frames:
        errors.append("timeline section frames do not cover the full export")
    if not _close(timeline.get("audio_start_seconds", -1), sections.get("silent_intro", -1) / fps):
        errors.append("audio start does not match silent title lead-in")
    song_frames = sum(sections.get(key, 0) for key in ("opening_replacement", "protected_song_core", "ending_replacement"))
    if not _close(timeline.get("audio_duration_seconds", -1), song_frames / fps):
        errors.append("audio duration does not match the complete song picture")

    title_qc = payload.get("title_qc") or {}
    if title_qc.get("exact_strings") != ["MOUNTAIN NOIR", "@MotañaNegra"]:
        errors.append("title strings do not match approved branding")
    if title_qc.get("safe_area_pass") is not True or title_qc.get("typography_review") != "PASS":
        errors.append("title safe-area and typography approval are required")

    audio_qc = payload.get("audio_qc") or {}
    if audio_qc.get("best_lag_samples") != 0 or float(audio_qc.get("decoded_correlation", 0)) < 0.999:
        errors.append("audio sync or decoded correlation failed")
    if audio_qc.get("silent_intro_max_amplitude") != 0 or audio_qc.get("source_master_preserved") is not True:
        errors.append("silent lead-in or source-audio preservation failed")

    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        return errors + ["content-addressed artifacts are required"]
    by_id = {}
    roles = set()
    for artifact in artifacts:
        aid = artifact.get("id")
        if not aid or aid in by_id:
            errors.append("artifact IDs must be non-empty and unique")
            continue
        by_id[aid] = artifact
        roles.add(artifact.get("role"))
        if not _SHA256.fullmatch(str(artifact.get("sha256") or "")):
            errors.append(f"{aid}: invalid SHA-256")
        if not isinstance(artifact.get("size_bytes"), int) or artifact["size_bytes"] <= 0:
            errors.append(f"{aid}: invalid byte size")
        if artifact.get("access") not in _ACCESS:
            errors.append(f"{aid}: invalid access mode")
        if not artifact.get("locator"):
            errors.append(f"{aid}: locator is required")
        if artifact.get("access") == "lossless_transfer_parts":
            parts = artifact.get("parts") or []
            if artifact.get("directly_playable") is not False or not parts:
                errors.append(f"{aid}: transfer parts must be explicit and non-playable")
            elif sum(part.get("size_bytes", 0) for part in parts) != artifact.get("size_bytes"):
                errors.append(f"{aid}: transfer-part byte total differs from master")
            for part in parts:
                if not _SHA256.fullmatch(str(part.get("sha256") or "")):
                    errors.append(f"{aid}: invalid transfer-part SHA-256")

    required_roles = {"accepted_artistic_master", "review_proxy", "audio_master", "technical_qc", "thumbnail"}
    if not required_roles.issubset(roles):
        errors.append("archive omits an accepted master, proxy, audio, QC, or thumbnail")

    lineage = payload.get("lineage") or {}
    master = by_id.get(lineage.get("accepted_master_id")) or {}
    proxy = by_id.get(lineage.get("review_proxy_id")) or {}
    if master.get("role") != "accepted_artistic_master":
        errors.append("accepted master lineage is missing")
    if proxy.get("role") != "review_proxy" or proxy.get("access") != "directly_playable" or proxy.get("directly_playable") is not True:
        errors.append("review proxy must be directly playable")
    if proxy.get("parent_sha256") != master.get("sha256"):
        errors.append("review proxy is not bound to the accepted master")

    derivative_id = lineage.get("platform_4k_id")
    if derivative_id:
        derivative = by_id.get(derivative_id) or {}
        media = derivative.get("media") or {}
        master_media = master.get("media") or {}
        if media.get("width") != 3840 or media.get("height") != 2160:
            errors.append("4K derivative is not 3840x2160")
        for key in ("fps", "frame_count", "duration_seconds", "edit_identity"):
            if media.get(key) != master_media.get(key):
                errors.append(f"4K derivative changed {key}")
        if derivative.get("audio_identity") != proxy.get("audio_identity"):
            errors.append("review-derived 4K audio identity differs from its parent proxy")
        if derivative.get("release_eligible") is True and derivative.get("parent_sha256") != master.get("sha256"):
            errors.append("release-eligible 4K must derive directly from the accepted master")

    lifecycle = payload.get("lifecycle") or {}
    if lifecycle.get("state") in {"RELEASE_AUTHORIZED", "RELEASED", "SUPERSEDED"}:
        approval = payload.get("release_approval") or {}
        if approval.get("authenticated") is not True or not approval.get("comment_url") or approval.get("approved_sha256") != master.get("sha256"):
            errors.append("release state requires authenticated approval bound to the accepted master")
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.manifest.read_text(encoding="utf-8"))
    errors = validate_manifest(payload)
    print(json.dumps({"ok": not errors, "errors": errors}, indent=2))
    raise SystemExit(1 if errors else 0)


if __name__ == "__main__":
    main()
