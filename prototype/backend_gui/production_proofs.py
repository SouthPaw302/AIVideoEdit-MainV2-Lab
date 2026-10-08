#!/usr/bin/env python3
"""Real-media shot proofs and explicit creative acceptance."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
import server as base
import production_project
MODE_CHECKS={"living_scene":["internal_motion_visible","material_motion_independent","identity_stable","camera_restrained","loop_or_join_clean"],"cinematic":["story_action_readable","coverage_sufficient","continuity_controlled","shot_progression_present","pacing_music_directed"]}
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
def _proof_path(project_dir,shot_id):return project_dir/"shot_proofs"/f"{shot_id}.json"
def _effective_mode(project_dir,shot_id,requested=""):
    requested=str(requested or "").strip();script=_read(project_dir/"SCRIPT.json",{});entry=next((x for x in script.get("entries",[]) if isinstance(x,dict) and str(x.get("shot_id"))==shot_id),{});order=_read(project_dir/"OPERATING_ORDER.json",{});overall=str(order.get("production_mode") or "").strip()
    if overall=="hybrid":
        mode=str(entry.get("production_mode") or requested).strip()
        if mode not in {"living_scene","cinematic"}:raise ValueError("hybrid proof requires shot production_mode living_scene or cinematic")
        return mode
    if overall in {"living_scene","cinematic"}:return overall
    if requested in {"living_scene","cinematic"}:return requested
    return "cinematic"
def record_proof(project_id,*,shot_id,proof_asset_id,checks,production_mode="",notes=""):
    current,engine,project_dir=_project(project_id)
    if current.get("stage") not in {"SHOT_PACKAGES_BUILT","SHOT_PROOFS_ACCEPTED"}:raise RuntimeError("shot proofs require SHOT_PACKAGES_BUILT stage")
    shot_id=str(shot_id or "").strip();pkg_path=project_dir/"shot_packages"/shot_id/"package.json"
    if not shot_id or not pkg_path.is_file():raise ValueError("shot package not found")
    package=_read(pkg_path,{})
    if not package.get("media_evidence"):raise RuntimeError("shot package has no real media evidence")
    with base.LOCK:
        asset=base.find_asset(str(proof_asset_id))
        if not asset or asset.get("project")!=project_id:raise ValueError("proof asset is not part of this project")
        if asset.get("status")!="ready" or not asset.get("sha256"):raise RuntimeError("proof asset must be ready and hashed")
        if asset.get("creative_status")=="rejected":raise RuntimeError("rejected media cannot be used as a proof")
        meta=asset.get("metadata") or {};content=str(asset.get("content_type") or "")
        if not (content.startswith("video/") or meta.get("video_codec")):raise RuntimeError("shot proof must be temporal video media; a still image cannot prove motion behavior")
        duration=float(meta.get("duration_seconds") or 0)
        if duration<=0:raise RuntimeError("proof video has no measurable duration")
        proof_asset=dict(asset)
    mode=_effective_mode(project_dir,shot_id,production_mode);required=MODE_CHECKS[mode];checks=checks if isinstance(checks,dict) else {};missing=[k for k in required if checks.get(k) is not True]
    if missing:raise RuntimeError("mode-aware proof checks not satisfied: "+", ".join(missing))
    rec={"schema":"aivideoedit.shot-proof.v1","shot_id":shot_id,"production_mode":mode,"package_sha256":_sha(pkg_path),"proof_asset":{"asset_id":proof_asset_id,"uri":f"aive://asset/{proof_asset_id}","sha256":proof_asset.get("sha256"),"content_type":proof_asset.get("content_type"),"name":proof_asset.get("filename"),"duration_seconds":duration},"checks":{k:bool(checks.get(k)) for k in required},"technical_and_mode_checks_passed":True,"creative_status":"needs_review","notes":str(notes or "").strip(),"recorded_at":base.now()}
    path=_proof_path(project_dir,shot_id);_write(path,rec);state_path=project_dir/"PROJECT_STATE.json";state=_read(state_path,{});state["shot_proofs_accepted"]=False;state["mode_aware_proofs_accepted"]=False;_write(state_path,state);commit=production_project._git_commit_paths(engine,[path,state_path],f"Record proof for {shot_id}");production_project._clear_guard_marker(engine);return {"ok":True,"proof":rec,"commit":commit}
def accept_proof(project_id,*,shot_id,instruction):
    current,engine,project_dir=_project(project_id);instruction=str(instruction or "").strip()
    if not instruction:raise ValueError("explicit acceptance instruction is required")
    path=_proof_path(project_dir,str(shot_id or "").strip());rec=_read(path,{})
    if not rec.get("technical_and_mode_checks_passed"):raise RuntimeError("proof has not passed technical/mode checks")
    rec.update({"creative_status":"accepted","user_acceptance_statement":instruction,"accepted_at":base.now()});_write(path,rec);commit=production_project._git_commit_paths(engine,[path],f"Accept proof for {shot_id}");production_project._clear_guard_marker(engine);return {"ok":True,"proof":rec,"commit":commit}
def finalize_acceptance(project_id,*,instruction):
    current,engine,project_dir=_project(project_id);instruction=str(instruction or "").strip()
    if current.get("stage")!="SHOT_PACKAGES_BUILT":raise RuntimeError("proof acceptance finalization requires SHOT_PACKAGES_BUILT stage")
    if not instruction:raise ValueError("final proof-set acceptance instruction is required")
    packages=[p for p in (project_dir/"shot_packages").iterdir() if p.is_dir()] if (project_dir/"shot_packages").is_dir() else []
    if not packages:raise RuntimeError("no shot packages exist")
    missing=[];proofs=[]
    for pkg in packages:
        rec=_read(_proof_path(project_dir,pkg.name),{})
        if rec.get("creative_status")!="accepted" or not rec.get("technical_and_mode_checks_passed"):missing.append(pkg.name)
        else:
            current_hash=_sha(pkg/"package.json")
            if rec.get("package_sha256")!=current_hash:missing.append(pkg.name+" (package changed after proof)")
            else:proofs.append(rec)
    if missing:raise RuntimeError("all shot proofs must be explicitly accepted against current packages: "+", ".join(missing))
    state_path=project_dir/"PROJECT_STATE.json";state=_read(state_path,{});state.update({"shot_proofs_accepted":True,"mode_aware_proofs_accepted":True,"shot_proof_acceptance_instruction":instruction,"shot_proof_count":len(proofs),"shot_proofs_accepted_at":base.now()});_write(state_path,state);summary=project_dir/"shot_proofs"/"ACCEPTANCE.json";_write(summary,{"schema":"aivideoedit.shot-proof-acceptance.v1","accepted":True,"instruction":instruction,"shot_ids":[p.get("shot_id") for p in proofs],"accepted_at":base.now()});commit=production_project._git_commit_paths(engine,[state_path,summary],"Accept complete shot proof set");production_project._clear_guard_marker(engine);return {**status(project_id),"commit":commit}
def reject_proof(project_id,*,shot_id,reason):
    current,engine,project_dir=_project(project_id);reason=str(reason or "").strip();shot_id=str(shot_id or "").strip()
    if not reason:raise ValueError("rejection reason is required")
    path=_proof_path(project_dir,shot_id);rec=_read(path,{})
    if not rec:raise ValueError("proof not found")
    rec.update({"creative_status":"rejected","rejection_reason":reason,"rejected_at":base.now()});_write(path,rec);state_path=project_dir/"PROJECT_STATE.json";state=_read(state_path,{});states=["INITIALIZED","SOURCE_INGESTED","REFERENCES_ANALYZED","APPROACH_ESTABLISHED","STORYBOARD_LOCKED","SHOT_PACKAGES_BUILT","SHOT_PROOFS_ACCEPTED","FX_LOCKED","ASSEMBLED","FINAL_QC_PASSED","ARCHIVED"]
    if state.get("stage") in states and states.index(state["stage"])>=states.index("SHOT_PROOFS_ACCEPTED"):state["stage"]="SHOT_PACKAGES_BUILT"
    for key in ["shot_proofs_accepted","mode_aware_proofs_accepted","fx_lock_verified","assembly_complete","final_qc_passed","mode_aware_qc_passed","archive_complete"]:state[key]=False
    state["last_creative_rejection"]={"shot_id":shot_id,"reason":reason,"at":base.now()};_write(state_path,state);commit=production_project._git_commit_paths(engine,[path,state_path],f"Reject proof for {shot_id}");production_project._clear_guard_marker(engine);return {**status(project_id),"commit":commit}
def status(project_id):
    current,_engine,project_dir=_project(project_id);root=project_dir/"shot_proofs";proofs=[]
    if root.is_dir():
        for path in sorted(root.glob("*.json")):
            if path.name=="ACCEPTANCE.json":continue
            rec=_read(path,{})
            if rec:proofs.append({"shot_id":rec.get("shot_id"),"production_mode":rec.get("production_mode"),"creative_status":rec.get("creative_status"),"technical_and_mode_checks_passed":bool(rec.get("technical_and_mode_checks_passed")),"proof_asset":rec.get("proof_asset")})
    state=_read(project_dir/"PROJECT_STATE.json",{});return {**current,"proofs":proofs,"proof_count":len(proofs),"accepted_count":sum(1 for p in proofs if p.get("creative_status")=="accepted"),"rejected_count":sum(1 for p in proofs if p.get("creative_status")=="rejected"),"shot_proofs_accepted":bool(state.get("shot_proofs_accepted")),"mode_aware_proofs_accepted":bool(state.get("mode_aware_proofs_accepted"))}
