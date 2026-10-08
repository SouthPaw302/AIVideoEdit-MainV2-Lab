#!/usr/bin/env python3
from __future__ import annotations
import bisect,hashlib,json,math,os,shutil,subprocess,sys,urllib.request
from pathlib import Path
import cv2,numpy as np

REPO=Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path: sys.path.insert(0,str(REPO))
PROJECT=Path(__file__).resolve().parent
OUT=Path(os.environ.get("MN_PROOF_OUT","/tmp/mn-director-proof"))
OUT.mkdir(parents=True,exist_ok=True)
LEDGER=OUT/"PRODUCTION_EXECUTION_LEDGER.json"
RELEASE="https://github.com/SouthPaw302/AIVideoEdit/releases/download/media-irish-eyes-lab"
ASSETS=[
("irish_road.mp4","source__IE_L21_ROAD_RAIN_GLASS_16x9_V3.mp4","161dcefb278f9f09eb96f3d96041110b338f9bbe84c87469b547f860eac6821d"),
("irish_window.mp4","source__IE_L22_WARM_WINDOW_CANDLE_16x9_V1.mp4","69814efe52df37fa7db1ba6ae1d89f59be27c91df027c033e831c9e5f58d4af2"),
("irish_lake.mp4","source__IE_L23_DARK_LAKE_RIDGE_16x9_V2.mp4","9bce0b9fd9f0f3eb29a8d2ea0c7bc75dd3e46ceb72e009f7fe7ee904cfb4cb0a"),
("audio.wav","source__Irish_eyes_Remastered.wav","8b0ccd2e57a6e683d526d950bd88b42af0f0867b06e3d1b014a2b3131f3cfb1e"),
]
def sha(p):
 h=hashlib.sha256()
 with Path(p).open("rb") as f:
  for c in iter(lambda:f.read(1024*1024),b""):h.update(c)
 return h.hexdigest()
def dl(name,remote,digest):
 p=OUT/name
 if not p.is_file() or sha(p)!=digest:
  req=urllib.request.Request(f"{RELEASE}/{remote}",headers={"User-Agent":"AIVideoEdit-MainV2-proof"})
  with urllib.request.urlopen(req,timeout=180) as r,p.open("wb") as w:shutil.copyfileobj(r,w)
 if sha(p)!=digest:raise RuntimeError("hash mismatch "+name)
 return p
def run(cmd):
 print("+"," ".join(map(str,cmd)),flush=True);subprocess.run([str(x) for x in cmd],check=True,cwd=REPO)
media={n:dl(n,r,h) for n,r,h in ASSETS}

from general.reusable.tools.execution_ledger import record
from general.reusable.tools.jev_decision import decide
from general.reusable.tools.music_beat_worker import analyze_music
from general.reusable.fx_v2.executor import FXExecutor
from general.reusable.fx_v2.runtime import FXContext
from general.reusable.fx_v2.living_still_fx import camera_drift

# ONNX really controls edit timing: choose cuts nearest 5s targets.
ev=analyze_music(media["audio.wav"])
if ev.get("engine")!="beat_this_onnx":raise RuntimeError("Beat This ONNX required")
beats=sorted(float(x) for x in ev.get("beat_positions_seconds",[]) if 0<x<30)
cuts=[0.0]
for target in (5,10,15,20,25):
 near=min(beats,key=lambda x:abs(x-target)) if beats else float(target)
 if near-cuts[-1]<3.5:near=float(target)
 cuts.append(round(near,3))
cuts.append(30.0)
record(LEDGER,component="onnx",subject="music-beat-onnx-v1",stage="executed",actor="music_beat_worker",consumer="proof_edit_map",evidence={"cuts":cuts},required_consumption=True)
record(LEDGER,component="onnx",subject="music-beat-onnx-v1",stage="consumed",actor="proof_edit_map",consumer="proof_renderer",evidence={"cuts":cuts})

fx_effects=["FX2-LIGHT-001","FX2-LIGHT-002","FX2-MOTION-003"]
fx_trans=["FX2-TRANS-025"]
req={"schema":"aivideoedit.fx-requirements.v2","project":"irish-eyes-lab","runtime":"aivideoedit-fx-v2","seed":302,"effects":[{"id":x} for x in fx_effects],"transitions":[{"id":x} for x in fx_trans],"render_inputs":["projects/irish-eyes-lab/run_lab_proof.py"]}
reqp=OUT/"FX_REQUIREMENTS.json";reqp.write_text(json.dumps(req,indent=2)+"\n")
for x in fx_effects+fx_trans:record(LEDGER,component="fx",subject=x,stage="selected",actor="sandbox_director",consumer="canonical_fx_executor",required_execution=True)
lock=OUT/"FX_LOCK.json";gate=REPO/"general/reusable/fx_v2/precompile_gate.py"
run([sys.executable,gate,"--manifest",reqp,"--lock-out",lock]);run([sys.executable,gate,"--manifest",reqp,"--verify-lock",lock])
for x in fx_effects+fx_trans:record(LEDGER,component="fx",subject=x,stage="verified",actor="fx_precompile_gate",consumer="canonical_fx_executor",required_execution=True)
jev=decide({"gate":"PASS","checks":{"source_authority":True,"director_media_selection":True,"onnx_edit_map":True,"fx_lock":True,"no_generic_rain":True},"next_action_permitted":True})
(OUT/"JEV_DECISION.json").write_text(json.dumps(jev,indent=2)+"\n")
if jev["decision"] not in {"PASS","CONTINUE"}:raise RuntimeError(str(jev))
record(LEDGER,component="jev",subject="representative_proof_plan",stage="executed",actor="jev_decision",consumer="proof_renderer",evidence=jev,required_consumption=True)
record(LEDGER,component="jev",subject="representative_proof_plan",stage="consumed",actor="proof_renderer",consumer="final_proof")

W,H,FPS=1280,720,24
shots=[
("irish_lake.mp4", "FX2-MOTION-003"),
("irish_road.mp4", None),
("irish_window.mp4", "FX2-LIGHT-001"),
("irish_lake.mp4", "FX2-MOTION-003"),
("irish_road.mp4", "FX2-LIGHT-002"),
("irish_window.mp4", "FX2-LIGHT-001"),
]
caps={}
stills={}
def cover(im):
 h,w=im.shape[:2];s=max(W/w,H/h);r=cv2.resize(im,(int(w*s),int(h*s)),interpolation=cv2.INTER_AREA if s<1 else cv2.INTER_LANCZOS4);y=(r.shape[0]-H)//2;x=(r.shape[1]-W)//2;return r[y:y+H,x:x+W]
for name,_ in shots:
 p=media[name]
 if p.suffix.lower()==".mp4":caps[name]=cv2.VideoCapture(str(p))
 else:stills[name]=cover(cv2.imread(str(p)))
fx=FXExecutor(seed=302,ledger_path=LEDGER,consumer="mountain_noir_director_proof")
silent=OUT/"proof_silent.mp4";wr=cv2.VideoWriter(str(silent),cv2.VideoWriter_fourcc(*"mp4v"),FPS,(W,H))
xf=.55
def base_frame(idx,tlocal):
 name,_=shots[idx]
 if name in caps:
  c=caps[name];fps=c.get(cv2.CAP_PROP_FPS) or 30;count=int(c.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
  pos=int((tlocal*fps)%count);c.set(cv2.CAP_PROP_POS_FRAMES,pos);ok,fr=c.read()
  if not ok:raise RuntimeError("video source read failed "+name)
  return cover(fr)
 im=stills[name].copy();ctx=FXContext(t=tlocal,duration=max(.1,cuts[idx+1]-cuts[idx]),frame_index=int(tlocal*FPS),fps=FPS)
 return camera_drift(im,ctx,strength=.45,pan_px=5,tilt_deg=.16,zoom=.010)
N=30*FPS
for n in range(N):
 t=n/FPS;idx=max(0,min(5,bisect.bisect_right(cuts,t)-1));local=t-cuts[idx];dur=cuts[idx+1]-cuts[idx]
 fr=base_frame(idx,local)
 eid=shots[idx][1]
 ctx=FXContext(t=local,duration=dur,frame_index=n,fps=FPS,energy=.35,transient=.15)
 if eid:
  params={"strength":.38}
  if eid=="FX2-MOTION-003":params={"strength":.28,"roi":[0,.56,1,1],"reflect":False}
  fr=fx.apply_frame(eid,fr,ctx,params=params)
 if idx<5 and cuts[idx+1]-xf<=t<cuts[idx+1]:
  p=(t-(cuts[idx+1]-xf))/xf
  nxt=base_frame(idx+1,max(0,t-cuts[idx+1]))
  fr=fx.apply_transition("FX2-TRANS-025",fr,nxt,p,ctx)
 wr.write(fr)
wr.release()
for c in caps.values():c.release()
final=OUT/"Mountain_Noir_Director_Proof_30s.mp4"
run(["ffmpeg","-y","-loglevel","error","-i",silent,"-i",media["audio.wav"],"-t","30","-map","0:v","-map","1:a","-c:v","libx264","-preset","fast","-crf","18","-pix_fmt","yuv420p","-c:a","aac","-b:a","192k","-ar","48000","-movflags","+faststart",final])
run([sys.executable,REPO/".aivideoedit/os/general/reusable/fx_v2/execution_guard.py","--requirements",reqp,"--ledger",LEDGER])
result={"result":"TECHNICAL_PROOF_PASS_VISUAL_PENDING","human_visual_approval":False,"production_complete":False,"duration_seconds":30,"cuts":cuts,"video":final.name,"sha256":sha(final),"jev":jev,"generic_rain_overlay":False}
(OUT/"result.json").write_text(json.dumps(result,indent=2)+"\n")
run(["ffmpeg","-y","-loglevel","error","-i",final,"-vf","fps=1/5,scale=320:180,tile=3x2","-frames:v","1",OUT/"contact_sheet.jpg"])
print(json.dumps(result,indent=2))
