#!/usr/bin/env python3
"""CPU-only surface preparation for painterly music-video keyframes.

The method preserves scene content while matching a stable living-painting surface:
visible pigment/canvas, luminous highlights, controlled split-toning, and no frame-to-frame
texture regeneration. It is intended as a preprocessing stage before parallax/NeRF/effects.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import cv2
import numpy as np

TONES = {
    "village": {"shadow": (15,7,-3), "mid": (4,2,0), "high": (-5,4,8)},
    "threshold": {"shadow": (10,4,-2), "mid": (0,3,5), "high": (-8,9,18)},
    "tavern": {"shadow": (0,2,2), "mid": (-5,8,18), "high": (-10,12,26)},
    "coin": {"shadow": (10,7,4), "mid": (4,4,4), "high": (8,8,8)},
    "dawn": {"shadow": (8,5,1), "mid": (-1,5,10), "high": (-8,10,24)},
}

def fit_16x9(im:np.ndarray,w:int=1280,h:int=720,zoom:float=1.03,xoff:float=0,yoff:float=0)->np.ndarray:
    ih,iw=im.shape[:2]; target=w/h; src=iw/ih
    if src>target: ch=ih; cw=int(ch*target)
    else: cw=iw; ch=int(cw/target)
    cw=max(8,int(cw/zoom)); ch=max(8,int(ch/zoom))
    cx=int(iw*(0.5+xoff)); cy=int(ih*(0.5+yoff))
    x0=max(0,min(iw-cw,cx-cw//2)); y0=max(0,min(ih-ch,cy-ch//2))
    return cv2.resize(im[y0:y0+ch,x0:x0+cw],(w,h),interpolation=cv2.INTER_LANCZOS4)

def split_tone(im:np.ndarray,family:str)->np.ndarray:
    f=im.astype(np.float32)
    lab=cv2.cvtColor(im,cv2.COLOR_BGR2LAB)
    L=lab[:,:,0].astype(np.float32)/255.0
    sh=np.clip((0.58-L)/0.58,0,1)**1.35
    hi=np.clip((L-0.44)/0.56,0,1)**1.55
    mid=np.clip(1.0-np.abs(L-0.52)/0.52,0,1)**1.6
    t=TONES[family]
    for c in range(3):
        f[:,:,c]+=sh*t['shadow'][c]+mid*t['mid'][c]+hi*t['high'][c]
    return np.clip(f,0,255).astype(np.uint8)

def luminous_pigment(im:np.ndarray,family:str)->np.ndarray:
    sm=cv2.bilateralFilter(im,7,20,20)
    lab=cv2.cvtColor(sm,cv2.COLOR_BGR2LAB)
    clahe=cv2.createCLAHE(clipLimit=1.55,tileGridSize=(10,10))
    lab[:,:,0]=clahe.apply(lab[:,:,0])
    out=cv2.cvtColor(lab,cv2.COLOR_LAB2BGR)
    out=split_tone(out,family)
    gray=cv2.cvtColor(out,cv2.COLOR_BGR2GRAY).astype(np.float32)/255
    m=np.clip((gray-0.62)/0.38,0,1)**1.7
    glow=cv2.GaussianBlur(out,(0,0),4.2).astype(np.float32)
    f=out.astype(np.float32)*(1-(0.10*m)[...,None])+glow*(0.10*m)[...,None]
    return np.clip(f,0,255).astype(np.uint8)

def canvas_and_brush_texture(im:np.ndarray,seed:int,strength:float=1.0)->np.ndarray:
    h,w=im.shape[:2]
    rng=np.random.default_rng(seed)
    yy,xx=np.mgrid[0:h,0:w].astype(np.float32)
    weave=0.55*np.sin(xx/3.1)+0.38*np.sin(yy/4.4)+0.24*np.sin((xx+yy)/7.7)
    coarse=rng.normal(0,1,(max(8,h//24),max(8,w//24))).astype(np.float32)
    coarse=cv2.resize(coarse,(w,h),interpolation=cv2.INTER_CUBIC)
    coarse=cv2.GaussianBlur(coarse,(0,0),2.4)
    fine=rng.normal(0,1,(h,w)).astype(np.float32)
    fine=cv2.GaussianBlur(fine,(0,0),0.65)
    tex=(weave*0.72+coarse*1.75+fine*0.45)*strength
    f=im.astype(np.float32)
    f[:,:,0]+=tex*0.72; f[:,:,1]+=tex*0.88; f[:,:,2]+=tex
    return np.clip(f,0,255).astype(np.uint8)

def finish(im:np.ndarray,family:str,seed:int)->np.ndarray:
    out=luminous_pigment(im,family)
    out=canvas_and_brush_texture(out,seed,0.85 if family=='coin' else 1.0)
    blur=cv2.GaussianBlur(out,(0,0),0.95)
    out=cv2.addWeighted(out,1.065,blur,-0.065,0)
    h,w=out.shape[:2]; y,x=np.mgrid[-1:1:complex(h),-1:1:complex(w)]
    r=np.sqrt((x*0.80)**2+(y*0.72)**2)
    vig=np.clip(1.035-0.095*np.maximum(0,r-0.35),0.90,1.035)
    return np.clip(out.astype(np.float32)*vig[...,None],0,255).astype(np.uint8)

def load_family_map(path:str|None)->dict[str,str]:
    if not path:return {}
    data=json.loads(Path(path).read_text())
    return data.get('families',data)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--input',required=True); ap.add_argument('--output',required=True)
    ap.add_argument('--width',type=int,default=1280); ap.add_argument('--height',type=int,default=720)
    ap.add_argument('--seed',type=int,default=302); ap.add_argument('--default-family',choices=TONES,default='tavern')
    ap.add_argument('--family-map',help='JSON mapping filename or stem to village/threshold/tavern/coin/dawn')
    args=ap.parse_args()
    inp=Path(args.input); outdir=Path(args.output); outdir.mkdir(parents=True,exist_ok=True)
    fmap=load_family_map(args.family_map); records=[]
    for i,p in enumerate(sorted(inp.glob('*'))):
        if p.suffix.lower() not in {'.jpg','.jpeg','.png','.webp'}: continue
        im=cv2.imread(str(p),cv2.IMREAD_COLOR)
        if im is None: continue
        family=fmap.get(p.name,fmap.get(p.stem,args.default_family))
        if family not in TONES: raise SystemExit(f'unknown family {family} for {p.name}')
        im=fit_16x9(im,args.width,args.height)
        im=finish(im,family,args.seed+i*101)
        out=outdir/(p.stem+'_paint.jpg')
        cv2.imwrite(str(out),im,[int(cv2.IMWRITE_JPEG_QUALITY),94])
        records.append({'source':p.name,'output':out.name,'family':family,'seed':args.seed+i*101})
    (outdir/'index.json').write_text(json.dumps({'method':'living-paint-transfer-v1','records':records},indent=2))
    print(f'wrote {len(records)} styled frames to {outdir}')

if __name__=='__main__': main()
