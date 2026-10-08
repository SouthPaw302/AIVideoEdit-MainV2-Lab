#!/usr/bin/env python3
"""Evidence-producing reference and music analysis for workstation projects.

This module does not make creative decisions. It produces machine-observable
reference coverage and audio signal evidence, then records only the state flags
that those observations support. Genre and lyrics authority remain explicit
user/agent inputs.
"""
from __future__ import annotations

import array
import json
import math
import shutil
import subprocess
import wave
from pathlib import Path

import server as base
import production_project
from core_adapter import CORE


def _read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _run(cmd: list[str], timeout: int = 1800) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)


def _asset_map(project_id: str) -> dict[str, dict]:
    with base.LOCK:
        return {a["id"]: dict(a) for a in base.STATE["assets"] if a.get("project") == project_id}


def _extract_frame(source: Path, target: Path, timestamp: float) -> bool:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg is required for reference analysis")
    target.parent.mkdir(parents=True, exist_ok=True)
    p = _run([
        ffmpeg, "-y", "-ss", f"{max(0.0, timestamp):.3f}", "-i", str(source),
        "-frames:v", "1", "-vf", "scale='min(1280,iw)':-2", "-q:v", "3", str(target),
    ], timeout=180)
    return p.returncode == 0 and target.is_file()


def _analyze_video(ref: dict, asset: dict, analysis_root: Path, contract: dict) -> dict:
    source = Path(asset["local_path"])
    duration = float(ref.get("duration_seconds") or 0)
    total_frames = int(ref.get("total_frames") or 0)
    policy = contract.get("reference_policy", {})
    short = duration <= float(policy.get("short_video_max_seconds", 30.0)) and total_frames <= int(policy.get("short_video_max_frames", 1800))
    out_dir = analysis_root / str(asset["id"]) / "frames"
    shutil.rmtree(out_dir, ignore_errors=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg is required for reference analysis")

    result = dict(ref)
    if short:
        pattern = out_dir / "frame_%06d.jpg"
        p = _run([ffmpeg, "-y", "-i", str(source), "-vsync", "0", "-q:v", "4", str(pattern)], timeout=1800)
        files = sorted(out_dir.glob("frame_*.jpg"))
        if p.returncode != 0 or not files:
            raise RuntimeError(f"all-frame extraction failed for {asset.get('filename')}: {(p.stderr or p.stdout)[-500:]}")
        # FFmpeg's decoded-frame count is authoritative for this pass. Keep the
        # canonical total aligned to observed decoded frames so ext == total.
        result.update({
            "total_frames": len(files),
            "extracted_frames": len(files),
            "extraction_policy": "all_frames",
            "sampling_description": "Every decodable frame extracted for canonical short-reference analysis.",
            "coverage": [{"start_seconds": 0.0, "end_seconds": duration, "frames": len(files)}],
            "analysis_complete": True,
            "analysis_evidence_uri": f"aive://analysis/{asset['id']}/frames",
        })
        return result

    # Long references: combine broad temporal coverage with extra scene-change
    # samples. The broad samples prevent scene detection from leaving gaps.
    broad_count = 12 if duration >= 12 else max(4, int(math.ceil(duration)))
    broad_times = [duration * (i + 0.5) / broad_count for i in range(broad_count)] if duration > 0 else [0.0]
    broad_files = []
    for i, ts in enumerate(broad_times, start=1):
        target = out_dir / f"coverage_{i:03d}.jpg"
        if _extract_frame(source, target, ts):
            broad_files.append(target)

    scene_dir = out_dir / "scenes"
    scene_dir.mkdir(parents=True, exist_ok=True)
    scene_pattern = scene_dir / "scene_%04d.jpg"
    scene = _run([
        ffmpeg, "-y", "-i", str(source),
        "-vf", "select='gt(scene,0.35)',scale='min(1280,iw)':-2",
        "-vsync", "vfr", "-frames:v", "24", "-q:v", "4", str(scene_pattern),
    ], timeout=1800)
    scene_files = sorted(scene_dir.glob("scene_*.jpg")) if scene.returncode == 0 else []
    extracted = len(broad_files) + len(scene_files)
    if extracted <= 0:
        raise RuntimeError(f"meaningful sampling failed for {asset.get('filename')}")
    coverage = []
    for i, ts in enumerate(broad_times):
        half = duration / broad_count / 2 if broad_count else 0
        coverage.append({"start_seconds": round(max(0.0, ts - half), 3), "end_seconds": round(min(duration, ts + half), 3), "sample": i + 1})
    result.update({
        "extracted_frames": extracted,
        "extraction_policy": "meaningful_sampling",
        "sampling_description": f"{len(broad_files)} evenly distributed coverage frames plus {len(scene_files)} scene-change frames at threshold 0.35.",
        "coverage": coverage,
        "analysis_complete": True,
        "analysis_evidence_uri": f"aive://analysis/{asset['id']}/frames",
    })
    return result


def _audio_envelope(source: Path, temp_wav: Path) -> tuple[list[float], float]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg is required for music analysis")
    temp_wav.parent.mkdir(parents=True, exist_ok=True)
    p = _run([ffmpeg, "-y", "-i", str(source), "-vn", "-ac", "1", "-ar", "8000", "-c:a", "pcm_s16le", str(temp_wav)], timeout=900)
    if p.returncode != 0 or not temp_wav.is_file():
        raise RuntimeError(f"audio decode failed: {(p.stderr or p.stdout)[-500:]}")
    with wave.open(str(temp_wav), "rb") as wf:
        rate = wf.getframerate()
        samples = array.array("h", wf.readframes(wf.getnframes()))
    if not samples:
        raise RuntimeError("decoded audio is empty")
    window = max(1, int(rate * 0.10))
    envelope = []
    for start in range(0, len(samples), window):
        chunk = samples[start:start + window]
        if not chunk:
            continue
        mean_sq = sum(float(x) * float(x) for x in chunk) / len(chunk)
        envelope.append(math.sqrt(mean_sq) / 32768.0)
    return envelope, 0.10


def _tempo_from_envelope(envelope: list[float], step: float) -> tuple[float | None, float]:
    if len(envelope) < 20:
        return None, 0.0
    onset = [0.0]
    for i in range(1, len(envelope)):
        onset.append(max(0.0, envelope[i] - envelope[i - 1]))
    mean = sum(onset) / len(onset)
    x = [v - mean for v in onset]
    energy = sum(v * v for v in x)
    if energy <= 1e-12:
        return None, 0.0
    best = (0.0, None)
    # 55-190 BPM search range.
    min_lag = max(1, int(round((60.0 / 190.0) / step)))
    max_lag = max(min_lag + 1, int(round((60.0 / 55.0) / step)))
    for lag in range(min_lag, min(max_lag, len(x) // 2) + 1):
        score = sum(x[i] * x[i - lag] for i in range(lag, len(x))) / energy
        if score > best[0]:
            best = (score, lag)
    if best[1] is None:
        return None, 0.0
    bpm = 60.0 / (best[1] * step)
    return round(bpm, 2), round(max(0.0, min(1.0, best[0])), 3)


def _music_analysis(asset: dict, analysis_root: Path) -> dict:
    source = Path(asset["local_path"])
    wav = analysis_root / str(asset["id"]) / "analysis_mono.wav"
    envelope, step = _audio_envelope(source, wav)
    try:
        wav.unlink()
    except Exception:
        pass
    bpm, confidence = _tempo_from_envelope(envelope, step)
    duration = float((asset.get("metadata") or {}).get("duration_seconds") or len(envelope) * step)
    points = []
    stride = max(1, len(envelope) // 40)
    peak = max(envelope) if envelope else 1.0
    for i in range(0, len(envelope), stride):
        points.append({"seconds": round(i * step, 2), "relative_energy": round(envelope[i] / peak if peak else 0.0, 3)})

    sections = []
    section_count = 8 if duration >= 80 else 4
    bins = max(1, len(envelope) // section_count)
    avgs = []
    for i in range(section_count):
        part = envelope[i * bins:(i + 1) * bins] if i < section_count - 1 else envelope[i * bins:]
        avgs.append(sum(part) / len(part) if part else 0.0)
    avg_all = sum(avgs) / len(avgs) if avgs else 0.0
    for i, value in enumerate(avgs):
        start = duration * i / section_count
        end = duration * (i + 1) / section_count
        label = "high" if value > avg_all * 1.18 else "low" if value < avg_all * 0.82 else "medium"
        sections.append({"index": i + 1, "start_seconds": round(start, 2), "end_seconds": round(end, 2), "energy": label, "mean_rms": round(value, 5)})

    cue_indices = sorted(range(len(envelope)), key=lambda i: envelope[i], reverse=True)[:8]
    cues = [{"seconds": round(i * step, 2), "type": "energy_peak", "relative_energy": round(envelope[i] / peak if peak else 0.0, 3)} for i in sorted(cue_indices)]
    metric = bpm is not None and confidence >= 0.08
    return {
        "schema": "aivideoedit.music-analysis.v1",
        "source_asset_id": asset["id"],
        "source_uri": f"aive://asset/{asset['id']}",
        "analysis_method": "ffmpeg PCM decode + 100ms RMS/onset autocorrelation",
        "rhythm_or_pulse": {"estimated_bpm": bpm, "confidence": confidence, "status": "pulse_detected" if metric else "weak_or_unresolved"},
        "tempo_or_non_metric_status": {"status": "estimated_metric" if metric else "non_metric_or_unresolved", "estimated_bpm": bpm, "confidence": confidence},
        "meter_or_groove": {"status": "unresolved_by_signal_only", "note": "Meter/groove interpretation is intentionally deferred to an agent or user."},
        "section_map": sections,
        "energy_curve": points,
        "musical_cues": cues,
        "narrative_function": {"status": "pending_interpretation", "note": "Signal analysis supplies timing/energy evidence but does not invent narrative intent."},
        "duration_seconds": duration,
        "analysis_complete": True,
    }


def analyze_project(project_id: str, progress=None) -> dict:
    current = production_project.status(project_id)
    if not current.get("initialized"):
        raise RuntimeError("production workspace is not initialized")
    if current.get("stage") not in {"SOURCE_INGESTED", "REFERENCES_ANALYZED"}:
        raise RuntimeError("reference analysis requires SOURCE_INGESTED stage")
    production_project.sync_assets(project_id)
    current = production_project.status(project_id)
    project_dir = Path(current["project_dir"])
    analysis_root = base.PROJECT_ROOT / project_id / "analysis"
    analysis_root.mkdir(parents=True, exist_ok=True)
    refs_path = project_dir / "REFERENCE_MANIFEST.json"
    refs = _read_json(refs_path, {"videos": [], "images": [], "audio": []})
    assets = _asset_map(project_id)
    contract = CORE.production_contract()

    total = len(refs.get("videos", [])) + len(refs.get("images", []))
    done = 0
    analyzed_videos = []
    for ref in refs.get("videos", []):
        asset = assets.get(str(ref.get("asset_id")))
        if not asset:
            raise RuntimeError(f"reference asset missing: {ref.get('asset_id')}")
        analyzed_videos.append(_analyze_video(ref, asset, analysis_root, contract))
        done += 1
        if progress:
            progress(done, max(1, total), f"Analyzed {asset.get('filename')}")

    analyzed_images = []
    for ref in refs.get("images", []):
        asset = assets.get(str(ref.get("asset_id")))
        if not asset or not asset.get("sha256"):
            raise RuntimeError(f"image reference is not ready: {ref.get('name')}")
        rec = dict(ref)
        rec.update({"analysis_complete": True, "analysis_method": "decoded metadata + SHA-256 identity", "analysis_evidence_uri": f"aive://asset/{asset['id']}"})
        analyzed_images.append(rec)
        done += 1
        if progress:
            progress(done, max(1, total), f"Inspected {asset.get('filename')}")

    refs["videos"] = analyzed_videos
    refs["images"] = analyzed_images
    refs["analysis_completed_at"] = base.now()
    _write_json(refs_path, refs)

    audio_candidates = []
    with base.LOCK:
        for asset in base.STATE["assets"]:
            if asset.get("project") != project_id or asset.get("status") != "ready":
                continue
            meta = asset.get("metadata") or {}
            if str(asset.get("content_type") or "").startswith("audio/") or meta.get("audio_codec"):
                audio_candidates.append(dict(asset))
    music_path = project_dir / "MUSIC_ANALYSIS.json"
    if audio_candidates:
        # Prefer a dedicated audio upload over audio embedded in a reference video.
        audio_candidates.sort(key=lambda a: 0 if str(a.get("content_type") or "").startswith("audio/") else 1)
        music = _music_analysis(audio_candidates[0], analysis_root)
        _write_json(music_path, music)
    else:
        music = {"schema": "aivideoedit.music-analysis.v1", "analysis_complete": False, "status": "no_audio_source"}
        _write_json(music_path, music)

    state_path = project_dir / "PROJECT_STATE.json"
    state = _read_json(state_path, {})
    state["reference_analysis_complete"] = all(bool(x.get("analysis_complete")) for x in analyzed_videos + analyzed_images)
    state["music_analysis_complete"] = bool(music.get("analysis_complete"))
    # These remain false until explicit authority is supplied.
    state.setdefault("lyrics_status_resolved", False)
    state.setdefault("genre_authority_resolved", False)
    state["reference_analysis_completed_at"] = base.now()
    _write_json(state_path, state)

    commit = production_project._git_commit_paths(
        Path(current["engine_root"]),
        [refs_path, music_path, state_path],
        "Analyze production references and music evidence",
    )
    production_project._clear_guard_marker(Path(current["engine_root"]))
    return {
        **production_project.status(project_id),
        "reference_analysis_complete": bool(state.get("reference_analysis_complete")),
        "music_analysis_complete": bool(state.get("music_analysis_complete")),
        "lyrics_status_resolved": bool(state.get("lyrics_status_resolved")),
        "genre_authority_resolved": bool(state.get("genre_authority_resolved")),
        "video_references_analyzed": len(analyzed_videos),
        "image_references_analyzed": len(analyzed_images),
        "music_source_asset_id": music.get("source_asset_id"),
        "commit": commit,
    }


def set_music_context(project_id: str, *, lyrics_status: str, genre: str, lyrics_text: str = "", directing_use: str = "default") -> dict:
    current = production_project.status(project_id)
    if not current.get("initialized"):
        raise RuntimeError("production workspace is not initialized")
    lyrics_status = str(lyrics_status or "").strip().lower()
    if lyrics_status not in {"present", "absent"}:
        raise ValueError("lyrics_status must be present or absent")
    genre = str(genre or "").strip()
    if not genre:
        raise ValueError("genre is required as explicit user/agent authority")
    project_dir = Path(current["project_dir"])
    state_path = project_dir / "PROJECT_STATE.json"
    state = _read_json(state_path, {})

    if lyrics_status == "present" and not str(lyrics_text or "").strip():
        raise ValueError("lyrics_text is required when lyrics_status=present")
    lyrics_path = project_dir / "LYRICS.md"
    if lyrics_status == "present":
        lyrics_path.write_text("# Lyrics\n\n" + str(lyrics_text).strip() + "\n", encoding="utf-8")
    else:
        lyrics_path.write_text("# Lyrics\n\nNo lyrics. Explicitly resolved for this production.\n", encoding="utf-8")

    music_path = project_dir / "MUSIC_ANALYSIS.json"
    music = _read_json(music_path, {})
    music["lyrics"] = {"status": lyrics_status, "directing_use": directing_use, "authority": "explicit_current_user_or_agent_input"}
    music["genre"] = {"value": genre, "authority": "explicit_current_user_or_agent_input", "confidence": 1.0}
    _write_json(music_path, music)
    state["lyrics_status_resolved"] = True
    state["genre_authority_resolved"] = True
    state["genre"] = genre
    state["lyrics_status"] = lyrics_status
    _write_json(state_path, state)

    engine = Path(current["engine_root"])
    commit = production_project._git_commit_paths(engine, [lyrics_path, music_path, state_path], "Resolve lyrics and genre authority")
    production_project._clear_guard_marker(engine)
    return {**production_project.status(project_id), "lyrics_status_resolved": True, "genre_authority_resolved": True, "genre": genre, "lyrics_status": lyrics_status, "commit": commit}
