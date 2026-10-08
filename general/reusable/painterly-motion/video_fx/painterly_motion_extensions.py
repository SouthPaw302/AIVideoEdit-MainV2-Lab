#!/usr/bin/env python3
"""Additional deterministic painterly motion effects for AIVideoEdit.

These effects were developed during Silver Coin V3/V4 and are kept separate from
the base CPU effects module so they can be selectively imported by other songs.
Requires OpenCV + NumPy.
"""
from __future__ import annotations
import math
import cv2
import numpy as np

def temporal_canvas_lock(shape, seed:int=302) -> np.ndarray:
    """Scene-fixed woven/pigment field. Reuse the same map for every frame."""
    h,w=shape[:2]; rng=np.random.default_rng(seed); yy,xx=np.mgrid[0:h,0:w].astype(np.float32)
    weave=.45*np.sin(xx/3.2)+.31*np.sin(yy/4.6)+.20*np.sin((xx+yy)/8.1)
    coarse=rng.normal(0,1,(max(8,h//22),max(8,w//22))).astype(np.float32)
    coarse=cv2.resize(coarse,(w,h),interpolation=cv2.INTER_CUBIC); coarse=cv2.GaussianBlur(coarse,(0,0),2.5)
    return (weave+coarse*.9).astype(np.float32)

def apply_canvas_lock(bgr:np.ndarray, field:np.ndarray, amount:float=.75) -> np.ndarray:
    return np.clip(bgr.astype(np.float32)+field[...,None]*amount,0,255).astype(np.uint8)

def mesh_breath(bgr:np.ndarray, phase:float, strength:float=1.5) -> np.ndarray:
    """Sub-pixel coherent cloth/crowd/hair movement with pinned frame edges."""
    h,w=bgr.shape[:2]; yy,xx=np.mgrid[0:h,0:w].astype(np.float32); p=phase*math.tau
    dx=strength*(.55*np.sin(yy/67.0+p)+.35*np.sin((xx+yy)/121.0-p*.7))
    dy=strength*(.45*np.sin(xx/79.0-p*.55)+.25*np.cos((xx-yy)/137.0+p))
    edge=np.minimum.reduce([xx/(w*.12+1),(w-1-xx)/(w*.12+1),yy/(h*.12+1),(h-1-yy)/(h*.12+1)])
    edge=np.clip(edge,0,1)
    return cv2.remap(bgr,xx+dx*edge,yy+dy*edge,cv2.INTER_CUBIC,borderMode=cv2.BORDER_REFLECT_101)

def wet_reflection_ripple(bgr:np.ndarray, phase:float, strength:float=.10) -> np.ndarray:
    """Restrained mirrored color memory in the lower frame for wet roads/puddles."""
    h,w=bgr.shape[:2]; y0=int(h*.67)
    if y0>=h-2:return bgr
    bh=h-y0; source=bgr[max(0,y0-bh):y0]
    if source.shape[0]!=bh:source=cv2.resize(source,(w,bh))
    refl=cv2.flip(source,0); yy,xx=np.mgrid[0:bh,0:w].astype(np.float32); p=phase*math.tau
    dx=4*np.sin(yy/8.5+p)+2*np.sin(xx/53.0-p*.6); dy=1.4*np.sin(xx/31.0+p*.8)
    refl=cv2.remap(refl,xx+dx,yy+dy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT_101)
    alpha=(np.linspace(0,1,bh,dtype=np.float32)[:,None]**1.5)*strength
    out=bgr.copy().astype(np.float32); out[y0:]=out[y0:]*(1-alpha[...,None])+refl.astype(np.float32)*alpha[...,None]
    return np.clip(out,0,255).astype(np.uint8)

def heat_haze(bgr:np.ndarray, phase:float, region=(0.0,.15,1.0,.92), strength:float=1.8) -> np.ndarray:
    """Low-amplitude refractive shimmer around motivated hot light sources."""
    h,w=bgr.shape[:2]; x0,y0,x1,y1=region; X0,X1=int(x0*w),int(x1*w); Y0,Y1=int(y0*h),int(y1*h); roi=bgr[Y0:Y1,X0:X1]
    if roi.size==0:return bgr
    rh,rw=roi.shape[:2]; yy,xx=np.mgrid[0:rh,0:rw].astype(np.float32); p=phase*math.tau
    dx=strength*(np.sin(yy/17.0+p)+.35*np.sin((xx+yy)/41.0-p*.7)); dy=.55*strength*np.sin(xx/37.0-p*.9)
    warped=cv2.remap(roi,xx+dx,yy+dy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT_101)
    out=bgr.copy(); out[Y0:Y1,X0:X1]=cv2.addWeighted(roi,.55,warped,.45,0); return out

def depth_focus_breath(bgr:np.ndarray, depth:np.ndarray, phase:float, amount:float=1.7) -> np.ndarray:
    """Gentle pseudo-depth rack focus for vocal/portrait emphasis."""
    focus=.50+.18*math.sin(phase*math.tau); dist=np.abs(depth-focus); a=np.clip((dist-.12)/.46,0,1)
    sigma=.7+amount*(.5+.5*math.sin(phase*math.tau*.5+1.1)); blur=cv2.GaussianBlur(bgr,(0,0),sigma)
    out=bgr.astype(np.float32)*(1-(a*.28)[...,None])+blur.astype(np.float32)*(a*.28)[...,None]
    return np.clip(out,0,255).astype(np.uint8)

def candle_light_shafts(bgr:np.ndarray, phase:float, origin=(.78,.18), strength:float=.065) -> np.ndarray:
    """Soft radial warm shafts tied to a window/candle source."""
    h,w=bgr.shape[:2]; cx,cy=origin[0]*w,origin[1]*h; yy,xx=np.mgrid[0:h,0:w].astype(np.float32)
    ang=np.arctan2(yy-cy,xx-cx); rad=np.sqrt(((xx-cx)/w)**2+((yy-cy)/h)**2)
    beam=(.5+.5*np.cos(ang*18+phase*math.tau*.7))**7; beam*=np.exp(-rad*2.7); beam*=strength*(.88+.12*math.sin(phase*math.tau))
    tint=np.zeros_like(bgr,dtype=np.float32); tint[:,:,1]=125; tint[:,:,2]=255
    return np.clip(bgr.astype(np.float32)*(1-beam[...,None])+tint*beam[...,None],0,255).astype(np.uint8)

def localized_specular_glint(bgr:np.ndarray, phase:float, center=(.50,.55), radius=.14, strength=38.0) -> np.ndarray:
    """Moving local specular sweep for metal/coin without affecting faces or room."""
    h,w=bgr.shape[:2]; cx,cy=center[0]*w,center[1]*h; yy,xx=np.mgrid[0:h,0:w].astype(np.float32)
    dx=(xx-cx)/(w*radius+1e-6); dy=(yy-cy)/(h*radius+1e-6); disc=np.exp(-(dx*dx+dy*dy)*3.0); sweep=np.exp(-((dx-(phase*2.4-1.2))*5.5)**2)
    return np.clip(bgr.astype(np.float32)+(disc*sweep*strength)[...,None],0,255).astype(np.uint8)

def performance_transient_warp(bgr:np.ndarray, phase:float, roi=(0.0,.25,.72,.86), pixels:float=2.2, cycles:float=4.0) -> np.ndarray:
    """Small impulse-like regional warp for bow strokes, drum hits, hand strikes, etc."""
    h,w=bgr.shape[:2]; X0,Y0,X1,Y1=int(roi[0]*w),int(roi[1]*h),int(roi[2]*w),int(roi[3]*h); r=bgr[Y0:Y1,X0:X1]
    if r.size==0:return bgr
    rh,rw=r.shape[:2]; yy,xx=np.mgrid[0:rh,0:rw].astype(np.float32); impulse=max(0,math.sin(phase*math.tau*cycles))**6; dx=pixels*impulse*(yy/rh-.5)
    warped=cv2.remap(r,xx+dx,yy,cv2.INTER_CUBIC,borderMode=cv2.BORDER_REFLECT_101); out=bgr.copy(); out[Y0:Y1,X0:X1]=warped; return out
