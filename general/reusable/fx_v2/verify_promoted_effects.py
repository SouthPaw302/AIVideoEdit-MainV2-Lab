from __future__ import annotations
import hashlib, json
import cv2, numpy as np
from promoted_effects import EFFECT_NAMES, LEGACY_ALIASES, apply_effect

def synth(w=320,h=180):
    y,x=np.mgrid[0:h,0:w]
    im=np.zeros((h,w,3),np.uint8)
    im[...,0]=np.clip(25+x*180/w,0,255); im[...,1]=np.clip(30+y*170/h,0,255); im[...,2]=np.clip(50+(x+y)%145,0,255)
    cv2.circle(im,(95,94),42,(35,165,235),-1,cv2.LINE_AA); cv2.rectangle(im,(190,32),(286,150),(175,75,45),-1)
    cv2.line(im,(0,130),(319,108),(225,225,225),2,cv2.LINE_AA)
    return im

def md(a,b): return float(np.mean(cv2.absdiff(a,b)))

def verify():
    src=synth(); alt=cv2.GaussianBlur(255-src,(0,0),1.3); results={}; all_bytes=[]
    for name in EFFECT_NAMES:
        outs=[apply_effect(name,src,t,2.0,.67,.61,alt) for t in (.17,.63,1.19,1.73)]
        if any(o.shape!=src.shape or o.dtype!=src.dtype for o in outs): raise RuntimeError(f'{name}: invalid output')
        source=max(md(src,o) for o in outs); temporal=max(md(outs[i],outs[j]) for i in range(len(outs)) for j in range(i+1,len(outs)))
        if source < .02: raise RuntimeError(f'{name}: source delta too low {source}')
        if temporal < .01: raise RuntimeError(f'{name}: temporal delta too low {temporal}')
        digest=hashlib.sha256(b''.join(o.tobytes() for o in outs)).hexdigest(); all_bytes.extend(o.tobytes() for o in outs)
        results[name]={'status':'PASS','source_delta_max':round(source,6),'temporal_delta_max':round(temporal,6),'sample_sha256':digest}
    missing=sorted(set(LEGACY_ALIASES.values())-set(EFFECT_NAMES))
    if missing: raise RuntimeError('alias targets missing: '+','.join(missing))
    return {'schema':'aivideoedit.promoted-effects-verification.v1','result':'PASS','effect_count':len(EFFECT_NAMES),'legacy_alias_count':len(LEGACY_ALIASES),'effects':results,'aggregate_sample_sha256':hashlib.sha256(b''.join(all_bytes)).hexdigest()}

if __name__=='__main__': print(json.dumps(verify(),indent=2,sort_keys=True))
