#!/usr/bin/env python3
"""Create a complete, non-overlapping render matrix from the actual manifest."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def plan_shards(shot_count: int, max_shots: int = 8) -> dict:
    if isinstance(shot_count, bool) or shot_count < 1:
        raise ValueError("shot count must be a positive integer")
    if isinstance(max_shots, bool) or not 1 <= max_shots <= 64:
        raise ValueError("max shots per shard must be between 1 and 64")
    include = []
    for start in range(0, shot_count, max_shots):
        end = min(start + max_shots, shot_count)
        include.append({"shard": len(include), "start": start, "end": end})
    return {"include": include}


def validate_plan(plan: dict, shot_count: int) -> None:
    rows = plan.get("include") if isinstance(plan, dict) else None
    if not isinstance(rows, list) or not rows:
        raise ValueError("shard plan is empty")
    cursor = 0
    seen = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or row.get("shard") != index:
            raise ValueError("shard IDs must be unique and sequential")
        start, end = row.get("start"), row.get("end")
        if start != cursor or not isinstance(end, int) or end <= start:
            raise ValueError("shards must be contiguous and non-empty")
        seen.update(range(start, end))
        cursor = end
    if cursor != shot_count or seen != set(range(shot_count)):
        raise ValueError("shard plan does not cover every shot exactly once")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--max-shots", type=int, default=8)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    shots = manifest.get("shots")
    if not isinstance(shots, list) or not shots:
        raise SystemExit("manifest must contain at least one shot")
    plan = plan_shards(len(shots), args.max_shots)
    validate_plan(plan, len(shots))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    compact = json.dumps(plan, separators=(",", ":"))
    if args.github_output:
        with args.github_output.open("a", encoding="utf-8") as stream:
            stream.write("matrix=" + compact + "\n")
    print(compact)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
