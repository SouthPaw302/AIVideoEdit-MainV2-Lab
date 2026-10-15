#!/usr/bin/env python3
"""La Luna B01/B02: source-preserving Director moving-scene proof compiler.
Existing approved-main FX A/B loops and hashed originals are the inputs.
This is a technical moving-scene proof, NEVER a performance/film approval.
"""
from __future__ import annotations
import argparse,hashlib,importlib.util,json,math,subprocess,time,sys
from pathlib import Path
import cv2,numpy as np

ROOT=Path(__file__).resolve().parents[1]
PROJ=ROOT/"projects/la-luna-de-florida"
RUNTIME=ROOT/".aivideoedit/os/general/reusable/fx_v2/runtime.py"
_runtime_module=None
def exact_main_runtime():
 global _runtime_module
 if _runtime_module is None:
  if not RUNTIME.is_file():raise RuntimeError("Must first bootstrap current-main FXRuntime")
  spec=importlib.util.spec_from_file_location("la_luna_native_os_runtime",str(RUNTIME))
  mod=importlib.util.module_from_spec(spec)
  sys.modules[spec.name]=mod
  spec.loader.exec_module(mod)
  _runtime_module=mod
 return _runtime_module
FPS=24; N=96; W=960; H=540
CLOTH={
"B01-S02":[(.72,.48,.97,.95)],
"B01-S03":[(.08,.44,.42,.98),(.51,.51,.78,.96)],
"B01-S04":[(.55,.44,.89,.95)],
"B01-S05":[(.08,.44,.42,.98),(.51,.51,.78,.96)],
"B01-S06":[(.52,.42,.85,.97)],
"B01-S08":[(.08,.43,.46,.95),(.55,.54,.81,.91)],
"B02-S04":[(.20,.55,.42,.86)],
"B02-S05":[(.18,.48,.42,.98),(.53,.51,.77,.98)],
"B02-S06":[(.16,.43,.45,.97),(.58,.50,.78,.90)],
"B02-S08":[(.24,.46,.43,.81)],
"B02-S09":[(.18,.41,.49,.98),(.49,.55,.69,.93)],
"B02-S10":[(.25,.43,.53,.97),(.53,.52,.76,.93)]
}
PERFORM={
"B01-S02":"guitar and violin performance plus dance",
"B01-S03":"body gesture/dance development",
"B01-S04":"dancing and violin bowing",
"B01-S05":"live couple dance and guitar",
"B01-S06":"flamenco skirt steps and live accompaniment",
"B01-S08":"dancing couple",
"B02-S03":"guitar plucking and fretting",
"B02-S04":"live laughter and hand gestures",
"B02-S05":"natural relationship gesture",
"B02-S06":"palmas and dance",
"B02-S07":"violin bow and guitar strumming",
"B02-S08":"conversation and laughing gestures",
"B02-S09":"coordinated dance movement",
"B02-S10":"continued live dance/performance"}
MISMATCH={
"B01-S07":"source harbor instead of storyboard first dance",
"B01-S10":"source contains typography and sunrise rather than nighttime story location",
"B02-S01":"source exterior waterfront rather than entrance",
"B02-S02":"source exterior deck rather than interior stepping-in"}
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1048576),b""):h.update(b)
 return h.hexdigest()
def original_and_loops(base,sid):
 prefix=base/sid[:3];orig=list((prefix/"original").glob(sid+"_ORIGINAL_UNCHANGED.*"))
 if len(orig)!=1:raise RuntimeError(f"{sid}: exact original missing")
 a=prefix/"loops"/f"{sid}_FX_A_LOOP_2p5s_24fps.mp4"
 b=prefix/"loops"/f"{sid}_FX_B_LOOP_2p5s_24fps.mp4"
 if not a.is_file() or not b.is_file():raise RuntimeError(f"{sid}: missing A/B motion")
 return orig[0],a,b
def readloop(path):
 cap=cv2.VideoCapture(str(path));f=[]
 while True:
  ok,im=cap.read()
  if not ok:break
  if im.shape[:2]!=(H,W):raise RuntimeError(f"Wrong input loop resolution: {path}")
  f.append(im)
 cap.release()
 if len(f)!=60:raise RuntimeError(f"Expected 60-frame loop, got {len(f)}: {path}")
 return f
def cloth_mask(sid):
 m=np.zeros((H,W),np.float32)
 for x0,y0,x1,y1 in CLOTH.get(sid,[]):
  cx=int((x0+x1)*W/2);cy=int((y0+y1)*H/2)
  rx=int((x1-x0)*W/2);ry=int((y1-y0)*H/2)
  cv2.ellipse(m,(cx,cy),(rx,ry),0,0,360,1,-1)
 return cv2.GaussianBlur(m,(0,0),9) if np.any(m) else None
def camera(im,i,style):
 t=i/(N-1)
 if style==0: z=1.018+.022*t*t*(3-2*t);px=.005*t;py=-.005*t
 elif style==1: z=1.035;px=-.01+.02*t;py=.004*math.sin(math.pi*t)
 elif style==2: z=1.018+.004*math.sin(math.pi*t);px=0;py=0
 else: z=1.025+.025*t;px=-.006*t;py=0
 cw=int(W/z);ch=int(H/z)
 x=max(0,min(W-cw,int((W-cw)/2+W*px)))
 y=max(0,min(H-ch,int((H-ch)/2+H*py)))
 return cv2.resize(im[y:y+ch,x:x+cw],(W,H))
def compile_shot(base,out,record,sid):
 orig,a,b=original_and_loops(base,sid)
 if sha(orig)!=record["source_sha256"]:raise RuntimeError(f"{sid}: pinned source SHA mismatch")
 source=cv2.imread(str(orig))
 if source is None:raise RuntimeError(f"{sid}: source unreadable")
 loopa=readloop(a);loopb=readloop(b)
 matte=cloth_mask(sid)
 module=exact_main_runtime()
 fx=module.FXRuntime(seed=302)
 yy2,xx2=np.ogrid[:H,:W]
 g=np.maximum(np.exp(-.5*(((xx2-W*.08)/(W*.14))**2+((yy2-H*.21)/(H*.22))**2)),
              np.exp(-.5*(((xx2-W*.83)/(W*.16))**2+((yy2-H*.17)/(H*.19))**2))).astype(np.float32)
 dest=out/"movies"/f"{sid}_DIRECTOR_SCENE_PROOF_4s.mp4";dest.parent.mkdir(parents=True,exist_ok=True)
 cmd=["ffmpeg","-hide_banner","-loglevel","error","-y","-f","rawvideo","-pixel_format","bgr24",
      "-video_size",f"{W}x{H}","-framerate","24","-i","-","-an","-c:v","libx264",
      "-preset","veryfast","-crf","20","-pix_fmt","yuv420p","-movflags","+faststart",str(dest)]
 process=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
 mid=None;maxdelta=0.;prev=None
 try:
  for i in range(N):
   t=i/(N-1)
   idx=int(round(59*(.5-.5*math.cos(2*math.pi*t))))
   im=cv2.addWeighted(loopa[idx],.70,loopb[idx],.30,0)
   ctx=module.FXContext(t=i/FPS,duration=N/FPS,frame_index=i,fps=FPS,energy=.3,transient=.04)
   if matte is not None:
    # Approved FX2-MOTION-002, semantic cloth mask. Faces/instruments outside the matte.
    im=fx.localized_living_flow(im,ctx,mask=matte,strength=1.85)
   if sid[:3]=="B02" and int(sid[-2:]) in (3,4,6,7,8,9,10) or sid in ("B01-S02","B01-S04","B01-S06"):
    # Approved FX2-ATM-001: upper-left ambient interior only, no performer shape warp.
    im=fx.advected_smoke(im,ctx,roi=(.0,.0,.22,.29),strength=.28)
   # 2D Gaussian image-space practical light, emphatically NOT 3DGS.
   pulse=.027*math.sin(5*math.pi*t)+.013*math.sin(11*math.pi*t)
   im=np.clip(im.astype(np.float32)*(1+pulse*g[:,:,None]),0,255).astype(np.uint8)
   im=camera(im,i,int(sid[-2:])%4)
   if prev is not None:maxdelta=max(maxdelta,float(np.mean(cv2.absdiff(im,prev))))
   if i==N//2:mid=im.copy()
   prev=im
   process.stdin.write(im.tobytes())
  process.stdin.close();err=process.stderr.read().decode("utf-8","replace")
  if process.wait(timeout=90)!=0:raise RuntimeError(f"ffmpeg failed: {err[-1000:]}")
 finally:
  if process.poll() is None:process.kill();process.wait()
 check=subprocess.run(["ffmpeg","-v","error","-i",str(dest),"-f","null","-"],capture_output=True,text=True,timeout=60)
 if check.returncode:raise RuntimeError(f"{sid} decoder fail: {check.stderr}")
 cnt=subprocess.check_output(["ffprobe","-v","error","-select_streams","v:0",
 "-show_entries","stream=nb_frames","-of","default=nw=1:nk=1",str(dest)],text=True).strip()
 if int(cnt)!=N:raise RuntimeError(f"{sid} frames mismatch: {cnt}")
 still=out/"midframes"/f"{sid}_MIDFRAME.jpg";still.parent.mkdir(parents=True,exist_ok=True)
 cv2.imwrite(str(still),mid,[cv2.IMWRITE_JPEG_QUALITY,90])
 return {"shot_id":sid,"source_sha256":sha(orig),"source_path":str(orig),
 "FX_A_SHA256":sha(a),"FX_B_SHA256":sha(b),"proof":str(dest.relative_to(out)),"proof_sha256":sha(dest),
 "midframe":str(still.relative_to(out)),"midframe_sha256":sha(still),
 "fps":FPS,"frames":N,"duration_s":N/FPS,"resolution":[W,H],
 "motion_methods":["current_main_existing_FXRuntime_light_loops","original_and_duplicate_motion_source",
                   "FX2-MOTION-002_canon_localized_living_flow_with_body_protection" if matte is not None else "no_cloth_deform",
                   "FX2-ATM-001_canon_advected_smoke_or_NOT_APPLICABLE",
                   "2D_Gaussian_light_not_3DGS","bounded_Director_camera"],
 "runtime_sha256":sha(RUNTIME),
 "max_adjacent_frame_mad":round(maxdelta,3),"full_video_decode":True,
 "semantic_status":"PERFORMANCE_MOTION_GAP" if sid in PERFORM else "NO_PERFORMANCE_ACTION_REQUIRED",
 "unproven_action":PERFORM.get(sid),"source_coverage_mismatch":MISMATCH.get(sid),
 "artistic_approval":False,"film_approval":False}
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--input-dir",type=Path,required=True)
 ap.add_argument("--out",type=Path,required=True)
 ap.add_argument("--shots",nargs="+",required=True)
 args=ap.parse_args();args.out.mkdir(parents=True,exist_ok=True)
 if not args.shots or any(not x.startswith(("B01-S","B02-S")) for x in args.shots):raise ValueError("Invalid shot IDs")
 if len(set(args.shots))!=len(args.shots):raise ValueError("Duplicate IDs")
 if any(int(x[-2:]) not in range(1,11) for x in args.shots):raise ValueError("Out of range")
 preflight={}
 for batch in set(x[:3] for x in args.shots):
  src=PROJ/f"{batch}_DIRECTOR_PREFLIGHT.json"
  preflight.update({r["shot_id"]:r for r in json.loads(src.read_text())["shots"]})
 results=[];t=time.monotonic()
 for sid in args.shots:
  results.append(compile_shot(args.input_dir,args.out,preflight[sid],sid))
  print("SHOT_MOVING_PROOF",sid,results[-1]["semantic_status"],results[-1]["proof_sha256"][:12],flush=True)
 audit={"schema":"aivideoedit.la-luna-motion-candidate.v1",
 "status":"MOVING_SCENE_PROOF_ONLY_PENDING_SEMANTIC_AND_DIRECTOR_REVIEW",
 "branch":"song/la-luna-de-florida","source_past_actions_runs":[38675807521,38673490212],
 "preserves_original_stills":True,"preserves_light_FX_runs":True,
 "generated":results,"count":len(results),
 "performance_gaps":sum(x["semantic_status"]=="PERFORMANCE_MOTION_GAP" for x in results),
 "coverage_mismatches":sum(bool(x["source_coverage_mismatch"]) for x in results),
 "elapsed_s":round(time.monotonic()-t,2),"human_release_approval":False,
 "note":"Camera/cloth/motivated light are visible 2.5D motion but not actor or instrument articulation. Production cannot creatively lock shots with uncovered performance or canonical framing mismatch."}
 (args.out/"MOVEMENT_PROOF_RECEIPT.json").write_text(json.dumps(audit,indent=2)+"\n")
 print(json.dumps({"technical_proofs":audit["count"],"performance_gaps":audit["performance_gaps"],
 "coverage_mismatches":audit["coverage_mismatches"]}))
if __name__=="__main__":main()
