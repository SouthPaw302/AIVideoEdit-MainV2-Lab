#!/usr/bin/env python3
"""Timeline-aware temporal QC scanner for rendered videos.

Samples a render and flags sudden frame-difference spikes, optical-flow spikes,
and sharpness collapses. If a timeline JSON is supplied, risks near expected
scene boundaries are labeled as intentional transitions instead of unexplained
artifacts.

This is not semantic face/hand QC. It is a fast first-pass detector that narrows
manual inspection to suspicious timestamps. Robust z-score tests are combined
with absolute floors so very stable renders do not generate tiny false positives.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import cv2,numpy as np


def robust_z(x):
    x=np.asarray(x,float);med=np.median(x);mad=np.median(np.abs(x-med))+1e-8
    return (x-med)/(1.4826*mad)


def scan(path,sample_fps=3.0,width=320,timeline_path=None,transition_window=.85):
    cap=cv2.VideoCapture(path);fps=cap.get(cv2.CAP_PROP_FPS) or 24;n=int(cap.get(cv2.CAP_PROP_FRAME_COUNT));dur=n/fps;step=max(1,int(round(fps/sample_fps)))
    rows=[];prev=None;idx=0
    while True:
        ok,fr=cap.read()
        if not ok:break
        if idx%step:idx+=1;continue
        h,w=fr.shape[:2];nh=max(2,int(h*width/w));sm=cv2.resize(fr,(width,nh),interpolation=cv2.INTER_AREA);g=cv2.cvtColor(sm,cv2.COLOR_BGR2GRAY)
        sharp=float(cv2.Laplacian(g,cv2.CV_32F).var());diff=flowm=0.0
        if prev is not None:
            diff=float(np.mean(cv2.absdiff(prev,g))/255.0)
            flow=cv2.calcOpticalFlowFarneback(prev,g,None,.5,2,13,2,5,1.1,0);flowm=float(np.mean(np.linalg.norm(flow,axis=2)))
        rows.append({'t':idx/fps,'sharpness':sharp,'frame_difference':diff,'flow':flowm});prev=g;idx+=1
    cap.release()
    arr={k:np.array([r[k] for r in rows]) for k in ['sharpness','frame_difference','flow']};zs={k:robust_z(v) for k,v in arr.items()}
    boundaries=[]
    if timeline_path:
        td=json.loads(Path(timeline_path).read_text());boundaries=[float(s['end']) for s in td.get('scenes',[])[:-1]]
    risks=[]
    for i,r in enumerate(rows):
        if i==0:continue
        score=max(abs(zs['frame_difference'][i]),abs(zs['flow'][i]),max(0,-zs['sharpness'][i]));reasons=[]
        # Robust z-score alone can over-flag tiny changes when the render is very stable.
        # Require a meaningful absolute magnitude as well.
        if zs['frame_difference'][i]>4 and r['frame_difference']>.035:reasons.append('frame-difference-spike')
        if zs['flow'][i]>4 and r['flow']>1.0:reasons.append('motion-spike')
        if zs['sharpness'][i]<-4 and r['sharpness']<80:reasons.append('sharpness-collapse')
        if reasons:
            expected=any(abs(r['t']-b)<=transition_window for b in boundaries)
            risks.append({'t':round(r['t'],3),'score':round(float(score),3),'reasons':reasons,'expected_transition':expected,'metrics':r})
    risks=sorted(risks,key=lambda x:x['score'],reverse=True);unexplained=[x for x in risks if not x['expected_transition']]
    return {'source':Path(path).name,'duration_seconds':dur,'source_fps':fps,'sample_fps':sample_fps,'samples':len(rows),'summary':{k:{'median':float(np.median(v)),'p95':float(np.percentile(v,95))} for k,v in arr.items()},'risk_count':len(risks),'unexplained_risk_count':len(unexplained),'top_risks':risks[:80],'top_unexplained_risks':unexplained[:80]}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('video');ap.add_argument('--json-out',required=True);ap.add_argument('--sample-fps',type=float,default=3.0);ap.add_argument('--timeline');ap.add_argument('--transition-window',type=float,default=.85)
    a=ap.parse_args();Path(a.json_out).write_text(json.dumps(scan(a.video,a.sample_fps,timeline_path=a.timeline,transition_window=a.transition_window),indent=2))

if __name__=='__main__':main()
