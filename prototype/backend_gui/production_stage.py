#!/usr/bin/env python3
"""Workstation preconditions layered in front of canonical stage advancement."""
from __future__ import annotations
import json
from pathlib import Path
import server as base
import production_project
import production_storyboard
import production_shots
import production_proofs
import production_fx
import production_assembly
import production_final_qc
import production_archive
from core_adapter import CORE

def _read_json(path,default):
    try:return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:return default

def _write_json(path,payload):Path(path).write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")

def _reference_policy_ok(refs,contract):
    problems=[];p=contract.get("reference_policy",{});ms=float(p.get("short_video_max_seconds",30));mf=int(p.get("short_video_max_frames",1800))
    for r in refs.get("videos",[]):
        n=str(r.get("name") or "video");d=float(r.get("duration_seconds") or 0);t=int(r.get("total_frames") or 0);e=int(r.get("extracted_frames") or 0);short=d<=ms and t<=mf
        if not r.get("analysis_complete"):problems.append(f"{n}: reference analysis incomplete")
        if short:
            if r.get("extraction_policy")!="all_frames" or e!=t or t<=0:problems.append(f"{n}: short reference requires all-frame evidence")
        else:
            if r.get("extraction_policy")!="meaningful_sampling":problems.append(f"{n}: long reference requires meaningful_sampling")
            if e<=0 or not r.get("sampling_description") or not r.get("coverage"):problems.append(f"{n}: long-reference sampling evidence incomplete")
    for r in refs.get("images",[]):
        if not r.get("analysis_complete"):problems.append(f"{r.get('name') or 'image'}: image inspection incomplete")
    return not problems,problems

def _validate_next_stage(current,target):
    states=CORE.production_contract().get("states",[]);cur=current.get("stage")
    if cur not in states:raise RuntimeError(f"current production stage is invalid: {cur}")
    if target not in states:raise ValueError(f"unknown production stage: {target}")
    i=states.index(cur);expected=states[i+1] if i+1<len(states) else None
    if target!=expected:raise ValueError(f"only the next stage may be requested; expected {expected or 'none'}")

def _generic_guarded_advance(project_id,target_stage,*,narrative=False):
    current=production_project.status(project_id);_validate_next_stage(current,target_stage)
    engine=Path(current["engine_root"]);project_dir=Path(current["project_dir"]);state_path=project_dir/"PROJECT_STATE.json";status_path=project_dir/"STATUS.md"
    old_state=state_path.read_text(encoding="utf-8");old_status=status_path.read_text(encoding="utf-8") if status_path.is_file() else ""
    state=_read_json(state_path,{});state["stage"]=target_stage;state["stage_requested_by"]="aivideoedit-workstation";state["stage_requested_at"]=base.now();_write_json(state_path,state)
    status_path.write_text(f"# Status\n\nStage: {target_stage}\n\nPending canonical guard verification.\n",encoding="utf-8");production_project._clear_guard_marker(engine)
    guard=production_project.run_guard(project_id);ng={"ok":True,"stdout":"","stderr":""}
    if guard.get("guard_pass") and narrative:ng=production_storyboard.run_narrative_guard(project_id)
    if not guard.get("guard_pass") or not ng.get("ok"):
        state_path.write_text(old_state,encoding="utf-8");status_path.write_text(old_status,encoding="utf-8");production_project._clear_guard_marker(engine)
        return {**production_project.status(project_id),"ok":False,"advanced":False,"requested_stage":target_stage,"guard_stdout":guard.get("stdout",""),"guard_stderr":guard.get("stderr",""),"narrative_stdout":ng.get("stdout",""),"narrative_stderr":ng.get("stderr",""),"error":"canonical guard rejected the requested stage"}
    status_path.write_text(f"# Status\n\nStage: {target_stage}\n\nCanonical production guard: PASS.\nCanonical narrative guard: {'PASS' if narrative else 'not required'}.\n",encoding="utf-8")
    commit=production_project._git_commit_paths(engine,[state_path,status_path],f"Advance production to {target_stage}");production_project._write_guard_marker(project_id)
    return {**production_project.status(project_id),"ok":True,"advanced":True,"requested_stage":target_stage,"commit":commit,"guard_stdout":guard.get("stdout",""),"narrative_stdout":ng.get("stdout","")}

def _validate_approach(project_dir):
    state=_read_json(project_dir/"PROJECT_STATE.json",{});plan=_read_json(project_dir/"MEDIA_PLAN.json",{});refs=_read_json(project_dir/"REFERENCE_MANIFEST.json",{"videos":[],"images":[]});problems=[]
    valid={str(x.get("id")) for x in CORE.capabilities() if isinstance(x,dict) and x.get("id")};selected=plan.get("selected_capabilities") if isinstance(plan.get("selected_capabilities"),list) else []
    if not selected:problems.append("select at least one canonical media capability")
    unknown=[str(x) for x in selected if str(x) not in valid]
    if unknown:problems.append("unknown media capabilities: "+", ".join(unknown))
    if not str(plan.get("approach_summary") or "").strip():problems.append("explicit approach summary is missing")
    if not state.get("media_plan_valid"):problems.append("media plan has not been validated")
    if not state.get("visual_approach_established"):problems.append("visual/media approach is not established")
    if not bool(refs.get("videos") or refs.get("images")):
        gate=plan.get("visual_direction_gate")
        if not isinstance(gate,dict):problems.append("no-reference production requires three visual-direction routes")
        else:
            opts=gate.get("options") if isinstance(gate.get("options"),list) else [];minimum=int(CORE.production_contract().get("reference_policy",{}).get("no_visual_reference_min_options",3))
            if len(opts)<minimum:problems.append(f"no-reference production requires at least {minimum} routes")
            if not gate.get("presented_in_chat"):problems.append("visual-direction routes have not been presented to the user")
            if not gate.get("locked"):problems.append("visual-direction selection is not locked")
            sel=gate.get("user_selection")
            if not isinstance(sel,dict) or not sel.get("selected_option_numbers"):problems.append("explicit user route selection is missing")
            if not str((sel or {}).get("recorded_user_instruction") or "").strip():problems.append("current user selection instruction is not recorded")
            if not plan.get("user_approach_established"):problems.append("user approach selection is not established")
    return state,plan,problems

def advance(project_id,target_stage):
    current=production_project.status(project_id)
    if not current.get("initialized"):raise RuntimeError("production workspace is not initialized")
    target_stage=str(target_stage or "").strip();_validate_next_stage(current,target_stage)
    if target_stage=="SOURCE_INGESTED":return production_project.advance(project_id,target_stage)
    project_dir=Path(current["project_dir"]);engine=Path(current["engine_root"])
    if target_stage=="REFERENCES_ANALYZED":
        state=_read_json(project_dir/"PROJECT_STATE.json",{});refs=_read_json(project_dir/"REFERENCE_MANIFEST.json",{"videos":[],"images":[]});music=_read_json(project_dir/"MUSIC_ANALYSIS.json",{});ok,problems=_reference_policy_ok(refs,CORE.production_contract())
        required={"reference_analysis_complete":bool(state.get("reference_analysis_complete")),"music_analysis_complete":bool(state.get("music_analysis_complete")) and bool(music.get("analysis_complete")),"lyrics_status_resolved":bool(state.get("lyrics_status_resolved")),"genre_authority_resolved":bool(state.get("genre_authority_resolved")),"reference_policy_satisfied":ok};missing=[k for k,v in required.items() if not v]
        if missing:raise RuntimeError("REFERENCES_ANALYZED gate is not satisfied: "+", ".join(missing)+(": "+"; ".join(problems[:6]) if problems else ""))
        state["reference_policy_satisfied"]=True;_write_json(project_dir/"PROJECT_STATE.json",state);production_project._git_commit_paths(engine,[project_dir/"PROJECT_STATE.json"],"Record reference-analysis gate evidence");production_project._clear_guard_marker(engine)
    if target_stage=="APPROACH_ESTABLISHED":
        state,_plan,problems=_validate_approach(project_dir)
        if problems:raise RuntimeError("APPROACH_ESTABLISHED gate is not satisfied: "+"; ".join(problems))
        state["visual_approach_established"]=True;state["media_plan_valid"]=True;_write_json(project_dir/"PROJECT_STATE.json",state);production_project._git_commit_paths(engine,[project_dir/"PROJECT_STATE.json"],"Record approach gate evidence");production_project._clear_guard_marker(engine)
    if target_stage=="STORYBOARD_LOCKED":
        board=production_storyboard.status(project_id);missing=[]
        if not board.get("storyboard_exists"):missing.append("storyboard is not authored")
        if not board.get("storyboard_locked"):missing.append("storyboard is not locked")
        if not board.get("script_locked"):missing.append("production script is not locked")
        if not board.get("entry_count"):missing.append("script has no entries")
        if missing:raise RuntimeError("STORYBOARD_LOCKED gate is not satisfied: "+"; ".join(missing))
        return _generic_guarded_advance(project_id,target_stage,narrative=True)
    if target_stage=="SHOT_PACKAGES_BUILT":
        shots=production_shots.status(project_id);missing=[]
        if not shots.get("package_count"):missing.append("no shot packages exist")
        if not shots.get("shot_packages_built"):missing.append("shot_packages_built evidence is false")
        if not shots.get("media_evidence_verified"):missing.append("real media evidence has not been verified")
        if any(int(x.get("media_evidence_count") or 0)<=0 for x in shots.get("packages",[])):missing.append("one or more shot packages have no media evidence")
        if any(bool(x.get("contains_rejected_media")) for x in shots.get("packages",[])):missing.append("one or more shot packages contain rejected media")
        if missing:raise RuntimeError("SHOT_PACKAGES_BUILT gate is not satisfied: "+"; ".join(missing))
        return _generic_guarded_advance(project_id,target_stage,narrative=True)
    if target_stage=="SHOT_PROOFS_ACCEPTED":
        proofs=production_proofs.status(project_id);shots=production_shots.status(project_id);missing=[];expected=int(shots.get("package_count") or 0)
        if expected<=0:missing.append("no shot packages exist")
        if int(proofs.get("proof_count") or 0)!=expected:missing.append(f"proof count {proofs.get('proof_count',0)} does not match package count {expected}")
        if int(proofs.get("accepted_count") or 0)!=expected:missing.append("every shot proof must be explicitly accepted")
        if int(proofs.get("rejected_count") or 0)>0:missing.append("rejected proofs remain")
        if not proofs.get("shot_proofs_accepted"):missing.append("proof set has not been finalized")
        if not proofs.get("mode_aware_proofs_accepted"):missing.append("mode-aware proof acceptance is incomplete")
        if missing:raise RuntimeError("SHOT_PROOFS_ACCEPTED gate is not satisfied: "+"; ".join(missing))
        return _generic_guarded_advance(project_id,target_stage,narrative=True)
    if target_stage=="FX_LOCKED":
        fx=production_fx.status(project_id);missing=[]
        if not fx.get("requirements_present"):missing.append("FX requirements are missing")
        if not fx.get("lock_present"):missing.append("fx.lock.json is missing")
        if fx.get("lock_result")!="PASS":missing.append("FX precompile lock does not contain PASS")
        if not fx.get("fx_lock_verified"):missing.append("FX lock has not been verified")
        if missing:raise RuntimeError("FX_LOCKED gate is not satisfied: "+"; ".join(missing))
        live=production_fx.verify(project_id)
        if not live.get("ok"):raise RuntimeError("FX_LOCKED live verification failed: "+str(live.get("stderr") or live.get("stdout") or live.get("error") or "unknown")[-1600:])
        return _generic_guarded_advance(project_id,target_stage,narrative=True)
    if target_stage=="ASSEMBLED":
        assembly=production_assembly.status(project_id);missing=[]
        if not assembly.get("assembly_complete"):missing.append("verified assembly is incomplete")
        if not assembly.get("output_present"):missing.append("assembly output artifact is missing or hash-invalid")
        if not (assembly.get("assembly") or {}).get("qc"):missing.append("assembly QC evidence is missing")
        if missing:raise RuntimeError("ASSEMBLED gate is not satisfied: "+"; ".join(missing))
        live=production_fx.verify(project_id)
        if not live.get("ok"):raise RuntimeError("ASSEMBLED requires current FX lock verification")
        return _generic_guarded_advance(project_id,target_stage,narrative=True)
    if target_stage=="FINAL_QC_PASSED":
        qc=production_final_qc.status(project_id);missing=[]
        if not qc.get("technical_pass"):missing.append("technical final QC has not passed")
        if qc.get("creative_status")!="accepted":missing.append("full export has not been creatively accepted")
        if not qc.get("final_pass"):missing.append("final QC evidence is incomplete")
        if not qc.get("mode_aware_qc_passed"):missing.append("mode-aware final QC has not passed")
        record=qc.get("qc") or {};assembly=production_assembly.status(project_id).get("assembly") or {}
        if assembly.get("sha256")!=record.get("assembly_sha256"):missing.append("assembly changed after final QC")
        if not (project_dir/"SCRIPT.json").is_file() or production_final_qc._sha(project_dir/"SCRIPT.json")!=record.get("script_sha256"):missing.append("script changed after final QC")
        if not (project_dir/"fx.lock.json").is_file() or production_final_qc._sha(project_dir/"fx.lock.json")!=record.get("fx_lock_sha256"):missing.append("FX lock changed after final QC")
        if missing:raise RuntimeError("FINAL_QC_PASSED gate is not satisfied: "+"; ".join(missing))
        return _generic_guarded_advance(project_id,target_stage,narrative=True)
    if target_stage=="ARCHIVED":
        archive=production_archive.status(project_id);missing=[]
        if not archive.get("archive_complete"):missing.append("archive manifest has not been built")
        if not archive.get("manifest_present"):missing.append("ARCHIVE_MANIFEST.json is missing")
        live=production_archive.verify(project_id)
        if not live.get("ok"):missing.extend(live.get("problems") or [live.get("error") or "archive verification failed"])
        if missing:raise RuntimeError("ARCHIVED gate is not satisfied: "+"; ".join(str(x) for x in missing))
        return _generic_guarded_advance(project_id,target_stage,narrative=True)
    return _generic_guarded_advance(project_id,target_stage)
