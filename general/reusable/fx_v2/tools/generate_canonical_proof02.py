#!/usr/bin/env python3
"""Generate the reproducible canonical FX2 living-scene proof.

The proof deliberately uses a synthetic verification scene so every input needed to
rebuild it is stored in the repository. Each approved runtime effect is shown in an
isolated segment, followed by the complete stack. Human QC must promote the record
from PENDING to PASS after inspecting the generated contact sheet/video.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

import cv2
import numpy as np

FPS = 24
WIDTH = 640
HEIGHT = 360
SEED = 302
PROOF_ID = "FX2_PROOF02_LIVING_SCENE_CANONICAL"
ARTIFACT = "general/reusable/fx_v2/proofs/FX2_PROOF02_LIVING_SCENE_CANONICAL.mp4"
CONTACT = "general/reusable/fx_v2/proofs/FX2_PROOF02_LIVING_SCENE_CANONICAL_contact_sheet.jpg"
RECORD = "general/reusable/fx_v2/proofs/FX2_PROOF02_LIVING_SCENE_CANONICAL.json"

EFFECTS = [
    {"id": "FX2-MOTION-002", "roi": [0.06, 0.08, 0.62, 0.72], "strength": 0.85},
    {"id": "FX2-MOTION-003", "roi": [0.00, 0.67, 1.00, 1.00], "strength": 0.80, "reflect": True},
    {"id": "FX2-ATM-001", "roi": [0.00, 0.00, 1.00, 0.78], "strength": 0.70},
    {"id": "FX2-ATM-002", "roi": [0.00, 0.00, 1.00, 0.82], "strength": 0.75},
    {"id": "FX2-FIRE-001", "roi": [0.68, 0.43, 0.92, 0.94], "strength": 0.95},
    {"id": "FX2-FIRE-002", "roi": [0.58, 0.14, 0.98, 0.94], "strength": 0.85},
    {"id": "FX2-LIGHT-001", "roi": [0.60, 0.22, 0.98, 0.98], "strength": 1.00},
    {"id": "FX2-LIGHT-002", "origin": [0.78, 0.23], "strength": 1.00},
    {"id": "FX2-SURFACE-001", "key": "proof02-canvas", "strength": 0.90},
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_runtime(path: Path):
    name = "aivideoedit_fx2_proof_runtime"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load runtime: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def source_scene() -> np.ndarray:
    im = np.zeros((HEIGHT, WIDTH, 3), np.uint8)
    # warm/cool room gradient
    yy, xx = np.mgrid[0:HEIGHT, 0:WIDTH]
    im[..., 0] = np.clip(35 + 65 * xx / WIDTH + 18 * yy / HEIGHT, 0, 255).astype(np.uint8)
    im[..., 1] = np.clip(42 + 32 * xx / WIDTH + 28 * yy / HEIGHT, 0, 255).astype(np.uint8)
    im[..., 2] = np.clip(58 + 58 * xx / WIDTH + 20 * yy / HEIGHT, 0, 255).astype(np.uint8)

    # window / rain-readable cool zone
    cv2.rectangle(im, (45, 38), (260, 205), (82, 103, 126), -1)
    cv2.rectangle(im, (53, 46), (252, 197), (112, 128, 143), 4)
    cv2.line(im, (152, 46), (152, 197), (70, 83, 96), 3)
    cv2.line(im, (53, 122), (252, 122), (70, 83, 96), 3)
    cv2.circle(im, (98, 96), 26, (155, 176, 187), -1, cv2.LINE_AA)

    # table/object textures for motion visibility
    cv2.rectangle(im, (235, 205), (520, 270), (62, 72, 91), -1)
    for x in range(245, 515, 30):
        cv2.line(im, (x, 208), (x + 16, 268), (72, 86, 108), 2, cv2.LINE_AA)
    cv2.circle(im, (330, 220), 32, (42, 128, 192), -1, cv2.LINE_AA)
    cv2.circle(im, (330, 220), 18, (24, 86, 145), 2, cv2.LINE_AA)

    # hearth/fire zone
    cv2.rectangle(im, (425, 145), (600, 330), (36, 42, 54), -1)
    cv2.rectangle(im, (442, 173), (582, 325), (25, 29, 37), -1)
    cv2.ellipse(im, (512, 310), (76, 18), 0, 0, 360, (18, 30, 55), -1)

    # reflective/water floor
    cv2.rectangle(im, (0, 270), (WIDTH - 1, HEIGHT - 1), (50, 64, 74), -1)
    for y in range(278, 355, 12):
        cv2.line(im, (0, y), (WIDTH - 1, y + 4), (72, 88, 98), 1, cv2.LINE_AA)

    # protected central silhouette-like subject for spatial reference
    cv2.circle(im, (355, 118), 28, (74, 82, 94), -1, cv2.LINE_AA)
    cv2.ellipse(im, (355, 205), (49, 87), 0, 0, 360, (66, 75, 88), -1, cv2.LINE_AA)
    cv2.line(im, (312, 194), (276, 246), (65, 73, 85), 13, cv2.LINE_AA)
    cv2.line(im, (398, 194), (426, 246), (65, 73, 85), 13, cv2.LINE_AA)
    return im


def label(frame: np.ndarray, text: str, sub: str) -> np.ndarray:
    out = frame.copy()
    cv2.rectangle(out, (0, 0), (WIDTH, 50), (12, 12, 14), -1)
    cv2.putText(out, text, (16, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (245, 245, 245), 1, cv2.LINE_AA)
    cv2.putText(out, sub, (16, 43), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (178, 196, 218), 1, cv2.LINE_AA)
    return out


def make_contact_sheet(frames: list[np.ndarray], labels: list[str], path: Path) -> None:
    thumbs = []
    tw, th = 320, 180
    for frame, txt in zip(frames, labels):
        thumb = cv2.resize(frame, (tw, th), interpolation=cv2.INTER_AREA)
        cv2.rectangle(thumb, (0, 0), (tw, 28), (10, 10, 12), -1)
        cv2.putText(thumb, txt[:42], (8, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (245, 245, 245), 1, cv2.LINE_AA)
        thumbs.append(thumb)
    while len(thumbs) % 3:
        thumbs.append(np.zeros((th, tw, 3), np.uint8))
    rows = [np.hstack(thumbs[i:i + 3]) for i in range(0, len(thumbs), 3)]
    sheet = np.vstack(rows)
    cv2.imwrite(str(path), sheet, [cv2.IMWRITE_JPEG_QUALITY, 92])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--source-commit", default=os.environ.get("GITHUB_SHA", "unknown"))
    args = ap.parse_args()

    root = Path(args.repo_root).resolve()
    runtime_path = root / "general/reusable/fx_v2/runtime.py"
    registry_path = root / "general/reusable/fx_v2/registry.json"
    generator_path = Path(__file__).resolve()
    artifact = root / ARTIFACT
    contact = root / CONTACT
    record = root / RECORD
    artifact.parent.mkdir(parents=True, exist_ok=True)

    module = load_runtime(runtime_path)
    runtime = module.FXRuntime(seed=SEED)
    src = source_scene()

    # 1 sec baseline + 0.75 sec per effect + 1.25 sec combined = 9 sec exactly.
    baseline_frames = FPS
    per_effect_frames = 18
    combined_frames = 30
    total_frames = baseline_frames + len(EFFECTS) * per_effect_frames + combined_frames
    assert total_frames == 216

    writer = cv2.VideoWriter(str(artifact), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (WIDTH, HEIGHT))
    if not writer.isOpened():
        raise RuntimeError("OpenCV could not open MP4 writer")

    representative: list[np.ndarray] = []
    representative_labels: list[str] = []
    adjacent_deltas: list[float] = []
    previous = None

    def emit(frame: np.ndarray):
        nonlocal previous
        writer.write(frame)
        if previous is not None:
            adjacent_deltas.append(float(np.mean(cv2.absdiff(previous, frame))))
        previous = frame.copy()

    for i in range(baseline_frames):
        frame = label(src, "BASELINE", "deterministic synthetic scene; no FX")
        emit(frame)
    representative.append(label(src, "BASELINE", "deterministic synthetic scene; no FX"))
    representative_labels.append("BASELINE")

    global_frame = baseline_frames
    for effect in EFFECTS:
        mid_frame = None
        for j in range(per_effect_frames):
            t = j / FPS
            ctx = module.FXContext(t=t, duration=per_effect_frames / FPS, frame_index=global_frame, fps=FPS,
                                   energy=.66, transient=.52, brightness=.58)
            out = runtime.apply(src.copy(), effect, ctx)
            frame = label(out, effect["id"], "isolated runtime proof; locked camera")
            if j == per_effect_frames // 2:
                mid_frame = frame.copy()
            emit(frame)
            global_frame += 1
        representative.append(mid_frame if mid_frame is not None else frame)
        representative_labels.append(effect["id"])

    combined_mid = None
    for j in range(combined_frames):
        t = j / FPS
        ctx = module.FXContext(t=t, duration=combined_frames / FPS, frame_index=global_frame, fps=FPS,
                               energy=.66 + .12 * np.sin(t * 2.2), transient=.52, brightness=.58)
        out = src.copy()
        for effect in EFFECTS:
            out = runtime.apply(out, effect, ctx)
        frame = label(out, "COMBINED APPROVED STACK", "all nine effects; locked camera; bounded synthetic controls")
        if j == combined_frames // 2:
            combined_mid = frame.copy()
        emit(frame)
        global_frame += 1
    representative.append(combined_mid if combined_mid is not None else frame)
    representative_labels.append("COMBINED")
    writer.release()

    make_contact_sheet(representative, representative_labels, contact)

    cap = cv2.VideoCapture(str(artifact))
    decoded = 0
    black = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        decoded += 1
        if float(np.mean(frame)) < 2.0:
            black += 1
    cap.release()
    if decoded != total_frames or black:
        raise RuntimeError(f"proof decode QC failed: decoded={decoded}/{total_frames}, black={black}")

    record_data = {
        "proof": PROOF_ID,
        "schema_version": 2,
        "purpose": "Canonical byte-verifiable reproducible proof for approved FX2 runtime effects.",
        "source": "repository-generated deterministic synthetic verification scene",
        "source_provenance": "generated entirely by this proof generator; no external source media",
        "generator_path": str(generator_path.relative_to(root)),
        "generator_sha256": sha256_file(generator_path),
        "source_commit": args.source_commit,
        "runtime_path": str(runtime_path.relative_to(root)),
        "runtime_sha256": sha256_file(runtime_path),
        "registry_path": str(registry_path.relative_to(root)),
        "registry_sha256_at_generation": sha256_file(registry_path),
        "artifact_path": ARTIFACT,
        "sha256": sha256_file(artifact),
        "contact_sheet_path": CONTACT,
        "contact_sheet_sha256": sha256_file(contact),
        "fps": FPS,
        "frames": total_frames,
        "duration_seconds": total_frames / FPS,
        "size": [WIDTH, HEIGHT],
        "camera": "locked; no camera transform or shake",
        "effects": [e["id"] for e in EFFECTS],
        "effect_parameters": EFFECTS,
        "mean_adjacent_frame_delta": float(np.mean(adjacent_deltas)),
        "p95_adjacent_frame_delta": float(np.percentile(adjacent_deltas, 95)),
        "decoded_frames": decoded,
        "black_frames": black,
        "visual_qc": "PENDING HUMAN REVIEW",
        "qc_notes": [
            "First second is an unmodified baseline.",
            "Each approved runtime effect is then shown in isolation with a locked camera.",
            "Final segment applies the complete approved stack with bounded synthetic control values.",
            "Synthetic controls are for isolated engine verification only; production films must use canonical song analysis."
        ]
    }
    record.write_text(json.dumps(record_data, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record_data, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
