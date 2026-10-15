#!/usr/bin/env python3
"""Source-faithful Godot + canonical FX proof compositor. Technical experiments only."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

FPS = 24
SIZE = 560
FRAMES = 144
FX_ID = "FX2-ATM-001"
# The user-provided woman's figure lives left/center. Never modify x < 0.72.
PROTECTED_FRACTION = 0.72

def hash_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def probe(path):
    return json.loads(subprocess.run(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(path)],capture_output=True,text=True,check=True).stdout)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source",required=True)
    ap.add_argument("--overlay",required=True)
    ap.add_argument("--output",required=True)
    ap.add_argument("--repo-root",required=True)
    ap.add_argument("--sha256",required=True)
    ap.add_argument("--label",default="repo-pinned-source")
    args = ap.parse_args()
    source = Path(args.source)
    output = Path(args.output)
    output.mkdir(parents=True,exist_ok=True)
    got_sha = hash_file(source)
    if got_sha != args.sha256:
        raise RuntimeError(f"Source SHA mismatch: {got_sha} != {args.sha256}")
    s = probe(source)
    streams = [x for x in s["streams"] if x["codec_type"]=="video"]
    if len(streams)!=1 or streams[0]["width"] != SIZE or streams[0]["height"]!=SIZE:
        raise RuntimeError("Source must be an exact 560x560 source. No silent scaling/reframing.")
    if streams[0]["avg_frame_rate"]!="24/1":
        raise RuntimeError("Source must be 24 FPS. No silent retiming.")
    audio = [x for x in s["streams"] if x["codec_type"]=="audio"]
    if len(audio) < 1:
        raise RuntimeError("Real source audio required: refusing fabricated soundtrack.")
    sys.path.insert(0,str(Path(args.repo_root).resolve()))
    from general.reusable.fx_v2.executor import FXExecutor
    from general.reusable.fx_v2.runtime import FXContext
    fx = FXExecutor(seed=302,consumer="lab_godot_source_technical")
    frames = sorted(Path(args.overlay).glob("overlay[0-9]*.png"))
    if len(frames)!=FRAMES:
        raise RuntimeError(f"Expected Godot movie writer to produce {FRAMES} overlay frames; found {len(frames)}")
    capture = cv2.VideoCapture(str(source))
    if not capture.isOpened():
        raise RuntimeError("Cannot decode source")
    dx = []
    before = []
    after = []
    roi_px = int(SIZE*PROTECTED_FRACTION)
    effect_counts = []
    for i,layer_path in enumerate(frames):
        ok, original = capture.read()
        if not ok:
            raise RuntimeError(f"Source ended at frame {i}, required {FRAMES}")
        layer = cv2.imread(str(layer_path),cv2.IMREAD_COLOR)
        if layer is None or layer.shape[:2]!=(SIZE,SIZE):
            raise RuntimeError(f"Invalid Godot overlay frame {layer_path}")
        # FXExecutor enforces the actual repo's registry approval status.
        ctx = FXContext(t=i/FPS,duration=FRAMES/FPS,frame_index=i,fps=FPS)
        effected = fx.apply_frame(FX_ID,original,ctx,params={"roi":(.74,.03,.99,.32),"strength":.62})
        # Blend is screen; black means absolutely no change. Explicitly limit
        # overlays to sky and lower-right sea. No broad blur or subject warping.
        screen = 255.0 - (255.0 - effected.astype(np.float32))*(255.0-layer.astype(np.float32))/255.0
        final = effected.copy()
        final[:,roi_px:] = np.clip(screen[:,roi_px:],0,255).astype(np.uint8)
        # Protected source pixels are restored exactly, even if FX changes them.
        final[:,:roi_px] = original[:,:roi_px]
        # Mid-band rightmost zone is also protected: only sky and water are allowed.
        final[int(SIZE*.35):int(SIZE*.72),:] = original[int(SIZE*.35):int(SIZE*.72),:]
        if np.any(final[:,:roi_px] != original[:,:roi_px]):
            raise RuntimeError(f"Protection failure frame {i}")
        delta = np.abs(final.astype(np.int16)-original.astype(np.int16))
        effect_counts.append(int(np.count_nonzero(delta)))
        if i in {0,FRAMES//2,FRAMES-1}:
            cv2.imwrite(str(output / f"before_{i:03}.png"),original)
            cv2.imwrite(str(output / f"after_{i:03}.png"),final)
            before.append(hash_file(output / f"before_{i:03}.png"))
            after.append(hash_file(output / f"after_{i:03}.png"))
        cv2.imwrite(str(output/f"frame_{i:06}.png"),final)
    capture.release()
    if sum(n>0 for n in effect_counts)<FRAMES//2:
        raise RuntimeError("Godot / FX layers not visibly changing enough frames")
    dst = output/"godot_mainv2_test.mp4"
    subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
        "-framerate",str(FPS),"-i",str(output/"frame_%06d.png"),"-i",str(source),
        "-map","0:v:0","-map","1:a:0","-c:v","libx264","-preset","veryfast","-crf","19","-pix_fmt","yuv420p",
        "-c:a","aac","-b:a","192k","-t","6","-movflags","+faststart",str(dst)],check=True)
    v = probe(dst)
    vstream=[x for x in v["streams"] if x["codec_type"]=="video"]
    astream=[x for x in v["streams"] if x["codec_type"]=="audio"]
    if len(vstream)!=1 or len(astream)!=1 or int(vstream[0].get("nb_frames",-1))!=FRAMES:
        raise RuntimeError("Encoded proof missing video frames or actual source audio")
    report={
      "schema":"aive.lab.godot-source-reconstruction.v1",
      "status":"TECHNICAL_SOURCE_PROOF_PASS",
      "source_label":args.label,"source_sha256":got_sha,"source_video":{"width":SIZE,"height":SIZE,"fps":FPS},
      "frames_rendered":FRAMES,"duration_seconds":6,"godot_role":"procedural environment-only screen overlay",
      "aive_role":"canonical FXExecutor via approved FX2-ATM-001",
      "effect_id":FX_ID,"seed":302,
      "protected_region":"x < 0.72, full height, plus y 0.35-0.72 full width",
      "protected_source_pixel_diff_max":0,
      "changed_frame_count":sum(n>0 for n in effect_counts),
      "sample_before_hashes":before,"sample_after_hashes":after,
      "output_video_sha256":hash_file(dst),
      "audio_policy":"original input audio retained and re-encoded; no synthesized music",
      "visual_acceptance":"NOT_GRANTED","canonical_production":False,
      "limitations":["This is a bounded technical proof, not a creative direction approval.","No identity or shape regeneration; decoded MP4 undergoes lossy compression.","No claims of 3D reconstruction or source FX equivalence."]
    }
    (output/"report.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
if __name__=="__main__":
    try: main()
    except Exception as e:
        print(f"GODOT SOURCE TECHNICAL FAIL: {e}",file=sys.stderr)
        sys.exit(2)
