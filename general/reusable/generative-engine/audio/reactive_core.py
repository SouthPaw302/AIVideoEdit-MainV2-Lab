#!/usr/bin/env python3
"""AIVideoEdit generative engine: normalized audio control bus.

Produces deterministic frame-aligned controls for visual systems:
RMS, onset, low, mid and high band energy. Band energy is derived from
windowed FFT bins, then normalized by robust percentiles and smoothed.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

try:
    import soundfile as sf
except ImportError as exc:  # pragma: no cover
    raise SystemExit("soundfile is required: pip install soundfile") from exc


@dataclass
class ReactiveFrame:
    time: float
    rms: float
    onset: float
    low: float
    mid: float
    high: float
    rms_n: float
    onset_n: float
    low_n: float
    mid_n: float
    high_n: float


def load_audio(path: str | Path) -> tuple[np.ndarray, int]:
    data, sr = sf.read(str(path), always_2d=True, dtype="float32")
    mono = data.mean(axis=1)
    return mono, int(sr)


def _robust_norm(values: np.ndarray, floor_pct: float = 5.0, ceil_pct: float = 99.0) -> np.ndarray:
    lo = float(np.percentile(values, floor_pct))
    hi = float(np.percentile(values, ceil_pct))
    if hi <= lo + 1e-12:
        return np.zeros_like(values, dtype=np.float32)
    return np.clip((values - lo) / (hi - lo), 0.0, 1.0).astype(np.float32)


def _smooth(values: np.ndarray, amount: float) -> np.ndarray:
    amount = float(np.clip(amount, 0.0, 0.999))
    if amount <= 0.0 or len(values) == 0:
        return values.astype(np.float32, copy=True)
    out = np.empty_like(values, dtype=np.float32)
    prev = float(values[0])
    for i, value in enumerate(values):
        prev = prev * amount + float(value) * (1.0 - amount)
        out[i] = prev
    return out


def compute_reactive(audio: np.ndarray, sr: int, fps: float = 30.0, smooth: float = 0.28) -> list[ReactiveFrame]:
    if fps <= 0:
        raise ValueError("fps must be > 0")
    if sr <= 0:
        raise ValueError("sample rate must be > 0")
    if audio.ndim != 1:
        raise ValueError("audio must be mono")

    hop = max(1, round(sr / fps))
    win = max(256, int(2 ** np.ceil(np.log2(hop * 2))))
    window = np.hanning(win).astype(np.float32)
    freqs = np.fft.rfftfreq(win, 1.0 / sr)
    band_masks = {
        "low": (freqs >= 20.0) & (freqs < 180.0),
        "mid": (freqs >= 180.0) & (freqs < 2200.0),
        "high": (freqs >= 2200.0) & (freqs < min(12000.0, sr / 2.0)),
    }

    n_frames = max(1, int(np.ceil(len(audio) / hop)))
    rms = np.zeros(n_frames, dtype=np.float32)
    low = np.zeros(n_frames, dtype=np.float32)
    mid = np.zeros(n_frames, dtype=np.float32)
    high = np.zeros(n_frames, dtype=np.float32)

    for i in range(n_frames):
        start = i * hop
        chunk = audio[start:start + win]
        if len(chunk) < win:
            chunk = np.pad(chunk, (0, win - len(chunk)))
        chunk = chunk.astype(np.float32, copy=False)
        rms[i] = float(np.sqrt(np.mean(chunk * chunk) + 1e-12))
        mag = np.abs(np.fft.rfft(chunk * window)).astype(np.float32)
        power = mag * mag
        for name, target in (("low", low), ("mid", mid), ("high", high)):
            mask = band_masks[name]
            target[i] = float(np.sqrt(np.mean(power[mask]) + 1e-12)) if np.any(mask) else 0.0

    onset = np.maximum(0.0, np.diff(np.log1p(rms * 100.0), prepend=np.log1p(rms[0] * 100.0))).astype(np.float32)

    normalized = {
        "rms": _smooth(_robust_norm(rms), smooth),
        "onset": _smooth(_robust_norm(onset), smooth * 0.55),
        "low": _smooth(_robust_norm(low), smooth),
        "mid": _smooth(_robust_norm(mid), smooth),
        "high": _smooth(_robust_norm(high), smooth),
    }

    return [
        ReactiveFrame(
            time=i / fps,
            rms=float(rms[i]), onset=float(onset[i]), low=float(low[i]), mid=float(mid[i]), high=float(high[i]),
            rms_n=float(normalized["rms"][i]), onset_n=float(normalized["onset"][i]),
            low_n=float(normalized["low"][i]), mid_n=float(normalized["mid"][i]), high_n=float(normalized["high"][i]),
        )
        for i in range(n_frames)
    ]


def save_reactive_json(frames: list[ReactiveFrame], path: str | Path, fps: float, sr: int, source: str) -> None:
    payload = {
        "schema": "aivideoedit.reactive-controls.v1",
        "source": source,
        "sample_rate": sr,
        "fps": fps,
        "bands_hz": {"low": [20, 180], "mid": [180, 2200], "high": [2200, 12000]},
        "normalization": "5th-99th percentile clamp + exponential smoothing",
        "frames": [asdict(frame) for frame in frames],
    }
    Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("audio")
    parser.add_argument("output")
    parser.add_argument("--fps", type=float, default=30.0)
    parser.add_argument("--smooth", type=float, default=0.28)
    args = parser.parse_args()
    audio, sr = load_audio(args.audio)
    frames = compute_reactive(audio, sr, fps=args.fps, smooth=args.smooth)
    save_reactive_json(frames, args.output, args.fps, sr, args.audio)
    print(f"wrote {len(frames)} control frames -> {args.output}")


if __name__ == "__main__":
    main()
