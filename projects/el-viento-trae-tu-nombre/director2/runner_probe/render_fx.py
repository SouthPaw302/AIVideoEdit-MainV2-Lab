#!/usr/bin/env python3
"""Isolated one-shot Director2 canonical FX proof. Does NOT assemble or full-FX a film."""
from __future__ import annotations
import argparse,hashlib,json,sys,subprocess
from pathlib import Path
import cv2,numpy as np
from PIL import Image
from general.reusable.fx_v2.executor import FXExecutor
from general.reusable.fx_v2.runtime import FXContext
p=argparse.ArgumentParser()
p.add_argument('--image',required=True);p.add_argument('--controls',required=True);p.add_argument('--out',required=True)
a=p.parse_args(); imfile=Path(a.image); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
expected='a7ab0337eb02184a5d25ecf6ae09ae3d5c09e943426e8f8abcd120d0eebc5560'
actual=hashlib.sha256(imfile.read_bytes()).hexdigest()
if actual!=expected:raise RuntimeError('Input derived-JPEG source hash mismatch: '+actual)
b=cv2.imread(str(imfile))
if b is None or b.shape[:2]!=(941,1672):raise RuntimeError('Source geometry mismatch')
source=cv2.resize(b,(960,540),interpolation=cv2.INTER_AREA)
import shutil
shutil.copy2(imfile,out/'B01-S03_preFX_copy.jpg')
music=json.loads(Path(a.controls).read_text())
vals=music['frame_values_energy_transient']
assert len(vals)==48
executor=FXExecutor(seed=302,ledger_path=str(out/'FX2_EXECUTION_LEDGER.jsonl'),consumer='director2-github-runner-B01-S03')
W,H=960,540
mask=np.zeros((H,W),np.float32);mask[round(.42*H):round(.94*H),:]=1
mask=cv2.GaussianBlur(mask,(0,0),13)[...,None]*.56
cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pixel_format','bgr24','-video_size','960x540','-framerate','24','-i','pipe:0','-an','-c:v','libx264','-preset','veryfast','-crf','22','-pix_fmt','yuv420p',str(out/'B01-S03_canonicalFX2_2s.mp4')]
run=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
thumbs=[]
for j in range(48):
 e,t=vals[j]
 ctx=FXContext(t=j/24,duration=2,frame_index=j,fps=24,energy=e,transient=t)
 altered=executor.apply_frame('FX2-SURFACE-022',source,ctx,params={'strength':.25})
 f=np.clip(source.astype(np.float32)*(1-mask)+altered.astype(np.float32)*mask,0,255).astype(np.uint8)
 run.stdin.write(f.tobytes())
 if j==24:cv2.imwrite(str(out/'B01-S03_fx_variant.png'),f)
 if j%2==0:thumbs.append(Image.fromarray(cv2.cvtColor(cv2.resize(f,(384,216)),cv2.COLOR_BGR2RGB)))
run.stdin.close();err=run.stderr.read();rc=run.wait()
if rc:raise RuntimeError(err.decode(errors='replace'))
thumbs[0].save(out/'B01-S03_2s_loop.gif',save_all=True,append_images=thumbs[1:],duration=83,loop=0)
vc=cv2.VideoCapture(str(out/'B01-S03_canonicalFX2_2s.mp4'));frames=int(vc.get(cv2.CAP_PROP_FRAME_COUNT));vc.release()
if frames!=48:raise RuntimeError('Invalid decoded frame count '+str(frames))
ledger=out/'FX2_EXECUTION_LEDGER.jsonl'
if not ledger.exists():raise RuntimeError('No canonical FX execution ledger')
receipt={'schema':'director2.real-runner-shot-proof.v1','shot':'B01-S03','full_film_fx':False,'film_assembly':False,'source_original_drive_id':'1xOGeTL3P9LnwW6fc3_cGkX6wJYyCml26','source_original_png_sha256':'e8864ecbfb037fa156bf29027ae78f2d98c4a99fe4db62a5e46ace442b2ce49','derived_JPEG_SHA256':actual,'effect_id':'FX2-SURFACE-022','backend':'canonical MainV2 FXExecutor','music_evidence':'original-WAV PCM measured RMS/flux','fps':24,'frames':frames,'dimensions':[W,H],'director_creative_approval':False,'files':{x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in out.iterdir() if x.is_file()}}
(out/'B01-S03_RUNNER_QC.json').write_text(json.dumps(receipt,indent=2))
print('Director2 per-shot real runner proof: PASS',receipt['effect_id'],'48 frames; FULL FX NOT RUN')
