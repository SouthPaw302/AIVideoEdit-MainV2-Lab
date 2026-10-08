from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

from general.reusable.tools.music_beat_worker import analyze_dsp


def make_click_track(path:Path,bpm:float=120.0,duration:float=8.0,sr:int=22050):
    total=int(duration*sr)
    samples=[0.0]*total
    interval=int(sr*60.0/bpm)
    pulse=int(sr*0.04)
    for start in range(0,total,interval):
        for i in range(pulse):
            idx=start+i
            if idx>=total:break
            env=1.0-(i/pulse)
            samples[idx]+=0.8*env*math.sin(2*math.pi*90*i/sr)
    with wave.open(str(path),"wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
        wf.writeframes(b"".join(struct.pack("<h",max(-32767,min(32767,int(x*32767)))) for x in samples))


def test_deterministic_fallback_tracks_120_bpm(tmp_path:Path):
    audio=tmp_path/"click.wav"
    make_click_track(audio)
    evidence=analyze_dsp(audio)
    assert evidence["engine"]=="deterministic_micro_dsp"
    assert evidence["bpm"] is not None
    assert 115 <= evidence["bpm"] <= 125
    assert len(evidence["beat_positions_seconds"]) >= 10
    assert evidence["authority"]=="evidence_only"
