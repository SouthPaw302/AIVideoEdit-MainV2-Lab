#!/usr/bin/env python3
"""MainV2 lab FX runner: ten anchored stills -> derived PNGs + 24fps MP4 + GIF loops.

All effects execute via the lab's exact inherited canonical FXExecutor.
No semantic truck/body motion is manufactured from a single still.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
import cv2
import numpy as np
from PIL import Image,ImageOps,ImageDraw
from general.reusable.fx_v2.executor import FXExecutor
from general.reusable.fx_v2.runtime import FXContext

ROOT=Path(__file__).resolve().parents[2]
def sha_file(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()
def render_shot(shot, cfg, out, fps, seconds, width, height):
    sid=shot["shot_id"]
    source=ROOT/shot["source"]
    assert source.is_file(), f"MISSING CANONICAL SOURCE IMAGE: {source}"
    actual=sha_file(source)
    assert actual == shot["source_sha256"], f"SHA MISMATCH {sid}: {actual}"
    base=cv2.imread(str(source),cv2.IMREAD_COLOR)
    assert base is not None and base.shape[1]>500 and base.shape[0]>300
    base=cv2.resize(base,(width,height),interpolation=cv2.INTER_AREA)
    n=round(fps*seconds)
    assert n>=24
    sub=out/sid
    src=sub/"derived_png"
    src.mkdir(parents=True,exist_ok=True)
    ledger=sub/"execution_ledger.json"
    executor=FXExecutor(seed=302,ledger_path=str(ledger),consumer=f"camion-{sid}-FX-batch-01")
    approved=executor.registry["effects"]
    for fx in shot["fx"]:
        assert fx["id"] in approved and approved[fx["id"]]["gate_status"]=="approved", f"FX NOT APPROVED {sid} {fx['id']}"
    raw=[]
    for i in range(n):
        ctx=FXContext(t=i/fps,duration=seconds,frame_index=i,fps=fps,energy=.3,transient=.05)
        frame=base.copy()
        for fx in shot["fx"]:
            frame=executor.apply_frame(fx["id"],frame,ctx,params=fx["params"])
        raw.append(frame)
    # Loop closure is an explicitly bounded postprocess; never hide discontinuities.
    tail=min(8,n//4)
    anchor=raw[0]
    for j in range(tail):
        k=n-tail+j
        weight=float(j+1)/float(tail)
        raw[k]=cv2.addWeighted(raw[k],1.0-weight,anchor,weight,0)
    assert np.array_equal(raw[-1],raw[0]), f"seam not closed: {sid}"
    diffs=[float(np.abs(f.astype(np.float32)-base.astype(np.float32)).mean()) for f in raw[1:-tail]]
    temporal=[float(np.abs(raw[i].astype(np.float32)-raw[i-1].astype(np.float32)).mean()) for i in range(1,n-tail)]
    pixel_delta=float(np.mean(diffs))
    temporal_delta=float(np.mean(temporal))
    assert pixel_delta>.012 and temporal_delta>.004, f"INVISIBLE FX: {sid} pixel={pixel_delta} temporal={temporal_delta}"
    # MP4 is primary at 24 fps; GIF is secondary browser-proof representation.
    mp4=sub/f"{sid}_FX_loop_24fps.mp4"
    command=["ffmpeg","-hide_banner","-loglevel","error","-y","-f","rawvideo","-pix_fmt","bgr24","-s",f"{width}x{height}","-r",str(fps),"-i","pipe:0","-an","-c:v","libx264","-preset","fast","-crf","20","-pix_fmt","yuv420p","-movflags","+faststart",str(mp4)]
    proc=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        for frame in raw:
            proc.stdin.write(frame.tobytes())
        proc.stdin.close()
        err=proc.stderr.read()
        ret=proc.wait()
    finally:
        if proc.poll() is None:
            proc.kill();proc.wait()
    assert ret==0 and mp4.stat().st_size>5000, f"mp4 failed {sid}: {err[-300:].decode(errors='replace')}"
    variants=[]
    indices=list(range(0,n,6))
    if n-1 not in indices: indices.append(n-1)
    for i in indices:
        p=src/f"{sid}_F{i:03d}.png"
        assert cv2.imwrite(str(p),raw[i])
        variants.append({"frame":i,"file":str(p.relative_to(out)),"sha256":sha_file(p)})
    gif=sub/f"{sid}_FX_loop.gif"
    gifs=[Image.fromarray(cv2.cvtColor(raw[i],cv2.COLOR_BGR2RGB)) for i in range(0,n,2)]
    gifs[0].save(gif,format="GIF",save_all=True,append_images=gifs[1:],duration=round(2000/fps),loop=0,optimize=False,disposal=2)
    assert gif.stat().st_size>5000
    receipt=json.loads(ledger.read_text(encoding="utf-8"))
    executed={e["subject"] for e in receipt.get("events",[]) if e.get("stage")=="executed" and e.get("component")=="fx"}
    expected={f["id"] for f in shot["fx"]}
    assert expected==executed, f"MISSING ACTUAL FX EXECUTION {sid}: expected={expected}, got={executed}"
    return {"shot_id":sid,"source_sha256":actual,"fx_executed":sorted(executed),"png_variations":variants,"mp4":str(mp4.relative_to(out)),"mp4_sha256":sha_file(mp4),"gif":str(gif.relative_to(out)),"gif_sha256":sha_file(gif),"original_vs_fx_mae":pixel_delta,"temporal_mae":temporal_delta,"seam_mae":float(np.abs(raw[0].astype(np.float32)-raw[-1].astype(np.float32)).mean()),"human_visual_qc":"PENDING","true_video_required":bool(shot.get("requires_true_continuation")),"thumbnail":raw[n//2]}
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--batch",type=int,required=True)
    ap.add_argument("--out",required=True)
    ap.add_argument("--manifest",default="projects/el-camion-y-la-carretera/FX_BATCH_01.json")
    args=ap.parse_args()
    cfg=json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    assert args.batch==cfg["batch"], "manifest batch mismatch"
    assert len(cfg["shots"])==10 and len({s["shot_id"] for s in cfg["shots"]})==10
    out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=True)
    report=[]
    for shot in cfg["shots"]:
        item=render_shot(shot,cfg,out,int(cfg["fps"]),float(cfg["seconds"]),int(cfg["width"]),int(cfg["height"]))
        thumb=item.pop("thumbnail")
        report.append(item)
        print(f"{item['shot_id']}: FX EXECUTED {item['fx_executed']} LOOP GIF+MP4; visual QC PENDING",flush=True)
    # Small complete contact sheet for director inspection.
    thumbs=[]
    for shot in cfg["shots"]:
        p=out/shot["shot_id"]/"derived_png"/f"{shot['shot_id']}_F024.png"
        im=Image.open(p).convert("RGB").resize((320,180))
        thumbs.append(im)
    sheet=Image.new("RGB",(320*5,180*2))
    for i,im in enumerate(thumbs):
        sheet.paste(im,((i%5)*320,(i//5)*180))
        ImageDraw.Draw(sheet).text(((i%5)*320+8,(i//5)*180+8),f"EC-{i+1:02d}",fill="white",stroke_width=1,stroke_fill="black")
    sheet.save(out/"FX_BATCH_01_contact_sheet.jpg",quality=88)
    result={"schema":"aivideoedit.fx-batch-result.v1","batch":args.batch,"source_images":len(cfg["shots"]),"rendered_mp4s":len(report),"rendered_gifs":len(report),"fps":cfg["fps"],"seconds_each":cfg["seconds"],"effects_actual_execution_verified":True,"temporary_artifacts_only":True,"human_visual_qc":"PENDING","next_batch_automatically_authorized":False,"shot_results":report}
    (out/"FX_BATCH_01_QC.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print("FX_BATCH_01_TECHNICAL: PASS | 10 SHOTS | HUMAN VISUAL QC PENDING")
if __name__=="__main__":main()
