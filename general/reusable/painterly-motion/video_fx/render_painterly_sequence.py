#!/usr/bin/env python3
"""Render a deterministic painterly keyframe sequence with reusable CPU effects.

This is a generic sequence renderer. Project-specific timing/family assignments
can be supplied through a JSON config. FFmpeg must be available on PATH.
"""
from __future__ import annotations
import argparse,json,math,subprocess
from pathlib import Path
import cv2
import numpy as np
from painterly_cpu_fx import (
    DEFAULT_FAMILIES, edge_reframe, painterly_upscale, pseudo_depth,
    depth_parallax, localized_micro_warp, advected_atmosphere,
    volumetric_light_shafts, motivated_particles, firelight_breath,
    puddle_shimmer, chroma_pigment_transport, pigment_dissolve, object_portal,
)

def fit_16x9(bgr,w,h,zoom=1.045):
    ih,iw=bgr.shape[:2]; target=w/h; src=iw/ih
    if src>target: ch=ih; cw=int(ch*target)
    else: cw=iw; ch=int(cw/target)
    cw=int(cw/zoom); ch=int(ch/zoom)
    x0=max(0,(iw-cw)//2); y0=max(0,(ih-ch)//2)
    return cv2.resize(bgr[y0:y0+ch,x0:x0+cw],(w,h),interpolation=cv2.INTER_LANCZOS4)

def load_config(path, count):
    if not path:
        return {
            'families':['tavern']*count,
            'edge_reframe':{},
            'portal_after':[],
            'seed':302,
            'transition_fraction':.18,
        }
    cfg=json.loads(Path(path).read_text())
    if len(cfg.get('families',[])) != count:
        raise SystemExit('config families count must equal keyframe count')
    return cfg

def preprocess(paths,w,h,cfg):
    imgs=[]; depths=[]
    edge={int(k):v for k,v in cfg.get('edge_reframe',{}).items()}
    for i,p in enumerate(paths):
        im=cv2.imread(str(p),cv2.IMREAD_COLOR)
        if im is None: raise SystemExit(f'could not read {p}')
        im=edge_reframe(im,float(edge.get(i,0)))
        im=painterly_upscale(im,2.0)
        im=fit_16x9(im,w,h)
        imgs.append(im); depths.append(pseudo_depth(im))
    return imgs,depths

def render_scene(base,depth,family,local,frame,seed,idx):
    st=DEFAULT_FAMILIES[family]
    amount=6.0 if family in ('village','threshold') else 4.2
    fr=depth_parallax(base,depth,local,amount)
    fr=localized_micro_warp(fr,depth,st.warp,local)
    fr=advected_atmosphere(fr,depth,st.fog_bgr,st.smoke,local,seed+idx*97)
    source=(.62,.12) if family=='dawn' else (.72,.18)
    fr=volumetric_light_shafts(fr,depth,st.light_bgr,st.light_shafts,local,seed+idx*131,source)
    fr=motivated_particles(fr,st.rain,st.embers,local,seed+idx*173)
    if family in ('tavern','threshold','dawn'):
        fr=firelight_breath(fr,frame,.04)
    if family=='village': fr=puddle_shimmer(fr,local)
    return fr

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--keyframes',required=True)
    ap.add_argument('--output',required=True)
    ap.add_argument('--config')
    ap.add_argument('--seconds',type=float,default=30)
    ap.add_argument('--fps',type=int,default=24)
    ap.add_argument('--width',type=int,default=960)
    ap.add_argument('--height',type=int,default=540)
    ap.add_argument('--audio')
    args=ap.parse_args()

    paths=sorted(Path(args.keyframes).glob('*'))
    paths=[p for p in paths if p.suffix.lower() in ('.jpg','.jpeg','.png','.webp')]
    if not paths: raise SystemExit('no keyframes')
    cfg=load_config(args.config,len(paths)); seed=int(cfg.get('seed',302))
    imgs,depths=preprocess(paths,args.width,args.height,cfg)
    families=cfg['families']; tf=float(cfg.get('transition_fraction',.18))
    portal_after=set(int(x) for x in cfg.get('portal_after',[]))
    total=int(round(args.seconds*args.fps)); scene_len=total/len(imgs)

    cmd=['ffmpeg','-y','-loglevel','error','-f','rawvideo','-pix_fmt','bgr24','-s',f'{args.width}x{args.height}','-r',str(args.fps),'-i','-']
    if args.audio:
        cmd += ['-i',args.audio,'-map','0:v:0','-map','1:a:0','-c:a','aac','-b:a','192k','-shortest']
    cmd += ['-c:v','libx264','-preset','veryfast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',args.output]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)

    for fi in range(total):
        s=min(len(imgs)-1,int(fi/scene_len)); local=(fi-s*scene_len)/scene_len
        fr=render_scene(imgs[s],depths[s],families[s],local,fi,seed,s)
        if local>1-tf and s+1<len(imgs):
            p=(local-(1-tf))/tf
            nxt=render_scene(imgs[s+1],depths[s+1],families[s+1],0,fi,seed,s+1)
            if s in portal_after:
                fr=object_portal(fr,nxt,p)
            else:
                fr=chroma_pigment_transport(fr,nxt,p*.78)
                fr=pigment_dissolve(fr,nxt,p,seed+s*241)
        proc.stdin.write(fr.tobytes())

    proc.stdin.close(); rc=proc.wait()
    if rc: raise SystemExit(rc)
    Path(args.output+'.json').write_text(json.dumps({
        'renderer':'aivideoedit-painterly-sequence-v1',
        'seconds':args.seconds,'fps':args.fps,'size':[args.width,args.height],
        'seed':seed,'keyframes':[p.name for p in paths],
        'families':families,'portal_after':sorted(portal_after),'audio':args.audio,
    },indent=2))

if __name__=='__main__': main()
