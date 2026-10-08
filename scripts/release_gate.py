#!/usr/bin/env python3
"""Fail-closed, full-song RELEASE authority. Technical renders are never releases.

Production authority: general/reusable/PRODUCTION_CONTRACT.json.
This program intentionally does not produce media or grant visual approval.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
HEX64 = re.compile(r"[a-f0-9]{64}\Z")
HEX40 = re.compile(r"[a-f0-9]{40}\Z")


class GateError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise GateError(message)


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def command(args):
    p = subprocess.run(args, capture_output=True, text=True, check=False, timeout=7200)
    require(p.returncode == 0, "media inspection failed: " + " ".join(args[:3]) + " " + p.stderr[-800:])
    return p.stdout


def probe(path, *, frames=False):
    args = ["ffprobe", "-v", "error"]
    if frames:
        args += ["-count_frames"]
    args += ["-show_streams", "-show_format", "-of", "json", str(path)]
    return json.loads(command(args))


def media_duration(info):
    return float(info.get("format", {}).get("duration") or 0)


def _approval_from_github(repo, comment_id, token):
    require(re.fullmatch(r"[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+", repo or "") is not None, "bad repository")
    require(type(comment_id) is int and comment_id > 0, "missing human approval comment ID")
    require(bool(token), "GITHUB_TOKEN required to authenticate human approval")
    req = urllib.request.Request(
        "https://api.github.com/repos/" + repo + "/issues/comments/" + str(comment_id),
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer " + token,
            "User-Agent": "AIVideoEdit-release-gate",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.load(r)
    return data


def preflight(manifest, receipt, review, contract, *, source_sha, engine_sha, audio_duration, comment):
    """Pure validation for tests and the CI media/approval inspector."""
    policy = contract.get("release_gate_policy", {})
    for name in ("fail_closed", "full_song_required", "real_source_required",
                 "human_verified_comment_required", "actual_export_inspection_required"):
        require(policy.get(name) is True, "production contract missing mandatory " + name)
    require(contract.get("schema") == "aivideoedit.production-contract.v3", "unknown production contract")
    require(manifest.get("schema") == "aivideoedit.real-render.v1", "unknown source manifest")
    require(manifest.get("render_authorization") == "explicit_user_render_request", "unauthorized render")
    production_id = manifest.get("production_id")
    require(isinstance(production_id, str) and bool(production_id.strip()), "production ID required")
    branch = review.get("source_branch")
    require(isinstance(branch, str) and
            (branch.startswith("song/") or branch.startswith("project/")), "release must be on a production branch, never main")
    require(bool(HEX40.fullmatch(source_sha or "")) and
            bool(HEX40.fullmatch(engine_sha or "")), "current immutable source and engine SHAs required")
    require(receipt.get("source_commit_sha") == source_sha and
            receipt.get("engine_commit_sha") == engine_sha, "stale source or runtime lineage")
    require(review.get("source_commit_sha") == source_sha and
            review.get("engine_commit_sha") == engine_sha, "review not bound to current commits")
    require(receipt.get("schema") == "aivideoedit.real-render-receipt.v1", "unknown render receipt")
    require(receipt.get("production_id") == production_id and
            review.get("production_id") == production_id, "contradictory production identities")
    require(receipt.get("status") == "TECHNICAL_RENDER_PASS_VISUAL_REVIEW_PENDING" and
            receipt.get("production_complete") is False and
            receipt.get("human_visual_approval") is False, "technical proof must not self-certify release")
    require(bool(HEX64.fullmatch(receipt.get("render_sha256", ""))), "missing export digest")
    require(review.get("approved_export_sha256") == receipt["render_sha256"], "review does not match export bytes")
    require(review.get("decision") == "ACCEPT" and review.get("watched_entire_film") is True and
            review.get("normal_speed_playback") is True, "explicit complete visual acceptance required")
    require(isinstance(review.get("playback_url"), str) and
            review["playback_url"].startswith("https://"), "durable human playback evidence missing")
    try:
        reviewed_at = datetime.fromisoformat(review["reviewed_at"].replace("Z", "+00:00"))
        require(reviewed_at.tzinfo is not None and reviewed_at <= datetime.now(timezone.utc),
                "invalid review time")
    except (KeyError, ValueError, TypeError) as exc:
        raise GateError("valid timezone-aware review date required") from exc
    reviewer = review.get("reviewer")
    require(isinstance(reviewer, str) and reviewer and
            not reviewer.lower().endswith("[bot]"), "human reviewer required")
    require(comment.get("user", {}).get("type") == "User" and
            comment.get("user", {}).get("login") == reviewer, "GitHub approval author mismatch or non-human")
    token = "AIVE-RELEASE-ACCEPT " + production_id + " " + receipt["render_sha256"] + " " + source_sha
    require(token in comment.get("body", "") and
            "watched entire film at normal speed" in comment.get("body", "").lower(),
            "GitHub human review must approve exact export, source and full playback")
    require(review.get("approval_comment_id") == comment.get("id"), "approval evidence ID mismatch")

    fps = int(manifest.get("output", {}).get("fps", 0))
    require(1 <= fps <= 60, "invalid timeline fps")
    shots = manifest.get("shots")
    require(isinstance(shots, list) and bool(shots), "complete shot timeline required")
    total_frames = 0
    ids = set()
    for shot in shots:
        require(isinstance(shot, dict), "malformed shot")
        sid = shot.get("id")
        require(isinstance(sid, str) and sid and sid not in ids, "duplicate or missing shot ID")
        ids.add(sid)
        src = shot.get("source")
        require(isinstance(src, dict) and bool(HEX64.fullmatch(src.get("sha256", ""))),
                "real byte-pinned source required for " + sid)
        require(shot.get("media_role") in ("real_source", "canonical_source_derived"),
                "FX-only, loop-only or undeclared media is not final source: " + sid)
        require(shot.get("loop") is not True, "looped replacement cannot count as full-song source: " + sid)
        if shot["media_role"] == "canonical_source_derived":
            require(bool(HEX64.fullmatch(shot.get("canonical_source_sha256", ""))) and
                    bool(shot.get("derivation")), "source-derived media missing canonical lineage: " + sid)
        dur = float(shot.get("duration_seconds") or 0)
        frames = round(dur * fps)
        require(frames > 0 and abs(frames / fps - dur) <= .03, "invalid frame coverage: " + sid)
        total_frames += frames
        require(receipt.get("clip_sha256", {}).get(sid) == src["sha256"],
                "rendered visual source differs from current manifest: " + sid)

    require(float(manifest.get("audio", {}).get("start_seconds") or 0) == 0,
            "release may not trim the original song")
    require(bool(HEX64.fullmatch(manifest.get("audio", {}).get("sha256", ""))) and
            receipt.get("audio_sha256") == manifest["audio"]["sha256"], "audio identity conflict")
    expected = total_frames / fps
    require(audio_duration > 0 and abs(audio_duration - expected) <= max(.125, 2 / fps),
            "bounded/partial timeline: source song duration is not fully covered")
    require(abs(float(receipt.get("duration_seconds") or 0) - expected) <= 1 / fps and
            receipt.get("render_frames") == total_frames and
            receipt.get("fps") == fps, "stale or contradictory render duration/frame state")
    require(review.get("reviewed_duration_seconds") is not None and
            abs(float(review["reviewed_duration_seconds"]) - expected) <= max(.125, 2 / fps),
            "human review did not cover the full song")
    require(receipt.get("fx", {}).get("lock_sha256") and receipt.get("ledger_sha256"),
            "current FX and execution provenance required")
    return {"production_id": production_id, "source_branch": branch,
            "source_sha": source_sha, "engine_sha": engine_sha,
            "duration_seconds": expected, "frames": total_frames}


def gate(args):
    contract = load(ROOT / "general/reusable/PRODUCTION_CONTRACT.json")
    manifest_path, receipt_path, export, review_path = map(Path,
        (args.manifest, args.receipt, args.export, args.review))
    manifest, receipt, review = load(manifest_path), load(receipt_path), load(review_path)
    require(args.repository == "SouthPaw302/AIVideoEdit-MainV2-Lab", "release restricted to Lab repository")
    require(review.get("source_branch") == args.source_branch, "wrong checked out production branch")
    require(sha(manifest_path) == receipt.get("manifest_sha256"), "stale manifest/render mismatch")
    require(export.is_file() and sha(export) == receipt.get("render_sha256"), "missing or changed actual export")
    require(sha(args.fx_lock) == receipt.get("fx", {}).get("lock_sha256"), "FX lock no longer matches render")
    require(sha(args.ledger) == receipt.get("ledger_sha256"), "executed FX/ONNX/JEV evidence changed")
    ledger = load(args.ledger)
    require(bool(ledger), "missing execution ledger")
    require(Path(args.contact_sheet).is_file() and Path(args.contact_sheet).stat().st_size > 0,
            "required visual review contact sheet missing")

    # Stage and hash-check all real sources: report-only hashes cannot be substituted.
    from scripts.render_real_music_film import stage
    input_root = Path(args.source_root).resolve()
    cache = Path(args.output).resolve().parent / "release_source_cache"
    cache.mkdir(parents=True, exist_ok=True)
    audio = stage(manifest["audio"], input_root=input_root, cache=cache)
    for shot in manifest.get("shots", []):
        stage(shot["source"], input_root=input_root, cache=cache)
    audio_info = probe(audio)
    require(any(s.get("codec_type") == "audio" for s in audio_info.get("streams", [])),
            "missing real master audio stream")

    comment = _approval_from_github(args.repository, review.get("approval_comment_id"), os.getenv("GITHUB_TOKEN"))
    evidence = preflight(manifest, receipt, review, contract, source_sha=args.source_sha,
                         engine_sha=args.engine_sha, audio_duration=media_duration(audio_info),
                         comment=comment)
    require(comment.get("html_url", "").startswith("https://github.com/" + args.repository + "/"),
            "review comment not owned by this repository")
    info = probe(export, frames=True)
    video = next((x for x in info["streams"] if x.get("codec_type") == "video"), None)
    sound = next((x for x in info["streams"] if x.get("codec_type") == "audio"), None)
    require(bool(video and sound), "actual export missing audio or video")
    require(video.get("codec_name") == receipt.get("video_codec") and
            sound.get("codec_name") == receipt.get("audio_codec"), "export streams contradict render receipt")
    require([video.get("width"), video.get("height")] == receipt.get("resolution"), "output geometry mismatch")
    require(int(sound.get("channels") or 0) >= 1, "export audio channels missing")
    require(abs(media_duration(info) - evidence["duration_seconds"]) <= max(.125, 2 / receipt["fps"]),
            "export not full duration")
    frames = int(video.get("nb_read_frames") or 0)
    require(frames > 0 and abs(frames - evidence["frames"]) <= 1, "full video frame decode count mismatch")
    # -xerror makes decode errors fatal. No metadata flag can bypass this actual media inspection.
    command(["ffmpeg", "-hide_banner", "-v", "error", "-xerror", "-i", str(export), "-f", "null", "-"])
    evidence.update({
        "schema": "aivideoedit.release-gate.v1", "status": "PASS",
        "export_sha256": sha(export), "manifest_sha256": sha(manifest_path),
        "contract_sha256": sha(ROOT / "general/reusable/PRODUCTION_CONTRACT.json"),
        "fx_lock_sha256": sha(args.fx_lock), "ledger_sha256": sha(args.ledger),
        "reviewer": review["reviewer"], "approval_comment_url": comment["html_url"],
        "human_visual_approval": True, "decoded_full_export": True,
        "inspection": {"frames_decoded": frames, "channels": sound["channels"],
                       "duration_seconds": media_duration(info), "video_codec": video["codec_name"],
                       "audio_codec": sound["codec_name"], "resolution": receipt["resolution"]},
    })
    Path(args.output).write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return evidence


def main():
    p = argparse.ArgumentParser()
    for name in ("manifest", "receipt", "export", "review", "fx-lock",
                 "ledger", "contact-sheet", "source-root", "source-sha", "source-branch",
                 "engine-sha", "repository", "output"):
        p.add_argument("--" + name, required=True)
    args = p.parse_args()
    try:
        result = gate(args)
        print("PRODUCTION_RELEASE_GATE: PASS", result["export_sha256"])
    except (GateError, ValueError, KeyError, FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        Path(args.output).unlink(missing_ok=True)
        print("PRODUCTION_RELEASE_GATE: FAIL — " + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
