#!/usr/bin/env python3
"""Measured render controls and technical visual evidence.

Nothing in this module grants artistic or release approval.  Its output is
machine evidence that the renderer consumed changing audio controls, visibly
applied locked FX, retained temporal motion, and did not restart incoming
footage after a transition.
"""
from __future__ import annotations

from bisect import bisect_right
import hashlib
from pathlib import Path
import re
from typing import Any
import zipfile


class QualityError(ValueError):
    pass


def transition_prerolls(shots: list[dict], first_preroll: float = 0.0) -> list[float]:
    result = [max(0.0, float(first_preroll))]
    for previous in shots[:-1]:
        value = float(previous.get("transition_seconds", 0.5)) if previous.get("transition_out") else 0.0
        result.append(min(max(0.0, value), float(previous.get("duration_seconds") or 0.0)))
    return result


def manifest_fx_disposition(manifest: dict) -> list[dict]:
    result = []
    for shot in manifest.get("shots") or []:
        for spec in shot.get("fx", []):
            result.append({
                "id": str(spec["id"]), "kind": "effect", "shot_id": shot["id"],
                "intent": str(spec.get("intent") or "manifest-authorized scene treatment"),
                "protected_roi": (spec.get("params") or {}).get("protected_roi"),
                "status": "DIRECTOR_RECOMMENDED_FOR_HUMAN_REVIEW", "human_accepted": False,
            })
        if shot.get("transition_out"):
            result.append({
                "id": str(shot["transition_out"]), "kind": "transition", "shot_id": shot["id"],
                "intent": str(shot.get("transition_intent") or "authored continuity transition"),
                "status": "DIRECTOR_RECOMMENDED_FOR_HUMAN_REVIEW", "human_accepted": False,
            })
    return result


class AudioControls:
    def __init__(self, evidence: dict):
        controls = evidence.get("audio_controls")
        if not isinstance(controls, dict) or controls.get("source") != "decoded_pcm_rms_flux":
            raise QualityError("measured PCM audio controls are missing")
        points = controls.get("points")
        if not isinstance(points, list) or len(points) < 2:
            raise QualityError("audio controls require at least two measured points")
        cleaned = []
        for point in points:
            try:
                t = float(point["seconds"])
                energy = float(point["energy"])
                transient = float(point["transient"])
            except (KeyError, TypeError, ValueError) as exc:
                raise QualityError("malformed audio control point") from exc
            if t < 0 or not (0.0 <= energy <= 1.0 and 0.0 <= transient <= 1.0):
                raise QualityError("audio control values are outside their measured range")
            if cleaned and t <= cleaned[-1][0]:
                raise QualityError("audio control timestamps are not strictly increasing")
            cleaned.append((t, energy, transient))
        self.points = cleaned
        self.times = [item[0] for item in cleaned]
        self.energy_range = max(x[1] for x in cleaned) - min(x[1] for x in cleaned)
        self.transient_range = max(x[2] for x in cleaned) - min(x[2] for x in cleaned)
        if max(self.energy_range, self.transient_range) < 0.01:
            raise QualityError("audio controls are constant; measured musical response is absent")

    def at(self, seconds: float) -> tuple[float, float]:
        t = max(0.0, float(seconds))
        index = bisect_right(self.times, t)
        if index <= 0:
            return self.points[0][1], self.points[0][2]
        if index >= len(self.points):
            return self.points[-1][1], self.points[-1][2]
        a, b = self.points[index - 1], self.points[index]
        mix = (t - a[0]) / max(1e-9, b[0] - a[0])
        return a[1] + (b[1] - a[1]) * mix, a[2] + (b[2] - a[2]) * mix

    def summary(self, consumed_frames: int = 0) -> dict:
        return {
            "source": "decoded_pcm_rms_flux",
            "point_count": len(self.points),
            "energy_range": round(self.energy_range, 6),
            "transient_range": round(self.transient_range, 6),
            "time_varying": True,
            "consumed_frames": int(consumed_frames),
        }


def _signature(frame) -> list[int]:
    import cv2
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
    return cv2.resize(gray, (16, 9), interpolation=cv2.INTER_AREA).astype("uint8").reshape(-1).tolist()


def signature_delta(a: list[int] | None, b: list[int] | None) -> dict:
    if not a or not b or len(a) != len(b):
        return {"mean_abs_delta": None, "changed_fraction": None}
    values = [abs(int(x) - int(y)) for x, y in zip(a, b)]
    return {
        "mean_abs_delta": round(sum(values) / len(values), 6),
        "changed_fraction": round(sum(v >= 4 for v in values) / len(values), 6),
    }


class QualityCollector:
    """Bounded frame sampling for effect visibility and temporal motion."""

    def __init__(self, fps: int, shots: list[dict], *, first_preroll: float = 0.0, proof_dir: Path | None = None):
        self.fps = int(fps)
        self.sample_every = max(1, self.fps // 4)
        prerolls = transition_prerolls(shots, first_preroll)
        self.shots = {
            shot["id"]: {
                "shot_id": shot["id"],
                "media_kind": Path(str((shot.get("source") or {}).get("path") or "")).suffix.lower(),
                "entry_preroll_seconds": round(prerolls[i], 6),
                "transition_out": shot.get("transition_out"),
                "transition_seconds": round(float(shot.get("transition_seconds", 0.5)), 6) if shot.get("transition_out") else 0.0,
                "source_pairs": [],
                "output_pairs": [],
                "first_output_signature": None,
                "last_output_signature": None,
                "_source_previous": None,
                "_output_previous": None,
            }
            for i, shot in enumerate(shots)
        }
        self.effects: dict[str, dict[str, Any]] = {}
        self.proof_dir = Path(proof_dir) if proof_dir else None
        if self.proof_dir:
            self.proof_dir.mkdir(parents=True, exist_ok=True)

    def _observe(self, shot_id: str, frame, frame_index: int, kind: str) -> None:
        record = self.shots[shot_id]
        signature = _signature(frame)
        if kind == "output":
            record["first_output_signature"] = record["first_output_signature"] or signature
            record["last_output_signature"] = signature
        if frame_index % self.sample_every:
            return
        previous_key = "_" + kind + "_previous"
        pairs_key = kind + "_pairs"
        previous = record[previous_key]
        if previous is not None:
            record[pairs_key].append(signature_delta(previous, signature))
        record[previous_key] = signature

    def observe_source(self, shot_id: str, frame, frame_index: int) -> None:
        self._observe(shot_id, frame, frame_index, "source")

    def observe_output(self, shot_id: str, frame, frame_index: int) -> None:
        self._observe(shot_id, frame, frame_index, "output")

    def effect(self, effect_id: str, before, after, frame_index: int, *, kind: str, params: dict | None = None) -> None:
        record = self.effects.setdefault(effect_id, {
            "id": effect_id, "kind": kind, "applied_frames": 0, "sampled_frames": 0,
            "changed_samples": 0, "mean_abs_delta_sum": 0.0, "roi_samples": [],
            "proof_file": None, "proof_sha256": None,
        })
        record["applied_frames"] += 1
        if frame_index % self.sample_every and kind != "transition" and record["sampled_frames"]:
            return
        import numpy as np
        delta = np.abs(after.astype(np.int16) - before.astype(np.int16))
        mean = float(delta.mean())
        changed = float((delta >= 2).mean())
        record["sampled_frames"] += 1
        record["mean_abs_delta_sum"] += mean
        if mean >= 0.08 and changed >= 0.0005:
            record["changed_samples"] += 1
            if self.proof_dir and record["proof_file"] is None:
                import cv2
                import numpy as np
                pair = np.concatenate([
                    cv2.resize(before, (320, 180), interpolation=cv2.INTER_AREA),
                    cv2.resize(after, (320, 180), interpolation=cv2.INTER_AREA),
                ], axis=1)
                cv2.putText(pair, "BEFORE", (8, 22), cv2.FONT_HERSHEY_SIMPLEX, .55, (255, 255, 255), 1, cv2.LINE_AA)
                cv2.putText(pair, "AFTER", (328, 22), cv2.FONT_HERSHEY_SIMPLEX, .55, (255, 255, 255), 1, cv2.LINE_AA)
                safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", effect_id).strip("-") or "effect"
                proof = self.proof_dir / f"{safe}-{kind}.jpg"
                if not cv2.imwrite(str(proof), pair, [cv2.IMWRITE_JPEG_QUALITY, 92]):
                    raise QualityError("could not write FX visibility proof: " + effect_id)
                record["proof_file"] = proof.name
                record["proof_sha256"] = hashlib.sha256(proof.read_bytes()).hexdigest()
        params = params or {}
        roi = params.get("roi") or params.get("protected_roi")
        if isinstance(roi, list) and len(roi) == 4:
            h, w = delta.shape[:2]
            x0, y0, x1, y1 = roi
            x0, x1 = max(0, min(w, round(float(x0) * w))), max(0, min(w, round(float(x1) * w)))
            y0, y1 = max(0, min(h, round(float(y0) * h))), max(0, min(h, round(float(y1) * h)))
            if x1 > x0 and y1 > y0:
                inside = float(delta[y0:y1, x0:x1].mean())
                outside_pixels = delta.copy()
                outside_pixels[y0:y1, x0:x1] = 0
                outside_count = max(1, delta.shape[0] * delta.shape[1] - (y1 - y0) * (x1 - x0))
                outside = float(outside_pixels.sum() / (outside_count * (delta.shape[2] if len(delta.shape) == 3 else 1)))
                protected = bool(params.get("protected_roi"))
                record["roi_samples"].append({
                    "mode": "protected" if protected else "effect",
                    "inside_mean_abs_delta": round(inside, 6),
                    "outside_mean_abs_delta": round(outside, 6),
                    "full_frame_mean_abs_delta": round(mean, 6),
                    "protected_roi_preserved": (inside <= max(1.0, outside * 0.35)) if protected else None,
                })

    @staticmethod
    def _motion(pairs: list[dict]) -> dict:
        usable = [p for p in pairs if p["mean_abs_delta"] is not None]
        mean = sum(p["mean_abs_delta"] for p in usable) / len(usable) if usable else 0.0
        changed = sum(p["changed_fraction"] for p in usable) / len(usable) if usable else 0.0
        return {
            "sample_pairs": len(usable),
            "mean_abs_delta": round(mean, 6),
            "changed_fraction": round(changed, 6),
            "motion_visible": bool(usable and mean >= 0.35 and changed >= 0.005),
        }

    def summary(self) -> dict:
        effects = []
        for record in self.effects.values():
            sampled = record["sampled_frames"]
            effects.append({
                "id": record["id"], "kind": record["kind"],
                "applied_frames": record["applied_frames"], "sampled_frames": sampled,
                "changed_samples": record["changed_samples"],
                "mean_abs_delta": round(record["mean_abs_delta_sum"] / sampled, 6) if sampled else 0.0,
                "visible_change": bool(sampled and record["changed_samples"]),
                "roi_comparisons": record["roi_samples"][:8],
                "proof_file": record["proof_file"], "proof_sha256": record["proof_sha256"],
            })
        shots = []
        for record in self.shots.values():
            shots.append({
                key: value for key, value in record.items()
                if not key.startswith("_") and not key.endswith("_pairs")
            } | {
                "source_motion": self._motion(record["source_pairs"]),
                "output_motion": self._motion(record["output_pairs"]),
            })
        return {"effects": sorted(effects, key=lambda item: item["id"]), "shots": shots}


def inspect_source_media(manifest: dict, paths: list[Path], width: int, height: int) -> dict:
    import cv2
    shots = manifest.get("shots") or []
    if len(paths) != len(shots):
        raise QualityError("source inventory does not match the manifest")
    prerolls = transition_prerolls(shots)
    records = []
    for shot, path, preroll in zip(shots, paths, prerolls):
        if shot.get("loop") is True:
            raise QualityError("short-loop substitution is forbidden: " + shot["id"])
        if shot.get("media_role") not in {"real_source", "canonical_source_derived"}:
            raise QualityError("production source role is not releasable: " + shot["id"])
        suffix = path.suffix.lower()
        if suffix in {".png", ".jpg", ".jpeg"}:
            image = cv2.imread(str(path), cv2.IMREAD_COLOR)
            if image is None:
                raise QualityError("source image is undecodable: " + shot["id"])
            source_height, source_width = image.shape[:2]
            duration = None
            kind = "still"
        else:
            cap = cv2.VideoCapture(str(path))
            if not cap.isOpened():
                raise QualityError("source video is undecodable: " + shot["id"])
            source_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
            source_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
            source_fps = float(cap.get(cv2.CAP_PROP_FPS) or 0)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            cap.release()
            duration = frame_count / source_fps if source_fps > 0 and frame_count > 0 else 0.0
            needed = float(shot.get("source_start_seconds") or 0) + preroll + float(shot.get("duration_seconds") or 0)
            if duration + max(0.08, 2 / max(source_fps, 1)) < needed:
                raise QualityError("source clip is too short and cannot be loop-substituted: " + shot["id"])
            kind = "video"
        if source_width <= 0 or source_height <= 0:
            raise QualityError("source geometry is missing: " + shot["id"])
        fit = str(shot.get("fit") or "cover")
        scale = max(width / source_width, height / source_height) if fit == "cover" else min(width / source_width, height / source_height)
        if scale > 1.25:
            raise QualityError("low-resolution source would require excessive upscale: " + shot["id"])
        records.append({
            "shot_id": shot["id"], "kind": kind, "width": source_width, "height": source_height,
            "duration_seconds": round(duration, 6) if duration is not None else None,
            "entry_preroll_seconds": round(preroll, 6), "fit_scale": round(scale, 6), "pass": True,
        })
    return {
        "schema": "aivideoedit.source-media-qc.v1", "status": "PASS", "sources": records,
        "loop_substitution": False, "low_resolution_substitution": False,
        "human_visual_approval": False, "artistic_approval": False, "release_authority": False,
    }


def bundle_fx_proofs(proof_sets: list[tuple[str, Path]], target: Path) -> str:
    files = []
    for prefix, directory in proof_sets:
        if directory.is_dir():
            files.extend((prefix, path) for path in sorted(directory.glob("*.jpg")))
    if not files:
        raise QualityError("paired before/after FX proof frames are missing")
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for prefix, path in files:
            archive.write(path, arcname=f"{prefix}/{path.name}")
    return hashlib.sha256(target.read_bytes()).hexdigest()


def combine_visual_evidence(manifest: dict, shard_receipts: list[dict], gate: dict, render_sha256: str,
                            fx_proof_sha256: str | None = None) -> dict:
    shots = []
    effects: dict[tuple[str, str], dict] = {}
    controls = []
    for receipt in shard_receipts:
        evidence = receipt.get("technical_visual_evidence") or {}
        shots.extend(evidence.get("shots") or [])
        controls.append(receipt.get("music_controls") or {})
        for item in evidence.get("effects") or []:
            key = (str(item.get("id")), str(item.get("kind")))
            target = effects.setdefault(key, {"id": key[0], "kind": key[1], "applied_frames": 0,
                                                   "sampled_frames": 0, "changed_samples": 0,
                                                   "weighted_delta": 0.0, "proofs": [], "roi_comparisons": []})
            target["applied_frames"] += int(item.get("applied_frames") or 0)
            sampled = int(item.get("sampled_frames") or 0)
            target["sampled_frames"] += sampled
            target["changed_samples"] += int(item.get("changed_samples") or 0)
            target["weighted_delta"] += float(item.get("mean_abs_delta") or 0) * sampled
            if item.get("proof_file") and item.get("proof_sha256"):
                target["proofs"].append({"file": item["proof_file"], "sha256": item["proof_sha256"]})
            target["roi_comparisons"].extend(item.get("roi_comparisons") or [])
    effect_rows = []
    for target in effects.values():
        sampled = target["sampled_frames"]
        effect_rows.append({
            "id": target["id"], "kind": target["kind"], "applied_frames": target["applied_frames"],
            "sampled_frames": sampled, "changed_samples": target["changed_samples"],
            "mean_abs_delta": round(target["weighted_delta"] / sampled, 6) if sampled else 0.0,
            "visible_change": bool(sampled and target["changed_samples"]),
            "paired_frame_proofs": target["proofs"], "roi_comparisons": target["roi_comparisons"][:12],
        })
    expected = {(str(x["id"]), "effect") for x in gate.get("effects", [])}
    expected |= {(str(x["id"]), "transition") for x in gate.get("transitions", [])}
    actual = {(x["id"], x["kind"]) for x in effect_rows if x["visible_change"] and x["paired_frame_proofs"]}
    dispositions = gate.get("director_fx_disposition") or []
    disposed = {str(item.get("id")) for item in dispositions if item.get("status") == "DIRECTOR_RECOMMENDED_FOR_HUMAN_REVIEW"}
    protected_required = {str(item.get("id")) for item in dispositions if item.get("protected_roi")}
    protected_pass = {
        row["id"] for row in effect_rows
        if any(item.get("mode") == "protected" and item.get("protected_roi_preserved") is True
               for item in row.get("roi_comparisons") or [])
    }
    shot_by_id = {item.get("shot_id"): item for item in shots}
    seams = []
    timeline = manifest.get("shots") or []
    fps = int((manifest.get("output") or {}).get("fps") or 24)
    for previous, current in zip(timeline, timeline[1:]):
        if not previous.get("transition_out"):
            continue
        a, b = shot_by_id.get(previous["id"], {}), shot_by_id.get(current["id"], {})
        duration = min(float(previous.get("transition_seconds", 0.5)), float(previous.get("duration_seconds") or 0))
        scheduled = abs(float(b.get("entry_preroll_seconds") or 0) - duration) <= 1 / fps
        delta = signature_delta(a.get("last_output_signature"), b.get("first_output_signature"))
        seam_pass = scheduled and delta["mean_abs_delta"] is not None and delta["mean_abs_delta"] <= 48.0
        seams.append({
            "from": previous["id"], "to": current["id"], "transition": previous["transition_out"],
            "incoming_preroll_seconds": b.get("entry_preroll_seconds"), **delta,
            "no_restart": scheduled, "pass": seam_pass,
        })
    motion = [item for item in shots if (item.get("source_motion") or {}).get("motion_visible") or
              (item.get("output_motion") or {}).get("motion_visible")]
    controls_pass = bool(controls) and all(x.get("time_varying") is True and int(x.get("consumed_frames") or 0) > 0 for x in controls)
    source_qc = gate.get("source_media_qc") or {}
    checks = {
        "source_media_quality": source_qc.get("status") == "PASS",
        "time_varying_audio_controls_consumed": controls_pass,
        "all_locked_fx_visibly_changed_frames": expected <= actual,
        "paired_fx_proof_bundle_present": bool(fx_proof_sha256),
        "director_disposition_recorded_without_auto_approval": {item[0] for item in expected} <= disposed,
        "declared_protected_rois_preserved": protected_required <= protected_pass,
        "temporal_motion_measured": bool(motion),
        "transition_seams_continuous": all(x["pass"] for x in seams),
    }
    return {
        "schema": "aivideoedit.visual-qc-evidence.v1", "status": "PASS" if all(checks.values()) else "FAIL",
        "candidate_sha256": render_sha256, "fx_visibility_proof_sha256": fx_proof_sha256,
        "checks": checks, "source_media_qc": source_qc, "director_fx_disposition": dispositions,
        "music_controls": controls, "effects": sorted(effect_rows, key=lambda item: (item["id"], item["kind"])),
        "motion_shots": [item["shot_id"] for item in motion], "transition_seams": seams,
        "human_visual_approval": False, "artistic_approval": False, "release_authority": False,
        "note": "Numeric QC is technical evidence only; a human must judge storytelling, taste, and final visual acceptance.",
    }
