#!/usr/bin/env python3
"""Technical video stream check. Intentionally does not grant creative approval."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

if len(sys.argv) != 3:
    raise SystemExit("usage: inspect_render.py <video.mp4> <report.json>")
video = Path(sys.argv[1])
report_path = Path(sys.argv[2])
if not video.is_file() or video.stat().st_size == 0:
    raise SystemExit(f"missing or empty video: {video}")
probe = subprocess.check_output(
    ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(video)],
    text=True
)
data = json.loads(probe)
streams = data.get("streams", [])
videos = [s for s in streams if s.get("codec_type") == "video"]
audios = [s for s in streams if s.get("codec_type") == "audio"]
duration = float(data.get("format", {}).get("duration") or 0)
technical_pass = bool(videos and audios and duration >= 5)
report = {
    "schema": "mainv2-lab.technical-report.v1",
    "source": "synthetic MainV2 smoke (NOT a production movie)",
    "technical_render_status": "PASS" if technical_pass else "FAIL",
    "creative_status": "UNREVIEWED",
    "human_visual_approval": False,
    "deployment_verified": False,
    "production_complete": False,
    "duration_seconds": duration,
    "width": videos[0].get("width") if videos else None,
    "height": videos[0].get("height") if videos else None,
    "video_codec": videos[0].get("codec_name") if videos else None,
    "audio_codec": audios[0].get("codec_name") if audios else None,
    "file_size_bytes": video.stat().st_size,
    "sha256": hashlib.file_digest(video.open("rb"), "sha256").hexdigest(),
}
report_path.parent.mkdir(parents=True, exist_ok=True)
report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))
if not technical_pass:
    raise SystemExit(1)
