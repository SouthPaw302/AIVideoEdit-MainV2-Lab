#!/usr/bin/env python3
"""Audit pinned low-resolution FX proof loops versus full-resolution production needs.

Does not fabricate motion, authorize final films, read private Drive credentials, or
alter source media. Inspects the 30 public release copies of the existing Drive proofs.
"""
import argparse, hashlib, json, sys
from pathlib import Path
import cv2
import numpy as np

def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()

def inspect(path):
    cap=cv2.VideoCapture(str(path))
    if not cap.isOpened():raise RuntimeError("cannot decode "+str(path))
    fps=float(cap.get(cv2.CAP_PROP_FPS));n=int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH));height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if fps<=0 or n<2:raise RuntimeError("invalid FX loop "+str(path))
    frames=[]
    for i in range(0,n,max(1,round(fps/4))):
        cap.set(cv2.CAP_PROP_POS_FRAMES,i)
        ok,frame=cap.read()
        if not ok:raise RuntimeError("undecodable frame "+str(path)+":"+str(i))
        sm=cv2.cvtColor(cv2.resize(frame,(320,180),interpolation=cv2.INTER_AREA),cv2.COLOR_BGR2GRAY)
        frames.append(sm.astype(np.float32))
    cap.release()
    deltas=[float(np.abs(a-b).mean()) for a,b in zip(frames,frames[1:])]
    return {"width":width,"height":height,"fps":fps,"frames":n,"duration_seconds":round(n/fps,5),
            "mean_quartersecond_luma_change_255":round(float(np.mean(deltas)),4),
            "max_quartersecond_luma_change_255":round(float(np.max(deltas)),4)}

def build(manifest,inventory,media):
    target=manifest.get("output") or {}
    out_w,out_h=int(target["width"]),int(target["height"])
    index={s["id"]:s for s in manifest["shots"]}
    originals=inventory["original_stills"]["count"]
    if originals != 30 or len(index)!=len(manifest["shots"]):raise RuntimeError("inventory/manifest problem")
    rows=[]
    for num in range(1,31):
        shot_id=f"EC-{num:02}"
        if shot_id not in index:raise RuntimeError("missing shot "+shot_id)
        shot=index[shot_id]
        url=shot["source"]["url"]
        expected=f"generated__{shot_id}_FX_loop_24fps.mp4"
        if url.rsplit("/",1)[-1]!=expected:
            raise RuntimeError(shot_id+" not mapped to expected, pinned original FX archive loop")
        path=media/expected
        if not path.is_file():raise RuntimeError("missing pinned release asset "+expected)
        actual=sha(path)
        if actual!=shot["source"]["sha256"]:raise RuntimeError("source SHA mismatch "+shot_id)
        metrics=inspect(path)
        duration=float(shot["duration_seconds"])
        reasons=[]
        if metrics["width"]<out_w or metrics["height"]<out_h:
            reasons.append("LOW_RES_FX_PROOF_NOT_FINAL_SOURCE")
        if duration>metrics["duration_seconds"]+.001:
            reasons.append("SHORT_2S_PROOF_REPEATED_OVER_SHOT")
        if metrics["mean_quartersecond_luma_change_255"]<0.5:
            reasons.append("LOW_MEASURED_INTERNAL_MOTION")
        if shot_id in inventory["qc_flags"]["batch3_true_video_required"]:
            reasons.append("EXPLICIT_TRUE_VIDEO_REQUIRED_BY_BATCH3_QC")
        rows.append({"shot_id":shot_id,"source_sha256":actual,"source_dimensions":[metrics["width"],metrics["height"]],
            "output_dimensions":[out_w,out_h],"source_duration_seconds":metrics["duration_seconds"],
            "render_duration_seconds":duration,"upscale_factor":round(max(out_w/metrics["width"],out_h/metrics["height"]),3),
            "mean_quartersecond_luma_change_255":metrics["mean_quartersecond_luma_change_255"],
            "findings":reasons,"usable_as_fx_reference":True,
            "approved_as_final_high_res_motion":False})
    return {"schema":"mainv2lab.director-fx-source-audit.v1","production":manifest["production_id"],
            "status":"REQUIRES_HIGH_RES_SOURCE_FX_PASS",
            "baseline_human_visual_approval":False,"source_stills":originals,
            "fx_loops_audited":len(rows),"low_res_proof_count":sum(any("LOW_RES" in x for x in r["findings"]) for r in rows),
            "repeated_short_loop_count":sum(any("REPEATED" in x for x in r["findings"]) for r in rows),
            "low_motion_watch_count":sum(any("LOW_MEASURED" in x for x in r["findings"]) for r in rows),
            "true_video_required_batch3":inventory["qc_flags"]["batch3_true_video_required"],
            "next_action":"Stage verified original high-res stills from connected private Drive into runner; execute canonical FX passes on source stills at output resolution; use derived GIF/MP4 loops as motion references and include true video only where approved; compare full result.",
            "shots":rows}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--inventory",type=Path,required=True)
    p.add_argument("--media-dir",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--strict-release",action="store_true")
    a=p.parse_args()
    result=build(json.loads(a.manifest.read_text()),json.loads(a.inventory.read_text()),a.media_dir)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k!="shots"},indent=2))
    if a.strict_release and result["low_res_proof_count"]>0:
        print("DIRECTOR RELEASE GATE: FAIL — short 640x360 FX loops are not high-res masters",file=sys.stderr)
        return 2
    print("FX SOURCE AUDIT: COMPLETE; VISUAL ACCEPTANCE NOT GRANTED")
    return 0

if __name__=="__main__":raise SystemExit(main())
