#!/usr/bin/env python3
"""Provider-neutral generated-media requests and canonical asset registration.

Generation requests are intent, not evidence. Only an existing ready + hashed
workstation asset can become canonical generated production media.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

import server as base
import production_project


def _read_json(path: Path, default):
    try:return json.loads(path.read_text(encoding="utf-8"))
    except Exception:return default

def _write_json(path: Path,payload)->None:
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def _project(project_id:str)->tuple[dict,Path,Path]:
    current=production_project.status(project_id)
    if not current.get("initialized"):raise RuntimeError("production workspace is not initialized")
    return current,Path(current["engine_root"]),Path(current["project_dir"])
def _requests_path(project_id:str)->Path:return base.PROJECT_ROOT/project_id/"generation_requests.json"
def _validate_shot_capability(project_dir:Path,shot_id:str,capability:str)->None:
    shot_id=str(shot_id or "").strip();capability=str(capability or "").strip()
    if not shot_id or not capability:raise ValueError("shot_id and capability are required")
    script=_read_json(project_dir/"SCRIPT.json",{})
    valid={str(x.get("shot_id")) for x in script.get("entries",[]) if isinstance(x,dict) and x.get("shot_id")}
    if shot_id not in valid:raise ValueError(f"unknown script shot: {shot_id}")
    plan=_read_json(project_dir/"MEDIA_PLAN.json",{});selected=set(plan.get("selected_capabilities",[])) if isinstance(plan.get("selected_capabilities"),list) else set()
    if capability not in selected:raise ValueError(f"capability is not selected in MEDIA_PLAN: {capability}")
def request_generation(project_id:str,*,shot_id:str,capability:str,prompt:str,provider_hint:str="",notes:str="")->dict:
    current,_engine,project_dir=_project(project_id)
    if current.get("stage") not in {"STORYBOARD_LOCKED","SHOT_PACKAGES_BUILT"}:raise RuntimeError("generated media requests require STORYBOARD_LOCKED or SHOT_PACKAGES_BUILT stage")
    prompt=str(prompt or "").strip()
    if not prompt:raise ValueError("prompt is required")
    _validate_shot_capability(project_dir,shot_id,capability)
    path=_requests_path(project_id);data=_read_json(path,{"schema":"aivideoedit.generation-requests.v1","requests":[]})
    rec={"id":uuid.uuid4().hex[:12],"project_id":project_id,"shot_id":str(shot_id).strip(),"capability":str(capability).strip(),"prompt":prompt,"provider_hint":str(provider_hint or "").strip() or None,"notes":str(notes or "").strip() or None,"status":"requested","created_at":base.now(),"asset_id":None}
    data.setdefault("requests",[]).append(rec);_write_json(path,data);return {"ok":True,"request":rec}
def register_generated(project_id:str,*,asset_id:str,shot_id:str,capability:str,request_id:str="",provider:str="",model:str="",prompt:str="",role:str="generated_visual")->dict:
    current,engine,project_dir=_project(project_id)
    if current.get("stage") not in {"STORYBOARD_LOCKED","SHOT_PACKAGES_BUILT"}:raise RuntimeError("generated media registration requires STORYBOARD_LOCKED or SHOT_PACKAGES_BUILT stage")
    shot_id=str(shot_id or "").strip();capability=str(capability or "").strip();_validate_shot_capability(project_dir,shot_id,capability);request_id=str(request_id or "").strip()
    req_path=_requests_path(project_id);reqs=_read_json(req_path,{"schema":"aivideoedit.generation-requests.v1","requests":[]})
    if request_id:
        req=next((x for x in reqs.get("requests",[]) if isinstance(x,dict) and x.get("id")==request_id),None)
        if not req:raise ValueError("generation request not found")
        if req.get("shot_id")!=shot_id or req.get("capability")!=capability:raise ValueError("generation request does not match shot/capability")
        if req.get("status") not in {"requested","fulfilled"}:raise RuntimeError("generation request is not fulfillable")
    with base.LOCK:
        asset=base.find_asset(str(asset_id))
        if not asset or asset.get("project")!=project_id:raise ValueError("generated asset is not part of this project")
        if asset.get("status")!="ready" or not str(asset.get("sha256") or "").strip():raise RuntimeError("generated asset must exist, be ready, and have SHA-256 evidence")
        generation={"request_id":request_id or None,"shot_id":shot_id,"capability":capability,"provider":str(provider or "").strip() or None,"model":str(model or "").strip() or None,"prompt":str(prompt or "").strip() or None,"registered_at":base.now()}
        asset.update({"origin":"generated","kind":capability,"role":str(role or "generated_visual"),"generation":generation,"creative_status":"candidate","updated_at":base.now()});base.save_state();asset_copy=dict(asset)
    manifest_path=project_dir/"ASSET_MANIFEST.json";manifest=_read_json(manifest_path,{"schema":"aivideoedit.asset-manifest.v1","assets":[]});assets=manifest.get("assets",[]) if isinstance(manifest.get("assets"),list) else []
    record={"id":asset_copy.get("id"),"name":asset_copy.get("filename"),"uri":f"aive://asset/{asset_copy.get('id')}","sha256":asset_copy.get("sha256"),"content_type":asset_copy.get("content_type"),"size_bytes":asset_copy.get("size_bytes"),"status":"ready","origin":"generated","kind":capability,"role":str(role or "generated_visual"),"authority":"current_project_generated","generation":generation,"metadata":asset_copy.get("metadata") or {},"qc":asset_copy.get("qc") or {"status":"unchecked"},"creative_status":"candidate"}
    for i,old in enumerate(assets):
        if isinstance(old,dict) and str(old.get("id"))==str(asset_id):assets[i]=record;break
    else:assets.append(record)
    manifest["assets"]=assets;manifest["generated_media_updated_at"]=base.now();_write_json(manifest_path,manifest)
    if request_id:
        for req in reqs.get("requests",[]):
            if isinstance(req,dict) and req.get("id")==request_id:req.update({"status":"fulfilled","asset_id":asset_id,"fulfilled_at":base.now()})
        _write_json(req_path,reqs)
    commit=production_project._git_commit_paths(engine,[manifest_path],"Register generated production media evidence");production_project._clear_guard_marker(engine)
    return {"ok":True,"asset":base.public_asset(asset_copy),"manifest_record":record,"commit":commit}
def accept_generated(project_id:str,*,asset_id:str,instruction:str)->dict:
    current,engine,project_dir=_project(project_id);instruction=str(instruction or "").strip()
    if not instruction:raise ValueError("acceptance instruction is required")
    with base.LOCK:
        asset=base.find_asset(str(asset_id))
        if not asset or asset.get("project")!=project_id or asset.get("origin")!="generated":raise ValueError("generated asset not found in project")
        asset.update({"creative_status":"accepted","acceptance_instruction":instruction,"accepted_at":base.now(),"updated_at":base.now()});base.save_state()
    manifest_path=project_dir/"ASSET_MANIFEST.json";manifest=_read_json(manifest_path,{})
    for rec in manifest.get("assets",[]) if isinstance(manifest.get("assets"),list) else []:
        if isinstance(rec,dict) and str(rec.get("id"))==str(asset_id):rec.update({"creative_status":"accepted","acceptance_instruction":instruction,"accepted_at":base.now()})
    _write_json(manifest_path,manifest);commit=production_project._git_commit_paths(engine,[manifest_path],"Accept generated production media");production_project._clear_guard_marker(engine)
    return {"ok":True,"asset_id":asset_id,"creative_status":"accepted","commit":commit}
def _used_in_packages(project_dir:Path,asset_id:str)->bool:
    root=project_dir/"shot_packages"
    if not root.is_dir():return False
    for path in root.glob("*/package.json"):
        data=_read_json(path,{})
        for ev in data.get("media_evidence",[]) if isinstance(data.get("media_evidence"),list) else []:
            if isinstance(ev,dict) and str(ev.get("asset_id"))==str(asset_id):return True
    return False
def reject_generated(project_id:str,*,asset_id:str,reason:str)->dict:
    current,engine,project_dir=_project(project_id);reason=str(reason or "").strip()
    if not reason:raise ValueError("rejection reason is required")
    with base.LOCK:
        asset=base.find_asset(str(asset_id))
        if not asset or asset.get("project")!=project_id:raise ValueError("asset not found in project")
        asset.update({"creative_status":"rejected","rejection_reason":reason,"updated_at":base.now()});base.save_state()
    manifest_path=project_dir/"ASSET_MANIFEST.json";manifest=_read_json(manifest_path,{})
    for rec in manifest.get("assets",[]) if isinstance(manifest.get("assets"),list) else []:
        if isinstance(rec,dict) and str(rec.get("id"))==str(asset_id):rec.update({"creative_status":"rejected","rejection_reason":reason})
    _write_json(manifest_path,manifest);state_path=project_dir/"PROJECT_STATE.json";state=_read_json(state_path,{})
    states=["INITIALIZED","SOURCE_INGESTED","REFERENCES_ANALYZED","APPROACH_ESTABLISHED","STORYBOARD_LOCKED","SHOT_PACKAGES_BUILT","SHOT_PROOFS_ACCEPTED","FX_LOCKED","ASSEMBLED","FINAL_QC_PASSED","ARCHIVED"]
    used=_used_in_packages(project_dir,asset_id)
    if used and state.get("stage") in states and states.index(state["stage"])>=states.index("SHOT_PACKAGES_BUILT"):
        state["stage"]="STORYBOARD_LOCKED";state["shot_packages_built"]=False;state["media_evidence_verified"]=False
    for key in ["shot_proofs_accepted","mode_aware_proofs_accepted","fx_lock_verified","assembly_complete","final_qc_passed","mode_aware_qc_passed","archive_complete"]:state[key]=False
    state["last_creative_rejection"]={"asset_id":asset_id,"reason":reason,"affected_shot_packages":used,"at":base.now()};_write_json(state_path,state)
    commit=production_project._git_commit_paths(engine,[manifest_path,state_path],"Record generated media rejection and dependent rollback");production_project._clear_guard_marker(engine)
    return {"ok":True,"asset_id":asset_id,"creative_status":"rejected","rolled_back_to":state.get("stage") if used else None,"commit":commit}
def status(project_id:str)->dict:
    current,_engine,project_dir=_project(project_id);reqs=_read_json(_requests_path(project_id),{"requests":[]});manifest=_read_json(project_dir/"ASSET_MANIFEST.json",{"assets":[]});generated=[x for x in manifest.get("assets",[]) if isinstance(x,dict) and x.get("origin")=="generated"]
    return {**current,"requests":reqs.get("requests",[]),"generated_assets":generated,"requested_count":sum(1 for x in reqs.get("requests",[]) if isinstance(x,dict) and x.get("status")=="requested"),"generated_count":len(generated),"accepted_count":sum(1 for x in generated if x.get("creative_status")=="accepted"),"rejected_count":sum(1 for x in generated if x.get("creative_status")=="rejected")}
