#!/usr/bin/env python3
"""Continuous soft-depth living-parallax reference renderer.

Real depth maps are preferred. A synthetic fallback exists only for proof/testing.
Frames stream to ffmpeg and are not accumulated in memory.
"""
from __future__ import annotations

import argparse
import math
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image


def load_rgb(path: Path, max_dim: int = 1280) -> np.ndarray:
    image = Image.open(path).convert("RGB")
    scale = min(1.0, max_dim / max(image.size))
    if scale < 1.0:
        image = image.resize((round(image.width * scale), round(image.height * scale)), Image.Resampling.LANCZOS)
    return np.asarray(image, dtype=np.float32) / 255.0


def load_depth(path: Path | None, height: int, width: int) -> tuple[np.ndarray, str]:
    if path is not None:
        image = Image.open(path).convert("L").resize((width, height), Image.Resampling.BICUBIC)
        depth = np.asarray(image, dtype=np.float32) / 255.0
        return depth, "provided_depth_map"
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
    cx, cy = width * 0.5, height * 0.45
    radius = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    depth = 1.0 - np.clip(radius / (max(width, height) * 0.68), 0.0, 1.0)
    return depth, "synthetic_radial_fallback"


def warp(rgb: np.ndarray, depth: np.ndarray, dx: float, dy: float, strength: float) -> np.ndarray:
    height, width = depth.shape
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
    z = depth - float(depth.mean())
    map_x = np.clip(xx + z * dx * width * strength, 0, width - 1.001)
    map_y = np.clip(yy + z * dy * height * strength, 0, height - 1.001)
    x0 = np.floor(map_x).astype(np.int32); y0 = np.floor(map_y).astype(np.int32)
    x1 = np.clip(x0 + 1, 0, width - 1); y1 = np.clip(y0 + 1, 0, height - 1)
    wx = (map_x - x0)[..., None]; wy = (map_y - y0)[..., None]
    a = rgb[y0, x0]; b = rgb[y0, x1]; c = rgb[y1, x0]; d = rgb[y1, x1]
    return np.clip(a * (1-wx)*(1-wy) + b*wx*(1-wy) + c*(1-wx)*wy + d*wx*wy, 0.0, 1.0)


def render(image: Path, output: Path, depth_path: Path | None, frames: int, fps: float, amplitude: float, strength: float, ffmpeg: str) -> str:
    rgb = load_rgb(image)
    height, width = rgb.shape[:2]
    depth, depth_mode = load_depth(depth_path, height, width)
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = [ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{width}x{height}", "-r", str(fps), "-i", "-", "-an",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", str(output)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    assert proc.stdin is not None
    try:
        for i in range(frames):
            angle = (i / frames) * math.tau
            dx = math.sin(angle) * amplitude
            dy = math.sin(angle * 2.0) * amplitude * 0.35
            frame = (warp(rgb, depth, dx, dy, strength) * 255.0).astype(np.uint8)
            proc.stdin.write(frame.tobytes())
    finally:
        proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg render failed")
    return depth_mode


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--depth", type=Path)
    parser.add_argument("--frames", type=int, default=90)
    parser.add_argument("--fps", type=float, default=30.0)
    parser.add_argument("--amplitude", type=float, default=0.9)
    parser.add_argument("--strength", type=float, default=0.032)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    args = parser.parse_args()
    mode = render(args.image, args.output, args.depth, args.frames, args.fps, args.amplitude, args.strength, args.ffmpeg)
    print(f"wrote {args.output} depth_mode={mode}")


if __name__ == "__main__":
    main()
