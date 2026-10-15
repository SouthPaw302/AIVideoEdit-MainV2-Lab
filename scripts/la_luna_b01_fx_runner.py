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

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "projects/la-luna-de-florida"
RUNTIME = ROOT / ".aivideoedit/os/general/reusable/fx_v2/runtime.py"
FPS = 24
DURATION = 2.5
FRAMES = 60
W, H = 960, 540
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


# Director repair: material-only masks built from observed B01 originals.
# Original crops (and older completed Actions run) remain untouched.
WATER_POLYGONS = {
    "B01-S01": [(0.46,.77),(.68,.72),(.88,.73),(.87,.99),(.53,.99)],
    "B01-S07": [(0.46,.76),(.66,.72),(.88,.73),(.88,.98),(.51,.98)],
    "B01-S09": [(0.53,.78),(.67,.77),(.95,.78),(.97,.98),(.57,.98)],
    "B01-S10": [(0.07,.71),(.20,.66),(.78,.66),(.88,.73),(.91,.97),(.04,.97)],
}
WATER_PROTECTED_RECTS = {
    "B01-S01": [(0.80,.55,.98,.85)],
    "B01-S07": [(0.79,.55,.99,.88)],
    "B01-S09": [(0.64,.56,.99,.81),(.00,.73,.18,.99)],
    "B01-S10": [(0.18,.61,.27,1.),(.35,.60,.43,1.),(.58,.60,.65,1.),(.78,.57,.85,1.)],
}
# Only practical fixtures/reflections, not bodies or general full-screen illumination.
LIGHT_POINTS = {
    "B01-S02": [(.10,.12,.075,.14),(.41,.09,.06,.12)],
    "B01-S03": [(.028,.12,.046,.12),(.10,.14,.055,.13)],
    "B01-S04": [(.11,.10,.07,.12),(.68,.08,.055,.11)],
    "B01-S05": [(.035,.14,.045,.11),(.12,.12,.05,.10)],
    "B01-S06": [(.31,.77,.075,.12),(.46,.76,.055,.10)],
    "B01-S08": [(.77,.75,.07,.13),(.91,.76,.06,.11)],
}

def material_mask(shape, shot_id, engine):
    h,w=shape[:2]
    if shot_id in WATER_SHOTS:
        mask=np.zeros((h,w),np.float32)
        points=np.array([[(int(x*w),int(y*h)) for x,y in WATER_POLYGONS[shot_id]]],np.int32)
        cv2.fillPoly(mask,points,1.0)
        mask=cv2.GaussianBlur(mask,(0,0),4.0)
        # Reapply exclusions after feather to keep geometry exactly locked.
        for x0,y0,x1,y1 in WATER_PROTECTED_RECTS[shot_id]:
            mask[int(y0*h):int(y1*h),int(x0*w):int(x1*w)]=0
    else:
        mask=np.zeros((h,w),np.float32)
        for cx,cy,rx,ry in LIGHT_POINTS[shot_id]:
            mask=np.maximum(mask,engine.ellipse_mask(shape,(cx,cy),(rx,ry),blur=9))
    if mask.max()<.95 or np.mean(mask)<.002:
        raise ValueError(f"{shot_id} missing visible approved material mask")
    return np.clip(mask,0,1)


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
    material = material_mask(bgr.shape, sid, effects)
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
    material_measures = []
    protected_measures = []
    start_frame = None
    end_frame = None
    roi = WATER_ROI.get(sid) if sid in WATER_SHOTS else LIGHT_ROI[sid][0 if variant == "A" else 1]
    try:
        for i in range(FRAMES):
            t = i / FPS
            ctx = rt.FXContext(t=t, duration=DURATION, frame_index=i, fps=FPS, energy=.18, transient=0)
            if sid in WATER_SHOTS:
                strength = 1.75 if variant == "A" else 2.75
                changed = effects.water_flow(bgr, ctx, roi=(0,.54,1,1), strength=strength, reflect=False)
            else:
                strength = .95 if variant == "A" else 1.40
                changed = effects.practical_light_breath(bgr, ctx, mask=material, strength=strength)
            # Exactly meet original at BOTH loop boundaries; never globally pan/zoom.
            envelope = math.sin(math.pi * i / (FRAMES-1)) ** 2
            picture = effects.blend(bgr, changed, material * envelope * (1.0 if sid in WATER_SHOTS else .92))
            # Avoid float->uint8 roundoff changing a supposedly protected pixel by 1.
            picture[material < .001] = bgr[material < .001]
            if i == 0 or i == FRAMES - 1:
                picture = bgr.copy()
            delta = np.abs(picture.astype(np.int16) - bgr.astype(np.int16))
            per_pixel = np.mean(delta,axis=2)
            measures.append(float(np.mean(delta)))
            material_measures.append(float(np.mean(per_pixel[material>.5])))
            protected_measures.append(float(np.max(per_pixel[material<.001])))
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
    material_max = max(material_measures)
    protected_max = max(protected_measures)
    seam = float(np.mean(np.abs(start_frame.astype(np.int16) - end_frame.astype(np.int16))))
    # A light effect must produce pixel changes, not just a successful shell exit.
    if mean_max < .03 or material_max < .45:
        raise ValueError(f"{sid}/{variant} effect lacks material motion (global {mean_max:.4f}, material {material_max:.4f})")
    if protected_max > .01:
        raise ValueError(f"{sid}/{variant} protected-frame pixels changed: {protected_max:.4f}")
    if seam > .01:
        raise ValueError(f"{sid}/{variant} loop boundary fails (MAD={seam:.3f})")
    return {
        "shot_id": sid, "variant": variant, "kind": "water_flow" if sid in WATER_SHOTS else "practical_light_breath",
        "canonical_fx_id": "FX2-MOTION-003" if sid in WATER_SHOTS else "FX2-LIGHT-023",
        "original_sha256": actual, "region": WATER_POLYGONS[sid] if sid in WATER_SHOTS else LIGHT_POINTS[sid],
        "protected_rectangles": WATER_PROTECTED_RECTS.get(sid, []),
        "max_material_pixel_change": round(material_max,4),
        "max_protected_pixel_change": round(protected_max,4),
        "repair_scope": "bounded water/material lighting; no actor articulation",
        "source_width":1280, "source_height":720,
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
            "schema":"aivideoedit.b01-director-fx-repair-proof.v1",
            "status":"TECHNICAL_FX_REPAIR_PROOFS_REVIEW_REQUIRED",
            "source_branch":"song/la-luna-de-florida",
            "source_preflight_sha256":digest(PROJECT/"B01_DIRECTOR_PREFLIGHT.json"),
            "runtime_sha256":digest(RUNTIME),
            "source_canon_status":"storyboard_locked_stills_not_accepted",
            "render_engine":"exact-current-main FXRuntime water_flow/practical_light_breath; Director source-localized masks",
            "preserves_prior_runner_proofs":True,
            "fx_repair_scope":"bounded localized material motion only",
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
