#!/usr/bin/env python3
"""Render a REAL, user-directed music film from byte-verified media.

No synthetic placeholders, no self-approval, no silent source regeneration.
Uses the inherited MainV2 canonical FX executor, precompile gate and music worker.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as fd:
        for part in iter(lambda: fd.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def run(cmd, *, timeout=3600):
    p = subprocess.run([str(x) for x in cmd], text=True, capture_output=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError("command failed (" + str(p.returncode) + "): " + " ".join(map(str, cmd[:6])) + "\n" + p.stderr[-2400:])
    return p.stdout


def probe(path):
    return json.loads(run(["ffprobe", "-v", "error", "-count_frames", "-show_streams", "-show_format", "-of", "json", path], timeout=180))


def sha_matches(path, expected):
    got = digest(path)
    if got != expected.lower():
        raise RuntimeError("source bytes changed: " + str(path) + " (expected " + expected + ", received " + got + ")")
    return got


def stage(media, *, input_root, cache):
    if not isinstance(media, dict):
        raise ValueError("media specification must be an object")
    want = str(media.get("sha256") or "").lower()
    if not re.fullmatch(r"[0-9a-f]{64}", want):
        raise ValueError("every media source requires an actual SHA-256")
    if media.get("path") and not media.get("url"):
        f = (input_root / str(media["path"])).resolve()
        if input_root not in f.parents and f != input_root:
            raise ValueError("source media path escapes input root")
        if not f.is_file():
            raise FileNotFoundError(f)
        sha_matches(f, want)
        return f
    url = str(media.get("url") or "")
    if not url.startswith("https://"):
        raise ValueError("source must be a local file or an HTTPS URL")
    cache.mkdir(parents=True, exist_ok=True)
    suffix = Path(urllib.parse.urlsplit(url).path).suffix.lower()
    if suffix not in (".wav", ".mp3", ".flac", ".mp4", ".mov", ".mkv", ".png", ".jpg", ".jpeg", ".webm"):
        suffix = ".media"
    target = cache / (want + suffix)
    if target.is_file():
        sha_matches(target, want)
        return target
    tmp = target.with_suffix(target.suffix + ".partial")
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "AIVideoEdit-Lab-RealRenderer/1.0"})
        try:
            with urllib.request.urlopen(request, timeout=180) as response, tmp.open("wb") as fd:
                while True:
                    block = response.read(1024 * 1024)
                    if not block:
                        break
                    fd.write(block)
        except Exception as http_error:
            # Public GitHub release may require authenticated asset download
            # in restricted runners; only exact release URLs qualify.
            match = re.fullmatch(r"https://github.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/releases/download/([^/]+)/([^/]+)", url)
            if match is None or shutil.which("gh") is None:
                raise
            owner_repo, tag, filename = match.groups()
            gh = subprocess.run(["gh", "release", "download", tag, "--repo", owner_repo,
                                 "--pattern", filename, "--dir", str(cache), "--clobber"],
                                capture_output=True, text=True, timeout=180)
            retrieved = cache / filename
            if gh.returncode or not retrieved.is_file():
                raise RuntimeError("verified source download failed: " + filename + " " + gh.stderr[-500:]) from http_error
            retrieved.replace(tmp)
        sha_matches(tmp, want)
        tmp.replace(target)
        return target
    finally:
        tmp.unlink(missing_ok=True)


def validate_manifest(m):
    if m.get("schema") != "aivideoedit.real-render.v1":
        raise ValueError("unsupported render manifest schema")
    if m.get("render_authorization") != "explicit_user_render_request":
        raise ValueError("missing explicit user authorization to render; no agent self-approval")
    if not isinstance(m.get("shots"), list) or not m["shots"]:
        raise ValueError("real render requires authored shot entries")
    ids = [s.get("id") for s in m["shots"]]
    if any(not isinstance(x, str) or not x for x in ids) or len(set(ids)) != len(ids):
        raise ValueError("shot IDs must be unique and non-empty")
    output = m.get("output") or {}
    fps = int(output.get("fps", 24))
    width = int(output.get("width", 1280))
    height = int(output.get("height", 720))
    if not (1 <= fps <= 60 and 160 <= width <= 3840 and 90 <= height <= 2160 and width % 2 == 0 and height % 2 == 0):
        raise ValueError("invalid output geometry")
    frames = []
    for shot in m["shots"]:
        d = float(shot.get("duration_seconds") or 0)
        n = round(d * fps)
        if n < 1 or abs(n / fps - d) > 0.03:
            raise ValueError("shot duration must resolve to whole frames: " + shot["id"])
        if shot.get("source") is None:
            raise ValueError("real source missing: " + shot["id"])
        frames.append(n)
    if sum(frames) > 60 * 60 * fps:
        raise ValueError("render exceeds one hour; split into approved bounded jobs")
    if not isinstance(m.get("audio"), dict):
        raise ValueError("real audio is mandatory")
    return fps, width, height, frames


def fit_frame(im, width, height, mode):
    import cv2
    if im is None or im.size == 0:
        raise RuntimeError("undecodable source frame")
    h, w = im.shape[:2]
    scale = max(width / w, height / h) if mode == "cover" else min(width / w, height / h)
    nw, nh = max(1, round(w * scale)), max(1, round(h * scale))
    resized = cv2.resize(im, (nw, nh), interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC)
    if mode == "cover":
        left = (nw - width) // 2
        top = (nh - height) // 2
        return resized[top:top + height, left:left + width].copy()
    import numpy as np
    canvas = np.zeros((height, width, 3), dtype=np.uint8)
    canvas[(height - nh) // 2:(height - nh) // 2 + nh, (width - nw) // 2:(width - nw) // 2 + nw] = resized
    return canvas


class VisualSource:
    def __init__(self, path, shot, width, height):
        import cv2
        self.path = path
        self.mode = str(shot.get("fit") or "cover")
        if self.mode not in ("cover", "contain"):
            raise ValueError("fit must be cover or contain")
        self.width, self.height = width, height
        self.offset = float(shot.get("source_start_seconds") or 0)
        self.loop = shot.get("loop") is True
        if self.offset < 0:
            raise ValueError("negative source offset")
        self.still = None
        self.cap = None
        self.cursor = -1
        self.video_fps = 0
        if path.suffix.lower() in (".jpg", ".jpeg", ".png"):
            self.still = cv2.imread(str(path), cv2.IMREAD_COLOR)
            if self.still is None:
                raise RuntimeError("image decode failed: " + str(path))
            self.still = fit_frame(self.still, width, height, self.mode)
        else:
            self.cap = cv2.VideoCapture(str(path))
            if not self.cap.isOpened():
                raise RuntimeError("video decode failed: " + str(path))
            self.video_fps = self.cap.get(cv2.CAP_PROP_FPS)
            if not self.video_fps or self.video_fps <= 0:
                raise RuntimeError("source video missing frame rate: " + str(path))
            self.count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

    def at(self, seconds):
        import cv2
        if self.still is not None:
            return self.still.copy()
        frame_idx = round((self.offset + seconds) * self.video_fps)
        if self.count and frame_idx >= self.count:
            if self.loop:
                frame_idx %= self.count
            else:
                raise RuntimeError("clip too short for requested shot: " + str(self.path))
        if frame_idx != self.cursor + 1:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ok, frame = self.cap.read()
        if not ok or frame is None:
            raise RuntimeError("source video exhausted or corrupt: " + str(self.path))
        self.cursor = frame_idx
        return fit_frame(frame, self.width, self.height, self.mode)

    def close(self):
        if self.cap is not None:
            self.cap.release()


def fx_lock(manifest, out):
    import json
    fx = []
    transitions = []
    for shot in manifest["shots"]:
        for spec in shot.get("fx", []):
            eid = str(spec.get("id") or "")
            if not eid:
                raise ValueError("effect missing canonical FX ID")
            fx.append({"id": eid})
        if shot.get("transition_out"):
            transitions.append({"id": str(shot["transition_out"])})
    fx = list({v["id"]: v for v in fx}.values())
    transitions = list({v["id"]: v for v in transitions}.values())
    if not fx and not transitions:
        return None, fx, transitions
    req = {
        "schema": "aivideoedit.fx-requirements.v2",
        "project": manifest.get("production_id"),
        "runtime": "aivideoedit-fx-v2",
        "seed": int(manifest.get("fx_seed", 302)),
        "effects": fx,
        "transitions": transitions,
        "render_inputs": ["scripts/render_real_music_film.py"],
    }
    req_file = out / "FX_REQUIREMENTS.json"
    req_file.write_text(json.dumps(req, indent=2) + "\n")
    locked = out / "FX_LOCK.json"
    gate = REPO / "general/reusable/fx_v2/precompile_gate.py"
    run([sys.executable, gate, "--manifest", req_file, "--lock-out", locked])
    run([sys.executable, gate, "--manifest", req_file, "--verify-lock", locked])
    return locked, fx, transitions


def render(manifest_path, input_root, out, *, require_onnx=False):
    import cv2
    from general.reusable.fx_v2.executor import FXExecutor
    from general.reusable.fx_v2.runtime import FXContext
    from general.reusable.tools.execution_ledger import record

    out.mkdir(parents=True, exist_ok=True)
    m = json.loads(manifest_path.read_text(encoding="utf-8"))
    fps, width, height, counts = validate_manifest(m)
    source_cache = out / "verified_inputs"
    audio = stage(m["audio"], input_root=input_root, cache=source_cache)
    sources = [stage(s["source"], input_root=input_root, cache=source_cache) for s in m["shots"]]
    audio_info = probe(audio)
    streams = audio_info.get("streams") or []
    if not any(s.get("codec_type") == "audio" for s in streams):
        raise RuntimeError("original audio is absent")
    duration = sum(counts) / fps
    audio_duration = float(audio_info.get("format", {}).get("duration") or 0)
    audio_offset = float(m["audio"].get("start_seconds") or 0)
    if audio_offset < 0 or audio_duration + 0.05 < audio_offset + duration:
        raise RuntimeError("source song is shorter than approved picture duration")
    lock_file, locked_fx, locked_transitions = fx_lock(m, out)
    ledger = out / "PRODUCTION_EXECUTION_LEDGER.json"
    for x in locked_fx + locked_transitions:
        record(ledger, component="fx", subject=x["id"], stage="selected",
               actor="approved_render_manifest", consumer="canonical_fx_executor", required_execution=True)
        record(ledger, component="fx", subject=x["id"], stage="verified",
               actor="fx_precompile_gate", consumer="canonical_fx_executor", required_execution=True)
    music_evidence = None
    if require_onnx:
        from general.reusable.tools.music_beat_worker import analyze_music
        music_evidence = analyze_music(audio)
        if music_evidence.get("engine") != "beat_this_onnx" or music_evidence.get("model_resolution", {}).get("used_fallback"):
            raise RuntimeError("real Beat This ONNX inference required; fallback is forbidden")
        (out / "MUSIC_BEAT_EVIDENCE.json").write_text(json.dumps(music_evidence, indent=2) + "\n")
        record(ledger, component="onnx", subject="music-beat-onnx-v1", stage="executed",
               actor="music_beat_worker", consumer="render_music_evidence",
               evidence={"bpm": music_evidence.get("bpm"), "beats": len(music_evidence.get("beat_positions_seconds") or [])},
               required_consumption=True)
        record(ledger, component="onnx", subject="music-beat-onnx-v1", stage="consumed",
               actor="render_music_evidence", consumer="render_receipt")
    # JEV is the bounded go/no-go director decision, not a replacement for real QC.
    from general.reusable.tools.jev_decision import decide
    fx_declared = any(s.get("fx") or s.get("transition_out") for s in m["shots"])
    jev = decide({
        "gate": "PASS",
        "checks": {
            "authorized_render_plan": m["render_authorization"] == "explicit_user_render_request",
            "verified_picture_and_audio": bool(audio and sources),
            "canonical_fx_lock": bool(lock_file) if fx_declared else True,
            "onnx_evidence_available": bool(music_evidence) if require_onnx else True,
        },
        "model_observations": ([{
            "authority": "evidence_only",
            "confidence": music_evidence.get("confidence", 0.9),
        }] if music_evidence else []),
        "next_action_permitted": True,
    })
    (out / "JEV_DECISION.json").write_text(json.dumps(jev, indent=2) + "\n")
    if jev.get("decision") not in ("PASS", "CONTINUE"):
        raise RuntimeError("JEV denied real film rendering: " + str(jev))
    record(ledger, component="jev", subject="verified_render_plan", stage="executed",
           actor="jev_decision", consumer="real_film_renderer",
           evidence=jev, required_consumption=True)
    record(ledger, component="jev", subject="verified_render_plan", stage="consumed",
           actor="real_film_renderer", consumer="render_receipt")
    fx = FXExecutor(seed=int(m.get("fx_seed", 302)), ledger_path=ledger, consumer="real_film_renderer")
    raw = out / "picture_intermediate.mp4"
    writer = cv2.VideoWriter(str(raw), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    if not writer.isOpened():
        raise RuntimeError("unable to open video encoder")
    srcs = [VisualSource(path, shot, width, height) for path, shot in zip(sources, m["shots"])]
    total = 0
    try:
        for i, (shot, count) in enumerate(zip(m["shots"], counts)):
            for n in range(count):
                t = n / fps
                frame = srcs[i].at(t)
                ctx = FXContext(t=t, duration=count / fps, frame_index=total, fps=fps, energy=0.35, transient=0.1)
                for spec in shot.get("fx", []):
                    frame = fx.apply_frame(spec["id"], frame, ctx, params=spec.get("params") or {})
                transition = shot.get("transition_out")
                transition_frames = min(max(1, round(float(shot.get("transition_seconds", 0.5)) * fps)), count)
                if transition and i + 1 < len(srcs) and n >= count - transition_frames:
                    into = (n - (count - transition_frames) + 1) / transition_frames
                    next_frame = srcs[i + 1].at((n - (count - transition_frames)) / fps)
                    frame = fx.apply_transition(transition, frame, next_frame, into, ctx)
                writer.write(frame)
                total += 1
    finally:
        writer.release()
        for src in srcs:
            src.close()
    if total != sum(counts) or not raw.is_file() or raw.stat().st_size < 1024:
        raise RuntimeError("incomplete video encoding")
    target = out / "real_music_film.mp4"
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-i", raw, "-ss", f"{audio_offset:.6f}", "-i", audio,
         "-map", "0:v:0", "-map", "1:a:0", "-t", f"{duration:.6f}",
         "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", target], timeout=7200)
    info = probe(target)
    video = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    sound = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    measured = float(info["format"].get("duration") or 0)
    if video is None or sound is None or video.get("width") != width or video.get("height") != height:
        raise RuntimeError("decoded master is missing expected streams or geometry")
    if abs(measured - duration) > max(0.2, 2 / fps):
        raise RuntimeError("rendered duration mismatch")
    decoded_frames = int(video.get("nb_read_frames") or video.get("nb_frames") or 0)
    if decoded_frames and abs(decoded_frames - total) > 1:
        raise RuntimeError("decoded frame count mismatch")
    run(["ffmpeg", "-hide_banner", "-v", "error", "-i", target, "-f", "null", "-"], timeout=7200)
    fx_result = {"lock_sha256": digest(lock_file), "effects": locked_fx, "transitions": locked_transitions} if lock_file else {"effects": [], "transitions": []}
    receipt = {
        "schema": "aivideoedit.real-render-receipt.v1", "production_id": m.get("production_id"),
        "status": "TECHNICAL_RENDER_PASS_VISUAL_REVIEW_PENDING", "human_visual_approval": False,
        "production_complete": False, "manifest_sha256": digest(manifest_path),
        "audio_sha256": digest(audio), "clip_sha256": {s["id"]: digest(p) for s, p in zip(m["shots"], sources)},
        "render_sha256": digest(target), "render_bytes": target.stat().st_size,
        "duration_seconds": duration, "render_frames": total, "decoded_frames": decoded_frames,
        "fps": fps, "resolution": [width, height], "video_codec": video.get("codec_name"),
        "audio_codec": sound.get("codec_name"), "fx": fx_result,
        "model": music_evidence.get("engine") if music_evidence else "not_requested",
        "jev": jev,
        "source_lineage": "AIVideoEdit/main -> AIVideoEdit/MainV2 -> AIVideoEdit-MainV2-Lab/main",
    }
    (out / "render_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", target,
         "-vf", "fps=1/5,scale=320:180,tile=3x2", "-frames:v", "1", out / "contact_sheet.jpg"], timeout=180)
    print(json.dumps(receipt, indent=2))
    return receipt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--input-root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--require-onnx", action="store_true")
    args = parser.parse_args()
    render(args.manifest.resolve(), args.input_root.resolve(), args.out.resolve(), require_onnx=args.require_onnx)


if __name__ == "__main__":
    main()
