#!/usr/bin/env python3
"""Experimental real multimodal Director observation; never grants artistic approval.

Intended only for the isolated prototype/ai engine branch. A missing model,
projector, source clip, executable, valid inference output, or trace fails closed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def decode_observation(output: str) -> dict:
    """Only accept an actual JSON result from the external model process."""
    decoder = json.JSONDecoder()
    matches = []
    for i, char in enumerate(output):
        if char == "{":
            try:
                value, _ = decoder.raw_decode(output[i:])
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict) and "observation" in value:
                matches.append(value)
    if not matches:
        raise ValueError("model returned no parseable Director observation")
    value = matches[-1]
    if not isinstance(value.get("observation"), str) or not value["observation"].strip():
        raise ValueError("model observation is blank")
    if not isinstance(value.get("possible_defects"), list) or any(
        not isinstance(x, str) for x in value["possible_defects"]
    ):
        raise ValueError("model defects must be a list of strings")
    if value.get("needs_human_review") is not True:
        raise ValueError("model cannot grant human approval or bypass review")
    return {
        "observation": value["observation"].strip()[:4000],
        "possible_defects": [x[:350] for x in value["possible_defects"][:20]],
        "needs_human_review": True,
    }


def sample_frames(clip: Path, directory: Path, count: int = 3) -> list[dict]:
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(clip)],
        text=True, capture_output=True, check=True, timeout=60,
    )
    duration = float(probe.stdout.strip())
    if not 2 <= duration <= 120:
        raise ValueError("expected a bounded 2-120 second source clip")
    directory.mkdir(parents=True, exist_ok=True)
    result = []
    for index in range(count):
        second = duration * (index + 1) / (count + 1)
        path = directory / f"frame-{index + 1:02}.jpg"
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
             "-ss", f"{second:.4f}", "-i", str(clip),
             "-vf", "scale=448:-2", "-frames:v", "1", str(path)],
            capture_output=True, text=True, check=True, timeout=90,
        )
        if not path.is_file() or not path.stat().st_size:
            raise RuntimeError(f"frame extraction failed at {second:.3f}s")
        result.append({"timestamp_seconds": round(second, 4),
                       "sha256": sha256(path), "path": str(path)})
    return result


def invoke(clip: Path, direction: str, model: Path, projector: Path,
           binary: Path, out: Path) -> dict:
    for name, path in (("clip", clip), ("model", model),
                       ("projector", projector), ("runner", binary)):
        if not path.is_file() or path.stat().st_size == 0:
            raise FileNotFoundError(f"required {name} absent: {path}")
    if not direction.strip():
        raise ValueError("Director direction is required")
    out.mkdir(parents=True, exist_ok=True)
    frames = sample_frames(clip, out / "frames")
    instruction = (
        "You are an advisory video-quality observer, not an approving Director. "
        "Inspect these three images in timestamp order as samples from a real clip. "
        "Check scene continuity, identifiable subjects, possible drift, and "
        "visible local motion only where the samples justify it. "
        "Do not infer unseen frames or assert continuous motion from stills. "
        "Current direction: " + direction[:2500] + "\n"
        "Return ONLY one JSON object. The required keys are observation "
        "(string), possible_defects (array of strings), and "
        "needs_human_review (boolean, always true). "
        "Do not output PASS, COMPLETE, or an automatic approval."
    )
    command = [
        str(binary), "-m", str(model), "--mmproj", str(projector),
        "--no-mmproj-offload", "-ngl", "0", "-t", "2",
        "-c", "4096", "-n", "320", "--temp", "0",
        "--image", ",".join(x["path"] for x in frames),
        "-p", instruction,
    ]
    started = time.monotonic()
    try:
        process = subprocess.run(command, text=True, capture_output=True,
                                 timeout=1200, check=False)
        (out / "MODEL_STDOUT.txt").write_text(process.stdout, encoding="utf-8")
        (out / "MODEL_STDERR.txt").write_text(process.stderr, encoding="utf-8")
        if process.returncode:
            raise RuntimeError(f"real model process exited {process.returncode}: "
                               + process.stderr[-1600:])
        observation = decode_observation(process.stdout)
        result = {
            "schema": "aivideoedit.prototype-ai-observation.v1",
            "status": "MODEL_OBSERVATION_REVIEW_REQUIRED",
            "source_sha256": sha256(clip),
            "frames": frames,
            "model_name": "Qwen3-VL-2B-Instruct-Q4_K_M",
            "model_sha256": sha256(model),
            "projector_sha256": sha256(projector),
            "executable_sha256": sha256(binary),
            "inference_exit_code": process.returncode,
            "inference_elapsed_seconds": round(time.monotonic() - started, 3),
            "raw_output_sha256": sha256(out / "MODEL_STDOUT.txt"),
            "director_observation": observation,
            "human_visual_approval": False,
            "production_complete": False,
        }
        (out / "PROTOTYPE_AI_RECEIPT.json").write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8"
        )
        return result
    except Exception as exc:
        failure = {"status": "INFERENCE_FAILED", "error": str(exc),
                   "source_sha256": sha256(clip),
                   "human_visual_approval": False, "production_complete": False}
        (out / "PROTOTYPE_AI_FAILURE.json").write_text(
            json.dumps(failure, indent=2) + "\n", encoding="utf-8"
        )
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    for arg in ("clip", "model", "projector", "binary", "out"):
        parser.add_argument("--" + arg, required=True, type=Path)
    parser.add_argument("--direction", required=True)
    args = parser.parse_args()
    result = invoke(args.clip, args.direction, args.model, args.projector,
                    args.binary, args.out)
    print(json.dumps({"status": result["status"],
                      "receipt": str(args.out / "PROTOTYPE_AI_RECEIPT.json")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
