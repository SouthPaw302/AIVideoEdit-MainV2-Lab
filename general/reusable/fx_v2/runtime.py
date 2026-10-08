from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from typing import Any

import cv2
import numpy as np

TAU = math.tau


def _stable_seed_offset(key: str, modulus: int = 100000) -> int:
    """Return a process-stable integer derived from a textual cache/effect key."""
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % modulus


@dataclass
class FXContext:
    t: float
    duration: float
    frame_index: int
    fps: float
    energy: float = 0.0
    transient: float = 0.0
    brightness: float = 0.0

    @property
    def phase(self) -> float:
        d = max(self.duration, 1e-6)
        return (self.t / d) % 1.0


@dataclass
class FXRuntime:
    seed: int = 302
    cache: dict[str, Any] = field(default_factory=dict)

    def _grid(self, shape):
        h, w = shape[:2]
        k = f"grid:{w}x{h}"
        if k not in self.cache:
            yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
            self.cache[k] = (yy, xx)
        return self.cache[k]

    def roi_mask(self, shape, roi, blur=18.0, key=None):
        h, w = shape[:2]
        roi = tuple(float(x) for x in roi)
        k = key or f"roi:{w}x{h}:{roi}:{blur}"
        if k in self.cache:
            return self.cache[k]
        x0, y0, x1, y1 = roi
        m = np.zeros((h, w), np.float32)
        X0, X1 = max(0, int(x0 * w)), min(w, int(x1 * w))
        Y0, Y1 = max(0, int(y0 * h)), min(h, int(y1 * h))
        if X1 > X0 and Y1 > Y0:
            m[Y0:Y1, X0:X1] = 1.0
        if blur > 0:
            m = cv2.GaussianBlur(m, (0, 0), blur)
        self.cache[k] = m
        return m

    def ellipse_mask(self, shape, center, radius, blur=12.0, key=None):
        h, w = shape[:2]
        cx, cy = center
        rx, ry = radius
        k = key or f"ell:{w}x{h}:{center}:{radius}:{blur}"
        if k in self.cache:
            return self.cache[k]
        yy, xx = self._grid(shape)
        m = ((((xx - cx * w) / (rx * w + 1e-6)) ** 2 + ((yy - cy * h) / (ry * h + 1e-6)) ** 2) <= 1).astype(np.float32)
        if blur:
            m = cv2.GaussianBlur(m, (0, 0), blur)
        self.cache[k] = m
        return m

    def noise_field(self, shape, key, phase, scale=22, drift=(24.0, -18.0), sigma=5.5):
        h, w = shape[:2]
        base_key = f"noisebase:{key}:{w}x{h}:{scale}:{self.seed}"
        if base_key not in self.cache:
            rng = np.random.default_rng(self.seed + _stable_seed_offset(str(key)))
            base = rng.random((max(8, h // scale), max(8, w // scale)), dtype=np.float32)
            base = cv2.resize(base, (w, h), interpolation=cv2.INTER_CUBIC)
            base = cv2.GaussianBlur(base, (0, 0), sigma)
            lo, hi = np.percentile(base, [2, 98])
            base = np.clip((base - lo) / (hi - lo + 1e-6), 0, 1)
            self.cache[base_key] = base
        base = self.cache[base_key]
        yy, xx = self._grid(shape)
        p = phase * TAU
        dx = drift[0] * math.sin(p) + 5 * np.sin(yy / 77.0 + p)
        dy = drift[1] * (0.5 - 0.5 * math.cos(p)) + 4 * np.sin(xx / 103.0 - p * .8)
        return cv2.remap(base, xx + dx.astype(np.float32), yy + dy.astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)

    @staticmethod
    def blend(a, b, m):
        m = np.clip(m, 0, 1).astype(np.float32)
        return np.clip(a.astype(np.float32) * (1 - m[..., None]) + b.astype(np.float32) * m[..., None], 0, 255).astype(np.uint8)

    def localized_living_flow(self, bgr, ctx, mask=None, roi=None, strength=1.0, protect=None):
        h, w = bgr.shape[:2]
        yy, xx = self._grid(bgr.shape)
        p = ctx.phase * TAU
        if mask is None:
            mask = self.roi_mask(bgr.shape, roi or (0.0, 0.0, 1.0, 1.0), 20)
        m = mask.astype(np.float32)
        if protect is not None:
            m *= np.clip(1 - protect, 0, 1)
        amp = float(strength) * (0.72 + 0.18 * ctx.energy + 0.10 * ctx.transient)
        dx = amp * (1.15 * np.sin(yy / 61 + p) + .55 * np.sin((xx + yy) / 133 - p * .65))
        dy = amp * (.80 * np.sin(xx / 83 - p * .75) + .30 * np.cos((xx - yy) / 149 + p * .55))
        warped = cv2.remap(bgr, xx + dx.astype(np.float32), yy + dy.astype(np.float32), cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT_101)
        return self.blend(bgr, warped, np.clip(m * .72, 0, 1))

    def water_flow(self, bgr, ctx, roi=(0, 0.62, 1, 1), strength=.65, reflect=False):
        h, w = bgr.shape[:2]
        yy, xx = self._grid(bgr.shape)
        p = ctx.phase * TAU
        m = self.roi_mask(bgr.shape, roi, 15)
        amp = float(strength) * (1 + .25 * ctx.energy)
        dx = amp * (3.5 * np.sin(yy / 8.5 + p * 2) + 1.7 * np.sin(xx / 55 - p * .9))
        dy = amp * (.8 * np.sin(xx / 31 + p * 1.3))
        warped = cv2.remap(bgr, xx + dx.astype(np.float32), yy + dy.astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)
        out = self.blend(bgr, warped, m * .34)
        if reflect:
            x0, y0, x1, y1 = roi
            Y0 = int(y0 * h)
            if Y0 < h - 2:
                band = out[Y0:].copy()
                src = out[max(0, Y0 - band.shape[0]):Y0]
                if src.size:
                    src = cv2.resize(src, (w, band.shape[0]))
                    refl = cv2.flip(src, 0)
                    alpha = np.linspace(0, .14 * strength, band.shape[0], dtype=np.float32)[:, None, None]
                    out[Y0:] = np.clip(band * (1 - alpha) + refl * alpha, 0, 255).astype(np.uint8)
        return out

    def advected_smoke(self, bgr, ctx, roi=(0, 0, 1, 1), strength=.45, tint=(108, 108, 112), rise=True):
        m = self.roi_mask(bgr.shape, roi, 24)
        drift = (22, -30 if rise else -12)
        f = self.noise_field(bgr.shape, "smoke", ctx.phase, scale=28, drift=drift, sigma=7)
        alpha = np.clip((f - .45) * .28 * strength, 0, .16) * m
        tint_im = np.empty_like(bgr, dtype=np.float32)
        tint_im[:] = tint
        return np.clip(bgr.astype(np.float32) * (1 - alpha[..., None]) + tint_im * alpha[..., None], 0, 255).astype(np.uint8)

    def rain_plane(self, bgr, ctx, roi=(0, 0, 1, 1), strength=.55, angle=-.18):
        out = bgr.copy()
        h, w = bgr.shape[:2]
        mask = self.roi_mask(bgr.shape, roi, 10)
        rng = np.random.default_rng(self.seed + 411)
        count = max(1, int(115 * strength))
        pts = rng.random((count, 5), dtype=np.float32)
        for q in range(count):
            x0 = pts[q, 0] * w
            y0 = pts[q, 1] * (h + 100) - 50
            speed = .65 + pts[q, 2] * .85
            L = 8 + pts[q, 3] * 20
            y = (y0 + ctx.t * (210 + 90 * ctx.energy) * speed) % (h + 80) - 40
            x = (x0 + ctx.t * (18 + 25 * strength) * speed) % w
            xi, yi = int(x), int(y)
            if 0 <= xi < w and 0 <= yi < h and mask[yi, xi] > .18:
                dx = int(angle * L)
                c = int(150 + 70 * pts[q, 4])
                cv2.line(out, (xi, yi), (max(0, min(w - 1, xi + dx)), max(0, min(h - 1, yi + int(L)))), (c, c + 5, c + 10), 1, cv2.LINE_AA)
        return out

    def rain_glass(self, bgr, ctx, roi=(0, 0, 1, 1), strength=.6, drop_count=38):
        h, w = bgr.shape[:2]
        yy, xx = self._grid(bgr.shape)
        m = self.roi_mask(bgr.shape, roi, 8)
        rng = np.random.default_rng(self.seed + 719)
        drops = rng.random((drop_count, 5), dtype=np.float32)
        disp_x = np.zeros((h, w), np.float32)
        disp_y = np.zeros((h, w), np.float32)
        sheen = np.zeros((h, w), np.float32)
        for rx, ry, rs, rv, rp in drops:
            cx = rx * w
            cy = ((ry * h) + ctx.t * (18 + 55 * rv)) % (h + 50) - 25
            rad = 4 + 13 * rs * strength
            g = np.exp(-.5 * (((xx - cx) / (rad * 1.1)) ** 2 + ((yy - cy) / (rad * 1.5)) ** 2)).astype(np.float32)
            disp_x += g * (xx - cx) / (rad + 1e-6) * 1.8 * strength
            disp_y += g * (yy - cy) / (rad + 1e-6) * 1.1 * strength
            trail = np.exp(-.5 * ((xx - cx) / (rad * .55 + 1e-6)) ** 2) * np.exp(-np.maximum(0, cy - yy) / (rad * 5 + 1e-6))
            sheen += trail * .055 * strength
        refr = cv2.remap(bgr, xx + disp_x * m, yy + disp_y * m, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)
        out = self.blend(bgr, refr, m * .58)
        out = np.clip(out.astype(np.float32) + sheen[..., None] * m[..., None] * np.array([110, 118, 124], np.float32), 0, 255).astype(np.uint8)
        return out

    def living_flame(self, bgr, ctx, roi=(0.1, .45, .35, .95), strength=.8, core=(25, 145, 255), glow=(10, 55, 130)):
        h, w = bgr.shape[:2]
        yy, xx = self._grid(bgr.shape)
        x0, y0, x1, y1 = roi
        cx = (x0 + x1) * .5 * w
        base = y1 * h
        rw = max(6, (x1 - x0) * w * .32)
        rh = max(12, (y1 - y0) * h * .62)
        p = ctx.phase * TAU
        wobble = math.sin(p * 3.0) * rw * .10 + math.sin(p * 5.0 + 1.2) * rw * .06
        nx = (xx - (cx + wobble)) / (rw + 1e-6)
        ny = (base - yy) / (rh + 1e-6)
        body = np.exp(-(nx * nx * 2.3 + (ny - .33) ** 2 * 2.0))
        taper = np.clip(ny, 0, 1.2) * np.clip(1.35 - ny, 0, 1)
        n = self.noise_field(bgr.shape, "flame", ctx.phase, scale=36, drift=(9, -24), sigma=3.2)
        tongue = np.clip((n - .34) * 2.2, 0, 1) * taper
        flame = np.clip(body * (.55 + .85 * tongue), 0, 1)
        flame *= self.roi_mask(bgr.shape, roi, 7)
        pulse = .82 + .14 * math.sin(ctx.t * 7.3) + .07 * math.sin(ctx.t * 13.7 + 1.1) + .09 * ctx.transient
        flame = np.clip(flame * pulse * strength, 0, 1)
        halo = cv2.GaussianBlur(flame, (0, 0), max(4, rw * .75))
        f = bgr.astype(np.float32)
        f += halo[..., None] * np.array(glow, np.float32) * (.48 + .30 * ctx.energy)
        f += flame[..., None] * np.array(core, np.float32)
        out = np.clip(f, 0, 255).astype(np.uint8)
        dx = (np.sin(yy / 15 + p * 2) + .35 * np.sin((xx + yy) / 39 - p)) * 1.1 * strength
        warped = cv2.remap(out, xx + dx.astype(np.float32), yy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)
        return self.blend(out, warped, cv2.GaussianBlur(flame, (0, 0), 3) * .28)

    def embers(self, bgr, ctx, roi=(0, 0, 1, 1), strength=.5, count=55):
        out = bgr.copy()
        h, w = bgr.shape[:2]
        m = self.roi_mask(bgr.shape, roi, 8)
        rng = np.random.default_rng(self.seed + 983)
        pts = rng.random((count, 5), dtype=np.float32)
        for x0, y0, sp, ph, sz in pts:
            x = x0 * w + 10 * math.sin(ctx.t * (.7 + sp) + ph * TAU)
            y = (y0 * h - ctx.t * (16 + 35 * sp)) % (h + 40) - 20
            xi, yi = int(x), int(y)
            if 0 <= xi < w and 0 <= yi < h and m[yi, xi] > .15:
                a = max(0, math.sin(ctx.t * (2.1 + sp * 1.8) + ph * TAU)) ** 5
                if a > .08:
                    r = 1 if sz < .82 else 2
                    cv2.circle(out, (xi, yi), r, (25, int(95 + 70 * a), int(205 + 48 * a)), -1, cv2.LINE_AA)
        return out

    def practical_light_breath(self, bgr, ctx, mask=None, roi=(0, 0, 1, 1), strength=.08, warm=(4, 28, 74)):
        if mask is None:
            mask = self.roi_mask(bgr.shape, roi, 28)
        pulse = 1 + strength * (.48 * math.sin(ctx.t * 7.1) + .22 * math.sin(ctx.t * 13.9 + 1.3) + .14 * ctx.energy + .12 * ctx.transient)
        f = bgr.astype(np.float32)
        gain = (pulse - 1.0) * mask
        f += gain[..., None] * np.array(warm, np.float32)
        return np.clip(f, 0, 255).astype(np.uint8)

    def moving_light_field(self, bgr, ctx, origin=(.76, .17), strength=.08, warm=(8, 70, 160)):
        h, w = bgr.shape[:2]
        yy, xx = self._grid(bgr.shape)
        cx = (origin[0] + .025 * math.sin(ctx.phase * TAU)) * w
        cy = (origin[1] + .018 * math.cos(ctx.phase * TAU)) * h
        ang = np.arctan2(yy - cy, xx - cx)
        rad = np.sqrt(((xx - cx) / w) ** 2 + ((yy - cy) / h) ** 2)
        beam = (.5 + .5 * np.cos(ang * 15 + ctx.phase * TAU * .7)) ** 8
        beam *= np.exp(-rad * 2.7)
        noise = self.noise_field(bgr.shape, "light", ctx.phase, scale=30, drift=(14, -8), sigma=8)
        alpha = np.clip(beam * (.72 + .28 * noise) * strength * (.86 + .18 * ctx.energy), 0, .11)
        tint = np.empty_like(bgr, dtype=np.float32)
        tint[:] = warm
        return np.clip(bgr.astype(np.float32) * (1 - alpha[..., None]) + tint * alpha[..., None], 0, 255).astype(np.uint8)

    def temporal_palette_migration(self, bgr, ctx, cool=(18, 4, -8), warm=(-10, 9, 24), strength=.6):
        lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
        q = np.clip(ctx.phase, 0, 1) * strength
        lab[:, :, 1] += q * (warm[1] - cool[1])
        lab[:, :, 2] += q * (warm[2] - cool[2])
        return cv2.cvtColor(np.clip(lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)

    def temporal_canvas_lock(self, shape, key="canvas", amount=.55):
        h, w = shape[:2]
        k = f"canvas:{key}:{w}x{h}:{self.seed}"
        if k not in self.cache:
            rng = np.random.default_rng(self.seed + 29)
            yy, xx = self._grid(shape)
            weave = .38 * np.sin(xx / 3.2) + .28 * np.sin(yy / 4.6) + .16 * np.sin((xx + yy) / 8.1)
            coarse = rng.normal(0, 1, (max(8, h // 24), max(8, w // 24))).astype(np.float32)
            coarse = cv2.resize(coarse, (w, h), interpolation=cv2.INTER_CUBIC)
            coarse = cv2.GaussianBlur(coarse, (0, 0), 2.5)
            self.cache[k] = (weave + coarse * .8).astype(np.float32)
        return self.cache[k] * amount

    def apply_canvas(self, bgr, key="canvas", amount=.55):
        field = self.temporal_canvas_lock(bgr.shape, key, amount)
        return np.clip(bgr.astype(np.float32) + field[..., None], 0, 255).astype(np.uint8)

    def pigment_gate(self, a, b, p, key="pigment", softness=5.8):
        p = float(np.clip(p, 0, 1))
        if p <= 0:
            return a
        if p >= 1:
            return b
        n = self.noise_field(a.shape, key, 0.0, scale=24, drift=(0, 0), sigma=7)
        m = np.clip(((.16 + .68 * p) - n) * softness + .5, 0, 1)
        m = cv2.GaussianBlur(m, (0, 0), 2.2)
        bloom = 2.4 * math.sin(math.pi * p)
        aa = cv2.GaussianBlur(a, (0, 0), bloom) if bloom > .2 else a
        bb = cv2.GaussianBlur(b, (0, 0), bloom) if bloom > .2 else b
        return self.blend(aa, bb, m)

    def light_peak_handoff(self, a, b, p, origin=(.78, .17), strength=.42):
        p = float(np.clip(p, 0, 1))
        h, w = a.shape[:2]
        yy, xx = self._grid(a.shape)
        cx, cy = origin[0] * w, origin[1] * h
        r = np.sqrt(((xx - cx) / (w * .78)) ** 2 + ((yy - cy) / (h * .78)) ** 2)
        flare = np.exp(-r * r * 4.5) * math.sin(math.pi * p) ** 2
        hand = np.clip((p - .35) / .30, 0, 1)
        base = cv2.addWeighted(a, 1 - hand, b, hand, 0).astype(np.float32)
        base += flare[..., None] * np.array([95, 125, 190], np.float32) * strength
        return np.clip(base, 0, 255).astype(np.uint8)

    def reflection_gate(self, a, b, p, roi=(0, .58, 1, 1), strength=.85):
        p = float(np.clip(p, 0, 1))
        h, w = a.shape[:2]
        yy, xx = self._grid(a.shape)
        m = self.roi_mask(a.shape, roi, 18)
        wave = (2.8 * np.sin(yy / 9 + p * TAU * 2) + 1.1 * np.sin(xx / 47 - p * TAU)) * strength * math.sin(math.pi * p)
        bb = cv2.remap(b, xx + wave.astype(np.float32), yy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)
        q = np.clip((p - .18) / .64, 0, 1)
        return self.blend(a, bb, m * q)

    def doorway_depth_gate(self, a, b, p, door_roi=(.34, .10, .70, .98), strength=1.0):
        p = float(np.clip(p, 0, 1))
        h, w = a.shape[:2]
        yy, xx = self._grid(a.shape)
        x0, y0, x1, y1 = door_roi
        cx, cy = (x0 + x1) * .5 * w, (y0 + y1) * .5 * h
        rx, ry = (x1 - x0) * w * .5, (y1 - y0) * h * .5
        d = np.sqrt(((xx - cx) / (rx + 1e-6)) ** 2 + ((yy - cy) / (ry + 1e-6)) ** 2)
        radius = .08 + 1.32 * (p ** 1.25)
        mask = np.clip((radius - d) / .08 + .5, 0, 1)
        sc = 1.10 - .10 * p
        M = cv2.getRotationMatrix2D((w / 2, h / 2), 0, sc)
        bb = cv2.warpAffine(b, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT_101)
        out = self.blend(a, bb, mask)
        rim = np.exp(-((d - radius) / .055) ** 2) * math.sin(math.pi * p) * strength
        f = out.astype(np.float32) + rim[..., None] * np.array([18, 62, 125], np.float32)
        return np.clip(f, 0, 255).astype(np.uint8)

    def ember_to_light(self, a, b, p, origin=(.5, .55), strength=1.0):
        p = float(np.clip(p, 0, 1))
        h, w = a.shape[:2]
        yy, xx = self._grid(a.shape)
        cx, cy = origin[0] * w, origin[1] * h
        rr = np.sqrt(((xx - cx) / (w * .66)) ** 2 + ((yy - cy) / (h * .66)) ** 2)
        gate = np.clip((p * 1.5 - .18 - rr) * 5 + .5, 0, 1)
        out = self.blend(a, b, gate)
        peak = math.sin(math.pi * p) ** 2
        glow = np.exp(-rr * rr * 4.5) * peak
        return np.clip(out.astype(np.float32) + glow[..., None] * np.array([18, 82, 188], np.float32) * strength, 0, 255).astype(np.uint8)

    def apply(self, bgr, effect, ctx, protect=None):
        eid = effect["id"]
        s = float(effect.get("strength", 1.0))
        roi = tuple(effect.get("roi", [0, 0, 1, 1]))
        if eid == "FX2-MOTION-002":
            return self.localized_living_flow(bgr, ctx, roi=roi, strength=s, protect=protect)
        if eid == "FX2-MOTION-003":
            return self.water_flow(bgr, ctx, roi=roi, strength=s, reflect=bool(effect.get("reflect", False)))
        if eid == "FX2-ATM-001":
            return self.advected_smoke(bgr, ctx, roi=roi, strength=s)
        if eid == "FX2-ATM-002":
            return self.rain_plane(bgr, ctx, roi=roi, strength=s)
        if eid == "FX2-ATM-003":
            return self.rain_glass(bgr, ctx, roi=roi, strength=s, drop_count=int(effect.get("drop_count", 38)))
        if eid == "FX2-FIRE-001":
            return self.living_flame(bgr, ctx, roi=roi, strength=s)
        if eid == "FX2-FIRE-002":
            return self.embers(bgr, ctx, roi=roi, strength=s)
        if eid == "FX2-LIGHT-001":
            return self.practical_light_breath(bgr, ctx, roi=roi, strength=s * .08)
        if eid == "FX2-LIGHT-002":
            return self.moving_light_field(bgr, ctx, origin=tuple(effect.get("origin", [.76, .17])), strength=s * .08)
        if eid == "FX2-LIGHT-004":
            return self.temporal_palette_migration(bgr, ctx, strength=s)
        if eid == "FX2-SURFACE-001":
            return self.apply_canvas(bgr, effect.get("key", "canvas"), amount=s * .55)
        raise KeyError(f"Effect {eid} is not a single-frame effect or is not implemented in this module")
