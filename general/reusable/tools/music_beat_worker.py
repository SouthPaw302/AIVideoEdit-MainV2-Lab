#!/usr/bin/env python3
"""Bounded music/beat evidence worker with optional Beat This ONNX inference."""
from __future__ import annotations

import math
import shutil
import subprocess
import tempfile
import wave
from array import array
from pathlib import Path
from typing import Any

from general.reusable.tools.model_registry import ModelRegistry

SR = 22050
N_FFT = 1024
HOP = 441
N_MELS = 128
F_MIN = 30.0
F_MAX = 11000.0
CHUNK = 1500
BORDER = 6
FPS = SR / HOP


def _read_wav_mono(path: Path) -> tuple[list[float], int]:
    with wave.open(str(path), "rb") as wf:
        channels = wf.getnchannels()
        width = wf.getsampwidth()
        rate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())
    if width != 2:
        raise ValueError("worker expects 16-bit PCM WAV after decoding")
    samples = array("h")
    samples.frombytes(frames)
    if channels == 1:
        mono = [float(x) / 32768.0 for x in samples]
    else:
        mono = []
        for i in range(0, len(samples), channels):
            frame = samples[i:i + channels]
            mono.append(sum(frame) / (32768.0 * len(frame)))
    return mono, rate


def _decode(path: Path) -> tuple[list[float], int]:
    try:
        samples, rate = _read_wav_mono(path)
        if rate == SR:
            return samples, rate
    except (wave.Error, ValueError, EOFError):
        pass
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is required for non-22050Hz PCM WAV input")
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        out = Path(tmp.name)
    try:
        p = subprocess.run(
            ["ffmpeg","-hide_banner","-loglevel","error","-y","-i",str(path),
             "-vn","-ac","1","-ar",str(SR),"-c:a","pcm_s16le",str(out)],
            capture_output=True,text=True,check=False,
        )
        if p.returncode != 0:
            raise RuntimeError("ffmpeg decode failed: " + p.stderr.strip())
        return _read_wav_mono(out)
    finally:
        out.unlink(missing_ok=True)


def _hz_to_mel(hz):
    import numpy as np
    hz = np.asarray(hz, dtype=np.float64)
    f_sp = 200.0 / 3.0
    mels = hz / f_sp
    min_log_hz = 1000.0
    min_log_mel = min_log_hz / f_sp
    logstep = np.log(6.4) / 27.0
    return np.where(hz >= min_log_hz,
                    min_log_mel + np.log(np.maximum(hz,1e-12)/min_log_hz)/logstep,
                    mels)


def _mel_to_hz(mel):
    import numpy as np
    mel = np.asarray(mel, dtype=np.float64)
    f_sp = 200.0 / 3.0
    hz = f_sp * mel
    min_log_hz = 1000.0
    min_log_mel = min_log_hz / f_sp
    logstep = np.log(6.4) / 27.0
    return np.where(mel >= min_log_mel,
                    min_log_hz * np.exp(logstep * (mel-min_log_mel)), hz)


def _filterbank():
    import numpy as np
    mel_points = np.linspace(float(_hz_to_mel(F_MIN)), float(_hz_to_mel(F_MAX)), N_MELS + 2)
    hz_points = _mel_to_hz(mel_points)
    freqs = np.arange(N_FFT // 2 + 1, dtype=np.float64) * (SR / N_FFT)
    left, center, right = hz_points[:-2], hz_points[1:-1], hz_points[2:]
    up = (freqs[:,None]-left[None,:]) / np.maximum(center-left,1e-12)[None,:]
    down = (right[None,:]-freqs[:,None]) / np.maximum(right-center,1e-12)[None,:]
    return np.maximum(0.0, np.minimum(up,down)).astype(np.float32)


def mel_spectrogram(samples: list[float]):
    import numpy as np
    audio=np.asarray(samples,dtype=np.float32)
    pad=N_FFT//2
    padded=np.pad(audio,(pad,pad),mode="reflect")
    count=1+(len(padded)-N_FFT)//HOP
    window=(0.5*(1.0-np.cos(2*np.pi*np.arange(N_FFT,dtype=np.float32)/N_FFT))).astype(np.float32)
    frames=np.empty((count,N_FFT),dtype=np.float32)
    for i in range(count):
        start=i*HOP
        frames[i]=padded[start:start+N_FFT]*window
    spectrum=np.abs(np.fft.rfft(frames,axis=1)).astype(np.float32)/math.sqrt(N_FFT)
    mel=spectrum@_filterbank()
    return np.log1p(1000.0*np.maximum(mel,1e-10)).astype(np.float32)


def _chunk_starts(length: int) -> list[int]:
    starts=list(range(-BORDER,length-BORDER,CHUNK-2*BORDER))
    if not starts:
        starts=[-BORDER]
    if length > CHUNK-2*BORDER:
        starts[-1]=length-(CHUNK-BORDER)
    return starts


def _split(spect):
    import numpy as np
    result=[]
    starts=_chunk_starts(len(spect))
    for start in starts:
        a=max(0,start); b=min(start+CHUNK,len(spect))
        cur=spect[a:b]
        lp=max(0,-start); rp=max(0,min(BORDER,start+CHUNK-len(spect)))
        if lp or rp:
            cur=np.pad(cur,((lp,rp),(0,0)),mode="constant")
        result.append(cur.astype(np.float32,copy=False))
    return starts,result


def _infer(spect, session):
    import numpy as np
    starts,chunks=_split(spect)
    preds=[]
    for chunk in chunks:
        out=session.run(["beat","downbeat"],{"input_spectrogram":chunk[None,:,:].astype(np.float32,copy=False)})
        preds.append((np.asarray(out[0]).reshape(-1),np.asarray(out[1]).reshape(-1)))
    beat=np.full(len(spect),-1000.0,dtype=np.float32)
    down=np.full(len(spect),-1000.0,dtype=np.float32)
    for idx in range(len(preds)-1,-1,-1):
        bc,dc=preds[idx]; start=starts[idx]
        begin,end=(BORDER,len(bc)-BORDER) if len(bc)>=2*BORDER else (0,len(bc))
        for j in range(begin,end):
            target=start+j
            if 0<=target<len(spect):
                beat[target]=bc[j]; down[target]=dc[j]
    return beat,down


def _dedupe(peaks:list[int],width:int=1)->list[int]:
    if not peaks:return []
    out=[]; p=float(peaks[0]); n=1
    for p2 in peaks[1:]:
        if p2-p<=width:
            n+=1; p+=(p2-p)/n
        else:
            out.append(int(math.floor(p+0.5))); p=float(p2); n=1
    out.append(int(math.floor(p+0.5)))
    return out


def _peak_frames(logits)->list[int]:
    values=[float(x) for x in logits]; peaks=[]
    for i,value in enumerate(values):
        left=max(0,i-3); right=min(len(values),i+4)
        if value>0 and value==max(values[left:right]):
            peaks.append(i)
    return _dedupe(peaks)


def _bpm(beats:list[float])->float|None:
    gaps=[b-a for a,b in zip(beats,beats[1:]) if 0.25<=b-a<=2.0]
    if not gaps:return None
    gaps.sort(); median=gaps[len(gaps)//2]
    bpm=60.0/median
    while bpm<60:bpm*=2
    while bpm>200:bpm/=2
    return round(bpm,2)


def _audio_controls(samples:list[float],rate:int)->dict[str,Any]:
    """Return bounded, time-varying RMS/flux controls measured from decoded PCM."""
    window=max(1,int(rate*.05))
    rms=[]
    for start in range(0,len(samples),window):
        chunk=samples[start:start+window]
        if chunk:rms.append(math.sqrt(sum(x*x for x in chunk)/len(chunk)))
    peak=max(rms) if rms else 0.0
    energy=[min(1.0,value/peak) if peak>1e-12 else 0.0 for value in rms]
    flux=[max(0.0,value-(energy[i-1] if i else 0.0)) for i,value in enumerate(energy)]
    flux_peak=max(flux) if flux else 0.0
    transient=[min(1.0,value/flux_peak) if flux_peak>1e-12 else 0.0 for value in flux]
    points=[
        {"seconds":round(i*window/rate,4),"energy":round(e,6),"transient":round(t,6)}
        for i,(e,t) in enumerate(zip(energy,transient))
    ]
    if len(points)==1:
        points.append({**points[0],"seconds":round(window/rate,4)})
    return {"source":"decoded_pcm_rms_flux","window_seconds":round(window/rate,6),"points":points}


def analyze_onnx(path:Path,model:Path)->dict[str,Any]:
    import onnxruntime as ort
    samples,rate=_decode(path)
    spect=mel_spectrogram(samples)
    session=ort.InferenceSession(str(model),providers=["CPUExecutionProvider"])
    inputs={x.name:x for x in session.get_inputs()}
    outputs={x.name:x for x in session.get_outputs()}
    if "input_spectrogram" not in inputs or not {"beat","downbeat"}.issubset(outputs):
        raise RuntimeError("Beat This ONNX signature mismatch")
    beat_logits,down_logits=_infer(spect,session)
    beat_frames=_peak_frames(beat_logits); down_frames=_peak_frames(down_logits)
    beats=[round(x/FPS,4) for x in beat_frames]
    downs=[round(x/FPS,4) for x in down_frames]
    if beats:
        downs=sorted(set(min(beats,key=lambda b:abs(b-d)) for d in downs))
    return {
        "schema":"aivideoedit.music-analysis-evidence.v1",
        "engine":"beat_this_onnx",
        "provider":"Beat This!",
        "providers":session.get_providers(),
        "sample_rate":rate,
        "bpm":_bpm(beats),
        "beat_positions_seconds":beats,
        "downbeat_positions_seconds":downs,
        "confidence":0.9 if len(beats)>=4 else 0.55,
        "authority":"evidence_only",
        "audio_controls":_audio_controls(samples,rate),
    }


def analyze_dsp(path:Path)->dict[str,Any]:
    samples,rate=_decode(path)
    hop=max(1,int(rate*0.01))
    env=[]
    for start in range(0,len(samples),hop):
        chunk=samples[start:start+hop]
        if chunk:
            env.append(math.sqrt(sum(x*x for x in chunk)/len(chunk)))
    avg=sum(env)/len(env) if env else 0.0
    peak=max(env) if env else 0.0
    threshold=avg+0.35*max(0.0,peak-avg)
    minimum=max(1,int(0.18/(hop/rate)))
    hits=[]; last=-minimum
    for i in range(1,len(env)-1):
        if env[i]>=threshold and env[i]>=env[i-1] and env[i]>env[i+1] and i-last>=minimum:
            hits.append(i); last=i
    beats=[round(i*(hop/rate),4) for i in hits]
    return {
        "schema":"aivideoedit.music-analysis-evidence.v1",
        "engine":"deterministic_micro_dsp",
        "sample_rate":rate,
        "bpm":_bpm(beats),
        "beat_positions_seconds":beats,
        "downbeat_positions_seconds":beats[::4],
        "confidence":0.75 if len(beats)>=4 else 0.35,
        "authority":"evidence_only",
        "audio_controls":_audio_controls(samples,rate),
    }


def analyze_music(path:str|Path, registry:ModelRegistry|None=None)->dict[str,Any]:
    path=Path(path)
    registry=registry or ModelRegistry.load()
    resolution=registry.resolve_capability("music_and_beat_analysis")
    if not resolution.available:
        raise RuntimeError(resolution.reason)
    if resolution.record.get("runtime")=="onnxruntime":
        evidence=analyze_onnx(path,Path(resolution.artifact_path or ""))
    else:
        evidence=analyze_dsp(path)
    evidence["model_resolution"]={
        "requested":resolution.requested,
        "resolved":resolution.resolved,
        "used_fallback":resolution.used_fallback,
        "reason":resolution.reason,
    }
    return evidence
