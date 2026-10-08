#!/usr/bin/env python3
from __future__ import annotations

"""Final-export visual progression QC.

Samples a rendered video, builds a contact sheet, and reports perceptual runs
that remain too compositionally similar. This is a creative-warning gate, not a
substitute for human inspection: motion can exist while visual progression is
still absent. The report is designed to be preserved as BEFORE/AFTER evidence
for recut/refinement work.
"""

import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def signature(frame: np.ndarray) -> np.ndarray:
    small = cv2.resize(frame, (64, 36), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    dct = cv2.dct(gray.astype(np.float32) / 255.0)[:12, :12].flatten()
    edges = cv2.Canny(gray, 60, 150).astype(np.float32) / 255.0
    hist = cv2.calcHist([small], [0, 1, 2], None, [4, 4, 4], [0, 256] * 3).flatten()
    hist /= max(hist.sum(), 1e-6)
    yy, xx = np.mgrid[0:36, 0:64]
    weight = gray.astype(np.float32) + 1.0
    cx = float((xx * weight).sum() / weight.sum()) / 64.0
    cy = float((yy * weight).sum() / weight.sum()) / 36.0
    return np.concatenate([dct * 0.35, hist * 8.0, [edges.mean() * 4.0, cx, cy]]).astype(np.float32)


def cosine(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))


def summarize_report(report: dict) -> dict:
    return {
        "result": report.get("result"),
        "similar_runs_count": len(report.get("similar_runs", [])) if isinstance(report.get("similar_runs"), list) else 0,
        "metrics": {
            "mean_adjacent_similarity": report.get("mean_adjacent_similarity"),
            "max_adjacent_similarity": report.get("max_adjacent_similarity"),
            "samples": report.get("samples"),
            "sample_interval_seconds": report.get("sample_interval_seconds"),
            "similarity_threshold": report.get("similarity_threshold"),
            "max_similar_run_samples": report.get("max_similar_run_samples"),
        },
    }


def compare_reports(before: dict, after: dict) -> dict:
    b = summarize_report(before)
    a = summarize_report(after)
    bm = b["metrics"].get("mean_adjacent_similarity")
    am = a["metrics"].get("mean_adjacent_similarity")
    return {
        "schema": "aivideoedit.export-variety-comparison.v1",
        "before": b,
        "after": a,
        "delta": {
            "similar_runs": a["similar_runs_count"] - b["similar_runs_count"],
            "mean_adjacent_similarity": (am - bm) if isinstance(am, (int, float)) and isinstance(bm, (int, float)) else None,
        },
        "interpretation": "Metrics are evidence for comparison, not an automatic artistic decision.",
    }


def analyze(video: Path, interval: float, threshold: float, max_run: int, sheet: Path | None):
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration = frames / fps if frames else 0.0
    times = np.arange(0.0, max(duration, 0.001), interval)
    imgs, sigs = [], []
    for t in times:
        cap.set(cv2.CAP_PROP_POS_MSEC, float(t * 1000.0))
        ok, frame = cap.read()
        if ok:
            imgs.append((float(t), frame))
            sigs.append(signature(frame))
    cap.release()
    similarities = [cosine(sigs[i - 1], sigs[i]) for i in range(1, len(sigs))]
    runs, start = [], None
    for i, s in enumerate(similarities, start=1):
        if s >= threshold and start is None:
            start = i - 1
        if (s < threshold or i == len(similarities)) and start is not None:
            end = i if s >= threshold and i == len(similarities) else i - 1
            if end - start + 1 >= max_run:
                runs.append({"sample_start": start, "sample_end": end, "seconds_start": imgs[start][0], "seconds_end": imgs[end][0]})
            start = None
    if sheet and imgs:
        thumbs = []
        for t, frame in imgs:
            th = cv2.resize(frame, (320, 180), interpolation=cv2.INTER_AREA)
            cv2.putText(th, f"{t:6.1f}s", (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
            thumbs.append(th)
        cols = min(5, len(thumbs))
        rows = (len(thumbs) + cols - 1) // cols
        canvas = np.zeros((rows * 180, cols * 320, 3), np.uint8)
        for i, th in enumerate(thumbs):
            canvas[(i // cols) * 180:(i // cols + 1) * 180, (i % cols) * 320:(i % cols + 1) * 320] = th
        sheet.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(sheet), canvas)
    report = {
        "schema": "aivideoedit.export-variety-qc.v2",
        "video": str(video),
        "video_sha256": sha256_file(video) if video.is_file() else None,
        "duration_seconds": duration,
        "sample_interval_seconds": interval,
        "samples": len(imgs),
        "similarity_threshold": threshold,
        "max_similar_run_samples": max_run,
        "mean_adjacent_similarity": float(np.mean(similarities)) if similarities else None,
        "max_adjacent_similarity": float(np.max(similarities)) if similarities else None,
        "similar_runs": runs,
        "similar_runs_count": len(runs),
        "result": "REVIEW" if runs else "PASS",
        "interpretation": "REVIEW means consecutive sampled compositions remained highly similar; inspect the contact sheet. Motion metrics alone do not establish visual progression."
    }
    report["metrics"] = summarize_report(report)["metrics"]
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video", type=Path)
    ap.add_argument("--interval", type=float, default=10.0)
    ap.add_argument("--threshold", type=float, default=0.992)
    ap.add_argument("--max-run", type=int, default=3)
    ap.add_argument("--contact-sheet", type=Path)
    ap.add_argument("--json", dest="json_path", type=Path)
    ap.add_argument("--compare-before", type=Path, help="prior export_variety_qc JSON to preserve/compare")
    ap.add_argument("--comparison-json", type=Path)
    a = ap.parse_args()
    report = analyze(a.video, a.interval, a.threshold, a.max_run, a.contact_sheet)
    text = json.dumps(report, indent=2) + "\n"
    if a.json_path:
        a.json_path.parent.mkdir(parents=True, exist_ok=True)
        a.json_path.write_text(text, encoding="utf-8")
    if a.compare_before:
        before = json.loads(a.compare_before.read_text(encoding="utf-8"))
        comparison = compare_reports(before, report)
        ctext = json.dumps(comparison, indent=2) + "\n"
        if a.comparison_json:
            a.comparison_json.parent.mkdir(parents=True, exist_ok=True)
            a.comparison_json.write_text(ctext, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
