#!/usr/bin/env python3
"""Fetch exact original media then derive a real measured 14-second music timeline."""
import hashlib, json, subprocess, sys, wave, urllib.request
from pathlib import Path
import numpy as np

FPS=24
FRAMES=336
SECS=FRAMES/FPS
def file_hash(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda:f.read(1048576),b""):h.update(b)
    return h.hexdigest()

project=Path(sys.argv[1])
evidence=Path(sys.argv[2])
evidence.mkdir(parents=True,exist_ok=True)
spec=json.loads((project/"source-lock.json").read_text())
(project/"assets").mkdir(parents=True,exist_ok=True)
(project/"data").mkdir(parents=True,exist_ok=True)
for kind in ["wav"]:
    item=spec[kind]
    dst=project/"assets"/item["file"]
    req=urllib.request.Request(item["url"],headers={"User-Agent":"Godot-AIVideoEdit-Authored-Film/1"})
    with urllib.request.urlopen(req,timeout=90) as response,open(dst,"wb") as fout:
        while True:
            b=response.read(1048576)
            if not b:break
            fout.write(b)
    found=file_hash(dst)
    if found!=item["sha256"]:
        dst.unlink(missing_ok=True)
        raise SystemExit("REFUSING MEDIA: SHA mismatch for "+kind+" "+found)
    print("REAL MEDIA VERIFIED: "+kind+" "+found,flush=True)
# Convert only for PCM analysis; the original verified WAV is never replaced.
normalized=evidence/"analysis_pcm.wav"
subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
    "-i",str(project/"assets/source.wav"),"-c:a","pcm_s16le","-ac","2","-ar","44100",str(normalized)],check=True)
with wave.open(str(normalized),"rb") as w:
    rate=w.getframerate()
    raw=w.readframes(w.getnframes())
    count=w.getnframes()
signal=np.frombuffer(raw,dtype="<i2").reshape(-1,2).astype(np.float32).mean(axis=1)/32768
duration=len(signal)/rate
if duration<SECS+10:raise SystemExit("Real instrumental audio too short for 14-second movie")
# Choose musically energetic and changing passage, within first 100s.
options=[]
for start in range(8,int(min(duration-SECS-2,102)),2):
    chunk=signal[int(start*rate):int((start+SECS)*rate)]
    values=[]
    for f in range(FRAMES):
        block=chunk[int(f*rate/FPS):int((f+1)*rate/FPS)]
        if len(block)==0:raise SystemExit("Empty measured audio frame")
        values.append(float(np.sqrt(np.mean(block*block))))
    rr=np.array(values)
    score=float(np.mean(rr)*.9+np.std(rr)*.7+np.percentile(rr,85)*.4)
    options.append((score,start,values))
if not options:raise SystemExit("No viable music window")
_,start,values=max(options,key=lambda x:x[0])
rms=np.array(values,dtype=np.float32)
lo,hi=np.percentile(rms,[10,94])
norm=np.clip((rms-lo)/max(float(hi-lo),1e-6),0,1)
smoothed=[]
old=0.0
for x in norm:
    a=.40 if x>old else .08
    old=(1-a)*old+a*float(x)
    smoothed.append(round(old,5))
deltas=np.maximum(0,np.diff(rms,prepend=rms[0]))
peak=max(float(np.percentile(deltas,96)),1e-6)
beats=np.round(np.clip(deltas/peak,0,1),5).tolist()
analysis={"schema":"aive.godot.real-pcm-controls.v1","source_sha256":spec["wav"]["sha256"],
    "start_seconds":start,"duration_seconds":SECS,"frames":FRAMES,"fps":FPS,
    "sample_rate":rate,"energy":smoothed,"onset":beats,
    "method":"real frame-aligned WAV RMS + positive change; no invented beat map"}
(project/"data/audio_drive.json").write_text(json.dumps(analysis,indent=2)+"\n")
(evidence/"audio_drive.json").write_text(json.dumps(analysis,indent=2)+"\n")
(evidence/"source-lock.json").write_text(json.dumps(spec,indent=2)+"\n")
subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
    "-ss",str(start),"-i",str(project/"assets/source.wav"),"-t",str(SECS),
    "-af","afade=t=in:st=0:d=0.35,afade=t=out:st=13.4:d=0.6",
    "-c:a","pcm_s16le",str(evidence/"music_clip.wav")],check=True)
print("AUTHORED MUSIC SELECTION: "+str(start)+" to "+str(start+SECS),flush=True)