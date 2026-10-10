"""Source-locked WAV/ONNX-driven, bounded controls for visual FX. No timeline changes."""
from __future__ import annotations
import hashlib, json, wave
from pathlib import Path
import numpy as np

def sha256_file(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
    return h.hexdigest()

class MusicFXDynamics:
    def __init__(self,audio_path,beat_path,expected_beat_sha,fps):
        self.audio_path=Path(audio_path);self.beat_path=Path(beat_path);self.fps=int(fps)
        if self.fps<=0:raise ValueError("invalid FPS")
        if sha256_file(self.beat_path)!=expected_beat_sha:raise ValueError("music evidence hash mismatch")
        evidence=json.loads(self.beat_path.read_text(encoding="utf-8"))
        if evidence.get("engine")!="beat_this_onnx" or evidence.get("model_resolution",{}).get("used_fallback"):
            raise ValueError("pinned Beat This ONNX required; no fallback")
        beats=evidence.get("beat_positions_seconds")
        if not isinstance(beats,list) or not beats:raise ValueError("nonempty ONNX beats required")
        self.beats=np.asarray(beats,dtype=np.float64)
        if not np.all(np.isfinite(self.beats)) or np.any(self.beats<0) or np.any(np.diff(self.beats)<=0):
            raise ValueError("invalid beat times")
        with wave.open(str(self.audio_path),"rb") as wav:
            rate=wav.getframerate()
            if wav.getsampwidth()!=2 or wav.getcomptype()!="NONE" or wav.getnchannels() not in (1,2):
                raise ValueError("only verified PCM16 mono/stereo WAV accepted")
            if rate%self.fps:raise ValueError("audio sample rate cannot exactly align to frames")
            chunk=(rate//self.fps)*wav.getnchannels()
            samples=np.frombuffer(wav.readframes(wav.getnframes()),dtype="<i2")
        count=len(samples)//chunk
        if count==0:raise ValueError("soundtrack shorter than one frame")
        values=samples[:count*chunk].astype(np.float32)/32768.0
        rms=np.sqrt(np.mean(values.reshape(count,chunk)**2,axis=1))
        rms=np.convolve(rms,np.asarray([1,2,3,4,3,2,1],dtype=np.float32)/16.0,mode="same")
        lo,hi=np.percentile(rms,[12,90])
        self.energy=(.22+.46*np.clip((rms-lo)/max(float(hi-lo),.00001),0,1)).astype(np.float32)
        self.evidence_sha=expected_beat_sha
        self.audio_sha=sha256_file(self.audio_path)
    def window(self,start_seconds,frame_count):
        start=round(float(start_seconds)*self.fps)
        if abs(start/self.fps-float(start_seconds))>1e-5:raise ValueError("shard not frame aligned")
        if start<0 or frame_count<1 or start+frame_count>len(self.energy):raise ValueError("soundtrack not covering shard")
        t=(start+np.arange(frame_count,dtype=np.float64))/self.fps
        near=np.searchsorted(self.beats,t)
        dist=np.full(frame_count,np.inf)
        use=near<len(self.beats)
        dist[use]=np.minimum(dist[use],abs(t[use]-self.beats[near[use]]))
        use=near>0
        dist[use]=np.minimum(dist[use],abs(t[use]-self.beats[near[use]-1]))
        transient=.06+.42*np.exp(-.5*(dist/.075)**2)
        return np.column_stack((self.energy[start:start+frame_count],transient)).astype(np.float32)
    def receipt(self,start_seconds,values):
        return {"schema":"aivideoedit.director-music-fx-dynamics.v1",
                "source_wav_sha256":self.audio_sha,"onnx_evidence_sha256":self.evidence_sha,
                "fps":self.fps,"start_seconds":float(start_seconds),"frame_count":len(values),
                "energy_min":float(values[:,0].min()),"energy_max":float(values[:,0].max()),
                "energy_std":float(values[:,0].std()),"transient_min":float(values[:,1].min()),
                "transient_max":float(values[:,1].max()),"transient_std":float(values[:,1].std()),
                "limits":{"energy":[.22,.68],"transient":[.06,.48]},
                "human_visual_approval":False,
                "note":"Measured FX controls only. A director must inspect visual frames before release."}
