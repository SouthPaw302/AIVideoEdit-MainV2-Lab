#!/usr/bin/env python3
"""Validate and compile an AIVideoEdit audio mix plan.

The plan is project-neutral and carries track/bus effects plus deterministic
voice-over ducking. It does not source audio, infer creative intent, or replace
an accepted master. Spectral voice carving is intentionally not guessed here.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

SCHEMA = "aivideoedit.audio-mix.v1"
ROLES = {"voice", "music", "sfx", "ambience", "other"}
FX_TYPES = {
    "gain", "highpass", "lowpass", "peaking", "lowshelf", "highshelf",
    "compressor", "limiter", "gate", "saturate", "delay", "reverb",
    "chorus", "phaser", "bitcrush",
}
NON_AUTOMATABLE = {"compressor", "limiter", "gate", "bitcrush"}


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"invalid JSON {path}: {exc}") from exc


def _float(value: Any, label: str, errors: list[str], default: float | None = None) -> float | None:
    if value is None and default is not None:
        return default
    try:
        return float(value)
    except Exception:
        errors.append(f"{label} must be numeric")
        return None


def validate_chain(chain: Any, label: str, errors: list[str]) -> set[str]:
    if chain is None:
        return set()
    if not isinstance(chain, dict) or chain.get("version") != 1 or not isinstance(chain.get("nodes"), list):
        errors.append(f"{label}.fx_chain must be version 1 with nodes[]")
        return set()
    node_ids: set[str] = set()
    for i, node in enumerate(chain["nodes"]):
        if not isinstance(node, dict):
            errors.append(f"{label}.fx_chain.nodes[{i}] must be an object")
            continue
        fx_type = str(node.get("type") or "")
        if fx_type not in FX_TYPES:
            errors.append(f"{label}.fx_chain.nodes[{i}] unknown type: {fx_type}")
        node_id = str(node.get("id") or "")
        if node_id:
            if node_id in node_ids:
                errors.append(f"{label}.fx_chain duplicate node id: {node_id}")
            node_ids.add(node_id)
        if node.get("fromCarve"):
            errors.append(f"{label}.fx_chain.nodes[{i}] fromCarve is reserved for measured carve analysis")
        if "params" in node and not isinstance(node["params"], dict):
            errors.append(f"{label}.fx_chain.nodes[{i}].params must be an object")
    return node_ids


def validate_automation(automation: Any, label: str, node_ids: set[str], chain: Any, errors: list[str]) -> None:
    if automation is None:
        return
    if not isinstance(automation, dict) or automation.get("version") != 1 or not isinstance(automation.get("lanes"), list):
        errors.append(f"{label}.automation must be version 1 with lanes[]")
        return
    node_types = {}
    if isinstance(chain, dict):
        for node in chain.get("nodes", []):
            if isinstance(node, dict) and node.get("id"):
                node_types[str(node["id"])] = str(node.get("type") or "")
    for i, lane in enumerate(automation["lanes"]):
        if not isinstance(lane, dict):
            errors.append(f"{label}.automation.lanes[{i}] must be an object")
            continue
        target = str(lane.get("target") or "")
        if target != "volume":
            parts = target.split(".")
            if len(parts) != 3 or parts[0] != "fx" or parts[1] not in node_ids:
                errors.append(f"{label}.automation.lanes[{i}] invalid target: {target}")
            elif node_types.get(parts[1]) in NON_AUTOMATABLE:
                errors.append(f"{label}.automation.lanes[{i}] targets non-automatable effect: {node_types[parts[1]]}")
        points = lane.get("points")
        if not isinstance(points, list) or not points:
            errors.append(f"{label}.automation.lanes[{i}] requires points[]")
            continue
        if len(points) > 512:
            errors.append(f"{label}.automation.lanes[{i}] exceeds 512 points")
        last_t = -1.0
        for j, point in enumerate(points):
            if not isinstance(point, dict):
                errors.append(f"{label}.automation.lanes[{i}].points[{j}] must be an object")
                continue
            t = _float(point.get("t"), f"{label}.automation.lanes[{i}].points[{j}].t", errors)
            _float(point.get("v"), f"{label}.automation.lanes[{i}].points[{j}].v", errors)
            if t is not None:
                if t < 0 or t < last_t:
                    errors.append(f"{label}.automation.lanes[{i}] points must be ordered with t >= 0")
                last_t = t
            if "curve" in point:
                curve = _float(point.get("curve"), f"{label}.automation.lanes[{i}].points[{j}].curve", errors)
                if curve is not None and not -1 <= curve <= 1:
                    errors.append(f"{label}.automation.lanes[{i}].points[{j}].curve must be -1..1")


def validate(plan: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if plan.get("schema") != SCHEMA:
        errors.append(f"schema must be {SCHEMA}")
    tracks = plan.get("tracks")
    if not isinstance(tracks, list) or not tracks:
        return errors + ["tracks must be a non-empty list"]

    track_map: dict[str, dict[str, Any]] = {}
    for i, track in enumerate(tracks):
        if not isinstance(track, dict):
            errors.append(f"track[{i}] must be an object")
            continue
        tid = str(track.get("id") or "")
        if not tid:
            errors.append(f"track[{i}] requires id")
            continue
        if tid in track_map:
            errors.append(f"duplicate track id: {tid}")
        track_map[tid] = track
        role = str(track.get("role") or "other")
        if role not in ROLES:
            errors.append(f"track {tid} invalid role: {role}")
        start = _float(track.get("start", 0), f"track {tid}.start", errors, 0)
        duration = _float(track.get("duration"), f"track {tid}.duration", errors)
        volume = _float(track.get("volume", 1), f"track {tid}.volume", errors, 1)
        if start is not None and start < 0:
            errors.append(f"track {tid}.start must be >= 0")
        if duration is not None and duration <= 0:
            errors.append(f"track {tid}.duration must be > 0")
        if volume is not None and not 0 <= volume <= 2:
            errors.append(f"track {tid}.volume must be 0..2")
        node_ids = validate_chain(track.get("fx_chain"), f"track {tid}", errors)
        validate_automation(track.get("automation"), f"track {tid}", node_ids, track.get("fx_chain"), errors)

    groups = plan.get("groups", [])
    if not isinstance(groups, list):
        return errors + ["groups must be a list"]
    group_map: dict[str, dict[str, Any]] = {}
    for i, group in enumerate(groups):
        if not isinstance(group, dict):
            errors.append(f"group[{i}] must be an object")
            continue
        gid = str(group.get("id") or "")
        if not gid or gid in group_map or gid in track_map:
            errors.append(f"group[{i}] requires unique id not shared with a track")
            continue
        group_map[gid] = group
        members = group.get("members")
        if not isinstance(members, list) or not members:
            errors.append(f"group {gid} requires members[]")
        else:
            for member in members:
                if str(member) not in track_map:
                    errors.append(f"group {gid} unknown member: {member}")
        volume = _float(group.get("volume", 1), f"group {gid}.volume", errors, 1)
        if volume is not None and not 0 <= volume <= 2:
            errors.append(f"group {gid}.volume must be 0..2")
        node_ids = validate_chain(group.get("fx_chain"), f"group {gid}", errors)
        validate_automation(group.get("automation"), f"group {gid}", node_ids, group.get("fx_chain"), errors)

    for i, relation in enumerate(plan.get("ducking", [])):
        if not isinstance(relation, dict):
            errors.append(f"ducking[{i}] must be an object")
            continue
        target = str(relation.get("target") or "")
        if target not in track_map:
            errors.append(f"ducking[{i}] target must be a track id")
            continue
        sources = relation.get("sources")
        if not isinstance(sources, list) or not sources:
            errors.append(f"ducking[{i}] requires sources[]")
            continue
        resolved: list[str] = []
        for source in sources:
            sid = str(source)
            if sid in group_map:
                resolved.extend(str(x) for x in group_map[sid].get("members", []))
            elif sid in track_map:
                resolved.append(sid)
            else:
                errors.append(f"ducking[{i}] unknown source: {sid}")
        if target in resolved:
            errors.append(f"ducking[{i}] target cannot duck against itself")
        for sid in resolved:
            if sid in track_map and str(track_map[sid].get("role") or "other") != "voice":
                errors.append(f"ducking[{i}] source {sid} must have role=voice")
        depth = _float(relation.get("depth", 0.45), f"ducking[{i}].depth", errors, 0.45)
        attack = _float(relation.get("attack", 0.12), f"ducking[{i}].attack", errors, 0.12)
        release = _float(relation.get("release", 0.35), f"ducking[{i}].release", errors, 0.35)
        if depth is not None and not 0 <= depth <= 0.95:
            errors.append(f"ducking[{i}].depth must be 0..0.95")
        if attack is not None and attack < 0:
            errors.append(f"ducking[{i}].attack must be >= 0")
        if release is not None and release < 0:
            errors.append(f"ducking[{i}].release must be >= 0")
    return errors


def _merge_intervals(intervals: list[tuple[float, float]], gap: float = 0.05) -> list[tuple[float, float]]:
    if not intervals:
        return []
    intervals = sorted(intervals)
    merged = [list(intervals[0])]
    for start, end in intervals[1:]:
        if start <= merged[-1][1] + gap:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(float(a), float(b)) for a, b in merged]


def compile_ducking(plan: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(plan)
    tracks = {str(x["id"]): x for x in result.get("tracks", [])}
    groups = {str(x["id"]): x for x in result.get("groups", [])}
    compiled = []

    def source_track_ids(sources: list[Any]) -> list[str]:
        ids: list[str] = []
        for source in sources:
            sid = str(source)
            if sid in groups:
                ids.extend(str(x) for x in groups[sid].get("members", []))
            elif sid in tracks:
                ids.append(sid)
        return list(dict.fromkeys(ids))

    for relation in result.get("ducking", []):
        target = tracks[str(relation["target"])]
        target_start = float(target.get("start", 0))
        target_duration = float(target["duration"])
        target_end = target_start + target_duration
        depth = float(relation.get("depth", 0.45))
        attack = float(relation.get("attack", 0.12))
        release = float(relation.get("release", 0.35))
        intervals = []
        for sid in source_track_ids(relation["sources"]):
            source = tracks[sid]
            start = max(target_start, float(source.get("start", 0)))
            end = min(target_end, float(source.get("start", 0)) + float(source["duration"]))
            if end > start:
                intervals.append((start, end))
        intervals = _merge_intervals(intervals)
        points = [{"t": 0.0, "v": 1.0}]
        duck_level = round(max(0.05, 1.0 - depth), 4)
        for start, end in intervals:
            local_start = start - target_start
            local_end = end - target_start
            points.extend([
                {"t": round(max(0.0, local_start - attack), 4), "v": 1.0},
                {"t": round(local_start, 4), "v": duck_level},
                {"t": round(local_end, 4), "v": duck_level},
                {"t": round(min(target_duration, local_end + release), 4), "v": 1.0},
            ])
        by_time: dict[float, float] = {}
        for point in points:
            t = float(point["t"])
            v = float(point["v"])
            by_time[t] = min(v, by_time.get(t, v))
        lane = {"target": "volume", "points": [{"t": t, "v": by_time[t]} for t in sorted(by_time)]}
        automation = target.setdefault("automation", {"version": 1, "lanes": []})
        automation.setdefault("version", 1)
        lanes = automation.setdefault("lanes", [])
        lanes[:] = [x for x in lanes if x.get("target") != "volume" or not x.get("generated_by") == "aivideoedit_ducking"]
        lane["generated_by"] = "aivideoedit_ducking"
        lanes.append(lane)
        compiled.append({"target": target["id"], "sources": relation["sources"], "intervals": intervals})

    result["ducking_compiled"] = {
        "relations": compiled,
        "rule": "Volume automation is deterministic from declared clip timing; no spectral carve is inferred without measured voice analysis.",
    }
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate/compile AIVideoEdit audio mix plan")
    ap.add_argument("mix", type=Path)
    ap.add_argument("-o", "--output", type=Path)
    ap.add_argument("--check-only", action="store_true")
    args = ap.parse_args()
    plan = load_json(args.mix)
    errors = validate(plan)
    if errors:
        raise SystemExit("audio mix validation failed: " + "; ".join(errors))
    if args.check_only:
        print(json.dumps({"schema": SCHEMA, "valid": True, "mix": str(args.mix)}, indent=2))
        return 0
    result = compile_ducking(plan)
    errors = validate(result)
    if errors:
        raise SystemExit("compiled audio mix validation failed: " + "; ".join(errors))
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
