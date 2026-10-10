#!/usr/bin/env python3
"""Content-addressed archive manifest for completed AIVideoEdit productions."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
import server as base
import production_project
import production_assembly
import production_final_qc
import delivery_archive

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
def build(pid,*,note:str=""):
    current,engine,project_dir=_project(pid)
    if current.get("stage")!="FINAL_QC_PASSED":raise RuntimeError("archive requires FINAL_QC_PASSED stage")
    qc=production_final_qc.status(pid)
    if not qc.get("final_pass") or qc.get("creative_status")!="accepted":raise RuntimeError("accepted final QC is required")
    assembly=production_assembly.status(pid)
    if not assembly.get("assembly_complete") or not assembly.get("output_present"):raise RuntimeError("verified final assembly is required")
    # GUI archive is a final/release operation: the user's prior creative review
    # cannot substitute for a full-song release certificate bound to the exact bytes.
    state=_read(project_dir/"PROJECT_STATE.json",{})
    gate=_read(project_dir/"RELEASE_GATE.json",{})
    if (gate.get("schema")!="aivideoedit.release-gate.v1" or gate.get("status")!="PASS" or
        gate.get("human_visual_approval") is not True or gate.get("decoded_full_export") is not True or
        state.get("release_gate_status")!="PASS" or state.get("human_visual_approval") is not True or
        not gate.get("approval_comment_url") or not gate.get("reviewer")):
        raise RuntimeError("archive blocked: verified full-song production release gate is required")
    links={"release_gate_export_sha256":"export_sha256",
           "release_gate_manifest_sha256":"manifest_sha256",
           "release_gate_source_commit_sha":"source_sha",
           "release_gate_engine_commit_sha":"engine_sha"}
    if any(not state.get(k) or state[k]!=gate.get(v) for k,v in links.items()):
        raise RuntimeError("archive blocked: stale release gate or contradictory project state")
    if (assembly.get("assembly") or {}).get("sha256") != gate.get("export_sha256"):
        raise RuntimeError("archive blocked: assembled export differs from human-approved release")
    records=[]
    canonical_files=["PROJECT.md","STATUS.md","HANDOFF.md","SOURCE_AUTHORITY.json","REFERENCE_MANIFEST.json","MEDIA_PLAN.json","ASSET_MANIFEST.json","MUSIC_ANALYSIS.json","SCRIPT.md","SCRIPT.json","VISUAL_DNA.md","SHOT_LIST.md","RENDER_HISTORY.md","QC.md","STORYBOARD.json","ASSEMBLY.json","FINAL_QC.json","RELEASE_GATE.json","FX_REQUIREMENTS.json","fx.lock.json"]
    for name in canonical_files:
        path=project_dir/name
        if path.is_file():records.append({"path":name,"sha256":_sha(path),"size_bytes":path.stat().st_size})
    for root_name in ["shot_packages","shot_proofs"]:
        root=project_dir/root_name
        if root.is_dir():
            for path in sorted(root.rglob("*.json")):
                records.append({"path":path.relative_to(project_dir).as_posix(),"sha256":_sha(path),"size_bytes":path.stat().st_size})
    assembly_record=assembly.get("assembly") or {};asset=assembly.get("asset") or {}
    media={"asset_id":assembly_record.get("output_asset_id"),"uri":assembly_record.get("output_uri"),"sha256":assembly_record.get("sha256"),"browser_url":asset.get("source_url"),"size_bytes":asset.get("size_bytes"),"storage_policy":"heavy_media_external_or_workstation; not embedded in Git archive manifest"}
    state_before_archive=_read(project_dir/"PROJECT_STATE.json",{})
    lifecycle={"state":"RELEASE_AUTHORIZED","history":[
        {"state":"DIRECTOR_RECOMMENDED","evidence":"accepted full-song final QC"},
        {"state":"HUMAN_ACCEPTED","evidence":gate.get("approval_comment_url")},
        {"state":"RELEASE_AUTHORIZED","evidence":gate.get("approval_comment_url")},
    ]}
    artifacts=[{"id":"accepted-artistic-master","role":"accepted_artistic_master","sha256":media.get("sha256"),"size_bytes":media.get("size_bytes"),"locator":media.get("browser_url") or media.get("uri"),"access":"directly_playable"}]
    artifacts.extend({"id":f"record-{index:04d}","role":"production_record","sha256":rec["sha256"],"size_bytes":rec["size_bytes"],"locator":rec["path"],"access":"evidence"} for index,rec in enumerate(records,1))
    manifest={"schema":"aivideoedit.archive-manifest.v2","project_id":pid,"branch":current.get("branch"),"core_main_commit":current.get("main_commit"),"production_stage":"FINAL_QC_PASSED","delivery_lifecycle":lifecycle,"release_approval":{"authenticated":True,"reviewer":gate.get("reviewer"),"comment_url":gate.get("approval_comment_url"),"approved_sha256":media.get("sha256")},"project_state_snapshot":state_before_archive,"records":records,"artifacts":artifacts,"final_media":media,"final_qc_sha256":_sha(project_dir/"FINAL_QC.json"),"assembly_record_sha256":_sha(project_dir/"ASSEMBLY.json"),"note":str(note or "").strip() or None,"created_at":base.now()}
    archive_path=project_dir/"ARCHIVE_MANIFEST.json";_write(archive_path,manifest)
    state_path=project_dir/"PROJECT_STATE.json";state=_read(state_path,{});state.update({"archive_complete":True,"archive_manifest_sha256":_sha(archive_path),"archive_record_count":len(records),"archived_at":base.now()});_write(state_path,state)
    commit=production_project._git_commit_paths(engine,[archive_path,state_path],"Create content-addressed production archive manifest");production_project._clear_guard_marker(engine)
    return {**status(pid),"commit":commit}
def verify(pid):
    current,_engine,project_dir=_project(pid);manifest_path=project_dir/"ARCHIVE_MANIFEST.json";manifest=_read(manifest_path,{})
    if not manifest:return {"ok":False,"error":"archive manifest missing"}
    problems=[]
    if manifest.get("schema")!="aivideoedit.archive-manifest.v2":problems.append("unsupported archive schema")
    problems.extend(delivery_archive.validate_lifecycle(manifest.get("delivery_lifecycle") or {}))
    for rec in manifest.get("records",[]) if isinstance(manifest.get("records"),list) else []:
        path=project_dir/str(rec.get("path") or "")
        if not path.is_file():problems.append(f"missing {rec.get('path')}")
        elif _sha(path)!=rec.get("sha256"):problems.append(f"hash changed {rec.get('path')}")
    assembly=production_assembly.status(pid);media=manifest.get("final_media") or {};record=assembly.get("assembly") or {}
    if not assembly.get("output_present"):problems.append("final media artifact missing")
    elif record.get("sha256")!=media.get("sha256"):problems.append("final media hash differs from archive")
    if _sha(project_dir/"FINAL_QC.json")!=manifest.get("final_qc_sha256"):problems.append("FINAL_QC.json changed")
    if _sha(project_dir/"ASSEMBLY.json")!=manifest.get("assembly_record_sha256"):problems.append("ASSEMBLY.json changed")
    approval=manifest.get("release_approval") or {}
    if approval.get("authenticated") is not True or approval.get("approved_sha256")!=media.get("sha256") or not approval.get("comment_url"):
        problems.append("release approval no longer binds the archived master")
    return {"ok":not problems,"problems":problems,"manifest_sha256":_sha(manifest_path),"record_count":len(manifest.get("records",[]))}
def status(pid):
    current,_engine,project_dir=_project(pid);state=_read(project_dir/"PROJECT_STATE.json",{});manifest=_read(project_dir/"ARCHIVE_MANIFEST.json",{})
    return {**current,"archive_complete":bool(state.get("archive_complete")),"manifest_present":bool(manifest),"archive_manifest_sha256":state.get("archive_manifest_sha256"),"record_count":len(manifest.get("records",[])) if isinstance(manifest.get("records"),list) else 0,"delivery_lifecycle":(manifest.get("delivery_lifecycle") or {}).get("state"),"final_media":manifest.get("final_media")}
