#!/usr/bin/env python3
"""Apply existing approved MainV2 FX to true Godot-rendered frames, with receipts."""
import argparse, json, hashlib, sys
from pathlib import Path
import cv2
p=argparse.ArgumentParser()
p.add_argument("--repo-root",required=True)
p.add_argument("--source",required=True)
p.add_argument("--out",required=True)
a=p.parse_args()
sys.path.insert(0,str(Path(a.repo_root).resolve()))
from general.reusable.fx_v2.executor import FXExecutor
from general.reusable.fx_v2.runtime import FXContext
source=Path(a.source);out=Path(a.out)
out.mkdir(parents=True,exist_ok=True)
inputs=sorted(source.glob("shot*.png"))
if len(inputs)!=336:raise SystemExit("Missing original Godot Movie Maker frames: "+str(len(inputs)))
fx=FXExecutor(seed=302,consumer="godot_authored_movie_experiment")
changed=0
for i,path in enumerate(inputs):
    frame=cv2.imread(str(path),cv2.IMREAD_COLOR)
    if frame is None or frame.shape[:2]!=(540,960):
        raise SystemExit("Invalid rendered Godot scene frame: "+str(path))
    ctx=FXContext(t=i/24.0,duration=14.0,frame_index=i,fps=24.0,energy=0.5)
    # Actual approved atmosphere effect plus soft practical-light modulation.
    atmosphere=fx.apply_frame("FX2-ATM-001",frame,ctx,params={"strength":0.90,"roi":(.06,.06,.97,.95)})
    altered=fx.apply_frame("FX2-LIGHT-001",atmosphere,ctx,params={"strength":0.70,"roi":(.35,.14,.77,.71)})
    if (altered!=frame).any():changed+=1
    cv2.imwrite(str(out/("frame%06d.png"%i)),altered,[cv2.IMWRITE_PNG_COMPRESSION,2])
    if i in (28,167,300):
        cv2.imwrite(str(out/("before%03d.png"%i)),frame)
        cv2.imwrite(str(out/("after%03d.png"%i)),altered)
if changed<300:raise SystemExit("The canonical FX was not visible enough to validate")
result={"schema":"aive.godot.authored-film.fx.v1","frames":336,
    "changed_frames":changed,"canonical_fx_ids":["FX2-ATM-001","FX2-LIGHT-001"],
    "implementation":"existing FXExecutor and FXRuntime",
    "visual_acceptance":"NOT_GRANTED"}
(out/"fx_report.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps(result))