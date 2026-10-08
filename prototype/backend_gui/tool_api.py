#!/usr/bin/env python3
"""Provider-neutral Tool API for AIVideoEdit."""
from __future__ import annotations
from typing import Callable
from pathlib import Path
import os
import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import server as base
import storage
import production_project
import production_analysis
import production_stage
import production_approach
import production_storyboard
import production_shots
import production_generated
import production_proofs
import production_fx
import production_assembly
import production_final_qc
import production_archive
import runtime_gatekeeper
import operating_tools
from general.reusable.tools.jev_decision import decide as jev_decide
from core_adapter import CORE

TOOL_SCHEMAS=[
{"name":"core.status","description":"Show canonical AIVideoEdit OS/bootstrap status.","input_schema":{"type":"object","properties":{}}},
{"name":"core.bootstrap","description":"Install and attest an isolated exact current-main AIVideoEdit core.","input_schema":{"type":"object","properties":{"offline":{"type":"boolean"}}}},
{"name":"capabilities.list","description":"List canonical media capabilities from the bootstrapped OS.","input_schema":{"type":"object","properties":{}}},
{"name":"fx.list","description":"List reusable effects from the canonical FX registry.","input_schema":{"type":"object","properties":{}}},
{"name":"project.list","description":"List local workstation projects.","input_schema":{"type":"object","properties":{}}},
{"name":"project.create","description":"Create a local workstation project.","input_schema":{"type":"object","required":["name"],"properties":{"name":{"type":"string"}}}},
{"name":"project.status","description":"Return project media and QC summary.","input_schema":{"type":"object","required":["project_id"],"properties":{"project_id":{"type":"string"}}}},
{"name":"project.prepare","description":"Queue all missing preview, review-frame and QC work for a project.","input_schema":{"type":"object","required":["project_id"],"properties":{"project_id":{"type":"string"}}}},
{"name":"production.initialize","description":"Create an isolated canonical song-branch production workspace.","input_schema":{"type":"object","required":["project_id"],"properties":{"project_id":{"type":"string"}}}},
{"name":"production.status","description":"Show canonical production branch, stage, next stage, manifest sync state and guard status.","input_schema":{"type":"object","required":["project_id"],"properties":{"project_id":{"type":"string"}}}},
{"name":"production.sync_assets","description":"Sync workstation media into canonical manifests without advancing stage or claiming analysis.","input_schema":{"type":"object","required":["project_id"],"properties":{"project_id":{"type":"string"}}}},
{"name":"production.analyze","description":"Queue evidence-producing reference extraction and music signal analysis.","input_schema":{"type":"object","required":["project_id"],"properties":{"project_id":{"type":"string"}}}},
{"name":"production.set_music_context","description":"Record explicit lyrics status/text and genre authority.","input_schema":{"type":"object","required":["project_id","lyrics_status","genre"],"properties":{"project_id":{"type":"string"},"lyrics_status":{"type":"string","enum":["present","absent"]},"genre":{"type":"string"},"lyrics_text":{"type":"string"},"directing_use":{"type":"string"}}}},
{"name":"approach.status","description":"Show selected canonical capabilities and visual-direction gate state.","input_schema":{"type":"object","required":["project_id"],"properties":{"project_id":{"type":"string"}}}},
{"name":"approach.set_capabilities","description":"Record canonical media capabilities and an explicit production approach summary.","input_schema":{"type":"object","required":["project_id","capabilities","approach_summary"],"properties":{"project_id":{"type":"string"},"capabilities":{"type":"array","items":{"type":"string"}},"approach_summary":{"type":"string"}}}},
{"name":"approach.set_routes","description":"Record at least three distinct numbered no-reference visual routes with mini-storyboards.","input_schema":{"type":"object","required":["project_id","routes"],"properties":{"project_id":{"type":"string"},"routes":{"type":"array","items":{"type":"object"}},"presentation_channel":{"type":"string","enum":["chat","studio"]}}}},
{"name":"approach.select_route","description":"Lock the current user's selected visual route or hybrid.","input_schema":{"type":"object","required":["project_id","selected_option_numbers","recorded_user_instruction"],"properties":{"project_id":{"type":"string"},"selected_option_numbers":{"type":"array","items":{"type":"integer"}},"recorded_user_instruction":{"type":"string"},"status":{"type":"string","enum":["selected","hybrid"]}}}},
{"name":"storyboard.status","description":"Show authored storyboard/script coverage and lock state.","input_schema":{"type":"object","required":["project_id"],"properties":{"project_id":{"type":"string"}}}},
{"name":"storyboard.set","description":"Author a full-frame production storyboard/script from explicit user or agent creative decisions.","input_schema":{"type":"object","required":["project_id","entries"],"properties":{"project_id":{"type":"string"},"entries":{"type":"array","items":{"type":"object"}},"target_fps":{"type":"number"},"summary":{"type":"string"},"authority":{"type":"string"}}}},
{"name":"storyboard.lock","description":"Lock the authored storyboard and production script with a recorded instruction.","input_schema":{"type":"object","required":["project_id","recorded_instruction"],"properties":{"project_id":{"type":"string"},"recorded_instruction":{"type":"string"}}}},
{"name":"storyboard.guard","description":"Run the bootstrapped canonical narrative guard against the current project.","input_schema":{"type":"object","required":["project_id"],"properties":{"project_id":{"type":"string"}}}},
{"name":"shots.status","description":"Show shot package and media-evidence status.","input_schema":{"type":"object","required":["project_id"],"properties":{"project_id":{"type":"string"}}}},
{"name":"shots.template","description":"Return locked script shots plus usable real project assets and current assignments for the Shots UI.","input_schema":{"type":"object","required":["project_id"],"properties":{"project_id":{"type":"string"}}}},
{"name":"shots.build_packages","description":"Build one package per locked script shot using explicit real media asset assignments and hashes.","input_schema":{"type":"object","required":["project_id","assignments"],"properties":{"project_id":{"type":"string"},"assignments":{"type":"array","items":{"type":"object"}}}}},
{"name":"generated.status","description":"Show pending generation requests and registered generated production assets.","input_schema":{"type":"object","required":["project_id"],"properties":{"project_id":{"type":"string"}}}},
{"name":"generated.request","description":"Create a shot-scoped generation request. A request is intent only and does not count as media evidence.","input_schema":{"type":"object","required":["project_id","shot_id","capability","prompt"],"properties":{"project_id":{"type":"string"},"shot_id":{"type":"string"},"capability":{"type":"string"},"prompt":{"type":"string"},"provider_hint":{"type":"string"},"notes":{"type":"string"}}}},
{"name":"generated.register","description":"Register an existing ready + hashed project asset as generated production media with provenance.","input_schema":{"type":"object","required":["project_id","asset_id","shot_id","capability"],"properties":{"project_id":{"type":"string"},"asset_id":{"type":"string"},"shot_id":{"type":"string"},"capability":{"type":"string"},"request_id":{"type":"string"},"provider":{"type":"string"},"model":{"type":"string"},"prompt":{"type":"string"},"role":{"type":"string"}}}},
{"name":"generated.accept","description":"Record explicit creative acceptance of a generated production asset.","input_schema":{"type":"object","required":["project_id","asset_id","instruction"],"properties":{"project_id":{"type":"string"},"asset_id":{"type":"string"},"instruction":{"type":"string"}}}},
{"name":"generated.reject","description":"Record creative rejection and clear dependent proof/final-QC acceptance flags.","input_schema":{"type":"object","required":["project_id","asset_id","reason"],"properties":{"project_id":{"type":"string"},"asset_id":{"type":"string"},"reason":{"type":"string"}}}},
{"name":"proofs.status","description":"Show per-shot proof readiness and explicit creative acceptance status.","input_schema":{"type":"object","required":["project_id"],"properties":{"project_id":{"type":"string"}}}},
{"name":"proofs.record","description":"Bind a real proof video to a shot package and record required mode-aware checks.","input_schema":{"type":"object","required":["project_id","shot_id","proof_asset_id","checks"],"properties":{"project_id":{"type":"string"},"shot_id":{"type":"string"},"proof_asset_id":{"type":"string"},"checks":{"type":"object"},"production_mode":{"type":"string"},"notes":{"type":"string"}}}},
{"name":"proofs.accept","description":"Explicitly accept one proof after technical/mode checks pass.","input_schema":{"type":"object","required":["project_id","shot_id","instruction"],"properties":{"project_id":{"type":"string"},"shot_id":{"type":"string"},"instruction":{"type":"string"}}}},
{"name":"proofs.finalize","description":"Finalize the proof set only when every shot proof is independently accepted.","input_schema":{"type":"object","required":["project_id","instruction"],"properties":{"project_id":{"type":"string"},"instruction":{"type":"string"}}}},
{"name":"proofs.reject","description":"Reject a shot proof and roll dependent accepted production state back.","input_schema":{"type":"object","required":["project_id","shot_id","reason"],"properties":{"project_id":{"type":"string"},"shot_id":{"type":"string"},"reason":{"type":"string"}}}},
{"name":"fx.status","description":"Show FX requirements and immutable lock status.","input_schema":{"type":"object","required":["project_id"],"properties":{"project_id":{"type":"string"}}}},
{"name":"fx.registry","description":"List canonical FX with gate status and implementation class for project selection.","input_schema":{"type":"object","required":["project_id"],"properties":{"project_id":{"type":"string"}}}},
{"name":"fx.set_requirements","description":"Write production FX requirements using only canonical registered effects/transitions.","input_schema":{"type":"object","required":["project_id","effects","transitions"],"properties":{"project_id":{"type":"string"},"effects":{"type":"array","items":{"type":"object"}},"transitions":{"type":"array","items":{"type":"object"}},"seed":{"type":"integer"},"allow_conditional":{"type":"array","items":{"type":"string"}},"conditional_preflight":{"type":"object"}}}},
{"name":"fx.lock","description":"Run the canonical FX precompile gate, runtime smoke tests, write fx.lock.json, then verify it live.","input_schema":{"type":"object","required":["project_id"],"properties":{"project_id":{"type":"string"}}}},
{"name":"fx.verify","description":"Re-run live verification against the existing immutable FX lock.","input_schema":{"type":"object","required":["project_id"],"properties":{"project_id":{"type":"string"}}}},
{"name":"assembly.status","description":"Show verified assembled workprint status and browser-playable output asset.","input_schema":{"type":"object","required":["project_id"],"properties":{"project_id":{"type":"string"}}}},
{"name":"assembly.run","description":"Queue FFmpeg assembly of accepted proof videos against the locked script and source song.","input_schema":{"type":"object","required":["project_id"],"properties":{"project_id":{"type":"string"},"width":{"type":"integer"},"height":{"type":"integer"}}}},
{"name":"final_qc.status","description":"Show technical and creative final-QC state for the current assembly.","input_schema":{"type":"object","required":["project_id"],"properties":{"project_id":{"type":"string"}}}},
{"name":"final_qc.run_technical","description":"Run decode, duration, black/freeze, audio/video, hash, and FX-lock checks on the full assembly.","input_schema":{"type":"object","required":["project_id"],"properties":{"project_id":{"type":"string"}}}},
{"name":"final_qc.accept_creative","description":"Accept the full export only after every scripted section and required mode-aware visual check has been reviewed.","input_schema":{"type":"object","required":["project_id","verified_shot_ids","mode_aware_checks","instruction"],"properties":{"project_id":{"type":"string"},"verified_shot_ids":{"type":"array","items":{"type":"string"}},"mode_aware_checks":{"type":"object"},"instruction":{"type":"string"}}}},
{"name":"final_qc.reject","description":"Reject the final export and clear final/archive acceptance while preserving the assembled artifact for refinement.","input_schema":{"type":"object","required":["project_id","reason"],"properties":{"project_id":{"type":"string"},"reason":{"type":"string"}}}},
{"name":"archive.status","description":"Show content-addressed production archive state.","input_schema":{"type":"object","required":["project_id"],"properties":{"project_id":{"type":"string"}}}},
{"name":"archive.build","description":"Build a Git-friendly archive manifest containing hashes of production records and a pointer/hash for heavy final media.","input_schema":{"type":"object","required":["project_id"],"properties":{"project_id":{"type":"string"},"note":{"type":"string"}}}},
{"name":"archive.verify","description":"Re-hash archived production records and verify the final media still matches the archive manifest.","input_schema":{"type":"object","required":["project_id"],"properties":{"project_id":{"type":"string"}}}},
{"name":"production.guard","description":"Re-run the bootstrapped current-main production guard for a project.","input_schema":{"type":"object","required":["project_id"],"properties":{"project_id":{"type":"string"}}}},
{"name":"production.advance","description":"Request exactly the next canonical production stage. Workstation evidence and canonical guards must pass.","input_schema":{"type":"object","required":["project_id","target_stage"],"properties":{"project_id":{"type":"string"},"target_stage":{"type":"string"}}}},
{"name":"media.list","description":"List registered media assets for a project.","input_schema":{"type":"object","required":["project_id"],"properties":{"project_id":{"type":"string"}}}},
{"name":"media.prepare","description":"Queue one preparation operation for a registered asset.","input_schema":{"type":"object","required":["asset_id","operation"],"properties":{"asset_id":{"type":"string"},"operation":{"type":"string","enum":["make_proxy","extract_review_frames","qc_media"]}}}},
{"name":"storage.status","description":"Show local/external storage configuration.","input_schema":{"type":"object","properties":{}}},
{"name":"storage.sync","description":"Queue external backup for a project when storage is configured.","input_schema":{"type":"object","required":["project_id"],"properties":{"project_id":{"type":"string"}}}},]

def schemas():return TOOL_SCHEMAS

def _project(pid):
    p=base.find_project(pid)
    if not p:raise ValueError("project not found")
    return p

def _asset(aid):
    a=base.find_asset(aid)
    if not a:raise ValueError("asset not found")
    return a

def _create_project(name):
    clean=(name or "").strip()
    if not clean:raise ValueError("project name is required")
    root=base.slugify(clean);pid=root;n=2
    with base.LOCK:
        existing={p.get("id") for p in base.STATE["projects"]}
        while pid in existing:pid=f"{root}-{n}";n+=1
        p={"id":pid,"name":clean[:100],"created_at":base.now(),"updated_at":base.now()};base.STATE["projects"].append(p);base.PROJECT_ROOT.joinpath(pid).mkdir(parents=True,exist_ok=True);base.save_state()
    return p

def _project_status(pid):
    p=_project(pid)
    with base.LOCK:assets=[base.public_asset(a) for a in base.STATE["assets"] if a.get("project")==pid];jobs=[dict(j) for j in base.STATE["jobs"] if j.get("project")==pid]
    qp=sum(1 for a in assets if (a.get("qc") or {}).get("status")=="pass");qf=sum(1 for a in assets if (a.get("qc") or {}).get("status")=="fail")
    return {"project":p,"assets":len(assets),"ready_assets":sum(1 for a in assets if a.get("status")=="ready"),"qc_pass":qp,"qc_fail":qf,"unchecked":max(0,len(assets)-qp-qf),"active_jobs":sum(1 for j in jobs if j.get("status") in {"queued","running"}),"canonical_core":CORE.status(),"production":production_project.status(pid)}

def _call_tool_unchecked(name,arguments,*,dispatch_job:Callable[[dict],None],prepare_project:Callable[[str],list[dict]]):
    a=arguments or {};pid=str(a.get("project_id") or "")
    if name=="core.status":return CORE.status()
    if name=="core.bootstrap":return CORE.bootstrap(bool(a.get("offline",False)))
    if name=="capabilities.list":
        s=CORE.status();return {"core":s,"capabilities":CORE.capabilities() if s.get("bootstrapped") else []}
    if name=="fx.list":
        s=CORE.status();return {"core":s,"effects":CORE.effects() if s.get("bootstrapped") else []}
    if name=="project.list":
        with base.LOCK:return {"projects":[dict(p) for p in base.STATE["projects"]]}
    if name=="project.create":return {"project":_create_project(str(a.get("name") or ""))}
    if name=="project.status":return _project_status(pid)
    if name=="project.prepare":_project(pid);jobs=prepare_project(pid);return {"project_id":pid,"queued":len(jobs),"jobs":jobs}
    if name=="production.initialize":_project(pid);return production_project.initialize(pid)
    if name=="production.status":_project(pid);return production_project.status(pid)
    if name=="production.sync_assets":_project(pid);return production_project.sync_assets(pid)
    if name=="production.analyze":_project(pid);job=base.add_job("analyze_production",pid,None);dispatch_job(job);return {"job":job}
    if name=="production.set_music_context":_project(pid);return production_analysis.set_music_context(pid,lyrics_status=str(a.get("lyrics_status") or ""),genre=str(a.get("genre") or ""),lyrics_text=str(a.get("lyrics_text") or ""),directing_use=str(a.get("directing_use") or "default"))
    if name.startswith("operating."):
        _project(pid)
        return operating_tools.call(name,a)
    if name=="approach.status":_project(pid);return production_approach.status(pid)
    if name=="approach.set_capabilities":_project(pid);return production_approach.set_capabilities(pid,a.get("capabilities") if isinstance(a.get("capabilities"),list) else [],str(a.get("approach_summary") or ""))
    if name=="approach.set_routes":_project(pid);return production_approach.set_routes(pid,a.get("routes") if isinstance(a.get("routes"),list) else [],str(a.get("presentation_channel") or "studio"))
    if name=="approach.select_route":_project(pid);return production_approach.select_route(pid,a.get("selected_option_numbers") if isinstance(a.get("selected_option_numbers"),list) else [],str(a.get("recorded_user_instruction") or ""),str(a.get("status") or "selected"))
    if name=="storyboard.status":_project(pid);return production_storyboard.status(pid)
    if name=="storyboard.set":_project(pid);return production_storyboard.set_storyboard(pid,a.get("entries") if isinstance(a.get("entries"),list) else [],target_fps=float(a.get("target_fps") or 30),summary=str(a.get("summary") or ""),authority=str(a.get("authority") or "current_user_or_agent"))
    if name=="storyboard.lock":_project(pid);return production_storyboard.lock_storyboard(pid,str(a.get("recorded_instruction") or ""))
    if name=="storyboard.guard":_project(pid);return production_storyboard.run_narrative_guard(pid)
    if name=="shots.status":_project(pid);return production_shots.status(pid)
    if name=="shots.template":_project(pid);return production_shots.template(pid)
    if name=="shots.build_packages":_project(pid);return production_shots.build_packages(pid,a.get("assignments") if isinstance(a.get("assignments"),list) else [])
    if name=="generated.status":_project(pid);return production_generated.status(pid)
    if name=="generated.request":_project(pid);return production_generated.request_generation(pid,shot_id=str(a.get("shot_id") or ""),capability=str(a.get("capability") or ""),prompt=str(a.get("prompt") or ""),provider_hint=str(a.get("provider_hint") or ""),notes=str(a.get("notes") or ""))
    if name=="generated.register":_project(pid);return production_generated.register_generated(pid,asset_id=str(a.get("asset_id") or ""),shot_id=str(a.get("shot_id") or ""),capability=str(a.get("capability") or ""),request_id=str(a.get("request_id") or ""),provider=str(a.get("provider") or ""),model=str(a.get("model") or ""),prompt=str(a.get("prompt") or ""),role=str(a.get("role") or "generated_visual"))
    if name=="generated.accept":_project(pid);return production_generated.accept_generated(pid,asset_id=str(a.get("asset_id") or ""),instruction=str(a.get("instruction") or ""))
    if name=="generated.reject":_project(pid);return production_generated.reject_generated(pid,asset_id=str(a.get("asset_id") or ""),reason=str(a.get("reason") or ""))
    if name=="proofs.status":_project(pid);return production_proofs.status(pid)
    if name=="proofs.record":_project(pid);return production_proofs.record_proof(pid,shot_id=str(a.get("shot_id") or ""),proof_asset_id=str(a.get("proof_asset_id") or ""),checks=a.get("checks") if isinstance(a.get("checks"),dict) else {},production_mode=str(a.get("production_mode") or ""),notes=str(a.get("notes") or ""))
    if name=="proofs.accept":_project(pid);return production_proofs.accept_proof(pid,shot_id=str(a.get("shot_id") or ""),instruction=str(a.get("instruction") or ""))
    if name=="proofs.finalize":_project(pid);return production_proofs.finalize_acceptance(pid,instruction=str(a.get("instruction") or ""))
    if name=="proofs.reject":_project(pid);return production_proofs.reject_proof(pid,shot_id=str(a.get("shot_id") or ""),reason=str(a.get("reason") or ""))
    if name=="fx.status":_project(pid);return production_fx.status(pid)
    if name=="fx.registry":_project(pid);return production_fx.registry(pid)
    if name=="fx.set_requirements":_project(pid);return production_fx.set_requirements(pid,effects=a.get("effects") if isinstance(a.get("effects"),list) else [],transitions=a.get("transitions") if isinstance(a.get("transitions"),list) else [],seed=int(a.get("seed") or 302),allow_conditional=a.get("allow_conditional") if isinstance(a.get("allow_conditional"),list) else [],conditional_preflight=a.get("conditional_preflight") if isinstance(a.get("conditional_preflight"),dict) else {})
    if name=="fx.lock":_project(pid);return production_fx.lock(pid)
    if name=="fx.verify":_project(pid);return production_fx.verify(pid)
    if name=="assembly.status":_project(pid);return production_assembly.status(pid)
    if name=="assembly.run":
        _project(pid);job=base.add_job("assemble_production",pid,None);job["width"]=int(a.get("width") or 1280);job["height"]=int(a.get("height") or 720);dispatch_job(job);return {"job":job}
    if name=="final_qc.status":_project(pid);return production_final_qc.status(pid)
    if name=="final_qc.run_technical":_project(pid);return production_final_qc.run_technical(pid)
    if name=="final_qc.accept_creative":_project(pid);return production_final_qc.accept_creative(pid,verified_shot_ids=a.get("verified_shot_ids") if isinstance(a.get("verified_shot_ids"),list) else [],mode_aware_checks=a.get("mode_aware_checks") if isinstance(a.get("mode_aware_checks"),dict) else {},instruction=str(a.get("instruction") or ""))
    if name=="final_qc.reject":_project(pid);return production_final_qc.reject(pid,reason=str(a.get("reason") or ""))
    if name=="archive.status":_project(pid);return production_archive.status(pid)
    if name=="archive.build":_project(pid);return production_archive.build(pid,note=str(a.get("note") or ""))
    if name=="archive.verify":_project(pid);return production_archive.verify(pid)
    if name=="production.guard":_project(pid);return production_project.run_guard(pid)
    if name=="production.advance":_project(pid);return production_stage.advance(pid,str(a.get("target_stage") or ""))
    if name=="media.list":
        _project(pid)
        with base.LOCK:assets=[base.public_asset(x) for x in base.STATE["assets"] if x.get("project")==pid]
        return {"assets":assets}
    if name=="media.prepare":
        aid=str(a.get("asset_id") or "");op=str(a.get("operation") or "");asset=_asset(aid)
        if op not in {"make_proxy","extract_review_frames","qc_media"}:raise ValueError("unsupported media preparation operation")
        job=base.add_job(op,asset.get("project") or "prototype",aid);dispatch_job(job);return {"job":job}
    if name=="storage.status":return storage.status()
    if name=="storage.sync":
        _project(pid)
        if not storage.status().get("configured"):raise ValueError("external storage is not configured")
        job=base.add_job("sync_project",pid,None);dispatch_job(job);return {"job":job}
    raise ValueError(f"unknown tool: {name}")


_READ_ONLY_TOOLS = {
    "core.status", "capabilities.list", "fx.list", "project.list", "project.status",
    "production.status", "operating.status", "approach.status", "storyboard.status", "storyboard.guard",
    "shots.status", "shots.template", "generated.status", "proofs.status",
    "fx.status", "fx.registry", "fx.verify", "assembly.status", "final_qc.status",
    "archive.status", "archive.verify", "production.guard", "media.list",
    "storage.status",
}

_UNGATED_BOOTSTRAP_TOOLS = {
    "core.bootstrap", "project.create", "project.prepare", "production.initialize",
}

_CHANGE_TAGS = {
    "operating.configure_v2": ["operating order"],
    "operating.update_next_action": ["operating order"],
    "operating.lock_canon": ["canon lock"],
    "operating.set_refinement": ["refinement scope"],
    "production.sync_assets": ["media manifest update"],
    "production.analyze": ["analysis evidence"],
    "production.set_music_context": ["music context"],
    "approach.set_capabilities": ["production approach"],
    "approach.set_routes": ["visual direction"],
    "approach.select_route": ["visual direction"],
    "storyboard.set": ["storyboard"],
    "storyboard.lock": ["storyboard lock"],
    "shots.build_packages": ["shot packages"],
    "generated.request": ["generation request"],
    "generated.register": ["generated media registration"],
    "generated.accept": ["asset acceptance"],
    "generated.reject": ["asset rejection"],
    "proofs.record": ["proof record"],
    "proofs.accept": ["proof acceptance"],
    "proofs.finalize": ["proof acceptance"],
    "proofs.reject": ["proof rejection"],
    "fx.set_requirements": ["fx requirements"],
    "fx.lock": ["fx lock"],
    "assembly.run": ["assembly"],
    "final_qc.run_technical": ["qc evidence"],
    "final_qc.accept_creative": ["final acceptance"],
    "final_qc.reject": ["final rejection"],
    "archive.build": ["archive"],
    "production.advance": ["stage advance"],
    "media.prepare": ["media derivative"],
    "storage.sync": ["external backup"],
}


def _refresh_boot_capsule(project_id: str) -> None:
    current = production_project.status(project_id)
    if not current.get("initialized"):
        return
    engine = Path(current["engine_root"])
    project_dir = Path(current["project_dir"])
    env = dict(os.environ)
    core_ref = os.environ.get("AIVE_CORE_REF", "main").strip() or "main"
    if core_ref != "main":
        env["AIVIDEOEDIT_AUTHORITY_REF"] = core_ref
        env["AIVIDEOEDIT_VALIDATION_MODE"] = "1"
    boot_cmd = [
        sys.executable, str(engine / "bootstrap.py"), "boot",
        "--repo-root", str(engine),
        "--branch", str(current["branch"]),
        "--project-dir", str(project_dir.relative_to(engine)),
    ]
    if os.environ.get("AIVE_OFFLINE", "").strip().lower() in {"1", "true", "yes", "on"}:
        boot_cmd.append("--offline")
    proc = subprocess.run(
        boot_cmd,
        cwd=str(engine), capture_output=True, text=True, timeout=300, check=False,
        env=env,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            "mutation completed but boot capsule refresh failed: "
            + ((proc.stderr or proc.stdout or "unknown bootstrap failure")[-1600:])
        )


def _require_runtime_gate(project_id: str, operation: str) -> dict:
    current = production_project.status(project_id)
    if not current.get("initialized"):
        raise RuntimeError("production workspace is not initialized")
    gate = runtime_gatekeeper.require(
        engine=Path(current["engine_root"]),
        project_dir=Path(current["project_dir"]),
        branch=str(current["branch"]),
        operation=operation,
        change_tags=_CHANGE_TAGS.get(operation, [operation]),
    )
    decision = jev_decide({
        "gate": "PASS",
        "checks": {
            "runtime_gatekeeper": gate.get("decision") == "PASS",
            "session_attestation": True,
        },
        "next_action_permitted": True,
    })
    if decision.get("decision") != "CONTINUE":
        raise RuntimeError(
            "JEV BLOCK: " + str(decision.get("decision")) + ": " + str(decision.get("reason"))
        )
    return {"gatekeeper": gate, "jev": decision}


def call_tool(name,arguments,*,dispatch_job:Callable[[dict],None],prepare_project:Callable[[str],list[dict]]):
    a = arguments or {}
    pid = str(a.get("project_id") or "")
    if name not in _READ_ONLY_TOOLS and name not in _UNGATED_BOOTSTRAP_TOOLS and pid:
        _require_runtime_gate(pid, name)

    result = _call_tool_unchecked(
        name, a, dispatch_job=dispatch_job, prepare_project=prepare_project
    )

    if (
        name not in _READ_ONLY_TOOLS
        and name not in _UNGATED_BOOTSTRAP_TOOLS
        and pid
    ):
        _refresh_boot_capsule(pid)
    return result
