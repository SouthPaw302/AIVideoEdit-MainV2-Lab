#!/usr/bin/env python3
"""Fail-closed registry + pixel smoke verification for living-still adapters."""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

REQUIRED = {
    "FX2-MOTION-005": ("camera_drift", "frame"),
    "FX2-ATM-005": ("cloud_drift", "frame"),
    "FX2-ATM-006": ("star_field", "frame"),
    "FX2-ATM-007": ("snow_plane", "frame"),
    "FX2-ATM-008": ("bird_flock", "frame"),
    "FX2-LIGHT-005": ("lens_bloom_flare", "frame"),
    "FX2-LIGHT-006": ("sign_light_flicker", "frame"),
    "FX2-SURFACE-003": ("reflection_shimmer", "frame"),
    "FX2-TRANS-006": ("crossfade_dissolve", "transition"),
}


@dataclass
class Ctx:
    t: float
    duration: float = 4.0

    @property
    def phase(self):
        return (self.t / self.duration) % 1.0


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("aivideoedit_living_still_fx_verify", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def synthetic_frame(w=320, h=180):
    yy, xx = np.mgrid[0:h, 0:w]
    im = np.zeros((h, w, 3), np.uint8)
    im[..., 0] = np.clip(18 + xx * 165 / w, 0, 255).astype(np.uint8)
    im[..., 1] = np.clip(20 + yy * 150 / h, 0, 255).astype(np.uint8)
    im[..., 2] = np.clip(35 + ((xx + yy) % 120), 0, 255).astype(np.uint8)
    cv2.circle(im, (int(w * .28), int(h * .48)), int(h * .20), (32, 146, 225), -1, cv2.LINE_AA)
    cv2.rectangle(im, (int(w * .56), int(h * .22)), (int(w * .88), int(h * .82)), (168, 72, 48), -1)
    return im


def delta(a, b):
    return float(np.mean(cv2.absdiff(a, b)))


def verify(registry_path: Path, implementation_path: Path):
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    effects = registry.get("effects", {})
    mod = load_module(implementation_path)
    src = synthetic_frame()
    metrics = {}

    for eid, (symbol, kind) in REQUIRED.items():
        entry = effects.get(eid)
        if not isinstance(entry, dict):
            raise RuntimeError(f"missing registry entry {eid}")
        impl = entry.get("implementation") or {}
        if impl.get("kind") != "adapter":
            raise RuntimeError(f"{eid} must be an adapter")
        if impl.get("path") != "general/reusable/fx_v2/living_still_fx.py":
            raise RuntimeError(f"{eid} points at the wrong implementation path")
        if impl.get("symbol") != symbol:
            raise RuntimeError(f"{eid} must map to symbol {symbol}")
        fn = getattr(mod, symbol, None)
        if not callable(fn):
            raise RuntimeError(f"implementation symbol is not callable: {symbol}")

        if kind == "transition":
            other = 255 - src
            outs = [fn(src.copy(), other.copy(), p) for p in (0.0, .25, .5, .75, 1.0)]
            if delta(src, outs[0]) > 0.001 or delta(other, outs[-1]) > 0.001:
                raise RuntimeError(f"{eid} transition endpoints are not exact")
            mid = delta(src, outs[2])
            if mid < 4.0:
                raise RuntimeError(f"{eid} transition midpoint is effectively a no-op")
            metrics[eid] = {"endpoint_a_delta": delta(src, outs[0]), "endpoint_b_delta": delta(other, outs[-1]), "mid_delta": round(mid, 6)}
            continue

        outs = [fn(src.copy(), Ctx(t)) for t in (.48, 1.36, 2.72)]
        for out in outs:
            if out.shape != src.shape or out.dtype != src.dtype:
                raise RuntimeError(f"{eid} returned invalid frame shape/dtype")
        source_delta = max(delta(src, out) for out in outs)
        temporal_delta = max(delta(outs[i], outs[j]) for i in range(len(outs)) for j in range(i + 1, len(outs)))
        if source_delta < 0.02:
            raise RuntimeError(f"{eid} is effectively a no-op: {source_delta:.6f}")
        if temporal_delta < 0.01:
            raise RuntimeError(f"{eid} is not temporal: {temporal_delta:.6f}")
        loop_a = fn(src.copy(), Ctx(0.0))
        loop_b = fn(src.copy(), Ctx(4.0))
        loop_delta = delta(loop_a, loop_b)
        if loop_delta > 0.001:
            raise RuntimeError(f"{eid} is not loop-closed: {loop_delta:.6f}")
        metrics[eid] = {"source_delta_max": round(source_delta, 6), "temporal_delta_max": round(temporal_delta, 6), "loop_delta": round(loop_delta, 6)}

    return {"result": "PASS", "verified_effects": len(REQUIRED), "metrics": metrics}


def main():
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", default=str(here / "registry.json"))
    ap.add_argument("--implementation", default=str(here / "living_still_fx.py"))
    args = ap.parse_args()
    try:
        print(json.dumps(verify(Path(args.registry), Path(args.implementation)), indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"result": "FAIL", "error": str(exc)}, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
