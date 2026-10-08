"""Deterministic reusable effects for animating still images into living scenes.

All frame effects are image-space effects. They do not claim semantic depth or 3D
geometry. Functions accept a BGR uint8 frame and an FXContext-like object with
``phase`` and ``t`` attributes. Periodic effects are loop-safe when phase wraps.
"""
from __future__ import annotations

import math

import cv2
import numpy as np

TAU = math.tau


def _grid(shape):
    h, w = shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    return yy, xx


def _roi_mask(shape, roi=(0.0, 0.0, 1.0, 1.0), blur=12.0):
    h, w = shape[:2]
    x0, y0, x1, y1 = (float(v) for v in roi)
    m = np.zeros((h, w), np.float32)
    X0, X1 = max(0, int(x0 * w)), min(w, int(x1 * w))
    Y0, Y1 = max(0, int(y0 * h)), min(h, int(y1 * h))
    if X1 > X0 and Y1 > Y0:
        m[Y0:Y1, X0:X1] = 1.0
    if blur > 0:
        m = cv2.GaussianBlur(m, (0, 0), blur)
    return np.clip(m, 0.0, 1.0)


def _blend(a, b, mask):
    m = np.clip(mask, 0.0, 1.0).astype(np.float32)
    return np.clip(a.astype(np.float32) * (1.0 - m[..., None]) + b.astype(np.float32) * m[..., None], 0, 255).astype(np.uint8)


def _phase(ctx) -> float:
    return float(getattr(ctx, "phase", 0.0)) % 1.0


def camera_drift(bgr, ctx, strength=1.0, pan_px=8.0, tilt_deg=0.35, zoom=0.018):
    """Loop-safe gentle pan/tilt/zoom with reflected borders."""
    h, w = bgr.shape[:2]
    p = _phase(ctx) * TAU
    s = float(strength)
    dx = math.sin(p) * pan_px * s
    dy = math.sin(p * 2.0 + 0.55) * pan_px * 0.35 * s
    angle = math.sin(p + 1.2) * tilt_deg * s
    scale = 1.0 + (0.5 + 0.5 * math.cos(p)) * zoom * s
    M = cv2.getRotationMatrix2D((w * 0.5, h * 0.5), angle, scale)
    M[0, 2] += dx
    M[1, 2] += dy
    return cv2.warpAffine(bgr, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT_101)


def cloud_drift(bgr, ctx, roi=(0.0, 0.0, 1.0, 0.55), strength=0.55, seed=302):
    """Soft loop-safe cloud/fog layer intended for sky or distant atmosphere."""
    h, w = bgr.shape[:2]
    yy, xx = _grid(bgr.shape)
    rng = np.random.default_rng(int(seed))
    small = rng.random((max(8, h // 34), max(8, w // 34)), dtype=np.float32)
    field = cv2.resize(small, (w, h), interpolation=cv2.INTER_CUBIC)
    field = cv2.GaussianBlur(field, (0, 0), 8.0)
    lo, hi = np.percentile(field, [12, 91])
    field = np.clip((field - lo) / (hi - lo + 1e-6), 0, 1)
    p = _phase(ctx) * TAU
    dx = (22.0 * math.sin(p) + 7.0 * np.sin(yy / 83.0 + p)).astype(np.float32)
    dy = (5.0 * math.sin(p * 2.0) + 3.0 * np.sin(xx / 137.0 - p)).astype(np.float32)
    adv = cv2.remap(field, xx + dx, yy + dy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
    alpha = np.clip((adv - 0.40) * 0.20 * float(strength), 0, 0.11) * _roi_mask(bgr.shape, roi, 20)
    tint = np.full_like(bgr, 218, dtype=np.float32)
    return np.clip(bgr.astype(np.float32) * (1.0 - alpha[..., None]) + tint * alpha[..., None], 0, 255).astype(np.uint8)


def star_field(bgr, ctx, roi=(0.0, 0.0, 1.0, 0.65), strength=0.65, count=90, seed=302):
    """Deterministic twinkling star layer with no frame-to-frame random reseeding."""
    out = bgr.copy()
    h, w = bgr.shape[:2]
    m = _roi_mask(bgr.shape, roi, 5)
    rng = np.random.default_rng(int(seed) + 1109)
    pts = rng.random((int(count), 5), dtype=np.float32)
    p = _phase(ctx) * TAU
    for x, y, phase, size, warm in pts:
        xi, yi = int(x * (w - 1)), int(y * (h - 1))
        if m[yi, xi] < 0.2:
            continue
        freq = 1 + int(phase * 3.0)
        tw = max(0.0, 0.35 + 0.65 * math.sin(p * freq + phase * TAU))
        a = float(strength) * tw
        if a < 0.08:
            continue
        rad = 1 if size < 0.82 else 2
        c = int(min(255, 150 + 105 * a))
        color = (c, min(255, c + int(12 * warm)), min(255, c + int(28 * warm)))
        cv2.circle(out, (xi, yi), rad, color, -1, cv2.LINE_AA)
    return out


def snow_plane(bgr, ctx, roi=(0.0, 0.0, 1.0, 1.0), strength=0.65, count=100, seed=302):
    """Loop-safe depth-varied snow particle plane."""
    h, w = bgr.shape[:2]
    m = _roi_mask(bgr.shape, roi, 5)
    rng = np.random.default_rng(int(seed) + 2027)
    pts = rng.random((int(count), 5), dtype=np.float32)
    q = _phase(ctx)
    layer = np.zeros_like(bgr, dtype=np.uint8)
    for x0, y0, speed, phase, size in pts:
        depth = 0.35 + 0.65 * size
        y = ((y0 + q * (0.45 + speed * 0.75)) % 1.0) * h
        x = ((x0 + 0.018 * math.sin(q * TAU + phase * TAU) * depth) % 1.0) * w
        xi, yi = int(x) % w, int(y) % h
        if m[yi, xi] < 0.18:
            continue
        rad = max(1, int(1 + 2.2 * size))
        c = int((165 + 80 * depth) * m[yi, xi])
        cv2.circle(layer, (xi, yi), rad, (c, c, min(255, c + 7)), -1, cv2.LINE_AA)
    alpha = min(0.75, 0.24 + 0.42 * float(strength))
    return np.clip(bgr.astype(np.float32) + layer.astype(np.float32) * alpha, 0, 255).astype(np.uint8)


def bird_flock(bgr, ctx, roi=(0.05, 0.08, 0.95, 0.58), strength=0.7, count=7, seed=302):
    """Small distant looping flock silhouettes for atmospheric scale cues."""
    out = bgr.copy()
    h, w = bgr.shape[:2]
    x0, y0, x1, y1 = roi
    rng = np.random.default_rng(int(seed) + 3301)
    birds = rng.random((int(count), 4), dtype=np.float32)
    q = _phase(ctx)
    for base_x, base_y, speed, phase in birds:
        u = (base_x + q * (0.18 + 0.30 * speed)) % 1.0
        v = np.clip(base_y + 0.045 * math.sin(TAU * q + phase * TAU), 0, 1)
        x = int((x0 + u * (x1 - x0)) * w)
        y = int((y0 + v * (y1 - y0)) * h)
        wing = 1.0 + 0.7 * math.sin(q * TAU * (2.0 + speed) + phase * TAU)
        span = max(2, int((3 + 4 * speed) * float(strength)))
        rise = max(1, int(abs(wing) * 2))
        shade = int(35 + 30 * (1.0 - base_y))
        cv2.line(out, (x - span, y + rise), (x, y), (shade, shade, shade), 1, cv2.LINE_AA)
        cv2.line(out, (x, y), (x + span, y + rise), (shade, shade, shade), 1, cv2.LINE_AA)
    return out


def lens_bloom_flare(bgr, ctx, origin=(0.72, 0.22), strength=0.55, radius=0.24, warm=(55, 105, 185)):
    """Bounded breathing bloom/flare around a practical light or sun position."""
    h, w = bgr.shape[:2]
    yy, xx = _grid(bgr.shape)
    cx, cy = origin[0] * w, origin[1] * h
    rr = ((xx - cx) / (w * radius + 1e-6)) ** 2 + ((yy - cy) / (h * radius + 1e-6)) ** 2
    pulse = 0.72 + 0.28 * math.sin(_phase(ctx) * TAU) ** 2
    halo = np.exp(-rr * 2.2).astype(np.float32) * float(strength) * pulse
    streak = np.exp(-((yy - cy) / (h * 0.012 + 1e-6)) ** 2) * np.exp(-np.abs(xx - cx) / (w * 0.32 + 1e-6))
    alpha = np.clip(halo * 0.16 + streak * float(strength) * 0.035, 0, 0.20)
    tint = np.empty_like(bgr, dtype=np.float32)
    tint[:] = warm
    return np.clip(bgr.astype(np.float32) + tint * alpha[..., None], 0, 255).astype(np.uint8)


def sign_light_flicker(bgr, ctx, roi=(0.35, 0.28, 0.66, 0.58), strength=0.65, tint=(45, 105, 245)):
    """Loop-safe localized sign/window/practical-light flicker with bloom."""
    m = _roi_mask(bgr.shape, roi, 10)
    p = _phase(ctx) * TAU
    flick = 0.52 + 0.24 * math.sin(p) + 0.14 * math.sin(p * 3.0 + 0.7) + 0.10 * math.sin(p * 5.0 + 1.4)
    flick = np.clip(flick, 0.10, 1.0) * float(strength)
    glow = cv2.GaussianBlur(m, (0, 0), 14) * flick
    out = bgr.astype(np.float32)
    out += glow[..., None] * np.array(tint, np.float32) * 0.22
    return np.clip(out, 0, 255).astype(np.uint8)


def reflection_shimmer(bgr, ctx, roi=(0.0, 0.58, 1.0, 1.0), strength=0.7):
    """Localized loop-safe horizontal shimmer for water/glass/reflections."""
    h, w = bgr.shape[:2]
    yy, xx = _grid(bgr.shape)
    p = _phase(ctx) * TAU
    mask = _roi_mask(bgr.shape, roi, 12)
    dx = float(strength) * (2.8 * np.sin(yy / 8.5 + p * 2.0) + 1.2 * np.sin(xx / 47.0 - p))
    dy = float(strength) * 0.55 * np.sin(xx / 31.0 + p)
    warped = cv2.remap(bgr, xx + dx.astype(np.float32), yy + dy.astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)
    out = _blend(bgr, warped, mask * 0.42)
    shimmer = (0.5 + 0.5 * np.sin(xx / 16.0 + p * 2.0)) * mask * 4.0 * float(strength)
    return np.clip(out.astype(np.float32) + shimmer[..., None], 0, 255).astype(np.uint8)


def crossfade_dissolve(a, b, p, softness=1.0):
    """Endpoint-exact cosine-eased dissolve between equal-sized BGR frames."""
    if a.shape != b.shape:
        raise ValueError("crossfade_dissolve inputs must have identical shapes")
    q = float(np.clip(p, 0.0, 1.0))
    if q <= 0.0:
        return a.copy()
    if q >= 1.0:
        return b.copy()
    eased = 0.5 - 0.5 * math.cos(math.pi * q)
    if softness != 1.0:
        s = max(0.05, float(softness))
        eased = eased ** (1.0 / s)
    return cv2.addWeighted(a, 1.0 - eased, b, eased, 0.0)
