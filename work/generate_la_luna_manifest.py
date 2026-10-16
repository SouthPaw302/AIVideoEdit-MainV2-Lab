import hashlib
import json
from pathlib import Path

repo = Path(r"E:/AIVideoEdit-MainV2-Lab")
stage = repo / "_staging_test"
preflight = json.loads((repo / "projects/la-luna-de-florida/MASTER_50_SHOT_SOURCE_PREFLIGHT.json").read_text())
base = "https://github.com/SouthPaw302/AIVideoEdit-MainV2-Lab/releases/download/la-luna-source-stage-20261016"

def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()

def find(name):
    matches = list((stage / "clips2").rglob(name)) + list((stage / "assembly_media").rglob(name))
    if len(matches) != 1:
        raise RuntimeError(f"expected one local source for {name}, found {len(matches)}")
    return matches[0]

def source(local, role):
    return {"url": f"{base}/{local.name}", "sha256": sha(local), "media_role": role}

shots = []
for item in preflight["shots"]:
    name = Path(item["original_entry"]).name
    local = find(name)
    fx = [{"id": "FX2-ATM-024"}] if item["shot_id"].startswith("B03-") else [{"id": "FX2-MOTION-003"}] if item["shot_id"].startswith("B05-") else [{"id": "FX2-LIGHT-023"}]
    shot = {"id": item["shot_id"], "source": source(local, "canonical_batch_scene_proof"), "media_role": "canonical_source_derived", "duration_seconds": 4.0, "fit": "cover", "fx": fx}
    shots.append(shot)

extras = [
    ("B01_MasterDirector_FX_Proof_RC2_CANDIDATE_12s.mp4", "B01-MASTER-FX", 12.0, "master_fx_proof"),
    ("B02_MasterDirector_FX_Proof_RC2_CANDIDATE_12s.mp4", "B02-MASTER-FX", 12.0, "master_fx_proof"),
    ("B03_MasterDirector_FX_Proof_RC2_CANDIDATE_12s.mp4", "B03-MASTER-FX", 12.0, "master_fx_proof"),
    ("B04_MasterDirector_FX_Proof_RC2_CANDIDATE_12s.mp4", "B04-MASTER-FX", 12.0, "master_fx_proof"),
    ("B05_MasterDirector_FX_Proof_RC2_CANDIDATE_12s.mp4", "B05-MASTER-FX", 12.0, "master_fx_proof"),
    ("B06-S01_GEMINI_REAL_MOTION_10s.mp4", "B06-S01-GEMINI", 10.0, "b06_gemini_real_motion"),
    ("B06-S10_GEMINI_REAL_MOTION_10s.mp4", "B06-S10-GEMINI", 10.0, "b06_gemini_real_motion"),
    ("B03-S07_MASTER_FX_LYRIC_REALIGNED_RC2_CANDIDATE.mp4", "B03-S07-LYRIC", 7.416667, "lyric_realigned_fx_candidate"),
    ("B05-S05_MASTER_FX_LYRIC_REALIGNED_RC2_CANDIDATE.mp4", "B05-S05-LYRIC", 3.708333, "lyric_realigned_fx_candidate"),
    ("B05-S08_SUNRISE_REALIGNED_MASTER_FX_RC2_CANDIDATE.mp4", "B05-S08-SUNRISE", 5.208333, "sunrise_realigned_fx_candidate"),
    ("B05-S09_SUNRISE_REALIGNED_MASTER_FX_RC2_CANDIDATE.mp4", "B05-S09-SUNRISE", 8.166667, "sunrise_realigned_fx_candidate"),
    ("B05_S08_S09_DIRECTOR_LYRIC_DAWN_SEQUENCE_321f_RC2_CANDIDATE.mp4", "B05-DAWN-SEQUENCE", 13.375, "director_dawn_sequence"),
    ("B06-S02_MOVING_96f.mp4", "B06-S02-MOVING", 3.291667, "b06_moving_insert"),
]
for name, ident, duration, role in extras:
    local = find(name)
    shots.append({"id": ident, "source": source(local, role), "media_role": "real_source", "duration_seconds": duration, "fit": "cover", "fx": []})

for i, shot in enumerate(shots[:-1]):
    # The native shard planner validates each 8-shot slice independently;
    # leave every shard terminal clean while retaining one-frame transitions
    # throughout the interior of each slice.
    if i % 8 == 7:
        continue
    shot["transition_out"] = "FX2-TRANS-025"
    shot["transition_seconds"] = 0.02
    if shot["id"] == "B01-S10": shot["transition_out"] = "FX2-TRANS-032"
    if shot["id"] == "B03-S10": shot["transition_out"] = "FX2-TRANS-030"
    if shot["id"] == "B04-S10": shot["transition_out"] = "FX2-TRANS-029"
    if shot["id"] == "B05-S10": shot["transition_out"] = "FX2-TRANS-022"

audio = stage / "La_Luna_original.wav"
manifest = {
    "schema": "aivideoedit.real-render.v1",
    "production_id": "la-luna-de-florida-master-director-candidate-rc1",
    "render_authorization": "explicit_user_render_request",
    "director_review_status": "technical_candidate_render_requested_artistic_review_pending",
    "director_note": "Full-song candidate assembled from byte-verified B01-B05 canonical media, Drive Master FX proof packages, B06 Gemini motion, lyric/dawn proof inserts, and approved native MainV2 FX/transition IDs. This is a candidate, not release approval.",
    "audio": {"url": f"{base}/{audio.name}", "sha256": sha(audio)},
    "output": {"fps": 24, "width": 960, "height": 540},
    "fx_seed": 302,
    "shots": shots,
}
out = repo / "projects/la-luna-de-florida/MASTER_FX_REAL_RENDER_RC1.json"
out.write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps({"path": str(out), "shots": len(shots), "frames": sum(round(float(s["duration_seconds"])*24) for s in shots), "seconds": sum(float(s["duration_seconds"]) for s in shots)}, indent=2))
