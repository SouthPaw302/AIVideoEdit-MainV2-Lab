#!/usr/bin/env python3
"""Final export QC: machine evidence first, explicit creative review second."""
from __future__ import annotations
import hashlib,json,shutil,subprocess
from pathlib import Path
import server as base
import production_project
import production_assembly
import production_fx

def _read(path,default):
    try:return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:return default
def _write(path,payload):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def _sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for c in iter(lambda:f.read(1024*1024),b""):h.update(c)
    return h.hexdigest()
def _project(pid):
    s=production_project.status(pid)
    if not s.get("initialized"):raise RuntimeError("production workspace is not initialized")
    return s,Path(s["engine_root"]),Path(s["project_dir"])
def _asset(asset_id):
    with base.LOCK:
        a=base.find_asset(str(asset_id));return dict(a) if a else None
def _run(cmd,timeout=1800):return subprocess.run(cmd,capture_output=True,text=True,timeout=timeout,check=False)
def run_technical(pid):
    current,engine,project_dir=_project(pid)
    if current.get("stage") not in {"ASSEMBLED","FINAL_QC_PASSED"}:raise RuntimeError("final QC requires ASSEMBLED stage")
    assembly=production_assembly.status(pid)
    if not assembly.get("assembly_complete") or not assembly.get("output_present"):raise RuntimeError("verified assembly artifact is required")
    live_fx=production_fx.verify(pid)
    if not live_fx.get("ok"):raise RuntimeError("current FX lock verification failed before final QC")
    record=assembly.get("assembly") or {};asset=_asset(record.get("output_asset_id"));path=Path((asset or {}).get("local_path") or "")
    if not path.is_file() or _sha(path)!=record.get("sha256"):raise RuntimeError("assembly output hash mismatch")
    ffmpeg=shutil.which("ffmpeg");ffprobe=shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:raise RuntimeError("FFmpeg and FFprobe are required for final QC")
    probe=_run([ffprobe,"-v","error","-show_format","-show_streams","-of","json",str(path)],120)
    if probe.returncode!=0:raise RuntimeError("final export decode probe failed")
    info=json.loads(probe.stdout);fmt=info.get("format",{});streams=info.get("streams",[]);video=next((x for x in streams if x.get("codec_type")=="video"),{});audio=next((x for x in streams if x.get("codec_type")=="audio"),{})
    script=_read(project_dir/"SCRIPT.json",{});target=float(script.get("duration_seconds") or 0);actual=float(fmt.get("duration") or 0);fps=float(script.get("target_fps") or 0)
    duration_ok=target>0 and abs(actual-target)<=max(0.20,2.0/max(fps,1.0))
    black=_run([ffmpeg,"-hide_banner","-i",str(path),"-vf","blackdetect=d=0.25:pix_th=0.10","-an","-f","null","-"],1800)
    freeze=_run([ffmpeg,"-hide_banner","-i",str(path),"-vf","freezedetect=n=-55dB:d=1.5","-an","-f","null","-"],1800)
    black_events=[line.strip() for line in (black.stderr or "").splitlines() if "black_start:" in line]
    freeze_events=[line.strip() for line in (freeze.stderr or "").splitlines() if "freeze_start:" in line or "freeze_duration:" in line]
    technical={"schema":"aivideoedit.final-qc.v1","assembly_asset_id":record.get("output_asset_id"),"assembly_sha256":record.get("sha256"),"script_sha256":_sha(project_dir/"SCRIPT.json"),"fx_lock_sha256":_sha(project_dir/"fx.lock.json"),"technical":{"decode_probe":"PASS" if probe.returncode==0 else "FAIL","duration_match":"PASS" if duration_ok else "FAIL","expected_duration_seconds":target,"actual_duration_seconds":round(actual,6),"video_present":bool(video),"audio_present":bool(audio),"black_events":black_events,"freeze_events":freeze_events,"black_check":"PASS" if black.returncode==0 and not black_events else "FAIL","freeze_check":"PASS" if freeze.returncode==0 and not freeze_events else "FAIL","dimensions":[video.get("width"),video.get("height")],"video_codec":video.get("codec_name"),"audio_codec":audio.get("codec_name"),"fx_lock_live_verified":True},"creative":{"status":"pending_review","verified_shot_ids":[],"mode_aware_checks":{},"acceptance_instruction":None},"technical_pass":bool(duration_ok and video and audio and black.returncode==0 and freeze.returncode==0 and not black_events and not freeze_events),"final_pass":False,"recorded_at":base.now()}
    qc_path=project_dir/"FINAL_QC.json";_write(qc_path,technical);state_path=project_dir/"PROJECT_STATE.json";state=_read(state_path,{});state["final_qc_passed"]=False;state["mode_aware_qc_passed"]=False;_write(state_path,state)
    md=project_dir/"QC.md";md.write_text("# Final QC\n\nTechnical pass: "+("PASS" if technical["technical_pass"] else "FAIL")+"\nCreative review: pending\n",encoding="utf-8")
    commit=production_project._git_commit_paths(engine,[qc_path,state_path,md],"Record technical final QC evidence");production_project._clear_guard_marker(engine)
    return {**status(pid),"commit":commit}
def accept_creative(pid,*,verified_shot_ids:list[str],mode_aware_checks:dict,instruction:str):
    current,engine,project_dir=_project(pid)
    if current.get("stage")!="ASSEMBLED":raise RuntimeError("creative final review requires ASSEMBLED stage")
    instruction=str(instruction or "").strip()
    if not instruction:raise ValueError("explicit final creative acceptance instruction is required")
    qc_path=project_dir/"FINAL_QC.json";qc=_read(qc_path,{})
    if not qc.get("technical_pass"):raise RuntimeError("technical final QC has not passed")
    script=_read(project_dir/"SCRIPT.json",{});expected=[str(x.get("shot_id")) for x in script.get("entries",[]) if isinstance(x,dict) and x.get("shot_id")]
    supplied=[str(x) for x in verified_shot_ids if str(x)]
    missing=[x for x in expected if x not in set(supplied)]
    if missing:raise RuntimeError("creative review must verify every scripted section: "+", ".join(missing))
    required=["scripted_visuals_present","production_mode_visible","no_placeholder_substitution","pacing_and_transitions_accepted","full_export_reviewed_normal_speed"]
    mode_aware_checks=mode_aware_checks if isinstance(mode_aware_checks,dict) else {};failed=[k for k in required if mode_aware_checks.get(k) is not True]
    if failed:raise RuntimeError("final creative checks not satisfied: "+", ".join(failed))
    # Ensure the exact assembly/script/FX evidence reviewed has not changed.
    assembly=production_assembly.status(pid).get("assembly") or {}
    if assembly.get("sha256")!=qc.get("assembly_sha256"):raise RuntimeError("assembly changed after technical QC")
    if _sha(project_dir/"SCRIPT.json")!=qc.get("script_sha256"):raise RuntimeError("script changed after technical QC")
    if _sha(project_dir/"fx.lock.json")!=qc.get("fx_lock_sha256"):raise RuntimeError("FX lock changed after technical QC")
    qc["creative"]={"status":"accepted","verified_shot_ids":supplied,"mode_aware_checks":{k:True for k in required},"acceptance_instruction":instruction,"reviewed_at":base.now()};qc["final_pass"]=True;_write(qc_path,qc)
    state_path=project_dir/"PROJECT_STATE.json";state=_read(state_path,{});state.update({"final_qc_passed":True,"mode_aware_qc_passed":True,"final_qc_acceptance_instruction":instruction,"final_qc_passed_at":base.now()});_write(state_path,state)
    (project_dir/"QC.md").write_text("# Final QC\n\nTechnical pass: PASS\nCreative review: ACCEPTED\n\n"+instruction+"\n",encoding="utf-8")
    commit=production_project._git_commit_paths(engine,[qc_path,state_path,project_dir/"QC.md"],"Accept final creative QC");production_project._clear_guard_marker(engine)
    return {**status(pid),"commit":commit}
def reject(pid,*,reason:str):
    current,engine,project_dir=_project(pid);reason=str(reason or "").strip()
    if not reason:raise ValueError("rejection reason is required")
    qc_path=project_dir/"FINAL_QC.json";qc=_read(qc_path,{"schema":"aivideoedit.final-qc.v1"});qc["creative"]={"status":"rejected","reason":reason,"rejected_at":base.now()};qc["final_pass"]=False;_write(qc_path,qc)
    state_path=project_dir/"PROJECT_STATE.json";state=_read(state_path,{})
    states=["INITIALIZED","SOURCE_INGESTED","REFERENCES_ANALYZED","APPROACH_ESTABLISHED","STORYBOARD_LOCKED","SHOT_PACKAGES_BUILT","SHOT_PROOFS_ACCEPTED","FX_LOCKED","ASSEMBLED","FINAL_QC_PASSED","ARCHIVED"]
    if state.get("stage") in states and states.index(state["stage"])>=states.index("FINAL_QC_PASSED"):state["stage"]="ASSEMBLED"
    state["final_qc_passed"]=False;state["mode_aware_qc_passed"]=False;state["archive_complete"]=False;state["last_final_rejection"]={"reason":reason,"at":base.now()};_write(state_path,state)
    commit=production_project._git_commit_paths(engine,[qc_path,state_path],"Reject final creative QC");production_project._clear_guard_marker(engine);return {**status(pid),"commit":commit}
def status(pid):
    current,_engine,project_dir=_project(pid);qc=_read(project_dir/"FINAL_QC.json",{});state=_read(project_dir/"PROJECT_STATE.json",{})
    return {**current,"technical_pass":bool(qc.get("technical_pass")),"creative_status":(qc.get("creative") or {}).get("status"),"final_pass":bool(qc.get("final_pass")) and bool(state.get("final_qc_passed")),"mode_aware_qc_passed":bool(state.get("mode_aware_qc_passed")),"qc":qc}
