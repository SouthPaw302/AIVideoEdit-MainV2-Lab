#!/usr/bin/env python3
"""B03 native Lab-main FX A/B gate. Source ZIP is fetched on runner; no media stored in Git.
Only a per-still technical light/material proof. Never character/film acceptance.
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, math, subprocess, sys, time
from pathlib import Path
import cv2
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
PROJ=ROOT/"projects/la-luna-de-florida"
RUNTIME=ROOT/".aivideoedit/os/general/reusable/fx_v2/runtime.py"
FPS,N,W,H=24,60,960,540
# Geometry-aware ROIs source-screen normalized. No actor/face/prop deformation.
WATER={
"B03-S01":[(.35,.46),(.92,.46),(.96,.80),(.52,.83)],
"B03-S03":[(.64,.62),(.99,.62),(.99,.80),(.64,.80)],
"B03-S04":[(.73,.64),(.99,.64),(.99,.86),(.75,.86)],
}
LIGHTS={
"B03-S02":[(.08,.30,.08,.16),(.82,.20,.06,.13)],
"B03-S05":[(.10,.71,.07,.12),(.91,.77,.08,.12)],
"B03-S06":[(.96,.66,.04,.08),(.79,.21,.05,.09)],
"B03-S07":[(.16,.22,.10,.12),(.62,.48,.07,.08)], # road-memory sunlight/valley
"B03-S08":[(.43,.65,.07,.10),(.11,.33,.05,.08)],
"B03-S09":[(.10,.22,.07,.14),(.90,.31,.05,.11)],
}
def digest(p):
 h=hashlib.sha256()
 with Path(p).open("rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
 return h.hexdigest()
def load_runtime():
 if not RUNTIME.is_file():raise RuntimeError("Current main OS not booted")
 spec=importlib.util.spec_from_file_location("la_luna_b03_exact_main_runtime",RUNTIME)
 module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module
 spec.loader.exec_module(module);return module
def material_mask(shape,sid,engine):
 h,w=shape[:2];m=np.zeros((h,w),np.float32)
 if sid in WATER:
  cv2.fillPoly(m,[np.array([(int(x*w),int(y*h)) for x,y in WATER[sid]],np.int32)],1)
  m=cv2.GaussianBlur(m,(0,0),5)
 else:
  for cx,cy,rx,ry in LIGHTS[sid]:
   m=np.maximum(m,engine.ellipse_mask(shape,(cx,cy),(rx,ry),blur=8))
 if np.max(m)<.5 or np.mean(m)<.001:raise RuntimeError(f"{sid} material region missing")
 return np.clip(m,0,1)
def render_one(shot,variant,args,rt):
 sid=shot["shot_id"];source=Path(args.source_dir)/(sid+".png")
 if not source.is_file():raise FileNotFoundError(str(source))
 if digest(source)!=shot["original_sha256"]:raise RuntimeError(f"{sid} source mismatch")
 full=cv2.imread(str(source),cv2.IMREAD_COLOR)
 if full is None or full.shape[:2]!=(941,1672):raise RuntimeError(f"{sid} unexpected source resolution")
 frame=cv2.resize(full,(W,H),interpolation=cv2.INTER_AREA)
 fx=rt.FXRuntime(seed=302)
 mask=material_mask(frame.shape,sid,fx)
 out=Path(args.out);(out/"original").mkdir(parents=True,exist_ok=True)
 (out/"stills").mkdir(exist_ok=True);(out/"loops").mkdir(exist_ok=True)
 origcopy=out/"original"/(sid+"_ORIGINAL_UNCHANGED.png")
 if not origcopy.exists():origcopy.write_bytes(source.read_bytes())
 prefix=sid+"_FX_"+variant
 vid=out/"loops"/(prefix+"_LOOP_2p5s_24fps.mp4")
 still=out/"stills"/(prefix+"_DUPLICATE.jpg")
 proc=subprocess.Popen(["ffmpeg","-hide_banner","-loglevel","error","-y","-f","rawvideo","-pix_fmt","bgr24",
 "-s",f"{W}x{H}","-r",str(FPS),"-i","-","-an","-c:v","libx264","-preset","veryfast",
 "-crf","20","-pix_fmt","yuv420p","-movflags","+faststart",str(vid)],stdin=subprocess.PIPE,stderr=subprocess.PIPE)
 deltas=[];protected=[];material=[];first=None;last=None
 for k in range(N):
  ctx=rt.FXContext(t=k/FPS,duration=N/FPS,frame_index=k,fps=FPS,energy=.2,transient=.01)
  if sid in WATER:
   changed=fx.water_flow(frame,ctx,roi=(.3,.4,1,.9),strength=1.65 if variant=="A" else 2.35,reflect=False)
  else:
   changed=fx.practical_light_breath(frame,ctx,mask=mask,strength=.95 if variant=="A" else 1.25)
  env=math.sin(math.pi*k/(N-1))**2
  outframe=fx.blend(frame,changed,mask*env)
  outframe[mask<.001]=frame[mask<.001]
  if k==0 or k==N-1:outframe=frame.copy()
  if k==N//2:cv2.imwrite(str(still),outframe,[cv2.IMWRITE_JPEG_QUALITY,93])
  pixel=np.abs(outframe.astype(np.int16)-frame.astype(np.int16)).mean(2)
  deltas.append(float(pixel.mean()))
  protected.append(float(pixel[mask<.001].max()))
  material.append(float(pixel[mask>.5].mean()))
  if k==0:first=outframe.copy()
  if k==N-1:last=outframe.copy()
  proc.stdin.write(outframe.tobytes())
 proc.stdin.close();err=proc.stderr.read().decode(errors="replace");assert proc.wait()==0,err[-1300:]
 qc=subprocess.run(["ffmpeg","-v","error","-i",str(vid),"-f","null","-"],capture_output=True,text=True)
 if qc.returncode:raise RuntimeError(f"Decode failed {sid} {variant}: {qc.stderr}")
 seam=float(np.abs(first.astype(np.float32)-last.astype(np.float32)).mean())
 if max(deltas)<.03 or max(material)<.4 or max(protected)>.01 or seam>.01:
  raise RuntimeError(f"{sid}/{variant} effect QC FAIL {max(deltas):.4f}/{max(material):.4f}/{max(protected):.4f}/{seam}")
 return {"shot":sid,"variant":variant,"original_sha256":digest(source),"fx_id":"FX2-MOTION-003" if sid in WATER else "FX2-LIGHT-023",
 "fx_still":str(still.relative_to(out)),"fx_still_sha256":digest(still),"fx_loop":str(vid.relative_to(out)),"fx_loop_sha256":digest(vid),
 "frames":N,"fps":FPS,"width":W,"height":H,"max_global_delta":max(deltas),"max_material_delta":max(material),
 "max_protected_delta":max(protected),"first_last_frame_MAD":seam,"decoded":True,"human_accepted":False}
def main():
 a=argparse.ArgumentParser()
 a.add_argument("--source-dir",required=True);a.add_argument("--out",required=True)
 a.add_argument("--shots",nargs="+",required=True)
 args=a.parse_args()
 doc=json.loads((PROJ/"B03_DIRECTOR_PREFLIGHT.json").read_text())
 d={s["shot_id"]:s for s in doc["shot_intents"]}
 assert doc["original_source_stills_recovered"]==9 and doc["source_original_s10_missing"]
 assert all(s in d and s!="B03-S10" for s in args.shots)
 reg=json.loads((ROOT/".aivideoedit/os/general/reusable/fx_v2/registry.json").read_text())
 for e in ("FX2-MOTION-003","FX2-LIGHT-023"):
  assert reg["effects"][e]["gate_status"]=="approved",e
 rt=load_runtime();start=time.monotonic();generated=[]
 for sid in args.shots:
  for variant in ("A","B"):generated.append(render_one(d[sid],variant,args,rt))
 out=Path(args.out);r={"schema":"aivideoedit.la-luna-b03-native-main-fx-evidence.v1","status":"NATIVE_FX_TECHNICAL_PROOFS_REVIEW_PENDING",
 "batch":"B03","source_media":"external independently SHA checked Drive backup, NEVER checked into Git",
 "runtime_path":str(RUNTIME),"runtime_sha256":digest(RUNTIME),"preflight_sha256":digest(PROJ/"B03_DIRECTOR_PREFLIGHT.json"),
 "rendered_shots":args.shots,"originals_recovered":9,"S10_original_still_exists":False,"S10_source_derived_work_not_in_this_gate":True,
 "variant_count":len(generated),"processing_seconds":round(time.monotonic()-start,2),"generated":generated,
 "character_performance_approved":False,"director_approval":False,"film_release":False}
 (out/"B03_NATIVE_FX_PROOF_RECEIPT.json").write_text(json.dumps(r,indent=2)+"\n")
 print(json.dumps({"stage":r["status"],"outputs":len(generated),"runtime_sha":r["runtime_sha256"]}))
if __name__=="__main__":main()
