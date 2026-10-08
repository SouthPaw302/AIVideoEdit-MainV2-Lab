#!/usr/bin/env python3
"""Measure the motion envelope of a visual reference clip.

Outputs optical-flow magnitude, frame-difference, phase-correlation camera drift,
and basic color/luminance statistics. The result is intended to calibrate generated
or procedural animation to the motion density of a reference instead of copying
literal subject matter.

Requires OpenCV + NumPy only.
"""
from __future__ import annotations
import argparse,json,os
from pathlib import Path
import cv2
import numpy as np


def analyze(path:str, analysis_size:int=280):
    cap=cv2.VideoCapture(path)
    fps=float(cap.get(cv2.CAP_PROP_FPS) or 24.0)
    frames=[]
    while True:
        ok,fr=cap.read()
        if not ok: break
        frames.append(fr)
    cap.release()
    if len(frames)<2: raise RuntimeError(f"Not enough frames in {path}")
    flows=[];diffs=[];shifts=[];sats=[];lums=[]
    for i,fr in enumerate(frames):
        hsv=cv2.cvtColor(fr,cv2.COLOR_BGR2HSV)
        sats.append(float(hsv[:,:,1].mean()/255.0))
        lums.append(float(cv2.cvtColor(fr,cv2.COLOR_BGR2GRAY).mean()/255.0))
        if not i: continue
        g0=cv2.resize(cv2.cvtColor(frames[i-1],cv2.COLOR_BGR2GRAY),(analysis_size,analysis_size))
        g1=cv2.resize(cv2.cvtColor(fr,cv2.COLOR_BGR2GRAY),(analysis_size,analysis_size))
        flow=cv2.calcOpticalFlowFarneback(g0,g1,None,.5,3,15,3,5,1.2,0)
        mag=np.linalg.norm(flow,axis=2)
        flows.append([float(np.mean(mag)),float(np.percentile(mag,90)),float(np.percentile(mag,99))])
        diffs.append(float(np.mean(cv2.absdiff(g0,g1))/255.0))
        shift,_=cv2.phaseCorrelate(np.float32(g0),np.float32(g1))
        shifts.append([float(shift[0]),float(shift[1])])
    arr=np.asarray(flows);sh=np.asarray(shifts)
    return {
        'source':os.path.basename(path),'fps':fps,'frames':len(frames),'duration_seconds':len(frames)/fps,
        'analysis_size':analysis_size,
        'mean_flow_px':float(arr[:,0].mean()),
        'median_p90_flow_px':float(np.median(arr[:,1])),
        'median_p99_flow_px':float(np.median(arr[:,2])),
        'mean_frame_difference':float(np.mean(diffs)),
        'phase_shift_mean_abs_px':[float(np.mean(np.abs(sh[:,0]))),float(np.mean(np.abs(sh[:,1])))],
        'phase_shift_net_px':[float(np.sum(sh[:,0])),float(np.sum(sh[:,1]))],
        'mean_saturation':float(np.mean(sats)),'mean_luminance':float(np.mean(lums)),
    }


def main():
    ap=argparse.ArgumentParser();ap.add_argument('clips',nargs='+');ap.add_argument('--json-out',required=True);ap.add_argument('--analysis-size',type=int,default=280)
    a=ap.parse_args();out={Path(p).name:analyze(p,a.analysis_size) for p in a.clips}
    Path(a.json_out).write_text(json.dumps(out,indent=2))

if __name__=='__main__': main()
