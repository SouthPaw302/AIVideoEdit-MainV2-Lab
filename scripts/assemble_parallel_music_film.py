#!/usr/bin/env python3
"""Fan-in verified picture shards and mux the original WAV once."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run(cmd: list[str], timeout: int = 7200):
    p = subprocess.run([str(x) for x in cmd], capture_output=True, text=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError((p.stderr or p.stdout)[-2400:])
    return p.stdout


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--input-root", type=Path, required=True)
    ap.add_argument("--engine-root", type=Path, required=True)
    ap.add_argument("--gate-dir", type=Path, required=True)
    ap.add_argument("--shards-dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    engine = args.engine_root.resolve()
    sys.path.insert(0, str(engine))
    from scripts import render_real_music_film as canonical

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    fps, width, height, counts = canonical.validate_manifest(manifest)
    total_frames = sum(counts)
    total_duration = total_frames / fps
    gate = json.loads((args.gate_dir / "DIRECTOR_HARNESS_RECEIPT.json").read_text(encoding="utf-8"))
    lock = args.gate_dir / "FX_LOCK.json"
    if canonical.digest(lock) != gate.get("fx_lock_sha256"):
        raise RuntimeError("director FX lock changed before assembly")

    records = []
    for receipt_path in sorted(args.shards_dir.glob("**/shard_receipt.json")):
        rec = json.loads(receipt_path.read_text(encoding="utf-8"))
        video = receipt_path.parent / "shard_video.mp4"
        if not video.is_file() or canonical.digest(video) != rec.get("video_sha256"):
            raise RuntimeError(f"shard video hash mismatch: {receipt_path}")
        if rec.get("fx_lock_sha256") != gate.get("fx_lock_sha256"):
            raise RuntimeError(f"shard FX lock mismatch: {receipt_path}")
        records.append((int(rec.get("start_index")), int(rec.get("end_index")), rec, video))
    records.sort(key=lambda x: x[0])
    if not records:
        raise RuntimeError("no shard receipts were downloaded")
    expected_start = 0
    frame_sum = 0
    for start, end, rec, _video in records:
        if start != expected_start or end <= start:
            raise RuntimeError("shards are not contiguous")
        expected_start = end
        frame_sum += int(rec.get("frame_count") or 0)
    if expected_start != len(manifest["shots"]) or frame_sum != total_frames:
        raise RuntimeError(f"shard coverage mismatch: shots={expected_start}/{len(manifest['shots'])}, frames={frame_sum}/{total_frames}")

    args.out.mkdir(parents=True, exist_ok=True)
    concat = args.out / "shards.concat.txt"
    lines = []
    for _start, _end, _rec, video in records:
        lines.append("file '" + str(video.resolve()).replace("'", "'\\''") + "'")
    concat.write_text("\n".join(lines) + "\n", encoding="utf-8")
    picture = args.out / "picture_assembled.mp4"
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", concat, "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", picture])

    audio = canonical.stage(manifest["audio"], input_root=args.input_root.resolve(), cache=args.out / "verified_inputs")
    target = args.out / "real_music_film.mp4"
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", picture, "-i", audio, "-map", "0:v:0", "-map", "1:a:0", "-t", f"{total_duration:.6f}", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", target])
    info = canonical.probe(target)
    video = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
    sound = next((s for s in info.get("streams", []) if s.get("codec_type") == "audio"), None)
    measured = float(info.get("format", {}).get("duration") or 0)
    decoded = int(video.get("nb_read_frames") or video.get("nb_frames") or 0) if video else 0
    if not video or not sound or video.get("width") != width or video.get("height") != height:
        raise RuntimeError("assembled master is missing expected streams or geometry")
    if abs(measured - total_duration) > max(0.2, 2 / fps) or (decoded and abs(decoded - total_frames) > 1):
        raise RuntimeError(f"assembled duration/frame mismatch: {measured:.3f}s/{decoded} vs {total_duration:.3f}s/{total_frames}")
    run(["ffmpeg", "-hide_banner", "-v", "error", "-i", target, "-f", "null", "-"])
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", target, "-vf", "fps=1/5,scale=320:180,tile=3x2", "-frames:v", "1", args.out / "contact_sheet.jpg"], timeout=180)

    events = []
    for _start, _end, _rec, video_path in records:
        ledger_path = video_path.parent / "PRODUCTION_EXECUTION_LEDGER.json"
        if ledger_path.is_file():
            data = json.loads(ledger_path.read_text(encoding="utf-8"))
            events.extend(data.get("events") or [])
    events.append({"component": "director_harness", "subject": "DIRECTOR_HARNESS_RECEIPT.json", "stage": "consumed", "actor": "parallel_assembly", "consumer": "render_receipt", "required_consumption": True})
    events.append({"component": "music", "subject": "MUSIC_BEAT_EVIDENCE.json", "stage": "consumed", "actor": "parallel_assembly", "consumer": "render_receipt", "required_consumption": True})
    ledger = {"schema": "aivideoedit.production-execution-ledger.v1", "project": manifest.get("production_id"), "events": events}
    (args.out / "PRODUCTION_EXECUTION_LEDGER.json").write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    receipt = {
        "schema": "aivideoedit.real-render-receipt.v1",
        "production_id": manifest.get("production_id"),
        "status": "TECHNICAL_RENDER_PASS_VISUAL_REVIEW_PENDING",
        "human_visual_approval": False,
        "production_complete": False,
        "manifest_sha256": sha(args.manifest),
        "audio_sha256": sha(audio),
        "render_sha256": sha(target),
        "render_bytes": target.stat().st_size,
        "duration_seconds": measured,
        "render_frames": total_frames,
        "decoded_frames": decoded,
        "width": width,
        "height": height,
        "fps": fps,
        "model": "beat_this_onnx",
        "director_harness_receipt_sha256": sha(args.gate_dir / "DIRECTOR_HARNESS_RECEIPT.json"),
        "fx_lock_sha256": sha(lock),
        "fx": {"effects": gate.get("effects", []), "transitions": gate.get("transitions", [])},
        "shards": [{"start_index": s, "end_index": e, "receipt": r.get("video_sha256")} for s, e, r, _ in records],
        "jev": gate.get("jev"),
        "harness_route": gate.get("harness_route"),
        "main_commit": (gate.get("core") or {}).get("main_commit"),
    }
    (args.out / "render_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    (args.out / "DIRECTOR_HARNESS_RECEIPT.json").write_text(json.dumps(gate, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"result": "PASS", "render": str(target), "duration_seconds": measured, "frames": decoded, "shards": len(records), "render_sha256": receipt["render_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
