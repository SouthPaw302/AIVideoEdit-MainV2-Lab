#!/usr/bin/env python3
"""Reusable CPU-first cinematic effects for AIVideoEdit.

Requires: OpenCV + NumPy. No GPU or cloud service required.
Designed for painterly keyframes and recovery environments where temporal
stability matters more than maximal synthetic motion.
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
    warp: float = 0.0
    light_shafts: float = 0.0

DEFAULT_FAMILIES = {
    "village": FamilyStyle((118,104,92),(190,196,188),rain=.72,smoke=.28,warp=.24,light_shafts=.12),
    "threshold": FamilyStyle((92,92,96),(70,172,245),rain=.28,embers=.12,smoke=.38,warp=.30,light_shafts=.40),
    "tavern": FamilyStyle((55,72,92),(32,132,255),embers=.66,smoke=.62,warp=.42,light_shafts=.30),
    "coin": FamilyStyle((118,110,104),(240,235,225),embers=.08,smoke=.18,warp=.18,light_shafts=.18),
    "dawn": FamilyStyle((90,110,132),(90,190,255),embers=.14,smoke=.24,warp=.22,light_shafts=.28),
}

def edge_reframe(bgr: np.ndarray, left_fraction: float = 0.0) -> np.ndarray:
    """Remove a contaminated left edge by reframing instead of inpainting."""
    if left_fraction <= 0: return bgr
    h,w=bgr.shape[:2]
    x=max(0,min(w-2,int(round(w*left_fraction))))
    return cv2.resize(bgr[:,x:],(w,h),interpolation=cv2.INTER_LANCZOS4)

def painterly_upscale(bgr: np.ndarray, scale: float=2.0) -> np.ndarray:
    h,w=bgr.shape[:2]
    out=cv2.resize(bgr,(int(w*scale),int(h*scale)),interpolation=cv2.INTER_LANCZOS4)
    smooth=cv2.bilateralFilter(out,5,18,18)
    blur=cv2.GaussianBlur(smooth,(0,0),.82)
    return np.clip(cv2.addWeighted(smooth,1.085,blur,-.085,0),0,255).astype(np.uint8)

def pseudo_depth(bgr: np.ndarray) -> np.ndarray:
    """Non-metric depth proxy for parallax, atmosphere, and light gating."""
    h,w=bgr.shape[:2]
    lab=cv2.cvtColor(bgr,cv2.COLOR_BGR2LAB)
    L=lab[:,:,0].astype(np.float32)/255.0
    local=np.abs(L-cv2.GaussianBlur(L,(0,0),5.0))
    edges=cv2.GaussianBlur(cv2.Canny(bgr,55,135).astype(np.float32)/255.0,(0,0),3.8)
    sat=cv2.cvtColor(bgr,cv2.COLOR_BGR2HSV)[:,:,1].astype(np.float32)/255.0
    y=np.repeat(np.linspace(0,1,h,dtype=np.float32)[:,None],w,axis=1)
    d=.57*y+.20*np.clip(local*4.2,0,1)+.13*edges+.10*sat
    d=cv2.GaussianBlur(d,(0,0),2.3)
    lo,hi=np.percentile(d,[3,97])
    return np.clip((d-lo)/(hi-lo+1e-6),0,1).astype(np.float32)

def depth_parallax(bgr: np.ndarray, depth: np.ndarray, phase: float, amount: float=7.0) -> np.ndarray:
    h,w=bgr.shape[:2]
    yy,xx=np.mgrid[0:h,0:w].astype(np.float32)
    dx=math.sin(phase*math.tau)*amount
    dy=math.sin(phase*math.tau*.5+.8)*(amount*.26)
    z=depth-.5
    return cv2.remap(bgr,xx-dx*z,yy-dy*z,cv2.INTER_CUBIC,borderMode=cv2.BORDER_REFLECT_101)

def _noise_field(h:int,w:int,seed:int,phase:float,scale:int=18) -> np.ndarray:
    rng=np.random.default_rng(seed)
    base=rng.random((max(8,h//scale),max(8,w//scale)),dtype=np.float32)
    field=cv2.resize(base,(w,h),interpolation=cv2.INTER_CUBIC)
    yy,xx=np.mgrid[0:h,0:w].astype(np.float32)
    mapx=xx+15*math.sin(phase*math.tau)+7*np.sin(yy/70.0+phase*math.tau)
    mapy=yy+9*math.cos(phase*math.tau*.7)+5*np.sin(xx/95.0-phase*math.tau)
    field=cv2.remap(field,mapx,mapy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_WRAP)
    return cv2.GaussianBlur(field,(0,0),7.0)

def localized_micro_warp(bgr: np.ndarray, depth: np.ndarray, amount: float, phase: float) -> np.ndarray:
    """Low-frequency sub-pixel motion for cloth, crowd, foliage, hair."""
    if amount<=0:return bgr
    h,w=bgr.shape[:2]
    yy,xx=np.mgrid[0:h,0:w].astype(np.float32)
    gate=np.clip((depth-.22)/.70,0,1)
    dx=(np.sin(yy/63.0+phase*math.tau)*1.4+np.sin(yy/121.0-phase*math.tau*.7))*amount*gate
    dy=(np.sin(xx/81.0-phase*math.tau*.8)*.9+np.cos(xx/147.0+phase*math.tau*.4))*amount*gate
    return cv2.remap(bgr,xx+dx.astype(np.float32),yy+dy.astype(np.float32),cv2.INTER_CUBIC,borderMode=cv2.BORDER_REFLECT_101)

def advected_atmosphere(bgr: np.ndarray, depth: np.ndarray, fog_bgr: tuple[int,int,int], strength: float, phase: float, seed:int) -> np.ndarray:
    if strength<=0:return bgr
    h,w=bgr.shape[:2]
    field=_noise_field(h,w,seed,phase)
    y=np.linspace(1.0,.16,h,dtype=np.float32)[:,None]
    gate=.60+.40*(1.0-depth)
    alpha=np.clip((field-.38)*.22*strength*y*gate,0,.145)
    tint=np.empty_like(bgr,dtype=np.float32); tint[:]=fog_bgr
    return np.clip(bgr.astype(np.float32)*(1-alpha[...,None])+tint*alpha[...,None],0,255).astype(np.uint8)

def volumetric_light_shafts(bgr: np.ndarray, depth: np.ndarray, light_bgr: tuple[int,int,int], strength: float, phase: float, seed:int, source=(.72,.18)) -> np.ndarray:
    if strength<=0:return bgr
    h,w=bgr.shape[:2]
    yy,xx=np.mgrid[0:h,0:w].astype(np.float32)
    sx,sy=source[0]*w,source[1]*h
    angle=np.arctan2(yy-sy,xx-sx)
    radius=np.sqrt((xx-sx)**2+(yy-sy)**2)
    fan=(.5+.5*np.cos(angle*12.0+phase*math.tau*.35))**7
    fall=np.exp(-radius/(max(h,w)*.72))
    noise=.72+.28*_noise_field(h,w,seed,phase,scale=24)
    gate=np.clip(1.10-depth,0,1)
    alpha=np.clip(fan*fall*noise*gate*strength*.11,0,.09)
    tint=np.empty_like(bgr,dtype=np.float32); tint[:]=light_bgr
    return np.clip(bgr.astype(np.float32)*(1-alpha[...,None])+tint*alpha[...,None],0,255).astype(np.uint8)

def motivated_particles(bgr: np.ndarray, rain: float, embers: float, phase: float, seed:int) -> np.ndarray:
    out=bgr.copy(); h,w=out.shape[:2]; rng=np.random.default_rng(seed)
    for i in range(int(72*rain)):
        x0=int(rng.uniform(0,w)); y0=float(rng.uniform(-h,h)); speed=rng.uniform(.75,1.35)
        y=int((y0+phase*h*1.8*speed)%(h+60)-30); x=int((x0+phase*25*speed)%w)
        L=int(rng.uniform(9,19)); cv2.line(out,(x,y),(x-3,y+L),(168,177,184),1,cv2.LINE_AA)
    for i in range(int(48*embers)):
        x0=rng.uniform(0,w); y0=rng.uniform(h*.35,h*1.05)
        x=int((x0+math.sin((phase+i*.17)*math.tau)*8)%w)
        y=int((y0-phase*h*rng.uniform(.25,.60))%(h+40))
        cv2.circle(out,(x,y),1 if i%5 else 2,(45,142,250),-1,cv2.LINE_AA)
    return out

def firelight_breath(bgr: np.ndarray, frame_index:int, strength:float=.04) -> np.ndarray:
    gain=1.0+strength*(.50*math.sin(frame_index*.17)+.24*math.sin(frame_index*.071+1.3))
    warm=np.zeros_like(bgr,dtype=np.float32); warm[:,:,1]=7; warm[:,:,2]=17
    return np.clip(bgr.astype(np.float32)*gain+warm*(gain-.96),0,255).astype(np.uint8)

def puddle_shimmer(bgr: np.ndarray, phase:float, start_fraction:float=.72) -> np.ndarray:
    h,w=bgr.shape[:2]; y0=int(h*start_fraction)
    strip=bgr[y0:].copy(); sh=strip.shape[0]
    yy,xx=np.mgrid[0:sh,0:w].astype(np.float32)
    dx=(np.sin(yy/7.0+phase*math.tau*2.0)*1.8+np.sin(yy/15.0-phase*math.tau)*.8).astype(np.float32)
    warped=cv2.remap(strip,xx+dx,yy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT_101)
    mask=np.linspace(0,.24,sh,dtype=np.float32)[:,None,None]
    out=bgr.copy().astype(np.float32); out[y0:]=strip*(1-mask)+warped*mask
    return np.clip(out,0,255).astype(np.uint8)

def chroma_pigment_transport(a:np.ndarray,b:np.ndarray,p:float) -> np.ndarray:
    if p<=0:return a
    if p>=1:return b
    la=cv2.cvtColor(a,cv2.COLOR_BGR2LAB).astype(np.float32)
    lb=cv2.cvtColor(b,cv2.COLOR_BGR2LAB).astype(np.float32)
    q=np.clip(p*1.35,0,1); la[:,:,1:]=la[:,:,1:]*(1-q)+lb[:,:,1:]*q
    return cv2.cvtColor(np.clip(la,0,255).astype(np.uint8),cv2.COLOR_LAB2BGR)

def pigment_dissolve(a:np.ndarray,b:np.ndarray,p:float,seed:int) -> np.ndarray:
    if p<=0:return a
    if p>=1:return b
    h,w=a.shape[:2]; noise=_noise_field(h,w,seed,0.0)
    soft=np.clip(((.18+.64*p)-noise)*6.5+.5,0,1)
    soft=cv2.GaussianBlur(soft,(0,0),2.2)
    bloom=3.2*math.sin(math.pi*p)
    aa=cv2.GaussianBlur(a,(0,0),bloom) if bloom>.3 else a
    bb=cv2.GaussianBlur(b,(0,0),bloom) if bloom>.3 else b
    return np.clip(aa*(1-soft[...,None])+bb*soft[...,None],0,255).astype(np.uint8)

def object_portal(a:np.ndarray,b:np.ndarray,p:float,center=(.58,.56)) -> np.ndarray:
    """Circular object-driven portal/match cut with narrow optical glint."""
    if p<=0:return a
    if p>=1:return b
    h,w=a.shape[:2]; yy,xx=np.mgrid[0:h,0:w].astype(np.float32)
    cx,cy=center[0]*w,center[1]*h
    r=np.sqrt(((xx-cx)/(w*.62))**2+((yy-cy)/(h*.62))**2)
    radius=.035+1.25*(p**1.35); edge=.034+.024*math.sin(math.pi*p)
    mask=np.clip((radius-r)/edge+.5,0,1)
    M=cv2.getRotationMatrix2D((w/2,h/2),0,max(.70,1.12-.28*p))
    bb=cv2.warpAffine(b,M,(w,h),flags=cv2.INTER_CUBIC,borderMode=cv2.BORDER_REFLECT_101)
    out=a.astype(np.float32)*(1-mask[...,None])+bb.astype(np.float32)*mask[...,None]
    ring=np.exp(-((r-radius)/(edge*.75+1e-6))**2)
    glint=(.5+.5*np.sin((xx/w)*16.0+p*math.tau*2.0))*ring*36.0
    out[:,:,2]+=glint*.90; out[:,:,1]+=glint*.96; out[:,:,0]+=glint*1.05
    return np.clip(out,0,255).astype(np.uint8)
