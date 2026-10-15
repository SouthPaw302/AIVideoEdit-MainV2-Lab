#!/usr/bin/env python3
"""Fail-closed technical verifier for synthetic Godot movie-export evidence."""
import argparse
import hashlib
import json
import subprocess
import sys
import wave
from pathlib import Path

FPS = 24
WIDTH, HEIGHT = 640, 360

def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def ffprobe(path):
    p = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)], capture_output=True, text=True, check=True)
    return json.loads(p.stdout)

def verify(directory, label, expected_frames):
    directory = Path(directory)
    frames = sorted(directory.glob("proof[0-9]*.png"))
    if len(frames) != expected_frames:
        raise ValueError(f"{label}: expected {expected_frames} PNG frames, found {len(frames)}")
    if frames[0].stat().st_size < 512:
        raise ValueError(f"{label}: first frame blank/tiny")
    hashes = [sha(frames[0]), sha(frames[len(frames)//2]), sha(frames[-1])]
    if len(set(hashes)) < 2:
        raise ValueError(f"{label}: no measured change across sampled frames")
    wav = directory / "proof.wav"
    if not wav.is_file() or wav.stat().st_size < 44:
        raise ValueError(f"{label}: Godot movie-writer WAV missing")
    with wave.open(str(wav), "rb") as audio:
        wav_details = {"channels": audio.getnchannels(), "rate": audio.getframerate(), "frames": audio.getnframes()}
        if wav_details["rate"] <= 0 or wav_details["frames"] <= 0:
            raise ValueError(f"{label}: empty WAV")
    mp4 = directory / "proof.mp4"
    media = ffprobe(mp4)
    video = [s for s in media["streams"] if s["codec_type"] == "video"]
    if len(video) != 1 or (video[0]["width"], video[0]["height"]) != (WIDTH, HEIGHT):
        raise ValueError(f"{label}: wrong output geometry")
    if video[0].get("nb_frames") and int(video[0]["nb_frames"]) != expected_frames:
        raise ValueError(f"{label}: wrong output frame count")
    duration = float(media["format"]["duration"])
    if abs(duration - expected_frames / FPS) > 0.2:
        raise ValueError(f"{label}: unexpected duration {duration}")
    return {
        "label": label, "status": "TECHNICAL_SMOKE_PASS", "source_kind": "synthetic_procedural_fixture",
        "production_media": False, "visual_acceptance": "NOT_GRANTED",
        "fps": FPS, "resolution": [WIDTH, HEIGHT], "frames": len(frames),
        "movie_duration_seconds": duration, "sample_frame_hashes": hashes,
        "wav": wav_details, "mp4_sha256": sha(mp4),
        "first_frame_sha256": hashes[0], "last_frame_sha256": hashes[-1],
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", required=True)
    p.add_argument("--godot-version", required=True)
    p.add_argument("--source-sha", required=True)
    a = p.parse_args()
    root = Path(a.root)
    findings = [verify(root / "2d", "Godot canvas/rendering", 48), verify(root / "3d", "Godot 3D rendering", 48)]
    report = {"schema": "aivideoedit.godot-render-technical-smoke.v1", "godot_version": a.godot_version, "lab_source_sha": a.source_sha, "results": findings, "warnings": ["Synthetic media only, does not prove artistic quality", "No approved stills/audio/FX; not an AIVideoEdit release", "GitHub artifact is temporary, not persistent release storage"]}
    (root / "technical_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as ex:
        print(f"GODOT TECHNICAL SMOKE FAIL: {ex}", file=sys.stderr)
        sys.exit(2)
