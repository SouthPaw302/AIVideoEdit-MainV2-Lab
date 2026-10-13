#!/usr/bin/env python3
"""Project-local B01 FX evidence generator. Uses current-main FXRuntime; never grants creative approval."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "projects/la-luna-de-florida"
RUNTIME = ROOT / ".aivideoedit/os/general/reusable/fx_v2/runtime.py"
FPS = 24
DURATION = 2.5
FRAMES = 60
W, H = 640, 360
WATER_SHOTS = {"B01-S01", "B01-S07", "B01-S09", "B01-S10"}
WATER_ROI = {
    "B01-S01": (0.0, 0.69, 1.0, 0.98),
    "B01-S07": (0.0, 0.64, 1.0, 1.0),
    "B01-S09": (0.0, 0.76, 1.0, 1.0),
    "B01-S10": (0.0, 0.73, 1.0, 0.99),
}
LIGHT_ROI = {
    "B01-S02": ((0.07, 0.03, 0.42, 0.53), (0.65, 0.06, 0.98, 0.54)),
    "B01-S03": ((0.02, 0.03, 0.28, 0.35), (0.78, 0.04, 0.99, 0.36)),
    "B01-S04": ((0.05, 0.03, 0.25, 0.32), (0.75, 0.03, 0.98, 0.33)),
    "B01-S05": ((0.03, 0.02, 0.25, 0.35), (0.76, 0.02, 0.98, 0.36)),
    "B01-S06": ((0.03, 0.03, 0.32, 0.47), (0.70, 0.04, 0.98, 0.48)),
    "B01-S08": ((0.02, 0.01, 0.24, 0.32), (0.80, 0.02, 0.99, 0.32)),
}


def digest(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_runtime():
    if not RUNTIME.is_file():
        raise RuntimeError("Missing exact current-main runtime. Bootstrap first.")
    spec = importlib.util.spec_from_file_location("aive_b01_fx_runtime", str(RUNTIME))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def render_one(src: Path, shot: dict, variant: str, rt, out: Path) -> dict:
    sid = shot["shot_id"]
    actual = digest(src)
    if actual != shot["source_sha256"]:
        raise ValueError(f"{sid} SOURCE HASH MISMATCH: {actual}")
    original = cv2.imread(str(src), cv2.IMREAD_COLOR)
    if original is None or original.shape[0] != 720 or original.shape[1] != 1280:
        raise ValueError(f"{sid} expected original 1280x720")
    bgr = cv2.resize(original, (W, H), interpolation=cv2.INTER_AREA)
    effects = rt.FXRuntime(seed=302)
    original_out = out / "original"
    original_out.mkdir(parents=True, exist_ok=True)
    source_copy = original_out / f"{sid}_ORIGINAL_UNCHANGED.jpg"
    if not source_copy.is_file():
        source_copy.write_bytes(src.read_bytes())
    prefix = f"{sid}_FX_{variant}"
    still_path = out / "stills" / f"{prefix}_DUPLICATE.jpg"
    video_path = out / "loops" / f"{prefix}_LOOP_2p5s_24fps.mp4"
    still_path.parent.mkdir(parents=True, exist_ok=True)
    video_path.parent.mkdir(parents=True, exist_ok=True)
    command = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo",
               "-pixel_format", "bgr24", "-video_size", f"{W}x{H}",
               "-framerate", str(FPS), "-i", "-", "-an",
               "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
               "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(video_path)]
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    measures = []
    start_frame = None
    end_frame = None
    roi = WATER_ROI.get(sid) if sid in WATER_SHOTS else LIGHT_ROI[sid][0 if variant == "A" else 1]
    try:
        for i in range(FRAMES):
            t = i / FPS
            ctx = rt.FXContext(t=t, duration=DURATION, frame_index=i, fps=FPS, energy=.16, transient=0)
            if sid in WATER_SHOTS:
                strength = .64 if variant == "A" else 1.12
                changed = effects.water_flow(bgr, ctx, roi=roi, strength=strength, reflect=False)
            else:
                strength = .26 if variant == "A" else .36
                changed = effects.practical_light_breath(bgr, ctx, roi=roi, strength=strength)
            # A cyclic transparent handoff to the unmodified source at the loop join.
            # This preserves the source at t=0 and bounds residual difference at t=2.46s.
            envelope = math.sin(math.pi * i / FRAMES) ** 2
            if envelope < 1e-8:
                picture = bgr
            else:
                picture = cv2.addWeighted(changed, envelope, bgr, 1.0 - envelope, 0)
            delta = np.abs(picture.astype(np.int16) - bgr.astype(np.int16))
            measures.append(float(np.mean(delta)))
            if i == FRAMES // 2:
                cv2.imwrite(str(still_path), picture, [cv2.IMWRITE_JPEG_QUALITY, 93])
            if i == 0:
                start_frame = picture.copy()
            if i == FRAMES-1:
                end_frame = picture.copy()
            process.stdin.write(picture.tobytes())
        process.stdin.close()
        stderr = process.stderr.read().decode("utf-8", "replace")
        rc = process.wait(timeout=90)
        if rc:
            raise RuntimeError(f"{sid}/{variant} ffmpeg exit {rc}: {stderr[-1000:]}")
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
    if not video_path.is_file() or video_path.stat().st_size < 1000:
        raise RuntimeError(f"{sid}/{variant} missing encoded video")
    decode = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video_path),
                             "-f", "null", "-"], capture_output=True, text=True, timeout=45)
    if decode.returncode:
        raise RuntimeError(f"{sid}/{variant} MP4 decoding failed: {decode.stderr[-700:]}")
    mean_max = max(measures)
    seam = float(np.mean(np.abs(start_frame.astype(np.int16) - end_frame.astype(np.int16))))
    # A light effect must produce pixel changes, not just a successful shell exit.
    if mean_max < .03:
        raise ValueError(f"{sid}/{variant} effect not measurably visible")
    if seam > 1.5:
        raise ValueError(f"{sid}/{variant} loop boundary fails (MAD={seam:.3f})")
    return {
        "shot_id": sid, "variant": variant, "kind": "water_flow" if sid in WATER_SHOTS else "practical_light_breath",
        "canonical_fx_id": "FX2-MOTION-003" if sid in WATER_SHOTS else "FX2-LIGHT-023",
        "original_sha256": actual, "region": roi, "source_width":1280, "source_height":720,
        "render_width": W, "render_height": H, "fps":FPS, "frames":FRAMES, "duration_seconds":DURATION,
        "original_copy":str(source_copy.relative_to(out)), "original_copy_sha256":digest(source_copy),
        "fx_still":str(still_path.relative_to(out)), "fx_still_sha256":digest(still_path),
        "fx_loop":str(video_path.relative_to(out)), "fx_loop_sha256":digest(video_path),
        "max_mean_absolute_pixel_change":round(mean_max,4),
        "loop_join_raw_frame_mad":round(seam,4),
        "decoded_without_error":True,
        "semantic_limitation":"No articulated subject/instrument motion; ROI-driven environmental/practical-light effect only",
        "director_approval":"PENDING", "human_approval":False,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--shots",nargs="*",default=[])
    args=p.parse_args()
    preflight=json.loads((PROJECT/"B01_DIRECTOR_PREFLIGHT.json").read_text())
    if preflight["director_disposition"]!="PROOF_AUTHORIZED_REVIEW_PENDING":
        raise RuntimeError("No Director pre-FX authorization")
    rt=load_runtime()
    out=args.out.resolve()
    out.mkdir(parents=True,exist_ok=True)
    shots=preflight["shots"]
    if args.shots:
        ids=set(args.shots)
        shots=[s for s in shots if s["shot_id"] in ids]
        if len(shots)!=len(ids):
            raise ValueError("Unknown shot requested")
    results=[]
    start=time.monotonic()
    try:
        for shot in shots:
            src=PROJECT/"media/b01_sources"/(shot["shot_id"]+".jpg")
            if not src.is_file():
                raise FileNotFoundError(f"Missing immutable original input: {src}")
            for variant in ("A","B"):
                results.append(render_one(src,shot,variant,rt,out))
        if len(results)!=2*len(shots):
            raise RuntimeError("FX proof count mismatch")
        receipt={
            "schema":"aivideoedit.b01-fx-runner-proof.v1",
            "status":"TECHNICAL_FX_PROOFS_REVIEW_REQUIRED",
            "source_branch":"song/la-luna-de-florida",
            "source_preflight_sha256":digest(PROJECT/"B01_DIRECTOR_PREFLIGHT.json"),
            "runtime_sha256":digest(RUNTIME),
            "source_canon_status":"storyboard_locked_stills_not_accepted",
            "render_engine":"exact-current-main FXRuntime water_flow/practical_light_breath",
            "shot_count":len(shots),"variant_count":len(results),
            "processing_seconds":round(time.monotonic()-start,2),
            "generated":results,
            "director_full_film_review":False, "human_release_approval":False,
            "complete_film_render":False,
        }
        (out/"B01_FX_RUNNER_RECEIPT.json").write_text(json.dumps(receipt,indent=2)+"\n")
        print(json.dumps({"status":receipt["status"],"shots":len(shots),"loops":len(results),
                          "output_dir":str(out),"runtime":str(RUNTIME)}))
        return 0
    except Exception as exc:
        (out/"B01_FX_RUNNER_FAILURE.json").write_text(json.dumps({"status":"FAIL","error":str(exc),
                                                                   "completed_variants":len(results)},indent=2)+"\n")
        raise


if __name__=="__main__":
    sys.exit(main())
