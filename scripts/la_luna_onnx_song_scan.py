#!/usr/bin/env python3
"""Full-song Beat This! ONNX evidence from source-verified mel features.

Do not replace the owner WAV, issue artistic approval, or alter the storyboard.
"""
from __future__ import annotations
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import onnxruntime as ort

from general.reusable.tools.model_registry import ModelRegistry
from general.reusable.tools.music_beat_worker import _infer, _peak_frames, _bpm, FPS

ROOT=Path(__file__).resolve().parents[1]
INPUT=ROOT/"projects/la-luna-de-florida/analysis_input"
OUT=Path("onnx-song-evidence")
SOURCE="La luna de Florida.wav"

def sha256(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def main()->int:
    manifest=json.loads((INPUT/"BEAT_THIS_INPUT_MANIFEST.json").read_text())
    assert manifest["song_source_sha256"]=="1a4bffef36930b504423d2653faff4cc5bfd9a15d44bdcf1083b27fbb0db1c10"
    pieces=[]
    for part in manifest["parts"]:
        zpath=INPUT/part["part_name"]
        with zipfile.ZipFile(zpath) as z:
            assert z.namelist()==[part["inner_name"]], z.namelist()
            chunk=z.read(part["inner_name"])
        assert len(chunk)==part["bytes"] and sha256(chunk)==part["sha256"], zpath
        pieces.append(chunk)
    payload=b"".join(pieces)
    assert len(payload)==manifest["whole_zip_bytes"] and sha256(payload)==manifest["whole_zip_sha256"]
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        assert z.namelist()==["la_luna_full_song_beat_this_mel_fp16.npz","la_luna_full_song_beat_this_mel_receipt.json"],z.namelist()
        npz=z.read("la_luna_full_song_beat_this_mel_fp16.npz")
        receipt=json.loads(z.read("la_luna_full_song_beat_this_mel_receipt.json"))
    assert sha256(npz)==receipt["npz_sha256"]
    assert receipt["audio_original_sha256"]==manifest["song_source_sha256"]
    assert receipt["model_id"]=="music-beat-onnx-v1"
    assert receipt["mel_preprocessing"]==manifest["mel_preprocessing"]
    with np.load(io.BytesIO(npz),allow_pickle=False) as arr:
        spect=arr["mel_fp16"].astype(np.float32)
    assert list(spect.shape)==receipt["mel_shape"]==[16059,128]
    assert np.isfinite(spect).all() and np.min(spect)>=0
    assert abs(spect.shape[0]/FPS-receipt["source_duration_seconds"])<.3

    registry=ModelRegistry.load(repo_root=ROOT)
    resolution=registry.resolve("music-beat-onnx-v1")
    assert resolution.available and not resolution.used_fallback and resolution.record["runtime"]=="onnxruntime",resolution
    session=ort.InferenceSession(str(resolution.artifact_path),providers=["CPUExecutionProvider"])
    assert session.get_providers()[0]=="CPUExecutionProvider",session.get_providers()
    assert "input_spectrogram" in [x.name for x in session.get_inputs()]
    assert {"beat","downbeat"}.issubset({x.name for x in session.get_outputs()})
    beats_logits,downbeats_logits=_infer(spect,session)
    beats=[round(i/FPS,4) for i in _peak_frames(beats_logits)]
    downs=[round(i/FPS,4) for i in _peak_frames(downbeats_logits)]
    if beats:
        downs=sorted(set(min(beats,key=lambda b:abs(b-d)) for d in downs))
    duration=receipt["source_duration_seconds"]
    beats=[t for t in beats if 0<=t<=duration+.02]
    downs=[t for t in downs if 0<=t<=duration+.02]
    if len(beats)<8:
        raise ValueError(f"ONNX detected only {len(beats)} beats in full song")
    bpm=_bpm(beats)
    if bpm is None:
        raise ValueError("ONNX returned no reliable BPM")
    OUT.mkdir(parents=True,exist_ok=True)
    result={
        "schema":"aivideoedit.song-onnx-beat-evidence.v1",
        "production":"la-luna-de-florida",
        "source_audio":{"name":SOURCE,"sha256":manifest["song_source_sha256"],"duration_seconds":duration,"sample_rate_hz":receipt["source_sample_rate"],"channels":receipt["source_channels"]},
        "analysis":{"engine":"beat_this_onnx","model_id":"music-beat-onnx-v1","provider":"Beat This!","providers":session.get_providers(),"model_pinned_git_blob_sha1":resolution.record["source_git_blob_sha1"],"feature_sha256":receipt["npz_sha256"],"feature_dtype_stored":"float16","feature_dtype_inference":"float32","quantization_caveat":receipt["quantization_caveat"],"feature_shape":list(spect.shape),"requested_model":resolution.requested,"resolved_model":resolution.resolved,"fallback_used":False},
        "rhythm":{"bpm":bpm,"beat_count":len(beats),"downbeat_count":len(downs),"beat_positions_seconds":beats,"downbeat_positions_seconds":downs},
        "authority":"evidence_only","creative_lock":False,"owner_release_approved":False,
        "note":"Mel extracted and sha256-verified from owner WAV before runner; this executes the original pinned ONNX model, not deterministic DSP fallback. Beat/downbeat estimates need Director alignment with lyrics and 50-shot storyboard."
    }
    full=OUT/"LA_LUNA_ONNX_MUSIC_ANALYSIS.json"
    full.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    summary={**{k:v for k,v in result.items() if k not in ("rhythm",)}, "rhythm":{"bpm":bpm,"beat_count":len(beats),"downbeat_count":len(downs),"first_ten_beats_seconds":beats[:10],"first_ten_downbeats_seconds":downs[:10]}, "complete_json_sha256":sha256(full.read_bytes())}
    (OUT/"LA_LUNA_ONNX_MUSIC_SUMMARY.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"result":"PASS","engine":"beat_this_onnx","provider":session.get_providers()[0],"bpm":bpm,"beats":len(beats),"downbeats":len(downs),"source_sha256":manifest["song_source_sha256"],"output_sha256":summary["complete_json_sha256"]},sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
