#!/usr/bin/env python3
"""Create a deterministic music-video edit map from an audio master.

Requires librosa + NumPy. Optional matplotlib produces a visual overview.
Outputs beat times, signal-derived section candidates, transients, energy peaks,
high-value sync points, and a compact 0.5-second envelope.

Section candidates are intentionally NOT named Verse/Chorus/Bridge automatically;
semantic labels must be verified by listening/lyrics.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import librosa

def robust01(x):
    x=np.asarray(x,dtype=np.float32)
    if x.size==0:return x
    lo,hi=np.percentile(x,[5,95])
    return np.clip((x-lo)/(hi-lo+1e-8),0,1)

def nearest_times(times, values, min_gap=1.0, top_n=32):
    picked=[]
    for i in np.argsort(values)[::-1]:
        t=float(times[i])
        if all(abs(t-p[0])>=min_gap for p in picked):
            picked.append((t,float(values[i])))
            if len(picked)>=top_n:break
    return sorted(picked)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('audio')
    ap.add_argument('--json-out',required=True)
    ap.add_argument('--png-out')
    ap.add_argument('--sr',type=int,default=22050)
    ap.add_argument('--hop',type=int,default=512)
    ap.add_argument('--section-min',type=float,default=7.0)
    a=ap.parse_args()

    y,sr=librosa.load(a.audio,sr=a.sr,mono=True)
    duration=float(librosa.get_duration(y=y,sr=sr)); hop=a.hop
    rms=librosa.feature.rms(y=y,hop_length=hop)[0]
    centroid=librosa.feature.spectral_centroid(y=y,sr=sr,hop_length=hop)[0]
    onset=librosa.onset.onset_strength(y=y,sr=sr,hop_length=hop)
    chroma=librosa.feature.chroma_cqt(y=y,sr=sr,hop_length=hop)
    n=min(len(rms),len(centroid),len(onset),chroma.shape[1])
    t=librosa.frames_to_time(np.arange(n),sr=sr,hop_length=hop)
    energy=robust01(rms[:n]); brightness=robust01(centroid[:n]); transients=robust01(onset[:n]); chroma=chroma[:,:n]

    tempo,beat_frames=librosa.beat.beat_track(y=y,sr=sr,hop_length=hop)
    tempo=float(np.asarray(tempo).reshape(-1)[0])
    beat_times=librosa.frames_to_time(beat_frames,sr=sr,hop_length=hop)

    mfcc=librosa.feature.mfcc(y=y,sr=sr,n_mfcc=12,hop_length=hop)[:,:n]
    feat=np.vstack([librosa.util.normalize(mfcc,axis=1),librosa.util.normalize(chroma,axis=1)])
    target=max(3,min(16,int(round(duration/18.0))))
    bounds=librosa.segment.agglomerative(feat,k=target)
    raw_bounds=librosa.frames_to_time(bounds,sr=sr,hop_length=hop)
    candidates=[0.0]
    for x in sorted(float(v) for v in raw_bounds):
        if x-candidates[-1]>=a.section_min and duration-x>=a.section_min*.65:
            candidates.append(x)
    if duration-candidates[-1] < a.section_min*.6 and len(candidates)>1:candidates.pop()
    candidates.append(duration)

    sections=[]
    for i,(s,e) in enumerate(zip(candidates[:-1],candidates[1:])):
        m=(t>=s)&(t<e)
        sections.append({'index':i,'start':round(s,3),'end':round(e,3),'duration':round(e-s,3),'mean_energy':round(float(energy[m].mean()) if m.any() else 0,4),'mean_brightness':round(float(brightness[m].mean()) if m.any() else 0,4),'mean_transient':round(float(transients[m].mean()) if m.any() else 0,4)})

    high_sync=nearest_times(t,transients*.65+energy*.25+brightness*.10,1.25,40)
    strong=nearest_times(t,transients,.65,64)
    peaks=nearest_times(t,energy,2.0,32)
    bins=np.arange(0,duration+.5,.5); coarse=[]
    for s,e in zip(bins[:-1],bins[1:]):
        m=(t>=s)&(t<e)
        if m.any():coarse.append({'t':round(float(s),3),'energy':round(float(energy[m].mean()),4),'brightness':round(float(brightness[m].mean()),4),'transient':round(float(transients[m].mean()),4)})

    data={'schema_version':1,'source':Path(a.audio).name,'duration_seconds':round(duration,6),'analysis_sample_rate':sr,'hop_length':hop,'tempo_bpm':round(tempo,3),'beat_times_seconds':[round(float(x),4) for x in beat_times],'section_candidates':sections,'high_value_sync_points':[{'t':round(x,4),'score':round(v,4)} for x,v in high_sync],'strong_transients':[{'t':round(x,4),'score':round(v,4)} for x,v in strong],'energy_peaks':[{'t':round(x,4),'score':round(v,4)} for x,v in peaks],'coarse_envelope_0p5s':coarse,'notes':['Section boundaries are signal-derived edit candidates, not lyric/semantic labels.','Verify structure by listening before assigning Verse/Chorus/Bridge names.']}
    Path(a.json_out).write_text(json.dumps(data,indent=2))

    if a.png_out:
        import matplotlib.pyplot as plt
        fig=plt.figure(figsize=(14,5)); ax=fig.add_subplot(111)
        ax.plot(t,energy,label='energy'); ax.plot(t,transients,label='transient',alpha=.72); ax.plot(t,brightness,label='brightness',alpha=.55)
        for b in candidates[1:-1]:ax.axvline(b,linestyle='--',alpha=.35)
        ax.set_xlim(0,duration); ax.set_ylim(0,1.05); ax.set_xlabel('seconds'); ax.set_title(f'Audio edit map — {Path(a.audio).name} — tempo ~{tempo:.1f} BPM'); ax.legend(loc='upper right')
        fig.tight_layout(); fig.savefig(a.png_out,dpi=150); plt.close(fig)

if __name__=='__main__':main()
