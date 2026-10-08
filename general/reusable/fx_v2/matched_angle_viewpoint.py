#!/usr/bin/env python3
"""Neutral proof-required matched-angle viewpoint candidate.

Creates tiny source-locked viewpoint changes from an accepted 2D plate using
bounded planar perspective projection. It generates/inpaints no new pixels.
"""
from __future__ import annotations
import math
import cv2
import numpy as np

def _homography_yaw(width:int,height:int,yaw_deg:float,focal_px:float)->np.ndarray:
    theta=math.radians(yaw_deg);c,s=math.cos(theta),math.sin(theta);cx,cy=(width-1)/2,(height-1)/2
    src=np.float32([[0,0],[width-1,0],[width-1,height-1],[0,height-1]]);dst=[]
    for x,y in src:
        X,Y=x-cx,y-cy;Xp=c*X;Zp=-s*X;den=max(1e-6,focal_px+Zp)
        dst.append([focal_px*Xp/den+cx,focal_px*Y/den+cy])
    return cv2.getPerspectiveTransform(src,np.float32(dst))

def matched_angle_viewpoint(frame:np.ndarray,yaw_deg:float=.85,overscan:float=1.025,focal_px:float=1700.0)->np.ndarray:
    h,w=frame.shape[:2];w2,h2=max(w,int(w*overscan)),max(h,int(h*overscan))
    big=cv2.resize(frame,(w2,h2),interpolation=cv2.INTER_LANCZOS4)
    warped=cv2.warpPerspective(big,_homography_yaw(w2,h2,yaw_deg,focal_px),(w2,h2),flags=cv2.INTER_CUBIC,borderMode=cv2.BORDER_REFLECT_101)
    x0,y0=(w2-w)//2,(h2-h)//2
    return warped[y0:y0+h,x0:x0+w]
