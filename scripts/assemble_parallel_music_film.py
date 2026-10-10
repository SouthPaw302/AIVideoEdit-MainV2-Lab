#!/usr/bin/env python3
"""Fan-in verified picture shards and mux the original WAV once."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
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


def load_verified_shards(shards_dir: Path, gate: dict, lineage: dict, lineage_path: Path):
    """Load fan-out products only when every byte and identity matches the lock."""
    from scripts.render_lineage import require_receipt_identity

    records = []
    for receipt_path in sorted(Path(shards_dir).glob("**/shard_receipt.json")):
        rec = json.loads(receipt_path.read_text(encoding="utf-8"))
        video = receipt_path.parent / "shard_video.mp4"
        shard_manifest = receipt_path.parent.parent / "manifest.json"
        require_receipt_identity(rec, lineage, lineage_path)
        if not video.is_file() or sha(video) != rec.get("video_sha256"):
            raise RuntimeError(f"shard video hash mismatch: {receipt_path}")
        if not shard_manifest.is_file() or sha(shard_manifest) != rec.get("shard_manifest_sha256"):
            raise RuntimeError(f"shard manifest hash mismatch: {receipt_path}")
        if rec.get("fx_lock_sha256") != gate.get("fx_lock_sha256"):
            raise RuntimeError(f"shard FX lock mismatch: {receipt_path}")
        shard_ledger = receipt_path.parent / "PRODUCTION_EXECUTION_LEDGER.json"
        if not shard_ledger.is_file() or sha(shard_ledger) != rec.get("ledger_sha256"):
            raise RuntimeError(f"shard execution ledger mismatch: {receipt_path}")
        if rec.get("audio_sha256") != lineage["audio_sha256"]:
            raise RuntimeError(f"shard audio byte identity mismatch: {receipt_path}")
        shard_data = json.loads(shard_manifest.read_text(encoding="utf-8"))
        expected_clips = {
            shot["id"]: lineage["clip_sha256"][shot["id"]]
            for shot in shard_data["shots"]
        }
        if rec.get("clip_sha256") != expected_clips:
            raise RuntimeError(f"shard source-byte identity mismatch: {receipt_path}")
        for effect in (rec.get("technical_visual_evidence") or {}).get("effects") or []:
            if not effect.get("proof_file"):
                continue
            proof = receipt_path.parent / "fx_proofs" / str(effect["proof_file"])
            if not proof.is_file() or sha(proof) != effect.get("proof_sha256"):
                raise RuntimeError(f"shard FX proof mismatch: {receipt_path}")
        records.append((int(rec.get("start_index")), int(rec.get("end_index")), rec, video))
    records.sort(key=lambda item: item[0])
    return records


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--original-manifest", type=Path, required=True)
    ap.add_argument("--lineage", type=Path, required=True)
    ap.add_argument("--input-root", type=Path, required=True)
    ap.add_argument("--source-root", type=Path, required=True)
    ap.add_argument("--project", type=Path, required=True)
    ap.add_argument("--engine-root", type=Path, required=True)
    ap.add_argument("--gate-dir", type=Path, required=True)
    ap.add_argument("--shards-dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    engine = args.engine_root.resolve()
    sys.path.insert(0, str(engine))
    from scripts import render_real_music_film as canonical
    from scripts.render_lineage import receipt_identity, verify_bundle
    from scripts.render_quality import bundle_fx_proofs, combine_visual_evidence

    lineage = verify_bundle(
        args.lineage, args.manifest, args.input_root,
        source_root=args.source_root, engine_root=engine, project=args.project,
        original_manifest=args.original_manifest,
    )
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    fps, width, height, counts = canonical.validate_manifest(manifest)
    total_frames = sum(counts)
    total_duration = total_frames / fps
    gate = json.loads((args.gate_dir / "DIRECTOR_HARNESS_RECEIPT.json").read_text(encoding="utf-8"))
    require_receipt_identity(gate, lineage, args.lineage)
    lock = args.gate_dir / "FX_LOCK.json"
    if canonical.digest(lock) != gate.get("fx_lock_sha256"):
        raise RuntimeError("director FX lock changed before assembly")
    source_qc_path = args.gate_dir / "SOURCE_MEDIA_QC.json"
    if not source_qc_path.is_file() or sha(source_qc_path) != gate.get("source_media_qc_sha256"):
        raise RuntimeError("source-media QC evidence is missing or changed")

    records = load_verified_shards(args.shards_dir, gate, lineage, args.lineage)
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
    expected_plan = [(row["shard"], row["start"], row["end"]) for row in gate.get("shard_plan", [])]
    actual_plan = [(rec.get("shard"), start, end) for start, end, rec, _video in records]
    if actual_plan != expected_plan:
        raise RuntimeError("fan-in shard identities differ from the locked dynamic plan")

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
    render_sha = sha(target)
    fx_proof_path = args.out / "FX_VISIBILITY_PROOF.zip"
    fx_proof_sha = bundle_fx_proofs(
        [(str(record[2].get("shard")), record[3].parent / "fx_proofs") for record in records],
        fx_proof_path,
    )
    visual_qc = combine_visual_evidence(manifest, [record[2] for record in records], gate, render_sha,
                                        fx_proof_sha)
    visual_qc_path = args.out / "VISUAL_QC_EVIDENCE.json"
    visual_qc_path.write_text(json.dumps(visual_qc, indent=2) + "\n", encoding="utf-8")
    if visual_qc["status"] != "PASS":
        raise RuntimeError("technical visual QC rejected the candidate: " + json.dumps(visual_qc["checks"], sort_keys=True))

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
    final_ledger = args.out / "PRODUCTION_EXECUTION_LEDGER.json"
    shutil.copyfile(lock, args.out / "FX_LOCK.json")
    shutil.copyfile(args.lineage, args.out / "RUN_LINEAGE.json")
    receipt = {
        "schema": "aivideoedit.real-render-receipt.v1",
        "production_id": lineage.get("production_id"),
        "status": "TECHNICAL_RENDER_PASS_VISUAL_REVIEW_PENDING",
        "human_visual_approval": False,
        "production_complete": False,
        "manifest_sha256": lineage["manifest_sha256"],
        "audio_sha256": lineage["audio_sha256"],
        "clip_sha256": lineage["clip_sha256"],
        "ledger_sha256": sha(final_ledger),
        "render_sha256": render_sha,
        "render_bytes": target.stat().st_size,
        "duration_seconds": measured,
        "render_frames": total_frames,
        "decoded_frames": decoded,
        "width": width,
        "height": height,
        "fps": fps,
        "resolution": [width, height],
        "video_codec": video.get("codec_name"),
        "audio_codec": sound.get("codec_name"),
        "model": "beat_this_onnx",
        "director_harness_receipt_sha256": sha(args.gate_dir / "DIRECTOR_HARNESS_RECEIPT.json"),
        "fx_lock_sha256": sha(lock),
        "fx": {"lock_sha256": sha(lock), "effects": gate.get("effects", []), "transitions": gate.get("transitions", [])},
        "visual_qc_sha256": sha(visual_qc_path),
        "fx_visibility_proof_sha256": fx_proof_sha,
        "music_controls": gate.get("music_controls"),
        "shards": [{
            "start_index": s,
            "end_index": e,
            "video_sha256": r.get("video_sha256"),
            "shard_manifest_sha256": r.get("shard_manifest_sha256"),
            "ledger_sha256": r.get("ledger_sha256"),
        } for s, e, r, _ in records],
        "jev": gate.get("jev"),
        "harness_route": gate.get("harness_route"),
        "main_commit": (gate.get("core") or {}).get("main_commit"),
        **receipt_identity(lineage, args.lineage),
    }
    (args.out / "render_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    (args.out / "DIRECTOR_HARNESS_RECEIPT.json").write_text(json.dumps(gate, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"result": "PASS", "render": str(target), "duration_seconds": measured, "frames": decoded, "shards": len(records), "render_sha256": receipt["render_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
