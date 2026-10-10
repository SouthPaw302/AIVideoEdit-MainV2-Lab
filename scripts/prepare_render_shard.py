#!/usr/bin/env python3
"""Create a contiguous, timeline-correct manifest for one render shard."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--start", type=int, required=True)
    ap.add_argument("--end", type=int, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    source = json.loads(args.manifest.read_text(encoding="utf-8"))
    shots = source.get("shots") if isinstance(source.get("shots"), list) else []
    fps = int((source.get("output") or {}).get("fps", 24))
    if not shots or args.start < 0 or args.end <= args.start or args.end > len(shots):
        raise SystemExit("invalid shard range")

    def duration(index: int) -> float:
        return float(shots[index].get("duration_seconds") or 0)

    start_seconds = sum(duration(i) for i in range(args.start))
    entry_preroll = 0.0
    if args.start and shots[args.start - 1].get("transition_out"):
        entry_preroll = min(
            float(shots[args.start - 1].get("transition_seconds", 0.5)),
            duration(args.start - 1),
        )
    shard_shots = [dict(x) for x in shots[args.start:args.end]]
    shard_duration = sum(float(x.get("duration_seconds") or 0) for x in shard_shots)
    audio = dict(source.get("audio") or {})
    audio["start_seconds"] = round(start_seconds, 6)
    out = dict(source)
    out["audio"] = audio
    out["shots"] = shard_shots
    out["production_id"] = f"{source.get('production_id', 'real-film')}-shard-{args.start:02d}-{args.end:02d}"
    out["shard"] = {
        "start_index": args.start,
        "end_index": args.end,
        "start_seconds": round(start_seconds, 6),
        "duration_seconds": round(shard_duration, 6),
        "start_frame": round(start_seconds * fps),
        "entry_preroll_seconds": round(entry_preroll, 6),
        "frame_count": round(shard_duration * fps),
        "parent_manifest_sha256": sha(args.manifest),
    }
    if args.end < len(shots):
        out["boundary_next_shot"] = dict(shots[args.end])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out["shard"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
