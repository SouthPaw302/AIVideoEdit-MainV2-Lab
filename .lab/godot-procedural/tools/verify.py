#!/usr/bin/env python3
"""Fail closed on generated Godot movies, frame coverage, music, and source hashes."""
import hashlib,json,subprocess,sys
from pathlib import Path
root=Path(sys.argv[1])
lock=json.loads((root/"source-lock.json").read_text())
controls=json.loads((root/"audio_drive.json").read_text())
def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for block in iter(lambda:f.read(1048576),b""):h.update(block)
    return h.hexdigest()
def probe(p):
    return json.loads(subprocess.run(["ffprobe","-v","error","-show_format","-show_streams","-of","json",str(p)],capture_output=True,text=True,check=True).stdout)
out={}
for name in ["godot","mainv2_fx"]:
    p=root/(name+".mp4")
    if not p.is_file():raise SystemExit("Absent real video "+str(p))
    inf=probe(p)
    vv=[x for x in inf["streams"] if x["codec_type"]=="video"]
    aa=[x for x in inf["streams"] if x["codec_type"]=="audio"]
    if len(vv)!=1 or len(aa)!=1:raise SystemExit("Encoded movie lacks real video or original music stream")
    if (vv[0]["width"],vv[0]["height"])!=(960,540):raise SystemExit("Wrong scene geometry")
    if int(vv[0].get("nb_frames",0))!=336:raise SystemExit("Missing movie frames")
    if abs(float(inf["format"]["duration"])-14)>0.15:raise SystemExit("Bad movie length")
    out[name]={"sha256":sha(p),"bytes":p.stat().st_size,"frames":336,"width":960,"height":540,
        "fps":24,"video_codec":vv[0]["codec_name"],"audio_codec":aa[0]["codec_name"],
        "duration":float(inf["format"]["duration"])}
report={"schema":"aive.godot.authored-film.technical-proof.v1","status":"TECHNICAL_PROOF_PASS",
    "source_repository":lock["source_repository"],"source_media":lock,"output":out,
    "audio_window_start":controls["start_seconds"],"audio_controls":"measured 24Hz PCM RMS/onset",
    "visual_acceptance":"PENDING_HUMAN_REVIEW",
    "production_acceptance":False,
    "limitations":["Real geometry via procedural Godot 3D; no original visual asset","Unapproved experimental new film",
    "Software OpenGL rendering, not GPU/4K performance evidence",
    "Exact production backend equivalence not demonstrated"]}
(root/"technical_report.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))