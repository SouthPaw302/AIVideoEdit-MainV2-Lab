#!/usr/bin/env python3
"""Reusable CPU video effects for AIVideoEdit.

Designed for painterly still/image sequences. No GPU or external model required.
Effects are deterministic and preserve a stable painted surface.
"""
from __future__ import annotations
import math
from dataclasses import dataclass
import cv2
import numpy as np

@dataclass(frozen=True)
class FamilyStyle:
    fog_bgr: tuple[int,int,int]
    light_bgr: tuple[int,int,int]
    rain: float = 0.0
    embers: float = 0.0
    smoke: float = 0.0

FAMILY_STYLES = {
    "village": FamilyStyle((118,104,92),(190,196,188),rain=0.75,smoke=0.35),
    "threshold": FamilyStyle((92,92,96),(70,172,245),rain=0.35,embers=0.15,smoke=0.40),
    "tavern": FamilyStyle((55,72,92),(32,132,255),embers=0.70,smoke=0.78),
    "coin": FamilyStyle((118,110,104),(240,235,225),embers=0.10,smoke=0.20),
    "dawn": FamilyStyle((90,110,132),(90,190,255),embers=0.20,smoke=0.28),
}

def clean_storyboard_text(bgr: np.ndarray, scene_index: int) -> np.ndarray:
    """Repair cropped storyboard labels that leaked into recovered keyframes."""
    h,w=bgr.shape[:2]
    widths={0:0.18, 4:0.19, 6:0.18, 9:0.19}
    if scene_index not in widths:
        return bgr
    mask=np.zeros((h,w),np.uint8)
    cv2.rectangle(mask,(0,0),(int(w*widths[scene_index]),int(h*0.18)),255,-1)
    return cv2.inpaint(bgr,mask,5,cv2.INPAINT_TELEA)

def upscale_painterly(bgr: np.ndarray, scale: float=2.0) -> np.ndarray:
    """Lanczos + edge-preserving micro-contrast; avoids plastic over-sharpening."""
    h,w=bgr.shape[:2]
    out=cv2.resize(bgr,(int(w*scale),int(h*scale)),interpolation=cv2.INTER_LANCZOS4)
    smooth=cv2.bilateralFilter(out,5,18,18)
    blur=cv2.GaussianBlur(smooth,(0,0),0.85)
    sharp=cv2.addWeighted(smooth,1.10,blur,-0.10,0)
    return np.clip(sharp,0,255).astype(np.uint8)

def depth_proxy(bgr: np.ndarray) -> np.ndarray:
    """Fast pseudo-depth for stable 2.5D parallax. This is not metric depth."""
    h,w=bgr.shape[:2]
    lab=cv2.cvtColor(bgr,cv2.COLOR_BGR2LAB)
    L=lab[:,:,0].astype(np.float32)/255.0
    local=np.abs(L-cv2.GaussianBlur(L,(0,0),5.0))
    edges=cv2.Canny(bgr,60,140).astype(np.float32)/255.0
    edges=cv2.GaussianBlur(edges,(0,0),3.5)
    y=np.linspace(0,1,h,dtype=np.float32)[:,None]
    perspective=np.repeat(y,w,axis=1)
    d=0.62*perspective+0.23*np.clip(local*4.0,0,1)+0.15*edges
    d=cv2.GaussianBlur(d,(0,0),2.0)
    lo,hi=np.percentile(d,[3,97])
    return np.clip((d-lo)/(hi-lo+1e-6),0,1).astype(np.float32)

def depth_parallax(bgr: np.ndarray, depth: np.ndarray, phase: float, amount: float=8.0) -> np.ndarray:
    """Per-pixel parallax remap driven by pseudo-depth."""
    h,w=bgr.shape[:2]
    yy,xx=np.mgrid[0:h,0:w].astype(np.float32)
    dx=math.sin(phase*math.tau)*amount
    dy=math.sin(phase*math.tau*0.5+0.8)*(amount*0.28)
    z=(depth-0.5)
    mapx=xx-dx*z
    mapy=yy-dy*z
    return cv2.remap(bgr,mapx,mapy,cv2.INTER_CUBIC,borderMode=cv2.BORDER_REFLECT_101)

def _noise_field(h:int,w:int,seed:int,phase:float) -> np.ndarray:
    rng=np.random.default_rng(seed)
    sh=max(8,h//18); sw=max(8,w//18)
    base=rng.random((sh,sw),dtype=np.float32)
    field=cv2.resize(base,(w,h),interpolation=cv2.INTER_CUBIC)
    yy,xx=np.mgrid[0:h,0:w].astype(np.float32)
    mapx=xx+16*math.sin(phase*math.tau)+7*np.sin(yy/70.0+phase*math.tau)
    mapy=yy+10*math.cos(phase*math.tau*0.7)+5*np.sin(xx/95.0-phase*math.tau)
    field=cv2.remap(field,mapx,mapy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_WRAP)
    return cv2.GaussianBlur(field,(0,0),7.0)

def advected_atmosphere(bgr: np.ndarray, family: str, phase: float, seed: int) -> np.ndarray:
    """Stable volumetric-looking fog/smoke from advected low-frequency fields."""
    style=FAMILY_STYLES[family]
    if style.smoke<=0: return bgr
    h,w=bgr.shape[:2]
    field=_noise_field(h,w,seed,phase)
    y=np.linspace(1.0,0.18,h,dtype=np.float32)[:,None]
    alpha=np.clip((field-0.38)*0.22*style.smoke*y,0,0.16)
    tint=np.empty_like(bgr,dtype=np.float32); tint[:]=style.fog_bgr
    out=bgr.astype(np.float32)*(1-alpha[...,None])+tint*alpha[...,None]
    return np.clip(out,0,255).astype(np.uint8)

def motivated_particles(bgr: np.ndarray, family: str, phase: float, seed:int) -> np.ndarray:
    """Rain outside; embers inside. Particles are scene-motivated and deterministic."""
    style=FAMILY_STYLES[family]
    out=bgr.copy(); h,w=out.shape[:2]
    rng=np.random.default_rng(seed)
    n=int(80*style.rain)
    for i in range(n):
        x0=int(rng.uniform(0,w)); y0=float(rng.uniform(-h,h))
        speed=rng.uniform(0.75,1.35)
        y=int((y0+phase*h*1.8*speed)%(h+60)-30)
        x=int((x0+phase*25*speed)%w)
        L=int(rng.uniform(9,20))
        cv2.line(out,(x,y),(x-3,y+L),(170,178,182),1,cv2.LINE_AA)
    n=int(55*style.embers)
    for i in range(n):
        x0=rng.uniform(0,w); y0=rng.uniform(h*0.35,h*1.05)
        drift=math.sin((phase+i*0.17)*math.tau)*8
        x=int((x0+drift)%w); y=int((y0-phase*h*rng.uniform(0.25,0.65))%(h+40))
        r=1 if i%4 else 2
        cv2.circle(out,(x,y),r,(45,145,255),-1,cv2.LINE_AA)
    return out

def firelight_breath(bgr: np.ndarray, family: str, frame_index:int, strength:float=0.06) -> np.ndarray:
    if family not in ("tavern","threshold","dawn"): return bgr
    gain=1.0 + strength*(0.55*math.sin(frame_index*0.17)+0.25*math.sin(frame_index*0.071+1.3))
    warm=np.zeros_like(bgr,dtype=np.float32); warm[:,:,1]=8; warm[:,:,2]=18
    out=bgr.astype(np.float32)*gain+warm*(gain-0.96)
    return np.clip(out,0,255).astype(np.uint8)

def pigment_dissolve(a:np.ndarray,b:np.ndarray,p:float,seed:int) -> np.ndarray:
    """Noise-shaped edge-soft dissolve that reads like wet pigment mixing."""
    if p<=0:return a
    if p>=1:return b
    h,w=a.shape[:2]
    noise=_noise_field(h,w,seed,0.0)
    threshold=0.18+0.64*p
    soft=np.clip((threshold-noise)*6.5+0.5,0,1)
    soft=cv2.GaussianBlur(soft,(0,0),2.2)
    bloom=3.5*math.sin(math.pi*p)
    aa=cv2.GaussianBlur(a,(0,0),bloom) if bloom>0.3 else a
    bb=cv2.GaussianBlur(b,(0,0),bloom) if bloom>0.3 else b
    return np.clip(aa*(1-soft[...,None])+bb*soft[...,None],0,255).astype(np.uint8)

def coin_portal(a:np.ndarray,b:np.ndarray,p:float,center:tuple[float,float]=(0.58,0.56)) -> np.ndarray:
    """Silver coin becomes a reflective circular portal/match-cut transition."""
    if p<=0:return a
    if p>=1:return b
    h,w=a.shape[:2]
    yy,xx=np.mgrid[0:h,0:w].astype(np.float32)
    cx,cy=center[0]*w,center[1]*h
    r=np.sqrt(((xx-cx)/(w*0.62))**2+((yy-cy)/(h*0.62))**2)
    radius=0.04 + 1.25*(p**1.35)
    edge=0.035+0.025*math.sin(math.pi*p)
    mask=np.clip((radius-r)/edge+0.5,0,1)
    scale=max(0.70,1.12-0.28*p)
    M=cv2.getRotationMatrix2D((w/2,h/2),0,scale)
    bb=cv2.warpAffine(b,M,(w,h),flags=cv2.INTER_CUBIC,borderMode=cv2.BORDER_REFLECT_101)
    out=a.astype(np.float32)*(1-mask[...,None])+bb.astype(np.float32)*mask[...,None]
    ring=np.exp(-((r-radius)/(edge*0.75+1e-6))**2)
    glint=(0.5+0.5*np.sin((xx/w)*16.0+p*math.tau*2.0))*ring*38.0
    out+=glint[...,None]
    return np.clip(out,0,255).astype(np.uint8)

def temporal_canvas_lock(shape, seed:int=302) -> np.ndarray:
    """Scene-fixed woven/pigment field. Reuse the same map for every frame in a shot."""
    h,w=shape[:2]
    rng=np.random.default_rng(seed)
    yy,xx=np.mgrid[0:h,0:w].astype(np.float32)
    weave=0.45*np.sin(xx/3.2)+0.31*np.sin(yy/4.6)+0.20*np.sin((xx+yy)/8.1)
    coarse=rng.normal(0,1,(max(8,h//22),max(8,w//22))).astype(np.float32)
    coarse=cv2.resize(coarse,(w,h),interpolation=cv2.INTER_CUBIC)
    coarse=cv2.GaussianBlur(coarse,(0,0),2.5)
    return (weave+coarse*0.9).astype(np.float32)

def apply_canvas_lock(bgr:np.ndarray, field:np.ndarray, amount:float=0.75) -> np.ndarray:
    f=bgr.astype(np.float32)
    f+=field[...,None]*amount
    return np.clip(f,0,255).astype(np.uint8)

def mesh_breath(bgr:np.ndarray, phase:float, strength:float=1.5, seed:int=0) -> np.ndarray:
    """Sub-pixel smooth cloth/crowd/hair motion; stable alternative to random jitter."""
    h,w=bgr.shape[:2]
    yy,xx=np.mgrid[0:h,0:w].astype(np.float32)
    p=phase*math.tau
    dx=strength*(0.55*np.sin(yy/67.0+p)+0.35*np.sin((xx+yy)/121.0-p*0.7))
    dy=strength*(0.45*np.sin(xx/79.0-p*0.55)+0.25*np.cos((xx-yy)/137.0+p))
    edge=np.minimum.reduce([xx/(w*0.12+1),(w-1-xx)/(w*0.12+1),yy/(h*0.12+1),(h-1-yy)/(h*0.12+1)])
    edge=np.clip(edge,0,1)
    return cv2.remap(bgr,xx+dx*edge,yy+dy*edge,cv2.INTER_CUBIC,borderMode=cv2.BORDER_REFLECT_101)

def wet_reflection_ripple(bgr:np.ndarray, phase:float, strength:float=0.10) -> np.ndarray:
    """Restrained puddle/wet-road reflection motion in the lower frame."""
    h,w=bgr.shape[:2]; y0=int(h*0.67)
    if y0>=h-2:return bgr
    band=bgr[y0:].copy(); bh=band.shape[0]
    source=bgr[max(0,y0-bh):y0]
    if source.shape[0]!=bh: source=cv2.resize(source,(w,bh))
    refl=cv2.flip(source,0)
    yy,xx=np.mgrid[0:bh,0:w].astype(np.float32); p=phase*math.tau
    dx=4.0*np.sin(yy/8.5+p)+2.0*np.sin(xx/53.0-p*0.6)
    dy=1.4*np.sin(xx/31.0+p*0.8)
    refl=cv2.remap(refl,xx+dx,yy+dy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT_101)
    alpha=(np.linspace(0.0,1.0,bh,dtype=np.float32)[:,None]**1.5)*strength
    out=bgr.copy().astype(np.float32)
    out[y0:]=out[y0:]*(1-alpha[...,None])+refl.astype(np.float32)*alpha[...,None]
    return np.clip(out,0,255).astype(np.uint8)

def heat_haze(bgr:np.ndarray, phase:float, region=(0.0,0.15,1.0,0.92), strength:float=1.8) -> np.ndarray:
    """Low-amplitude refractive shimmer for candles/hearths."""
    h,w=bgr.shape[:2]; x0,y0,x1,y1=region
    X0,X1=int(x0*w),int(x1*w); Y0,Y1=int(y0*h),int(y1*h)
    roi=bgr[Y0:Y1,X0:X1]
    if roi.size==0:return bgr
    rh,rw=roi.shape[:2]; yy,xx=np.mgrid[0:rh,0:rw].astype(np.float32); p=phase*math.tau
    dx=strength*(np.sin(yy/17.0+p)+0.35*np.sin((xx+yy)/41.0-p*0.7))
    dy=0.55*strength*np.sin(xx/37.0-p*0.9)
    warped=cv2.remap(roi,xx+dx,yy+dy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT_101)
    out=bgr.copy(); out[Y0:Y1,X0:X1]=cv2.addWeighted(roi,0.55,warped,0.45,0)
    return out

def depth_focus_breath(bgr:np.ndarray, depth:np.ndarray, phase:float, amount:float=1.7) -> np.ndarray:
    """Gentle rack-focus motion from pseudo-depth."""
    focus=0.50+0.18*math.sin(phase*math.tau)
    dist=np.abs(depth-focus)
    a=np.clip((dist-0.12)/0.46,0,1)
    sigma=0.7+amount*(0.5+0.5*math.sin(phase*math.tau*0.5+1.1))
    blur=cv2.GaussianBlur(bgr,(0,0),sigma)
    out=bgr.astype(np.float32)*(1-(a*0.28)[...,None])+blur.astype(np.float32)*(a*0.28)[...,None]
    return np.clip(out,0,255).astype(np.uint8)

def candle_light_shafts(bgr:np.ndarray, phase:float, origin=(0.78,0.18), strength:float=0.065) -> np.ndarray:
    """Soft radial warm shafts motivated by a window/candle source."""
    h,w=bgr.shape[:2]; cx,cy=origin[0]*w,origin[1]*h
    yy,xx=np.mgrid[0:h,0:w].astype(np.float32)
    ang=np.arctan2(yy-cy,xx-cx)
    rad=np.sqrt(((xx-cx)/w)**2+((yy-cy)/h)**2)
    beam=(0.5+0.5*np.cos(ang*18.0+phase*math.tau*0.7))**7
    beam*=np.exp(-rad*2.7)
    beam*=strength*(0.88+0.12*math.sin(phase*math.tau))
    tint=np.zeros_like(bgr,dtype=np.float32); tint[:,:,1]=125; tint[:,:,2]=255
    out=bgr.astype(np.float32)*(1-beam[...,None])+tint*beam[...,None]
    return np.clip(out,0,255).astype(np.uint8)

def silver_glint(bgr:np.ndarray, phase:float, center=(0.50,0.55), radius=0.14, strength=38.0) -> np.ndarray:
    """Localized moving specular sweep for a coin or polished metal object."""
    h,w=bgr.shape[:2]; cx,cy=center[0]*w,center[1]*h
    yy,xx=np.mgrid[0:h,0:w].astype(np.float32)
    dx=(xx-cx)/(w*radius+1e-6); dy=(yy-cy)/(h*radius+1e-6)
    disc=np.exp(-(dx*dx+dy*dy)*3.0)
    sweep=np.exp(-((dx-(phase*2.4-1.2))*5.5)**2)
    g=disc*sweep*strength
    return np.clip(bgr.astype(np.float32)+g[...,None],0,255).astype(np.uint8)

def bow_transient(bgr:np.ndarray, phase:float, roi=(0.0,0.25,0.72,0.86), pixels:float=2.2) -> np.ndarray:
    """Very small rhythmic warp for bowed-string performance shots."""
    h,w=bgr.shape[:2]; X0,Y0,X1,Y1=int(roi[0]*w),int(roi[1]*h),int(roi[2]*w),int(roi[3]*h)
    r=bgr[Y0:Y1,X0:X1]
    if r.size==0:return bgr
    rh,rw=r.shape[:2]; yy,xx=np.mgrid[0:rh,0:rw].astype(np.float32)
    impulse=max(0,math.sin(phase*math.tau*4.0))**6
    dx=pixels*impulse*(yy/rh-0.5)
    warped=cv2.remap(r,xx+dx,yy,cv2.INTER_CUBIC,borderMode=cv2.BORDER_REFLECT_101)
    out=bgr.copy(); out[Y0:Y1,X0:X1]=warped
    return out
