#!/usr/bin/env python3
"""Extract a perceptually diverse canonical hero-shot library from approved video.

Candidate frames are sampled densely, but final selection is quality/diversity driven;
this is intentionally not an every-N-seconds final sampler. Semantic properties that
are not directly measured (identity, subject, shot scale) are never asserted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

SCHEMA = "aivideoedit.hero-library.v1"
LIFECYCLE = {"candidate", "approved", "canonical", "derived", "retired"}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _valid_sha(v: Any) -> bool:
    return isinstance(v, str) and len(v) == 64 and all(c in "0123456789abcdefABCDEF" for c in v)


def library_warnings(manifest: dict) -> list[str]:
    warnings: list[str] = []
    entries = manifest.get("entries") if isinstance(manifest, dict) else None
    if not isinstance(entries, list) or not entries:
        return ["hero library is empty"]
    stats = manifest.get("selection", {}) if isinstance(manifest.get("selection"), dict) else {}
    candidates = int(stats.get("candidate_count") or 0)
    near_dupes = int(stats.get("near_duplicate_rejections") or 0)
    if candidates >= 4 and near_dupes / max(candidates, 1) >= 0.60:
        warnings.append("candidate pool is duplicate-heavy; inspect source coverage and thresholds")
    if len(entries) < min(3, max(candidates, 1)):
        warnings.append("hero library has limited perceptual coverage")
    return warnings


def validate_library_manifest(manifest: dict) -> list[str]:
    errors: list[str] = []
    if not isinstance(manifest, dict) or manifest.get("schema") != SCHEMA:
        return [f"hero library schema must be {SCHEMA}"]
    source = manifest.get("source")
    if not isinstance(source, dict):
        errors.append("hero library source must be an object")
    else:
        if not isinstance(source.get("identity"), str) or not source.get("identity", "").strip():
            errors.append("hero library source.identity is required")
        if not _valid_sha(source.get("sha256")):
            errors.append("hero library source.sha256 must be 64 hexadecimal characters")
    entries = manifest.get("entries")
    if not isinstance(entries, list) or not entries:
        errors.append("hero library must contain at least one selected entry")
        return errors
    seen = set()
    for i, entry in enumerate(entries, 1):
        if not isinstance(entry, dict):
            errors.append(f"hero library entry {i} must be an object")
            continue
        frame = entry.get("frame_index")
        t = entry.get("time_seconds")
        if not isinstance(frame, int) or isinstance(frame, bool) or frame < 0:
            errors.append(f"hero library entry {i} requires non-negative frame_index")
        if not isinstance(t, (int, float)) or isinstance(t, bool) or t < 0:
            errors.append(f"hero library entry {i} requires non-negative time_seconds")
        if not _valid_sha(entry.get("frame_sha256")):
            errors.append(f"hero library entry {i} requires frame_sha256")
        if entry.get("lifecycle_status") not in LIFECYCLE:
            errors.append(f"hero library entry {i} has invalid lifecycle_status")
        ev = entry.get("diversity_evidence")
        if not isinstance(ev, dict) or not isinstance(ev.get("min_distance_to_selected"), (int, float)):
            errors.append(f"hero library entry {i} requires measured diversity_evidence")
        visual = entry.get("visual_signature")
        if not isinstance(visual, dict) or not isinstance(visual.get("vector"), list) or not visual.get("vector"):
            errors.append(f"hero library entry {i} requires visual_signature.vector")
        source_range = entry.get("source_range_seconds")
        if (
            not isinstance(source_range, list)
            or len(source_range) != 2
            or not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in source_range)
            or source_range[0] < 0
            or source_range[1] < source_range[0]
        ):
            errors.append(f"hero library entry {i} requires valid source_range_seconds")
        key = (frame, round(float(t), 6) if isinstance(t, (int, float)) else t)
        if key in seen:
            errors.append(f"hero library entry {i} duplicates a selected frame/time")
        seen.add(key)
    return errors


def _cosine(a, b) -> float:
    import numpy as np
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))


def _frame_metrics(frame):
    import cv2
    import numpy as np
    small = cv2.resize(frame, (64, 36), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    dct = cv2.dct(gray.astype(np.float32) / 255.0)[:10, :10].flatten()
    hist = cv2.calcHist([small], [0, 1, 2], None, [4, 4, 4], [0, 256] * 3).flatten()
    hist /= max(float(hist.sum()), 1e-6)
    edges = cv2.Canny(gray, 60, 150).astype(np.float32) / 255.0
    yy, xx = np.mgrid[0:36, 0:64]
    weight = gray.astype(np.float32) + 1.0
    cx = float((xx * weight).sum() / weight.sum()) / 64.0
    cy = float((yy * weight).sum() / weight.sum()) / 36.0
    sat = float(hsv[:, :, 1].mean()) / 255.0
    lum = float(gray.mean()) / 255.0
    sharpness = float(cv2.Laplacian(gray, cv2.CV_32F).var())
    sig = np.concatenate([dct * 0.35, hist * 8.0, [edges.mean() * 4.0, cx, cy, sat, lum]]).astype(np.float32)
    return {"signature": sig, "centroid_x": cx, "centroid_y": cy, "saturation": sat, "luminance": lum, "sharpness": sharpness, "edge_density": float(edges.mean())}


def _read_landmarks(path: Path | None) -> list[float]:
    if not path:
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    times: list[float] = []
    for key in ("landmarks", "musical_landmarks", "times_seconds"):
        vals = data.get(key, []) if isinstance(data, dict) else []
        if isinstance(vals, list):
            for v in vals:
                if isinstance(v, (int, float)) and not isinstance(v, bool) and v >= 0:
                    times.append(float(v))
                elif isinstance(v, dict):
                    t = v.get("time_seconds")
                    if isinstance(t, (int, float)) and not isinstance(t, bool) and t >= 0:
                        times.append(float(t))
    sections = data.get("sections", []) if isinstance(data, dict) else []
    if isinstance(sections, list):
        for sec in sections:
            if not isinstance(sec, dict):
                continue
            for key in ("start_seconds", "end_seconds"):
                v = sec.get(key)
                if isinstance(v, (int, float)) and not isinstance(v, bool) and v >= 0:
                    times.append(float(v))
    return sorted(set(times))


def extract_library(video: Path, output_dir: Path, target_count: int = 16, candidate_interval: float = 0.5, duplicate_similarity: float = 0.985, landmarks_json: Path | None = None) -> dict:
    import cv2
    import numpy as np
    if target_count < 1:
        raise ValueError("target_count must be >= 1")
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise ValueError(f"cannot open source video: {video}")
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 24.0)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration = frame_count / fps if frame_count else 0.0
    if duration <= 0:
        cap.release()
        raise ValueError("source video has no measurable duration")
    base_times = list(np.arange(0.0, duration, max(candidate_interval, 0.1), dtype=float))
    landmarks = [t for t in _read_landmarks(landmarks_json) if t <= duration]
    times = sorted(set(round(float(t), 6) for t in [*base_times, *landmarks, max(0.0, duration - 1.0 / fps)]))
    landmark_set = set(round(t, 3) for t in landmarks)
    candidates = []
    prev_gray = None
    prev_sig = None
    for t in times:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
        ok, frame = cap.read()
        if not ok:
            continue
        m = _frame_metrics(frame)
        gray = cv2.cvtColor(cv2.resize(frame, (64, 36)), cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
        motion = float(np.mean(np.abs(gray - prev_gray))) if prev_gray is not None else 0.0
        transition = (1.0 - _cosine(prev_sig, m["signature"])) if prev_sig is not None else 0.0
        quality = min(m["sharpness"] / 400.0, 1.0) * 0.50 + (1.0 - min(motion / 0.25, 1.0)) * 0.30
        quality += (1.0 - min(abs(m["luminance"] - 0.5) * 1.6, 1.0)) * 0.20
        candidates.append({"time": t, "frame_index": int(round(t * fps)), "frame": frame, "metrics": m, "motion": motion, "transition": transition, "quality": quality, "landmark": round(t, 3) in landmark_set})
        prev_gray = gray
        prev_sig = m["signature"]
    cap.release()
    if not candidates:
        raise ValueError("no usable candidate frames were decoded")
    selected = []
    rejected_near_duplicates = 0
    remaining = candidates[:]
    while remaining and len(selected) < target_count:
        best = None
        best_score = -math.inf
        for c in remaining:
            if selected:
                similarities = [_cosine(c["metrics"]["signature"], s["metrics"]["signature"]) for s in selected]
                max_similarity = max(similarities)
                min_distance = 1.0 - max_similarity
            else:
                max_similarity = 0.0
                min_distance = 1.0
            if selected and max_similarity >= duplicate_similarity and not c["landmark"] and c["transition"] < 0.08:
                continue
            score = min_distance * 0.62 + c["quality"] * 0.23 + min(c["transition"] / 0.25, 1.0) * 0.10 + (0.05 if c["landmark"] else 0.0)
            if score > best_score:
                best = (c, min_distance)
                best_score = score
        if best is None:
            rejected_near_duplicates += len(remaining)
            break
        c, min_distance = best
        c["min_distance"] = float(min_distance)
        selected.append(c)
        next_remaining = []
        for r in remaining:
            if r is c:
                continue
            sim = _cosine(r["metrics"]["signature"], c["metrics"]["signature"])
            if sim >= duplicate_similarity and not r["landmark"] and r["transition"] < 0.08:
                rejected_near_duplicates += 1
            else:
                next_remaining.append(r)
        remaining = next_remaining
    if not selected:
        raise ValueError("hero-library selection produced no entries")
    output_dir.mkdir(parents=True, exist_ok=True)
    frame_dir = output_dir / "frames"
    frame_dir.mkdir(parents=True, exist_ok=True)
    entries = []
    for idx, c in enumerate(sorted(selected, key=lambda x: x["time"]), 1):
        out = frame_dir / f"hero_{idx:03d}_{c['frame_index']:08d}.png"
        if not cv2.imwrite(str(out), c["frame"]):
            raise ValueError(f"failed to write {out}")
        m = c["metrics"]
        motion_class = "low_motion" if c["motion"] <= 0.04 else "active_motion"
        half = 0.75 if motion_class == "low_motion" else 0.25
        palette_state = "monochrome_like" if m["saturation"] < 0.12 else "color"
        luminance_state = "dark" if m["luminance"] < 0.30 else ("bright" if m["luminance"] > 0.72 else "mid")
        centroid_state = "left" if m["centroid_x"] < 0.42 else ("right" if m["centroid_x"] > 0.58 else "center")
        entries.append({
            "id": f"hero_{idx:03d}", "frame_index": c["frame_index"], "time_seconds": round(float(c["time"]), 6),
            "file": out.relative_to(output_dir).as_posix(), "frame_sha256": sha256_file(out), "lifecycle_status": "candidate",
            "source_range_seconds": [round(max(0.0, c["time"] - half), 6), round(min(duration, c["time"] + half), 6)],
            "range_basis": f"bounded local source window; measured frame-change class={motion_class}",
            "visual_signature": {"method": "dct+color_histogram+edges+luminance_centroid+saturation+luminance", "vector": [round(float(x), 7) for x in m["signature"].tolist()]},
            "diversity_evidence": {"min_distance_to_selected": round(float(c["min_distance"]), 7), "transition_strength": round(float(c["transition"]), 7), "quality_score": round(float(c["quality"]), 7), "motion_score": round(float(c["motion"]), 7)},
            "measured_tags": {"visual_centroid": centroid_state, "palette_state": palette_state, "luminance_state": luminance_state, "motion_class": motion_class, "musical_landmark": bool(c["landmark"])},
        })
    manifest = {
        "schema": SCHEMA,
        "source": {"identity": video.name, "file_or_locator": str(video), "sha256": sha256_file(video), "fps": fps, "frame_count": frame_count, "duration_seconds": duration},
        "selection": {"method": "dense_candidates_then_quality_transition_perceptual_diversity_greedy_selection", "candidate_interval_seconds": candidate_interval, "candidate_count": len(candidates), "target_count": target_count, "selected_count": len(entries), "duplicate_similarity_threshold": duplicate_similarity, "near_duplicate_rejections": rejected_near_duplicates, "musical_landmarks_supplied": len(landmarks)},
        "entries": entries,
        "unmeasured_dimensions": ["semantic subject identity", "semantic shot scale (wide/medium/close)", "semantic subject position", "narrative meaning"],
    }
    manifest["warnings"] = library_warnings(manifest)
    errors = validate_library_manifest(manifest)
    if errors:
        raise ValueError("invalid hero library output: " + "; ".join(errors))
    (output_dir / "HERO_LIBRARY.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("video", type=Path)
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--target-count", type=int, default=16)
    ap.add_argument("--candidate-interval", type=float, default=0.5)
    ap.add_argument("--duplicate-similarity", type=float, default=0.985)
    ap.add_argument("--landmarks-json", type=Path)
    args = ap.parse_args()
    manifest = extract_library(args.video, args.output_dir, target_count=args.target_count, candidate_interval=args.candidate_interval, duplicate_similarity=args.duplicate_similarity, landmarks_json=args.landmarks_json)
    print(json.dumps({"result": "PASS", "manifest": str(args.output_dir / "HERO_LIBRARY.json"), "selected": len(manifest["entries"]), "warnings": manifest.get("warnings", [])}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
