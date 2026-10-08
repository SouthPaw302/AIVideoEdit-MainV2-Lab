#!/usr/bin/env python3
"""Neutral proof-required Threshold Prism Bleed candidate.

Stylized 2D/2.5D threshold-light compositor informed by edge spreading,
wavelength separation and scattering. This is not a physical diffraction,
wave-optics, NeRF, or 3DGS renderer.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
import cv2
import numpy as np

@dataclass(frozen=True)
class ThresholdPrismParams:
    intensity:float=.75
    chroma_shift_px:int=8
    bloom_sigma:float=8.0
    ray_count:int=18
    ghost_opacity:float=.13

def apply_threshold_prism_bleed(frame_bgr:np.ndarray,threshold_rect:tuple[int,int,int,int],time_seconds:float,params:ThresholdPrismParams=ThresholdPrismParams(),ghost_plate:np.ndarray|None=None)->np.ndarray:
    img=frame_bgr.astype(np.float32);h,w=frame_bgr.shape[:2]
    x1,y1,x2,y2=[int(v) for v in threshold_rect]
    x1,x2=sorted((max(0,x1),min(w-1,x2)));y1,y2=sorted((max(0,y1),min(h-1,y2)))
    p=float(np.clip(params.intensity,0,1))
    if p<=0 or x2<=x1 or y2<=y1:return frame_bgr.copy()
    edge=np.zeros((h,w),np.uint8);opening=np.zeros((h,w),np.uint8)
    cv2.rectangle(edge,(x1,y1),(x2,y2),255,max(2,int(3+8*p)))
    cv2.rectangle(opening,(x1+2,y1+2),(x2-2,y2-2),255,-1)
    ef=cv2.GaussianBlur(edge,(0,0),max(1.0,params.bloom_sigma*(.45+.55*p))).astype(np.float32)/255
    spectral=np.zeros_like(img);shift=max(1,int(params.chroma_shift_px*p))
    spectral[...,2]=np.roll(ef,shift,axis=1)*210;spectral[...,1]=ef*145;spectral[...,0]=np.roll(ef,-shift,axis=1)*225
    core=cv2.GaussianBlur(opening,(0,0),3+7*p).astype(np.float32)/255
    spectral+=core[...,None]*np.array([62,92,150],np.float32)*p
    rays=np.zeros((h,w),np.float32);cx,cy=(x1+x2)//2,(y1+y2)//2
    for k in range(max(1,params.ray_count)):
        a=k*math.tau/params.ray_count+.18*math.sin(time_seconds*.7+k)
        sx=int(cx+(x2-x1)*.48*math.cos(a));sy=int(cy+(y2-y1)*.48*math.sin(a))
        length=int((55+210*p)*(.55+.45*((k*37)%17)/16))
        cv2.line(rays,(sx,sy),(int(sx+length*math.cos(a)),int(sy+length*math.sin(a))),.12+.22*p,1)
    rays=cv2.GaussianBlur(rays,(0,0),4+4*p)
    spectral+=rays[...,None]*np.array([90,132,195],np.float32)*p
    if ghost_plate is not None and p>.3:
        ghost=cv2.resize(ghost_plate,(w,h)).astype(np.float32);alpha=(opening.astype(np.float32)/255)[...,None]*(params.ghost_opacity*p)
        img=img*(1-alpha)+ghost*alpha
    return np.clip(img+spectral*p,0,255).astype(np.uint8)
