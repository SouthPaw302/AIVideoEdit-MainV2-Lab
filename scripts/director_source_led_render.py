#!/usr/bin/env python3
"""Director proof: render real high-resolution original stills with their verified FX loops.

Inputs are private source assets; output is a review-only film. This implementation
is independently testable and fail-closed on source digests and original soundtrack.
Do not call the output a canon release or treat camera travel as genuine articulation.
"""
from __future__ import annotations
import argparse, hashlib, json, math, os, subprocess, sys, zipfile
from pathlib import Path
import cv2
import numpy as np

FPS=24
ROOT=Path(os.environ.get('AIVIDEO_SOURCE_ROOT', '/mnt/data')).resolve()
SOUNDTRACK_SHA='6789e6f3ea52501a0d4a151296a6ef7f8abc8516acd1f6cec959213a028ec0d9'
ARCHIVES=[ROOT/'El_Camion_Batch_01_FX_GIF_MP4_Proofs.zip', ROOT/'El_Camion_Batch_02_FX_GIF_MP4_Proofs.zip',ROOT/'Batch03_FX_Artifact_run-37757150942.zip']
MOTION={3: ROOT/'EC-03_Gemini_True_Motion_10s.mp4',4:ROOT/'EC-04_Gemini_Wiper_True_Motion_10s.mp4'}

# Scene-specific, approved FX references; true motion only where existing video footage proves it.
ROAD={1,3,4,6,9,10,12,14,16,18,19,21,23,25,27,29,30}
INTERIOR={2,4,5,8,9,11,13,15,17,20,22,24,28}
SLOW={5,8,11,13,15,17,22,24}
WIDE={1,6,7,10,12,14,16,18,19,21,23,26,27,29,30}

def digest(path:Path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()

def read_source_index():
 f=ROOT/'director_original_sources_index.json'; entries=json.loads(f.read_text()); lookup={e['id']:e for e in entries}
 if len(lookup)!=30:raise RuntimeError('need all 30 original stills')
 for e in entries:
  p=ROOT/e['name']
  if not p.exists() or digest(p)!=e['sha256']: raise RuntimeError('missing or altered source '+e['id'])
 return lookup

def load_shots():
 lists=[]
 for p in sorted((ROOT/'candidate03').glob('shard*/manifest.json')):
  obj=json.loads(p.read_text()); lists.append(obj)
 if len(lists)!=4:raise RuntimeError('four pinned Candidate03 shot manifests are required')
 m=sorted(lists,key=lambda x:x['shard']['start_index'])
 shots=sum((o['shots'] for o in m),[])
 if len(shots)!=32:raise RuntimeError('unexpected number of shots')
 return shots

def render_fx_proof_cache(shot_sources):
 fx={}
 for i,arc in enumerate(ARCHIVES):
  if not arc.exists():raise RuntimeError('missing FX archive '+str(arc))
  with zipfile.ZipFile(arc) as z:
   for n in range(i*10+1,i*10+11):
    id=f'EC-{n:02}';name=f'{id}/{id}_FX_loop_24fps.mp4'
    dest=ROOT/'candidate04_source_led'/'fxrefs'/f'{id}.mp4'
    dest.parent.mkdir(parents=True,exist_ok=True)
    if not dest.exists():dest.write_bytes(z.read(name))
    expected=shot_sources[id]['source']['sha256']
    if digest(dest)!=expected:
     raise RuntimeError('archived FX identity mismatch '+id)
    cap=cv2.VideoCapture(str(dest));frames=[]
    while True:
     ok,fr=cap.read()
     if not ok:break
     frames.append(fr)
    cap.release()
    if len(frames)!=48 or frames[0].shape[:2]!=(360,640):raise RuntimeError('noncanonical FX loop '+id)
    fx[n]=frames
 return fx

def source_position(scene_i,p):
 # Move camera, not subject pixels. Do not invent articulation or change geometry.
 a=.012 if scene_i in SLOW else .055
 if scene_i in WIDE:a=.065
 amp=.035 if scene_i in SLOW else .07
 ease=p*p*(3-2*p)
 # nonlinear variation by shot to avoid repeated camera pattern, deterministic
 inverse=(scene_i%3==0)
 zstart=1.014+scene_i%3*.005
 zend=zstart+(a*(-1 if inverse else 1))
 if zend<1:zend=1.005
 z=zstart+(zend-zstart)*ease
 dx=(scene_i%4-1.5)*amp*ease
 dy=(.5-scene_i%3/2)*amp*.30*ease
 return z,dx,dy

def warp_frame(source,w,h,scene_i,p):
 # Source pixels, resized once to chosen delivery size; tiny global camera travel.
 z,dx,dy=source_position(scene_i,p)
 center=(w*.5,h*.5)
 matrix=cv2.getRotationMatrix2D(center,0,z)
 matrix[0,2]+=dx*w/2;matrix[1,2]+=dy*h/2
 return cv2.warpAffine(source,matrix,(w,h),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT_101)

def fx_reference_overlay(frame,ref_orig,refs,n,t,w,h):
 # Recover the time-dependent *effect delta* of the archived 640x360 proof, not
 # its softened scene content. Original 1672x941 still remains the image base.
 source_small=ref_orig
 idx=int((t*.43+0.13*math.sin(t*.16)) *24)%48
 ref=refs[idx]
 delta=cv2.subtract(ref,source_small,dtype=cv2.CV_16S)
 # clip possible compression outliers and remap FX delta, bounded pixel deltas
 delta=np.clip(delta,-16,16).astype(np.int16)
 if n in (3,4):return frame
 gain=.58 if n in ROAD else .70
 if n in SLOW:gain=.46
 # Result stays full-resolution, never copies low-res original pixels.
 if frame.shape[1]!=640:
  delta=cv2.resize(delta.astype(np.float32),(w,h),interpolation=cv2.INTER_LINEAR)
 else:delta=delta.astype(np.float32)
 out=np.clip(frame.astype(np.float32)+delta*gain,0,255).astype(np.uint8)
 return out

def first_frame_cap(path):
 cap=cv2.VideoCapture(str(path));ok,first=cap.read()
 if not ok:raise RuntimeError('cannot decode '+str(path))
 cap.release();return first

def title_frames():
 clip=ROOT/'candidate03'/'real_music_film.mp4'
 cap=cv2.VideoCapture(str(clip));ok,first=cap.read();cap.set(cv2.CAP_PROP_POS_FRAMES,6740);ok2,last=cap.read();cap.release()
 if not ok or not ok2:raise RuntimeError('missing title/endcard from preserved Candidate03')
 return first,last

def video_frames(path):
 cap=cv2.VideoCapture(str(path));fps=cap.get(cv2.CAP_PROP_FPS);n=int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
 if abs(fps-24)>1:raise RuntimeError('Gemini source FPS differs unexpectedly')
 if n<150:raise RuntimeError('short Gemini source')
 return cap,n

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--width',type=int,default=1280);ap.add_argument('--height',type=int,default=720)
 ap.add_argument('--max-seconds',type=float,default=0);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--crf',type=int,default=22)
 a=ap.parse_args(); w,h=a.width,a.height
 if (w,h) not in [(1280,720),(1920,1080),(960,540)]:raise RuntimeError('approved QC resolution only')
 idx=read_source_index();shots=load_shots();fx=render_fx_proof_cache({s["id"]:s for s in shots if s["id"].startswith("EC-")})
 wav=ROOT/'El camión y el Camino (Remastered x2).wav'
 if digest(wav)!=SOUNDTRACK_SHA:raise RuntimeError('original WAV hash changed')
 title,outro=title_frames();shots_manifest=[];total=0
 frame_target=sum(round(s['duration_seconds']*FPS) for s in shots)
 if frame_target!=6788:raise RuntimeError('full-song candidate timing diverged')
 if a.max_seconds:frame_target=min(frame_target,int(round(a.max_seconds*FPS)))
 a.out.parent.mkdir(parents=True,exist_ok=True)
 cmd=['ffmpeg','-hide_banner','-nostdin','-loglevel','error','-y','-f','rawvideo','-pix_fmt','bgr24','-s',f'{w}x{h}','-r',str(FPS),'-i','pipe:0','-i',str(wav),'-map','0:v:0','-map','1:a:0','-t',str(frame_target/FPS),'-c:v','libx264','-preset','veryfast','-crf',str(a.crf),'-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart',str(a.out)]
 proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
 count=0
 prev=None
 try:
  for shot in shots:
   shot_id=shot['id'];frames=round(float(shot['duration_seconds'])*FPS)
   if count>=frame_target:break
   clip=None
   if shot_id.startswith('EC-'):
    n=int(shot_id[-2:]);p=ROOT/idx[shot_id]['name'];orig=cv2.imread(str(p),cv2.IMREAD_COLOR)
    if orig is None or orig.shape[:2]!=(941,1672):raise RuntimeError('missing source identity '+shot_id)
    base=cv2.resize(orig,(w,h),interpolation=cv2.INTER_LINEAR)
    ref_base=cv2.resize(orig,(640,360),interpolation=cv2.INTER_AREA)
    clip=None;clip_len=0
    if n in MOTION:
     clip,clip_len=video_frames(MOTION[n])
   else:
    n=0; base=cv2.resize(title if shot_id=='INTRO-TITLE' else outro,(w,h))
   for k in range(frames):
    if count>=frame_target:break
    progress=k/max(frames-1,1); t=k/FPS
    if n in MOTION:
     if n==3 and k<24:
      rendered=warp_frame(base,w,h,n,progress*.1)
     else:
      clipframe=k-24 if n==3 else k
      if clipframe>=clip_len:clipframe=clip_len-1
      if clipframe<0:clipframe=0
      ok,actual=clip.read()
      if not ok:raise RuntimeError(f'missing true-motion frame {n} {clipframe}')
      rendered=cv2.resize(actual,(w,h),interpolation=cv2.INTER_LINEAR)
      if n==3 and k<33:
       f=(k-24)/9
       sf=warp_frame(base,w,h,n,progress*.1)
       rendered=cv2.addWeighted(sf,1-f,rendered,f,0)
    elif n:
     rendered=warp_frame(base,w,h,n,progress)
     rendered=fx_reference_overlay(rendered,ref_base,fx[n],n,t,w,h)
    else:
     rendered=base
    if prev is not None and n in {5,8,11,13,15,17,21,23,24,27,30} and k<10:
     alpha=(k+1)/10
     rendered=cv2.addWeighted(prev,1-alpha,rendered,alpha,0)
    proc.stdin.write(rendered.tobytes());count+=1
    if k==frames-1:prev=rendered.copy()
   if clip:clip.release()
   shots_manifest.append({'shot_id':shot_id,'frames':min(frames,max(0,frame_target-(count-frames))), 'source_original_sha256':idx[shot_id]['sha256'] if n else 'retained_candidate03_title_or_outro', 'fx_original_archive':str(ARCHIVES[(n-1)//10].name) if n else None,'true_motion': n in MOTION,'source_resolution':[1672,941] if n else None,'render_resolution':[w,h]})
   print(f'{shot_id:>14} | frames completed {count}/{frame_target}',flush=True)
  proc.stdin.close();rc=proc.wait()
  if rc!=0:raise RuntimeError('ffmpeg encode failed: '+proc.stderr.read().decode()[:1200])
 finally:
  if proc.poll() is None:proc.kill()
 metadata={'schema':'aivideoedit.director-source-led-local-proof.v1','status':'TECHNICAL_PROOF_DIRECTOR_VISUAL_REVIEW_REQUIRED','human_visual_approval':False,'candidate':'04-SOURCE-LED-PROOF','source_originals_verified':len(idx),'source_wav_sha256':SOUNDTRACK_SHA,'render_file':str(a.out),'render_sha256':digest(a.out),'render_frames':count,'fps':FPS,'resolution':[w,h],'shots':shots_manifest, 'note':'NOT a canonical runner production, approved release, or proof of real articulation in other shots'}
 a.out.with_suffix('.receipt.json').write_text(json.dumps(metadata,indent=2)+'\n')
 print(json.dumps({k:v for k,v in metadata.items() if k!='shots'},indent=2))

if __name__=='__main__':main()
