from __future__ import annotations

"""Project-neutral reactive material animation extracted from production practice.

The module keeps image identity anchored while allowing bright/hot material and
dark/charred material to move independently. It also provides deterministic
orbital embers as an optional companion effect. Both functions are frame-local
and accept the canonical FXContext shape (t, duration, energy, transient).
"""

import math
from typing import Any

import cv2
import numpy as np

TAU = math.tau


def _ctx(ctx: Any, name: str, default: float = 0.0) -> float:
    return float(getattr(ctx, name, default))


def _grid(shape):
    h, w = shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    return yy, xx


def _blend(a: np.ndarray, b: np.ndarray, m: np.ndarray) -> np.ndarray:
    m = np.clip(m, 0.0, 1.0).astype(np.float32)
    return np.clip(a.astype(np.float32) * (1.0 - m[..., None]) + b.astype(np.float32) * m[..., None], 0, 255).astype(np.uint8)


def reactive_material_split(
    bgr: np.ndarray,
    ctx: Any,
    strength: float = 1.0,
    threshold: float = 0.62,
    softness: float = 0.13,
    hot_motion_px: float = 2.4,
    dark_motion_px: float = 1.15,
    bloom: float = 0.24,
    protect: np.ndarray | None = None,
) -> np.ndarray:
    """Animate luminous and dark material as separate bounded image layers."""
    if bgr.ndim != 3 or bgr.shape[2] != 3:
        raise ValueError("bgr must be HxWx3")
    h, w = bgr.shape[:2]
    yy, xx = _grid(bgr.shape)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
    threshold = float(np.clip(threshold, 0.05, 0.95))
    softness = max(0.01, float(softness))
    hot = np.clip((gray - (threshold - softness)) / (2.0 * softness), 0.0, 1.0)
    hot = cv2.GaussianBlur(hot, (0, 0), 2.2)
    dark = cv2.GaussianBlur(1.0 - hot, (0, 0), 3.0)
    if protect is not None:
        p = np.clip(protect.astype(np.float32), 0.0, 1.0)
        hot *= 1.0 - p
        dark *= 1.0 - p
    t = _ctx(ctx, "t")
    duration = max(_ctx(ctx, "duration", 1.0), 1e-6)
    energy = np.clip(_ctx(ctx, "energy"), 0.0, 1.5)
    transient = np.clip(_ctx(ctx, "transient"), 0.0, 1.5)
    p = ((t / duration) % 1.0) * TAU
    drive = float(strength) * (0.78 + 0.20 * energy + 0.12 * transient)
    hot_amp = hot_motion_px * drive
    hot_dx = hot_amp * (0.62 * np.sin(yy / 43.0 + p * 1.15) + 0.38 * np.sin((xx + yy) / 91.0 - p * 0.72))
    hot_dy = hot_amp * (0.48 * np.sin(xx / 57.0 - p * 0.88) + 0.24 * np.cos((xx - yy) / 113.0 + p * 0.63))
    dark_amp = dark_motion_px * drive
    dark_dx = dark_amp * (0.58 * np.sin(yy / 73.0 - p * 0.54) + 0.24 * np.cos((xx + yy) / 151.0 + p * 0.31))
    dark_dy = dark_amp * (0.42 * np.sin(xx / 89.0 + p * 0.47) + 0.18 * np.sin((xx - yy) / 137.0 - p * 0.29))
    hot_warp = cv2.remap(bgr, xx + hot_dx.astype(np.float32), yy + hot_dy.astype(np.float32), cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT_101)
    dark_warp = cv2.remap(bgr, xx + dark_dx.astype(np.float32), yy + dark_dy.astype(np.float32), cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT_101)
    out = _blend(bgr, dark_warp, dark * 0.28)
    out = _blend(out, hot_warp, hot * 0.48)
    if bloom > 0:
        hot_rgb = out.astype(np.float32) * hot[..., None]
        sigma = max(1.5, min(h, w) * 0.009)
        halo = cv2.GaussianBlur(hot_rgb, (0, 0), sigma)
        pulse = 0.68 + 0.18 * math.sin(t * 5.1) + 0.12 * energy + 0.12 * transient
        out = np.clip(out.astype(np.float32) + halo * float(bloom) * pulse, 0, 255).astype(np.uint8)
    return out


def orbital_embers(
    bgr: np.ndarray,
    ctx: Any,
    strength: float = 1.0,
    count: int = 72,
    center: tuple[float, float] = (0.5, 0.5),
    radius: tuple[float, float] = (0.42, 0.33),
    seed: int = 302,
) -> np.ndarray:
    """Deterministic audio-reactive ember particles following orbital/swirl paths."""
    out = bgr.copy()
    h, w = bgr.shape[:2]
    t = _ctx(ctx, "t")
    energy = np.clip(_ctx(ctx, "energy"), 0.0, 1.5)
    transient = np.clip(_ctx(ctx, "transient"), 0.0, 1.5)
    rng = np.random.default_rng(int(seed))
    pts = rng.random((max(1, int(count)), 6), dtype=np.float32)
    cx, cy = center[0] * w, center[1] * h
    rx, ry = radius[0] * w, radius[1] * h
    speed_drive = 0.72 + 0.42 * energy + 0.34 * transient
    glow_drive = float(strength) * (0.55 + 0.35 * energy + 0.35 * transient)
    glow = np.zeros((h, w), np.float32)
    for r0, ang0, sp, lift, tw, sz in pts:
        ang = ang0 * TAU + t * (0.24 + 0.72 * sp) * speed_drive
        rr = 0.22 + 0.78 * r0
        x = cx + math.cos(ang) * rx * rr + math.sin(t * (0.8 + sp) + tw * TAU) * 9.0
        y = cy + math.sin(ang * (0.86 + 0.18 * lift)) * ry * rr - (t * (5.0 + 10.0 * lift)) % 34.0
        xi, yi = int(round(x)), int(round(y))
        if 1 <= xi < w - 1 and 1 <= yi < h - 1:
            flicker = 0.32 + 0.68 * max(0.0, math.sin(t * (2.3 + 2.5 * sp) + tw * TAU)) ** 3
            rad = 1 + int(sz > 0.76) + int(transient > 0.8 and sz > 0.9)
            c = (18, int(92 + 92 * flicker), int(188 + 64 * flicker))
            cv2.circle(out, (xi, yi), rad, c, -1, cv2.LINE_AA)
            cv2.circle(glow, (xi, yi), max(2, rad * 3), flicker * glow_drive, -1, cv2.LINE_AA)
    glow = cv2.GaussianBlur(glow, (0, 0), 3.8)
    tint = np.zeros_like(out, np.float32)
    tint[:, :, 1] = 78.0
    tint[:, :, 2] = 176.0
    return np.clip(out.astype(np.float32) + glow[..., None] * tint, 0, 255).astype(np.uint8)
