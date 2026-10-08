#!/usr/bin/env python3
"""Build normalized audio-reactivity control envelopes for video rendering.

Controls are resampled to a compact fixed rate (default 20 Hz):
energy, transient, spectral brightness, low, mid, and high band activity.
The output may stand alone or be merged into an existing timeline JSON.

Requires librosa + NumPy. No cloud/API/model dependency.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import librosa


def robust01(x,lo=5,hi=95):
    x=np.asarray(x,float);a,b=np.percentile(x,[lo,hi]);return np.clip((x-a)/(b-a+1e-9),0,1)


def build(audio:str,control_hz:float=20.0,sr:int=22050):
    y,sr=librosa.load(audio,sr=sr,mono=True);dur=len(y)/sr;hop=512
    S=np.abs(librosa.stft(y,n_fft=2048,hop_length=hop));P=S**2;freq=librosa.fft_frequencies(sr=sr,n_fft=2048)
    rms=robust01(librosa.feature.rms(S=S,frame_length=2048,hop_length=hop)[0])
    onset=robust01(librosa.onset.onset_strength(S=librosa.amplitude_to_db(S+1e-7,ref=np.max),sr=sr,hop_length=hop),10,97)
    centroid=robust01(librosa.feature.spectral_centroid(S=S,sr=sr)[0])
    bands={}
    for name,(a,b) in {'low':(40,220),'mid':(220,2200),'high':(2200,9000)}.items():
        mask=(freq>=a)&(freq<b);bands[name]=robust01(np.sqrt(np.mean(P[mask],axis=0)+1e-12))
    frame_t=librosa.frames_to_time(np.arange(len(rms)),sr=sr,hop_length=hop)
    ctl_t=np.arange(0,dur+1e-6,1.0/control_hz)
    rs=lambda x:np.interp(ctl_t,frame_t,x).round(5).tolist()
    return {'hz':control_hz,'times':ctl_t.round(4).tolist(),'energy':rs(rms),'transient':rs(onset),'brightness':rs(centroid),'low':rs(bands['low']),'mid':rs(bands['mid']),'high':rs(bands['high'])}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('audio');ap.add_argument('--json-out',required=True);ap.add_argument('--timeline');ap.add_argument('--control-hz',type=float,default=20.0)
    a=ap.parse_args();controls=build(a.audio,a.control_hz)
    if a.timeline:
        out=json.loads(Path(a.timeline).read_text());out['controls']=controls
    else: out={'source':Path(a.audio).name,'controls':controls}
    Path(a.json_out).write_text(json.dumps(out,indent=2))

if __name__=='__main__':main()
