#!/usr/bin/env python3
"""Explicit Director Brain v3 operating-order configuration.

V2 is enabled only after the current user/agent supplies real direction authority,
production mode, mission and next action. No creative defaults are invented.
"""
from __future__ import annotations
import json
from pathlib import Path
import server as base
import production_project
from core_adapter import CORE

def _read(path,default):
    try:return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:return default

def _write(path,payload):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def _project(pid):
    current=production_project.status(pid)
    if not current.get("initialized"):raise RuntimeError("production workspace is not initialized")
    return current,Path(current["engine_root"]),Path(current["project_dir"])
def _modes():
    status=CORE.status()
    if not status.get("bootstrapped"):raise RuntimeError("canonical core is not loaded")
    path=Path(status.get("os_root") or "")/"general/reusable/PRODUCTION_MODES.json"
    data=_read(path,{})
    if data.get("schema") not in {"aivideoedit.production-modes.v1","aivideoedit.production-modes.v2"}:raise RuntimeError("canonical production modes are unavailable")
    return data
def configure(pid,*,direction_authority:str,production_mode:str,mission:str,current_user_direction:str,exact_next_action:str):
    current,engine,project_dir=_project(pid)
    if current.get("stage") not in {"REFERENCES_ANALYZED","APPROACH_ESTABLISHED"}:raise RuntimeError("Director Brain v3 must be configured during creative-direction setup")
    modes=_modes();authority=str(direction_authority or "").strip();mode=str(production_mode or "").strip()
    if authority not in set(modes.get("direction_authorities",[])):raise ValueError("invalid direction_authority")
    if mode not in set((modes.get("production_modes") or {}).keys()):raise ValueError("invalid production_mode")
    mission=str(mission or "").strip();direction=str(current_user_direction or "").strip();next_action=str(exact_next_action or "").strip()
    if not mission or not direction or not next_action:raise ValueError("mission, current_user_direction, and exact_next_action are required")
    # For a no-reference selected route, the selected route(s) must have explicit modes
    # and they must be compatible with the declared overall mode.
    plan=_read(project_dir/"MEDIA_PLAN.json",{});gate=plan.get("visual_direction_gate") if isinstance(plan.get("visual_direction_gate"),dict) else None
    if gate and gate.get("locked"):
        selection=gate.get("user_selection") or {};numbers=set(selection.get("selected_option_numbers") or []);options=[x for x in gate.get("options",[]) if isinstance(x,dict) and x.get("number") in numbers]
        missing=[str(x.get("number")) for x in options if x.get("production_mode") not in {"living_scene","cinematic","hybrid"}]
        if missing:raise RuntimeError("selected visual route(s) need production_mode before enabling Director Brain v3: "+", ".join(missing))
        selected_modes={x.get("production_mode") for x in options}
        if mode!="hybrid" and any(x!=mode for x in selected_modes):raise RuntimeError("overall production_mode conflicts with selected visual route")
    order={"schema":"aivideoedit.operating-order.v1","mission":mission,"current_user_direction":direction,"exact_next_action":next_action,"direction_authority":authority,"production_mode":mode,"canon_lock":{"locked":False,"picture_language":None,"items":[]},"accepted_baseline":{"status":"none","file_or_locator":None,"sha256":None,"user_acceptance_statement":None},"refinement_scope":{"active":False,"goal":None,"allowed_changes":[],"forbidden_changes":[],"restart_authorized":False},"configured_at":base.now(),"authority_source":"explicit_current_user_or_agent_input"}
    order_path=project_dir/"OPERATING_ORDER.json";_write(order_path,order)
    state_path=project_dir/"PROJECT_STATE.json";state=_read(state_path,{});state["director_brain_version"]=3;state["direction_authority_resolved"]=True;state["production_mode_resolved"]=True;state["production_mode"]=mode;state["direction_authority"]=authority;_write(state_path,state)
    commit=production_project._git_commit_paths(engine,[order_path,state_path],"Enable Director Brain v3 operating order");production_project._clear_guard_marker(engine)
    guard=production_project.run_guard(pid)
    if not guard.get("guard_pass"):
        raise RuntimeError("Director Brain v3 operating order was recorded but canonical guard rejected current project state: "+str(guard.get("stderr") or guard.get("stdout") or "unknown")[-1800:])
    return {**status(pid),"commit":commit,"guard":"PASS"}
def update_next_action(pid,*,exact_next_action:str,current_user_direction:str=""):
    current,engine,project_dir=_project(pid);order_path=project_dir/"OPERATING_ORDER.json";order=_read(order_path,{})
    if order.get("schema")!="aivideoedit.operating-order.v1":raise RuntimeError("Director Brain v3 operating order is not configured")
    action=str(exact_next_action or "").strip()
    if not action:raise ValueError("exact_next_action is required")
    order["exact_next_action"]=action
    if str(current_user_direction or "").strip():order["current_user_direction"]=str(current_user_direction).strip()
    order["updated_at"]=base.now();_write(order_path,order);commit=production_project._git_commit_paths(engine,[order_path],"Update Director Brain operating order");production_project._clear_guard_marker(engine);return {**status(pid),"commit":commit}
def lock_canon(pid,*,picture_language:str,items:list[str],baseline_asset_id:str="",acceptance_statement:str=""):
    current,engine,project_dir=_project(pid);order_path=project_dir/"OPERATING_ORDER.json";order=_read(order_path,{})
    if order.get("schema")!="aivideoedit.operating-order.v1":raise RuntimeError("Director Brain v3 operating order is not configured")
    language=str(picture_language or "").strip();canon_items=[str(x).strip() for x in items if str(x).strip()]
    if not language or not canon_items:raise ValueError("picture_language and at least one canon item are required")
    order["canon_lock"]={"locked":True,"picture_language":language,"items":canon_items,"locked_at":base.now()}
    aid=str(baseline_asset_id or "").strip()
    if aid:
        statement=str(acceptance_statement or "").strip()
        if not statement:raise ValueError("baseline acceptance_statement is required")
        with base.LOCK:
            asset=base.find_asset(aid);asset=dict(asset) if asset else None
        if not asset or asset.get("project")!=pid or asset.get("status")!="ready" or not asset.get("sha256"):raise ValueError("accepted baseline asset must be a ready hashed project asset")
        order["accepted_baseline"]={"status":"accepted","file_or_locator":f"aive://asset/{aid}","sha256":asset.get("sha256"),"user_acceptance_statement":statement,"asset_id":aid,"accepted_at":base.now()}
    _write(order_path,order);commit=production_project._git_commit_paths(engine,[order_path],"Lock Director Brain visual canon");production_project._clear_guard_marker(engine);return {**status(pid),"commit":commit}
def set_refinement(pid,*,goal:str,allowed_changes:list[str],forbidden_changes:list[str],restart_authorized:bool=False):
    current,engine,project_dir=_project(pid);order_path=project_dir/"OPERATING_ORDER.json";order=_read(order_path,{})
    if (order.get("accepted_baseline") or {}).get("status")!="accepted":raise RuntimeError("refinement scope requires an accepted baseline")
    goal=str(goal or "").strip();allowed=[str(x).strip() for x in allowed_changes if str(x).strip()];forbidden=[str(x).strip() for x in forbidden_changes if str(x).strip()]
    if not goal or not allowed or not forbidden:raise ValueError("goal, allowed_changes, and forbidden_changes are required")
    order["refinement_scope"]={"active":True,"goal":goal,"allowed_changes":allowed,"forbidden_changes":forbidden,"restart_authorized":bool(restart_authorized),"updated_at":base.now()};_write(order_path,order);commit=production_project._git_commit_paths(engine,[order_path],"Set bounded Director Brain refinement scope");production_project._clear_guard_marker(engine);return {**status(pid),"commit":commit}
def status(pid):
    current,_engine,project_dir=_project(pid);order=_read(project_dir/"OPERATING_ORDER.json",{});state=_read(project_dir/"PROJECT_STATE.json",{})
    return {**current,"director_brain_version":int(state.get("director_brain_version") or 0),"configured":order.get("schema")=="aivideoedit.operating-order.v1","direction_authority":order.get("direction_authority"),"production_mode":order.get("production_mode"),"mission":order.get("mission"),"current_user_direction":order.get("current_user_direction"),"exact_next_action":order.get("exact_next_action"),"canon_lock":order.get("canon_lock"),"accepted_baseline":order.get("accepted_baseline"),"refinement_scope":order.get("refinement_scope"),"available_modes":_modes()}
