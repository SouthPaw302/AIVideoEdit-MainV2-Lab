#!/usr/bin/env python3
"""AIVideoEdit deterministic music analysis.

Produces a canonical audiomap.json used by directors, storyboard planners, effects,
and render/QC tooling. This module is additive: it does not participate in agent
boot and is only invoked when a production asks for audio-grounded timing.

Design lineage: incorporates ideas from the Apache-2.0 heygen-com/hyperframes
music analysis workflow (single trusted analysis pass, energy/onset/roll/silence
layers), adapted to the AIVideoEdit production contract and naming.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCHEMA = "aivideoedit.audiomap.v1"
SR = 22050
HOP = 512


def _need_dependencies():
    try:
        import librosa  # type: ignore
        import numpy as np  # type: ignore
        import soundfile as sf  # type: ignore
    except ImportError as exc:
        raise SystemExit(
            "audio_map requires librosa, numpy and soundfile. Install with: "
            "python -m pip install librosa numpy soundfile"
        ) from exc
    return librosa, np, sf


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def decode_audio(path: Path, sf):
    if shutil.which("ffmpeg") is None:
        raise SystemExit("audio_map requires ffmpeg on PATH")
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav = Path(tmp.name)
    try:
        p = subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(path),
             "-vn", "-ac", "1", "-ar", str(SR), str(wav)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False,
        )
        if p.returncode != 0:
            raise SystemExit(f"ffmpeg audio decode failed: {p.stderr.strip()}")
        y, sr = sf.read(str(wav), dtype="float32")
    finally:
        wav.unlink(missing_ok=True)
    if getattr(y, "ndim", 1) > 1:
        y = y.mean(axis=1)
    return y, int(sr), float(len(y) / sr)


def round_times(values, digits: int = 4):
    return [round(float(v), digits) for v in values]


def normalize(values, np):
    arr = np.asarray(values, dtype=float)
    if arr.size == 0:
        return arr
    peak = float(np.max(arr))
    return arr / (peak + 1e-12)


def beat_layer(y, sr, librosa, np):
    tempo, frames = librosa.beat.beat_track(y=y, sr=sr, hop_length=HOP, units="frames")
    beats = librosa.frames_to_time(frames, sr=sr, hop_length=HOP)
    bpm = float(np.atleast_1d(tempo)[0]) if len(frames) >= 2 else 0.0

    # Resolve a stable 4/4 phase from local RMS around each detected beat.
    rms = librosa.feature.rms(y=y, hop_length=HOP)[0]
    best_phase, best_score = 0, -1.0
    if len(frames):
        for phase in range(4):
            idx = [min(int(f), len(rms) - 1) for i, f in enumerate(frames) if i % 4 == phase]
            score = float(np.sum(rms[idx])) if idx else 0.0
            if score > best_score:
                best_phase, best_score = phase, score
    downbeats = [beats[i] for i in range(best_phase, len(beats), 4)]
    return {
        "bpm": round(bpm, 4),
        "beats_sec": round_times(beats),
        "downbeats_sec": round_times(downbeats),
        "phase_4_4": int(best_phase),
        "confidence_note": (
            "Beat timing is a machine estimate. Directors must prefer phrase/energy anchors "
            "for sparse or weakly rhythmic material."
        ),
    }


def onset_layer(y, sr, librosa, np):
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=HOP)
    frames = librosa.onset.onset_detect(
        onset_envelope=onset_env, sr=sr, hop_length=HOP, backtrack=False, units="frames"
    )
    times = librosa.frames_to_time(frames, sr=sr, hop_length=HOP)

    # Band energy lets us attach a useful coarse transient family without a model.
    S = np.abs(librosa.stft(y, hop_length=HOP)) ** 2
    freqs = librosa.fft_frequencies(sr=sr)
    masks = {
        "low": freqs < 180,
        "mid": (freqs >= 180) & (freqs < 2200),
        "high": freqs >= 5000,
    }
    band = {k: S[m].sum(axis=0) for k, m in masks.items()}
    total_flux = normalize(onset_env, np)
    events = []
    for t, f in zip(times, frames):
        fi = min(int(f), S.shape[1] - 1)
        energies = {k: float(v[fi]) for k, v in band.items()}
        dominant = max(energies, key=energies.get) if energies else "mid"
        kind = {"low": "low_hit", "mid": "mid_hit", "high": "high_hit"}[dominant]
        flux_i = min(fi, len(total_flux) - 1)
        events.append({
            "t": round(float(t), 4),
            "kind": kind,
            "strength": round(float(total_flux[flux_i]) if len(total_flux) else 0.0, 4),
        })
    return events


def energy_layer(y, sr, duration, librosa, np):
    # ~1 second energy buckets give the director a stable macro narrative.
    frame_length = max(2048, int(sr))
    rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=frame_length)[0]
    norm = normalize(rms, np)

    def level(x: float) -> str:
        if x < 0.16:
            return "void"
        if x < 0.38:
            return "low"
        if x < 0.68:
            return "medium"
        return "high"

    buckets = []
    for i, value in enumerate(norm):
        start = float(i)
        end = min(duration, float(i + 1))
        buckets.append({"start": round(start, 3), "end": round(end, 3),
                        "energy": round(float(value), 4), "level": level(float(value))})

    phases = []
    for b in buckets:
        if not phases or phases[-1]["level"] != b["level"]:
            phases.append({"start": b["start"], "end": b["end"], "level": b["level"],
                           "energy_values": [b["energy"]]})
        else:
            phases[-1]["end"] = b["end"]
            phases[-1]["energy_values"].append(b["energy"])
    for p in phases:
        vals = p.pop("energy_values")
        p["energy"] = round(float(sum(vals) / max(1, len(vals))), 4)

    moments = []
    for prev, cur in zip(buckets, buckets[1:]):
        delta = cur["energy"] - prev["energy"]
        if abs(delta) >= 0.14:
            moments.append({
                "t": cur["start"],
                "kind": "surge" if delta > 0 else "drop",
                "delta": round(float(delta), 4),
            })
    moments.sort(key=lambda m: abs(m["delta"]), reverse=True)
    return buckets, phases, moments[:16]


def silence_layer(y, sr, duration, librosa, np):
    intervals = librosa.effects.split(y, top_db=38)
    nonsilent = [(a / sr, b / sr) for a, b in intervals]
    silences = []
    cursor = 0.0
    for a, b in nonsilent:
        if a - cursor >= 0.18:
            silences.append({"start": round(cursor, 4), "end": round(a, 4),
                             "duration": round(a - cursor, 4)})
        cursor = max(cursor, b)
    if duration - cursor >= 0.18:
        silences.append({"start": round(cursor, 4), "end": round(duration, 4),
                         "duration": round(duration - cursor, 4)})
    return silences


def roll_layer(events, bpm):
    if bpm <= 0 or len(events) < 4:
        return []
    beat = 60.0 / bpm
    continuation = beat * 0.58
    dense_mean = beat * 0.44
    rolls = []
    i = 0
    while i < len(events) - 3:
        j = i + 1
        while j < len(events) and events[j]["t"] - events[j - 1]["t"] <= continuation:
            j += 1
        run = events[i:j]
        if len(run) >= 4:
            gaps = [run[k]["t"] - run[k - 1]["t"] for k in range(1, len(run))]
            mean_gap = sum(gaps) / len(gaps)
            if mean_gap <= dense_mean:
                rolls.append({"start": run[0]["t"], "end": run[-1]["t"],
                              "hits": len(run), "mean_gap": round(mean_gap, 4)})
        i = max(i + 1, j)
    return rolls


def phrase_layer(duration, downbeats, moments, silences):
    # Facts only: phrase candidates are anchors, not semantic verse/chorus labels.
    anchors = {0.0, round(duration, 4)}
    for t in downbeats:
        if 0 < t < duration:
            anchors.add(round(float(t), 4))
    for m in moments:
        anchors.add(round(float(m["t"]), 4))
    for s in silences:
        anchors.add(round(float(s["start"]), 4))
        anchors.add(round(float(s["end"]), 4))
    ordered = sorted(anchors)

    # Keep macro candidates: at least ~4 seconds apart, while preserving strong moments.
    macro = [ordered[0]] if ordered else [0.0]
    strong = {round(float(m["t"]), 4) for m in moments[:8]}
    for t in ordered[1:-1]:
        if t in strong or t - macro[-1] >= 4.0:
            macro.append(t)
    if not macro or abs(macro[-1] - duration) > 1e-4:
        macro.append(round(duration, 4))
    return [{"start": macro[i], "end": macro[i + 1]}
            for i in range(len(macro) - 1) if macro[i + 1] > macro[i]]


def analyze(path: Path) -> dict:
    librosa, np, sf = _need_dependencies()
    y, sr, duration = decode_audio(path, sf)
    beat = beat_layer(y, sr, librosa, np)
    events = onset_layer(y, sr, librosa, np)
    buckets, phases, moments = energy_layer(y, sr, duration, librosa, np)
    silences = silence_layer(y, sr, duration, librosa, np)
    rolls = roll_layer(events, beat["bpm"])
    phrases = phrase_layer(duration, beat["downbeats_sec"], moments, silences)
    return {
        "schema": SCHEMA,
        "source": {
            "file": path.name,
            "sha256": sha256_file(path),
        },
        "audio": {
            "duration_sec": round(duration, 4),
            "analysis_sample_rate": sr,
        },
        "rhythm": beat,
        "events": events,
        "rolls": rolls,
        "silences": silences,
        "energy": {
            "buckets": buckets,
            "phases": phases,
            "key_moments": moments,
        },
        "phrase_candidates": phrases,
        "director_rule": (
            "This file is the canonical machine timing map for this source hash. "
            "Do not re-measure timing with another analyzer inside the same production."
        ),
    }


def validate(doc: dict) -> list[str]:
    errors = []
    if doc.get("schema") != SCHEMA:
        errors.append("wrong schema")
    dur = float(doc.get("audio", {}).get("duration_sec", 0))
    if dur <= 0:
        errors.append("duration must be positive")
    last = -1.0
    for t in doc.get("rhythm", {}).get("beats_sec", []):
        t = float(t)
        if t < last or t < 0 or t > dur + 0.05:
            errors.append("invalid beat ordering/range")
            break
        last = t
    for p in doc.get("phrase_candidates", []):
        if not (0 <= float(p["start"]) < float(p["end"]) <= dur + 0.05):
            errors.append("invalid phrase candidate")
            break
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description="Build canonical AIVideoEdit audiomap.json")
    ap.add_argument("input", type=Path)
    ap.add_argument("-o", "--output", type=Path, default=Path("audiomap.json"))
    ap.add_argument("--print", action="store_true", dest="print_summary")
    args = ap.parse_args()
    src = args.input.expanduser().resolve()
    if not src.is_file():
        raise SystemExit(f"audio input not found: {src}")
    doc = analyze(src)
    errors = validate(doc)
    if errors:
        raise SystemExit("audiomap validation failed: " + "; ".join(errors))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.print_summary:
        print(json.dumps({
            "output": str(args.output),
            "duration_sec": doc["audio"]["duration_sec"],
            "bpm": doc["rhythm"]["bpm"],
            "beats": len(doc["rhythm"]["beats_sec"]),
            "events": len(doc["events"]),
            "rolls": len(doc["rolls"]),
            "silences": len(doc["silences"]),
            "key_moments": doc["energy"]["key_moments"],
        }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
