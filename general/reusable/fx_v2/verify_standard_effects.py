#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
RUNTIME_PATH = HERE / "promoted_effects.py"


def load_runtime():
    spec = importlib.util.spec_from_file_location("aivideoedit_standard_effects", RUNTIME_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load promoted_effects.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def synthetic_frame(width=320, height=180):
    yy, xx = np.mgrid[0:height, 0:width]
    im = np.zeros((height, width, 3), np.uint8)
    im[..., 0] = np.clip(22 + xx * 190 / width, 0, 255).astype(np.uint8)
    im[..., 1] = np.clip(28 + yy * 170 / height, 0, 255).astype(np.uint8)
    im[..., 2] = np.clip(45 + ((xx + yy) % 155), 0, 255).astype(np.uint8)
    cv2.circle(im, (int(width * .29), int(height * .52)), int(height * .23), (30, 160, 235), -1, cv2.LINE_AA)
    cv2.rectangle(im, (int(width * .59), int(height * .20)), (int(width * .90), int(height * .84)), (180, 75, 45), -1)
    cv2.line(im, (0, int(height * .69)), (width - 1, int(height * .58)), (225, 225, 225), 2, cv2.LINE_AA)
    return im


def delta(a, b):
    return float(np.mean(cv2.absdiff(a, b)))


def global_shift(a, b):
    ga = np.float32(cv2.cvtColor(a, cv2.COLOR_BGR2GRAY))
    gb = np.float32(cv2.cvtColor(b, cv2.COLOR_BGR2GRAY))
    (dx, dy), _ = cv2.phaseCorrelate(ga, gb)
    return float((dx * dx + dy * dy) ** .5)


def verify_effects():
    mod = load_runtime()
    names = list(getattr(mod, "EFFECT_NAMES", []))
    aliases = dict(getattr(mod, "LEGACY_ALIASES", {}))
    if not names or len(names) != len(set(names)):
        raise RuntimeError("EFFECT_NAMES must be non-empty and unique")
    missing_alias_targets = sorted({v for v in aliases.values() if v not in names})
    if missing_alias_targets:
        raise RuntimeError("legacy aliases target unknown effects: " + ", ".join(missing_alias_targets))

    src = synthetic_frame()
    second = cv2.GaussianBlur(255 - src, (0, 0), 1.4)
    times = (0.13, 0.47, 0.91, 1.37)
    results = []
    failures = []
    for name in names:
        outs = []
        for i, t in enumerate(times):
            out = mod.apply_effect(name, src.copy(), t, 2.0, energy=.68, transient=.57, second_frame=second.copy())
            if not isinstance(out, np.ndarray) or out.shape != src.shape or out.dtype != src.dtype:
                failures.append(f"{name}: invalid output")
                outs = []
                break
            outs.append(out)
        if not outs:
            continue
        source_delta = max(delta(src, x) for x in outs)
        temporal_delta = max(delta(outs[i], outs[j]) for i in range(len(outs)) for j in range(i + 1, len(outs)))
        shift = max(global_shift(src, x) for x in outs)
        digest = hashlib.sha256(b"".join(np.ascontiguousarray(x).tobytes() for x in outs)).hexdigest()
        result = "PASS" if source_delta >= .02 and temporal_delta >= .005 else "FAIL"
        if result != "PASS":
            failures.append(f"{name}: source_delta={source_delta:.6f} temporal_delta={temporal_delta:.6f}")
        results.append({
            "name": name,
            "result": result,
            "source_delta_max": round(source_delta, 6),
            "temporal_delta_max": round(temporal_delta, 6),
            "global_shift_px_max": round(shift, 6),
            "sample_output_sha256": digest,
        })

    report = {
        "schema": "aivideoedit.standard-effects-verification.v1",
        "runtime": "aivideoedit-fx-v2",
        "effect_count": len(names),
        "alias_count": len(aliases),
        "sample_frames_per_effect": len(times),
        "sample_size": [320, 180],
        "fps_basis": 24,
        "criteria": {"source_delta_min": .02, "temporal_delta_min": .005, "deterministic": True},
        "effects": results,
        "result": "PASS" if not failures and len(results) == len(names) else "FAIL",
        "failures": failures,
    }
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report-out")
    args = ap.parse_args()
    report = verify_effects()
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.report_out:
        Path(args.report_out).write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
