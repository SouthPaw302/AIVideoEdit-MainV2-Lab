#!/usr/bin/env python3
"""Manifest-driven CPU renderer for living-painting music videos.

Uses tools/hybrid_painterly_fx.py. A project supplies scene stills plus a JSON scene manifest.
The renderer handles deterministic depth parallax, atmosphere, motivated particles, surface lock,
performance micro-motion, and painterly transitions. Optional audio is muxed by FFmpeg.
"""
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path
import cv2

try:
    from hybrid_painterly_fx import (
        depth_proxy, depth_parallax, advected_atmosphere, motivated_particles,
        firelight_breath, pigment_dissolve, coin_portal, temporal_canvas_lock,
        apply_canvas_lock, mesh_breath, wet_reflection_ripple, heat_haze,
        depth_focus_breath, candle_light_shafts, silver_glint, bow_transient,
    )
except ImportError:
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    from hybrid_painterly_fx import *

DEFAULT_EFFECTS={
    'village':['parallax','micro','reflection','atmosphere','particles','canvas'],
    'threshold':['parallax','micro','reflection','atmosphere','particles','firelight','haze','shafts','canvas'],
    'tavern':['parallax','micro','atmosphere','particles','firelight','haze','shafts','canvas'],
    'coin':['parallax','micro','atmosphere','glint','canvas'],
    'dawn':['parallax','micro','atmosphere','particles','firelight','shafts','canvas'],
}

def read_manifest(path:Path):
    data=json.loads(path.read_text())
    if not data.get('scenes'): raise SystemExit('manifest needs scenes[]')
    return data

def resolve_scene_image(base:Path,scene:dict)->Path:
    p=Path(scene['image'])
    return p if p.is_absolute() else base/p

def prep_scene(path:Path,w:int,h:int,seed:int):
    im=cv2.imread(str(path),cv2.IMREAD_COLOR)
    if im is None: raise SystemExit(f'cannot read {path}')
    im=cv2.resize(im,(w,h),interpolation=cv2.INTER_AREA if im.shape[1]>w else cv2.INTER_LANCZOS4)
    return im,depth_proxy(im),temporal_canvas_lock(im.shape,seed)

def render_frame(im,depth,canvas,scene,local,fi,seed):
    fam=scene.get('family','tavern')
    fx=set(scene.get('effects') or DEFAULT_EFFECTS.get(fam,DEFAULT_EFFECTS['tavern']))
    fr=im
    if 'parallax' in fx: fr=depth_parallax(fr,depth,local,amount=float(scene.get('parallax',5.0)))
    if 'micro' in fx: fr=mesh_breath(fr,local,float(scene.get('micro_strength',0.85)),seed)
    if 'reflection' in fx: fr=wet_reflection_ripple(fr,local,float(scene.get('reflection_strength',0.075)))
    if 'atmosphere' in fx: fr=advected_atmosphere(fr,fam,local,seed+137)
    if 'particles' in fx: fr=motivated_particles(fr,fam,local,seed+181)
    if 'firelight' in fx: fr=firelight_breath(fr,fam,fi,float(scene.get('firelight_strength',0.035)))
    if 'haze' in fx: fr=heat_haze(fr,local,strength=float(scene.get('haze_strength',0.95)))
    if 'shafts' in fx: fr=candle_light_shafts(fr,local,tuple(scene.get('light_origin',[0.80,0.15])),float(scene.get('shaft_strength',0.035)))
    if 'focus' in fx: fr=depth_focus_breath(fr,depth,local,float(scene.get('focus_amount',1.25)))
    if 'glint' in fx: fr=silver_glint(fr,local,tuple(scene.get('glint_center',[0.5,0.55])),float(scene.get('glint_radius',0.14)),float(scene.get('glint_strength',36)))
    if 'bow' in fx: fr=bow_transient(fr,local,tuple(scene.get('bow_roi',[0.0,0.25,0.72,0.86])),float(scene.get('bow_pixels',2.1)))
    if 'canvas' in fx: fr=apply_canvas_lock(fr,canvas,float(scene.get('canvas_amount',0.52)))
    return fr

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--manifest',required=True); ap.add_argument('--output',required=True)
    ap.add_argument('--audio'); ap.add_argument('--fps',type=int); ap.add_argument('--width',type=int); ap.add_argument('--height',type=int); ap.add_argument('--seed',type=int)
    args=ap.parse_args()
    mp=Path(args.manifest); data=read_manifest(mp); base=mp.parent
    fps=args.fps or int(data.get('fps',24)); w=args.width or int(data.get('width',960)); h=args.height or int(data.get('height',540)); seed=args.seed or int(data.get('seed',302))
    scenes=data['scenes']; durations=[float(s.get('duration',2.0)) for s in scenes]
    starts=[]; cur=0.0
    for d in durations: starts.append(cur); cur+=d
    total_seconds=cur; total_frames=int(round(total_seconds*fps))
    prepared=[]
    for i,s in enumerate(scenes):
        image=resolve_scene_image(base,s)
        im,depth,canvas=prep_scene(image,w,h,seed+i*97)
        prepared.append((im,depth,canvas))
    cmd=['ffmpeg','-y','-loglevel','error','-f','rawvideo','-pix_fmt','bgr24','-s',f'{w}x{h}','-r',str(fps),'-i','-']
    audio=args.audio or data.get('audio')
    if audio:
        apath=Path(audio); apath=apath if apath.is_absolute() else base/apath
        cmd+=['-i',str(apath),'-map','0:v:0','-map','1:a:0','-c:a','aac','-b:a','192k','-shortest']
    cmd+=['-c:v','libx264','-preset',data.get('preset','veryfast'),'-crf',str(data.get('crf',18)),'-pix_fmt','yuv420p','-movflags','+faststart',args.output]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    si=0
    for fi in range(total_frames):
        t=fi/fps
        while si+1<len(scenes) and t>=starts[si]+durations[si]: si+=1
        local=(t-starts[si])/max(durations[si],1e-6)
        im,depth,canvas=prepared[si]
        fr=render_frame(im,depth,canvas,scenes[si],local,fi,seed+si*211)
        trans=float(scenes[si].get('transition_fraction',data.get('transition_fraction',0.18)))
        if si+1<len(scenes) and local>1-trans:
            p=(local-(1-trans))/trans
            nim,ndepth,ncanvas=prepared[si+1]
            nxt=render_frame(nim,ndepth,ncanvas,scenes[si+1],0.0,fi,seed+(si+1)*211)
            mode=scenes[si].get('transition','pigment')
            if mode=='coin': fr=coin_portal(fr,nxt,p,tuple(scenes[si].get('portal_center',[0.54,0.56])))
            elif mode=='cut': fr=fr if p<1 else nxt
            else: fr=pigment_dissolve(fr,nxt,p,seed+si*233)
        proc.stdin.write(fr.tobytes())
    proc.stdin.close(); rc=proc.wait()
    if rc: raise SystemExit(rc)
    meta={'renderer':'aivideoedit-living-painting-v1','source_manifest':str(mp),'seconds':total_seconds,'fps':fps,'size':[w,h],'seed':seed,'scene_count':len(scenes)}
    Path(args.output+'.json').write_text(json.dumps(meta,indent=2))

if __name__=='__main__': main()
