#!/usr/bin/env python3
"""Validate and optionally music-snap an AIVideoEdit scene timeline.

This tool does not invent scenes or directing decisions. It preserves scene order
and only moves explicit internal boundaries/transitions to nearby anchors from the
canonical audiomap produced by audio_map.py.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

SCHEMA = "aivideoedit.scene-timeline.v1"


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"invalid JSON {path}: {exc}") from exc


def effect_names() -> set[str]:
    catalog = Path(__file__).resolve().parents[1] / "render_runtime" / "effects_catalog.json"
    if not catalog.is_file():
        return set()
    doc = load_json(catalog)
    return {str(x.get("id")) for x in doc.get("effects", []) if x.get("id")}


def validate(plan: dict[str, Any], known_effects: set[str] | None = None) -> list[str]:
    errors: list[str] = []
    if plan.get("schema") != SCHEMA:
        errors.append(f"schema must be {SCHEMA}")
    try:
        duration = float(plan.get("duration_sec", 0))
    except Exception:
        duration = 0.0
    if duration <= 0:
        errors.append("duration_sec must be > 0")

    scenes = plan.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        errors.append("scenes must be a non-empty list")
        return errors

    ids: set[str] = set()
    previous_end = 0.0
    for i, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            errors.append(f"scene[{i}] must be an object")
            continue
        sid = str(scene.get("id") or "")
        if not sid:
            errors.append(f"scene[{i}] requires id")
        elif sid in ids:
            errors.append(f"duplicate scene id: {sid}")
        ids.add(sid)
        try:
            start = float(scene["start"])
            end = float(scene["end"])
        except Exception:
            errors.append(f"scene[{i}] requires numeric start/end")
            continue
        if start < -1e-6 or end <= start:
            errors.append(f"scene[{i}] has invalid range")
        if end > duration + 0.05:
            errors.append(f"scene[{i}] exceeds duration")
        if i and start < previous_end - 1e-6:
            errors.append(f"scene[{i}] overlaps previous scene")
        previous_end = end

    transitions = plan.get("transitions", [])
    if not isinstance(transitions, list):
        errors.append("transitions must be a list")
        return errors
    for i, transition in enumerate(transitions):
        if not isinstance(transition, dict):
            errors.append(f"transition[{i}] must be an object")
            continue
        effect = str(transition.get("effect") or "")
        if not effect:
            errors.append(f"transition[{i}] requires effect")
        elif known_effects and effect not in known_effects:
            errors.append(f"transition[{i}] unknown effect: {effect}")
        try:
            at = float(transition["at"])
            td = float(transition.get("duration", 0.7))
        except Exception:
            errors.append(f"transition[{i}] requires numeric at/duration")
            continue
        if not 0 <= at <= duration:
            errors.append(f"transition[{i}] at is outside duration")
        if td <= 0:
            errors.append(f"transition[{i}] duration must be > 0")
    return errors


def audio_anchors(audiomap: dict[str, Any]) -> list[tuple[float, str, int]]:
    anchors: dict[float, tuple[str, int]] = {}

    def add(value: Any, source: str, priority: int) -> None:
        try:
            t = round(float(value), 4)
        except Exception:
            return
        if t < 0:
            return
        current = anchors.get(t)
        if current is None or priority < current[1]:
            anchors[t] = (source, priority)

    for item in audiomap.get("energy", {}).get("key_moments", []):
        add(item.get("t"), f"energy_{item.get('kind', 'moment')}", 0)
    for item in audiomap.get("phrase_candidates", []):
        add(item.get("start"), "phrase_boundary", 1)
        add(item.get("end"), "phrase_boundary", 1)
    for t in audiomap.get("rhythm", {}).get("downbeats_sec", []):
        add(t, "downbeat", 2)
    for item in audiomap.get("silences", []):
        add(item.get("start"), "silence_edge", 2)
        add(item.get("end"), "silence_edge", 2)
    for t in audiomap.get("rhythm", {}).get("beats_sec", []):
        add(t, "beat", 3)
    return sorted((t, source, priority) for t, (source, priority) in anchors.items())


def nearest_anchor(time_sec: float, anchors: list[tuple[float, str, int]], window: float):
    candidates = [a for a in anchors if abs(a[0] - time_sec) <= window]
    if not candidates:
        return None
    return min(candidates, key=lambda a: (abs(a[0] - time_sec), a[2], a[0]))


def contiguous_boundaries(scenes: list[dict[str, Any]], tolerance: float = 0.08):
    out = []
    for i in range(len(scenes) - 1):
        left = float(scenes[i]["end"])
        right = float(scenes[i + 1]["start"])
        if abs(left - right) <= tolerance:
            out.append((i, round((left + right) / 2.0, 4)))
    return out


def snap_timeline(
    plan: dict[str, Any],
    audiomap: dict[str, Any],
    window: float = 0.25,
    snap_all_boundaries: bool = False,
    min_scene_duration: float = 0.25,
) -> dict[str, Any]:
    result = copy.deepcopy(plan)
    scenes = result["scenes"]
    transitions = result.setdefault("transitions", [])
    anchors = audio_anchors(audiomap)
    changes: list[dict[str, Any]] = []

    if snap_all_boundaries:
        for left_index, original in contiguous_boundaries(scenes):
            match = nearest_anchor(original, anchors, window)
            if not match:
                continue
            target, source, _priority = match
            left = scenes[left_index]
            right = scenes[left_index + 1]
            if target - float(left["start"]) < min_scene_duration:
                continue
            if float(right["end"]) - target < min_scene_duration:
                continue
            left["end"] = target
            right["start"] = target
            changes.append({"kind": "scene_boundary", "from": original, "to": target, "source": source})
            for transition in transitions:
                if abs(float(transition["at"]) - original) <= 0.08:
                    transition["at"] = target

    for transition in transitions:
        original = float(transition["at"])
        match = nearest_anchor(original, anchors, window)
        if not match:
            continue
        target, source, _priority = match
        transition["at"] = target
        transition["snap"] = {"from": round(original, 4), "to": target, "source": source}
        changes.append({"kind": "transition", "effect": transition.get("effect"),
                        "from": round(original, 4), "to": target, "source": source})

        # Keep a contiguous scene cut and its transition on the same timestamp.
        boundaries = contiguous_boundaries(scenes)
        if boundaries:
            left_index, boundary = min(boundaries, key=lambda b: abs(b[1] - original))
            if abs(boundary - original) <= 0.08:
                left = scenes[left_index]
                right = scenes[left_index + 1]
                if target - float(left["start"]) >= min_scene_duration and float(right["end"]) - target >= min_scene_duration:
                    left["end"] = target
                    right["start"] = target

    result["audio_timing"] = {
        "schema": audiomap.get("schema"),
        "source_sha256": audiomap.get("source", {}).get("sha256"),
        "snap_window_sec": window,
        "changes": changes,
        "rule": "Scene order is immutable; only explicit boundaries/transitions may move to nearby canonical audio anchors.",
    }
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate/snap AIVideoEdit scene timeline JSON")
    ap.add_argument("timeline", type=Path)
    ap.add_argument("-o", "--output", type=Path)
    ap.add_argument("--audio-map", type=Path)
    ap.add_argument("--snap-window", type=float, default=0.25)
    ap.add_argument("--snap-all-boundaries", action="store_true")
    ap.add_argument("--check-only", action="store_true")
    args = ap.parse_args()

    plan = load_json(args.timeline)
    errors = validate(plan, effect_names())
    if errors:
        raise SystemExit("timeline validation failed: " + "; ".join(errors))
    if args.check_only:
        print(json.dumps({"schema": SCHEMA, "valid": True, "timeline": str(args.timeline)}, indent=2))
        return 0

    result = plan
    if args.audio_map:
        audiomap = load_json(args.audio_map)
        if audiomap.get("schema") != "aivideoedit.audiomap.v1":
            raise SystemExit("--audio-map must use aivideoedit.audiomap.v1")
        if args.snap_window < 0:
            raise SystemExit("--snap-window must be >= 0")
        result = snap_timeline(plan, audiomap, args.snap_window, args.snap_all_boundaries)
        errors = validate(result, effect_names())
        if errors:
            raise SystemExit("snapped timeline validation failed: " + "; ".join(errors))

    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
        print(json.dumps({"output": str(args.output), "valid": True}, indent=2))
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
