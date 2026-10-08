#!/usr/bin/env python3
"""CPU reference renderer for an organic audio-reactive visual field.

Frames are streamed directly to ffmpeg; the full movie is never retained in RAM.
This is a compositing plate, not a claim of projectM/MilkDrop compatibility.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import numpy as np


def _smoothstep(a: float, b: float, x: np.ndarray) -> np.ndarray:
    t = np.clip((x - a) / (b - a + 1e-9), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def render_frame(width: int, height: int, control: dict) -> np.ndarray:
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
    x = (xx - width * 0.5) / max(width, height)
    y = (yy - height * 0.5) / max(width, height)
    r = np.sqrt(x * x + y * y) + 1e-6
    angle = np.arctan2(y, x)
    t = float(control["time"])
    rms = float(control["rms_n"]); onset = float(control["onset_n"])
    low = float(control["low_n"]); mid = float(control["mid_n"]); high = float(control["high_n"])

    spin = t * (0.16 + 0.35 * mid)
    layer1 = np.sin(r * (6.0 + 4.0 * low) - t * 1.4 + angle * 2.0) * 0.5 + 0.5
    layer2 = np.sin(r * (9.0 + 5.0 * high) + t * 2.1 - angle * 3.0 + spin) * 0.5 + 0.5
    layer3 = np.sin((x * 4.0 + y * 3.0) * (1.5 + mid) + t * 1.7) * 0.5 + 0.5
    field = layer1 * 0.45 + layer2 * 0.35 + layer3 * 0.25
    field *= 0.58 + 0.42 * rms

    vignette = _smoothstep(0.95, 0.14, r)
    glow = np.exp(-r * r * (3.6 - 1.5 * rms))
    red = field * (0.34 + 0.42 * low) + glow * 0.55 * (0.55 + 0.45 * onset)
    green = field * (0.44 + 0.27 * mid) + glow * 0.34
    blue = field * (0.54 + 0.36 * high) + glow * 0.43 * (0.5 + 0.5 * mid)
    rgb = np.stack([red, green, blue], axis=-1) * vignette[..., None]
    return (np.clip(rgb, 0.0, 1.0) * 255.0).astype(np.uint8)


def render(controls_path: Path, output: Path, width: int, height: int, ffmpeg: str = "ffmpeg") -> None:
    payload = json.loads(controls_path.read_text(encoding="utf-8"))
    fps = float(payload["fps"])
    frames = payload["frames"]
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = [ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{width}x{height}", "-r", str(fps), "-i", "-", "-an",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", str(output)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    assert proc.stdin is not None
    try:
        for control in frames:
            proc.stdin.write(render_frame(width, height, control).tobytes())
    finally:
        proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg render failed")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("controls", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--width", type=int, default=960)
    parser.add_argument("--height", type=int, default=540)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    args = parser.parse_args()
    render(args.controls, args.output, args.width, args.height, args.ffmpeg)


if __name__ == "__main__":
    main()
