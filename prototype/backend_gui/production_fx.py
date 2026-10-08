#!/usr/bin/env python3
"""Canonical FX selection, precompile gating, and immutable lock verification."""
from __future__ import annotations
import hashlib,json,os,subprocess,sys
from pathlib import Path
import server as base
import production_project
from core_adapter import CORE

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
def _session(engine):return _read(engine/".aivideoedit"/"session.json",{})

def _ledger(engine,project_dir,component,subject,stage,*,required_execution=False,required_consumption=False,reason=None):
    tool=engine/"general/reusable/tools/execution_ledger.py"
    ledger=project_dir/"PRODUCTION_EXECUTION_LEDGER.json"
    if not tool.is_file():raise RuntimeError("execution ledger tool missing from production OS")
    cmd=[sys.executable,str(tool),"record","--ledger",str(ledger),"--project",project_dir.name,"--component",component,"--subject",subject,"--stage",stage]
    if required_execution:cmd.append("--required-execution")
    if required_consumption:cmd.append("--required-consumption")
    if reason:cmd += ["--reason",str(reason)]
    proc=subprocess.run(cmd,cwd=str(engine),capture_output=True,text=True,timeout=60,check=False)
    if proc.returncode!=0:raise RuntimeError("execution ledger write failed: "+str(proc.stderr or proc.stdout)[-1600:])
    return ledger
def registry(pid):
    current,engine,_project_dir=_project(pid);session=_session(engine);os_root=Path(session.get("os_root") or "")
    reg=_read(os_root/"general/reusable/fx_v2/registry.json",{})
    effects=[]
    for eid,e in (reg.get("effects",{}) or {}).items():
        if isinstance(e,dict):effects.append({"id":eid,"name":e.get("name"),"family":e.get("family"),"status":e.get("status"),"gate_status":e.get("gate_status"),"implementation":e.get("implementation"),"proofs":e.get("proofs",[])})
    return {**current,"runtime":reg.get("runtime"),"effects":effects}
def _canonical_paths(engine):
    session=_session(engine);os_root=Path(session.get("os_root") or "")
    canonical=os_root/"general/reusable/fx_v2";working=engine/"general/reusable/fx_v2"
    pairs=[("registry.json",canonical/"registry.json",working/"registry.json"),("runtime.py",canonical/"runtime.py",working/"runtime.py"),("precompile_gate.py",canonical/"precompile_gate.py",working/"precompile_gate.py")]
    for name,src,dst in pairs:
        if not src.is_file() or not dst.is_file():raise RuntimeError(f"canonical FX file missing: {name}")
        if _sha(src)!=_sha(dst):raise RuntimeError(f"working FX {name} differs from attested current-main core")
    return working/"precompile_gate.py",working/"registry.json",working/"proofs",working/"runtime.py"
def set_requirements(pid,*,effects:list[dict],transitions:list[dict],seed:int=302,allow_conditional:list[str]|None=None,conditional_preflight:dict|None=None):
    current,engine,project_dir=_project(pid)
    if current.get("stage") not in {"SHOT_PROOFS_ACCEPTED","FX_LOCKED"}:raise RuntimeError("FX requirements require SHOT_PROOFS_ACCEPTED stage")
    reg=registry(pid);known={x["id"]:x for x in reg["effects"]};seen=set()
    def norm(items,kind):
        out=[]
        for raw in items if isinstance(items,list) else []:
            item={"id":raw} if isinstance(raw,str) else dict(raw) if isinstance(raw,dict) else {}
            eid=str(item.get("id") or "")
            if not eid or eid not in known:raise ValueError(f"unknown FX id: {eid}")
            if eid in seen:raise ValueError(f"duplicate FX id: {eid}")
            seen.add(eid);gate=known[eid].get("gate_status")
            if gate=="unavailable":raise RuntimeError(f"FX is unavailable: {eid}")
            if gate=="proof_required":raise RuntimeError(f"FX is not production-approved yet: {eid}")
            impl=(known[eid].get("implementation") or {}).get("kind")
            if kind=="transition" and impl!="runtime_transition":raise ValueError(f"{eid} is not a runtime transition")
            if kind=="effect" and impl=="runtime_transition":raise ValueError(f"{eid} must be requested as a transition")
            out.append({k:v for k,v in item.items() if k!="_kind"})
        return out
    fx=norm(effects,"effect");tr=norm(transitions,"transition")
    if not fx and not tr:raise ValueError("select at least one production-approved effect or transition")
    render_inputs=[]
    for path in [project_dir/"SCRIPT.json",project_dir/"ASSET_MANIFEST.json"]:
        render_inputs.append(path.relative_to(engine).as_posix())
    root=project_dir/"shot_packages"
    if root.is_dir():
        for p in sorted(root.glob("*/package.json")):render_inputs.append(p.relative_to(engine).as_posix())
    req={"schema":"aivideoedit.fx-requirements.v1","project":project_dir.name,"runtime":reg.get("runtime"),"seed":int(seed),"effects":fx,"transitions":tr,"render_inputs":render_inputs,"allow_conditional":list(allow_conditional or []),"conditional_preflight":dict(conditional_preflight or {}),"execution_entrypoint":"general/reusable/fx_v2/executor.py","created_at":base.now()}
    path=project_dir/"FX_REQUIREMENTS.json";_write(path,req)
    for item in fx+tr:_ledger(engine,project_dir,"fx",item["id"],"selected",required_execution=True)
    state_path=project_dir/"PROJECT_STATE.json";state=_read(state_path,{});state["fx_lock_verified"]=False;_write(state_path,state)
    commit=production_project._git_commit_paths(engine,[path,state_path],"Record production FX requirements");production_project._clear_guard_marker(engine)
    return {**status(pid),"requirements":req,"commit":commit}
def lock(pid):
    current,engine,project_dir=_project(pid)
    if current.get("stage")!="SHOT_PROOFS_ACCEPTED":raise RuntimeError("FX lock requires SHOT_PROOFS_ACCEPTED stage")
    manifest=project_dir/"FX_REQUIREMENTS.json"
    if not manifest.is_file():raise RuntimeError("FX_REQUIREMENTS.json is missing")
    gate,registry_path,proof_dir,runtime=_canonical_paths(engine);lock_path=project_dir/"fx.lock.json"
    cmd=[sys.executable,str(gate),"--manifest",str(manifest),"--registry",str(registry_path),"--proof-dir",str(proof_dir),"--runtime",str(runtime),"--lock-out",str(lock_path)]
    proc=subprocess.run(cmd,cwd=str(engine),capture_output=True,text=True,timeout=600,check=False)
    if proc.returncode!=0 or not lock_path.is_file():raise RuntimeError("canonical FX precompile gate failed: "+str(proc.stderr or proc.stdout)[-2400:])
    verify=subprocess.run([sys.executable,str(gate),"--manifest",str(manifest),"--registry",str(registry_path),"--proof-dir",str(proof_dir),"--runtime",str(runtime),"--verify-lock",str(lock_path)],cwd=str(engine),capture_output=True,text=True,timeout=600,check=False)
    if verify.returncode!=0:raise RuntimeError("FX lock verification failed: "+str(verify.stderr or verify.stdout)[-2400:])
    req=_read(manifest,{})
    for item in (req.get("effects",[])+req.get("transitions",[])):
        if isinstance(item,dict) and item.get("id"):_ledger(engine,project_dir,"fx",item["id"],"verified",required_execution=True)
    state_path=project_dir/"PROJECT_STATE.json";state=_read(state_path,{});state.update({"fx_lock_verified":True,"fx_lock_sha256":_sha(lock_path),"fx_lock_verified_at":base.now()});_write(state_path,state)
    commit=production_project._git_commit_paths(engine,[lock_path,state_path],"Lock verified production FX");production_project._clear_guard_marker(engine)
    return {**status(pid),"commit":commit,"precompile_stdout":proc.stdout[-1600:],"verify_stdout":verify.stdout[-1600:]}
def verify(pid):
    current,engine,project_dir=_project(pid);manifest=project_dir/"FX_REQUIREMENTS.json";lock_path=project_dir/"fx.lock.json"
    if not manifest.is_file() or not lock_path.is_file():return {"ok":False,"error":"FX requirements/lock missing"}
    gate,registry_path,proof_dir,runtime=_canonical_paths(engine)
    proc=subprocess.run([sys.executable,str(gate),"--manifest",str(manifest),"--registry",str(registry_path),"--proof-dir",str(proof_dir),"--runtime",str(runtime),"--verify-lock",str(lock_path)],cwd=str(engine),capture_output=True,text=True,timeout=600,check=False)
    return {"ok":proc.returncode==0,"stdout":proc.stdout[-2000:],"stderr":proc.stderr[-2000:],"lock_sha256":_sha(lock_path)}
def status(pid):
    current,_engine,project_dir=_project(pid);req=_read(project_dir/"FX_REQUIREMENTS.json",{});lock_data=_read(project_dir/"fx.lock.json",{});state=_read(project_dir/"PROJECT_STATE.json",{})
    return {**current,"requirements_present":bool(req),"requested_effects":req.get("effects",[]),"requested_transitions":req.get("transitions",[]),"lock_present":bool(lock_data),"lock_result":lock_data.get("result"),"fx_lock_verified":bool(state.get("fx_lock_verified")),"fx_lock_sha256":state.get("fx_lock_sha256"),"execution_ledger_present":(project_dir/"PRODUCTION_EXECUTION_LEDGER.json").is_file()}
