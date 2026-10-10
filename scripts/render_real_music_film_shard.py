#!/usr/bin/env python3
"""Render one exact picture shard with the canonical MainV2 FX executor."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--staged-manifest", type=Path, required=True)
    ap.add_argument("--lineage", type=Path, required=True)
    ap.add_argument("--input-root", type=Path, required=True)
    ap.add_argument("--source-root", type=Path, required=True)
    ap.add_argument("--project", type=Path, required=True)
    ap.add_argument("--engine-root", type=Path, required=True)
    ap.add_argument("--director-gate", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    engine = args.engine_root.resolve()
    sys.path.insert(0, str(engine))
    from scripts import render_real_music_film as canonical
    from scripts.render_lineage import receipt_identity, verify_bundle
    import cv2
    from general.reusable.fx_v2.executor import FXExecutor
    from general.reusable.fx_v2.runtime import FXContext
    from general.reusable.tools.execution_ledger import record
    from scripts.render_quality import AudioControls, QualityCollector, transition_prerolls

    lineage = verify_bundle(
        args.lineage, args.staged_manifest, args.input_root,
        source_root=args.source_root, engine_root=engine, project=args.project,
    )
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    fps, width, height, counts = canonical.validate_manifest(manifest)
    gate = json.loads(args.director_gate.read_text(encoding="utf-8"))
    if gate.get("schema") != "aivideoedit.director-harness-receipt.v1":
        raise RuntimeError("director/harness receipt is missing or invalid")
    if gate.get("jev", {}).get("decision") not in {"PASS", "CONTINUE"}:
        raise RuntimeError("director/harness gate did not authorize shard rendering")
    from scripts.render_lineage import require_receipt_identity
    require_receipt_identity(gate, lineage, args.lineage)
    shard_identity = {
        "shard": next((row.get("shard") for row in gate.get("shard_plan", [])
                       if row.get("start") == (manifest.get("shard") or {}).get("start_index")
                       and row.get("end") == (manifest.get("shard") or {}).get("end_index")), None),
        "start": (manifest.get("shard") or {}).get("start_index"),
        "end": (manifest.get("shard") or {}).get("end_index"),
    }
    if shard_identity["shard"] is None:
        raise RuntimeError("shard range was not authorized by the locked dynamic plan")
    lock_path = args.director_gate.parent / "FX_LOCK.json"
    if not lock_path.is_file() or canonical.digest(lock_path) != gate.get("fx_lock_sha256"):
        raise RuntimeError("shared canonical FX lock is missing or changed")
    music_path = args.director_gate.parent / "MUSIC_BEAT_EVIDENCE.json"
    if not music_path.is_file() or canonical.digest(music_path) != gate.get("music_evidence_sha256"):
        raise RuntimeError("measured music evidence is missing or changed")
    music_controls = AudioControls(json.loads(music_path.read_text(encoding="utf-8")))
    locked_effects = {str(x.get("id")) for x in gate.get("effects", []) if isinstance(x, dict)}
    locked_transitions = {str(x.get("id")) for x in gate.get("transitions", []) if isinstance(x, dict)}
    for shot in manifest["shots"]:
        for spec in shot.get("fx", []):
            if str(spec.get("id")) not in locked_effects:
                raise RuntimeError("shard effect is absent from shared FX lock: " + str(spec.get("id")))
        if shot.get("transition_out") and str(shot["transition_out"]) not in locked_transitions:
            raise RuntimeError("shard transition is absent from shared FX lock: " + str(shot["transition_out"]))

    args.out.mkdir(parents=True, exist_ok=True)
    cache = args.out / "verified_inputs"
    audio = canonical.stage(manifest["audio"], input_root=args.input_root.resolve(), cache=cache)
    sources = [canonical.stage(s["source"], input_root=args.input_root.resolve(), cache=cache) for s in manifest["shots"]]
    boundary = manifest.get("boundary_next_shot") if isinstance(manifest.get("boundary_next_shot"), dict) else None
    next_source = None
    if boundary:
        next_source = canonical.stage(boundary["source"], input_root=args.input_root.resolve(), cache=cache)
    ledger = args.out / "PRODUCTION_EXECUTION_LEDGER.json"
    for effect in sorted(locked_effects):
        record(ledger, project=manifest.get("production_id"), component="fx", subject=effect, stage="verified", actor="director_harness_gate", consumer="canonical_fx_executor")
    for transition in sorted(locked_transitions):
        record(ledger, project=manifest.get("production_id"), component="fx", subject=transition, stage="verified", actor="director_harness_gate", consumer="canonical_fx_executor")
    record(ledger, project=manifest.get("production_id"), component="director_harness", subject="DIRECTOR_HARNESS_RECEIPT.json", stage="consumed", actor="director_harness_gate", consumer="parallel_shard_renderer", required_consumption=True)
    record(ledger, project=manifest.get("production_id"), component="music", subject="MUSIC_BEAT_EVIDENCE.json", stage="consumed", actor="director_harness_gate", consumer="parallel_shard_renderer", required_consumption=True)

    fx = FXExecutor(seed=int(manifest.get("fx_seed", 302)), ledger_path=ledger, consumer="parallel_shard_renderer")
    target = args.out / "shard_video.mp4"
    writer = cv2.VideoWriter(str(target), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    if not writer.isOpened():
        raise RuntimeError("unable to open shard video encoder")
    srcs = [canonical.VisualSource(path, shot, width, height) for path, shot in zip(sources, manifest["shots"])]
    next_src = canonical.VisualSource(next_source, boundary, width, height) if next_source and boundary else None
    first_preroll = float((manifest.get("shard") or {}).get("entry_preroll_seconds") or 0.0)
    prerolls = transition_prerolls(manifest["shots"], first_preroll)
    quality = QualityCollector(fps, manifest["shots"], first_preroll=first_preroll,
                               proof_dir=args.out / "fx_proofs")
    timeline_start = float((manifest.get("shard") or {}).get("start_seconds") or 0.0)
    global_start_frame = int((manifest.get("shard") or {}).get("start_frame") or 0)
    total = 0
    try:
        for i, (shot, count) in enumerate(zip(manifest["shots"], counts)):
            for n in range(count):
                t = n / fps
                frame = srcs[i].at(prerolls[i] + t)
                quality.observe_source(shot["id"], frame, n)
                energy, transient = music_controls.at(timeline_start + total / fps)
                global_frame = global_start_frame + total
                ctx = FXContext(t=t, duration=count / fps, frame_index=global_frame, fps=fps, energy=energy, transient=transient)
                for spec in shot.get("fx", []):
                    before = frame.copy()
                    frame = fx.apply_frame(spec["id"], frame, ctx, params=spec.get("params") or {})
                    quality.effect(spec["id"], before, frame, global_frame, kind="effect",
                                   params=spec.get("params") or {})
                transition = shot.get("transition_out")
                transition_frames = min(max(1, round(float(shot.get("transition_seconds", 0.5)) * fps)), count)
                if transition and n >= count - transition_frames:
                    into = (n - (count - transition_frames) + 1) / transition_frames
                    relative = (n - (count - transition_frames)) / fps
                    if i + 1 < len(srcs):
                        incoming = srcs[i + 1].at(relative)
                    elif next_src is not None:
                        incoming = next_src.at(relative)
                    else:
                        raise RuntimeError("transition at shard boundary has no incoming source")
                    before = frame.copy()
                    frame = fx.apply_transition(transition, frame, incoming, into, ctx)
                    quality.effect(transition, before, frame, global_frame, kind="transition",
                                   params=shot.get("transition_params") or {})
                quality.observe_output(shot["id"], frame, n)
                writer.write(frame)
                total += 1
    finally:
        writer.release()
        for src in srcs:
            src.close()
        if next_src:
            next_src.close()
    expected = sum(counts)
    if total != expected or not target.is_file() or target.stat().st_size < 1024:
        raise RuntimeError(f"incomplete shard encoding: {total} != {expected}")
    info = canonical.probe(target)
    video = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
    if not video or video.get("width") != width or video.get("height") != height:
        raise RuntimeError("shard geometry or decode verification failed")
    receipt = {
        "schema": "aivideoedit.real-render-shard-receipt.v1",
        "production_id": lineage.get("production_id"),
        "start_index": (manifest.get("shard") or {}).get("start_index"),
        "end_index": (manifest.get("shard") or {}).get("end_index"),
        "shard": shard_identity["shard"],
        "start_frame": (manifest.get("shard") or {}).get("start_frame"),
        "frame_count": total,
        "duration_seconds": round(total / fps, 6),
        "fps": fps,
        "width": width,
        "height": height,
        "video_sha256": canonical.digest(target),
        "video_bytes": target.stat().st_size,
        "fx_lock_sha256": canonical.digest(lock_path),
        "director_harness_receipt_sha256": canonical.digest(args.director_gate),
        "music_evidence_sha256": gate.get("music_evidence_sha256"),
        "music_controls": music_controls.summary(total),
        "technical_visual_evidence": quality.summary(),
        "audio_sha256": canonical.digest(audio),
        "clip_sha256": {
            shot["id"]: canonical.digest(source)
            for shot, source in zip(manifest["shots"], sources)
        },
        "shard_manifest_sha256": canonical.digest(args.manifest),
        "ledger_sha256": canonical.digest(ledger),
        "human_visual_approval": False,
        "production_complete": False,
        **receipt_identity(lineage, args.lineage),
    }
    (args.out / "shard_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
