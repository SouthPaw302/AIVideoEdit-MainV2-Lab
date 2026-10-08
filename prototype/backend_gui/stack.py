#!/usr/bin/env python3
"""AIVideoEdit alpha stack runtime."""
from __future__ import annotations
import json,os,queue,shutil,threading
from pathlib import Path
from http.server import ThreadingHTTPServer
from urllib.parse import urlparse
import server as base
import storage
import tool_api
import operating_tools
import harness_tools
import remote_bridge
import production_analysis
import production_assembly
import production_project
from core_adapter import CORE

WORKER_COUNT=max(1,int(os.environ.get("AIVE_WORKERS","2")))
JOB_QUEUE:queue.Queue[dict]=queue.Queue()
def all_tool_schemas():return tool_api.schemas()+operating_tools.schemas()+harness_tools.schemas()

def sync_project_job(job):
    pid=job["project"];base.update_job(job["id"],status="running",started_at=base.now(),progress=5)
    with base.LOCK:assets=[dict(a) for a in base.STATE["assets"] if a.get("project")==pid]
    def progress(index,total,name):base.update_job(job["id"],progress=10 if total<=0 else min(95,10+int(index/total*85)),result=f"Uploading {name} · {index}/{total}")
    try:
        manifest=storage.sync_project(pid,assets,base.PROJECT_ROOT,progress=progress);base.update_job(job["id"],status="complete",progress=100,result=f"External sync complete · {len(manifest['objects'])} objects",finished_at=base.now())
    except Exception as exc:base.update_job(job["id"],status="failed",progress=100,result=str(exc)[:600],finished_at=base.now())

def _capture_music_authority(pid):
    try:
        s=production_project.status(pid);project_dir=Path(s.get("project_dir") or "")
        music=production_analysis._read_json(project_dir/"MUSIC_ANALYSIS.json",{}) if project_dir.is_dir() else {}
        lyrics=music.get("lyrics") if isinstance(music.get("lyrics"),dict) else None
        genre=music.get("genre") if isinstance(music.get("genre"),dict) else None
        state=production_analysis._read_json(project_dir/"PROJECT_STATE.json",{}) if project_dir.is_dir() else {}
        if not state.get("lyrics_status_resolved") and not state.get("genre_authority_resolved"):return None
        return {"lyrics":dict(lyrics) if lyrics else None,"genre":dict(genre) if genre else None,"lyrics_status_resolved":bool(state.get("lyrics_status_resolved")),"genre_authority_resolved":bool(state.get("genre_authority_resolved"))}
    except Exception:return None

def _restore_music_authority(pid,preserved):
    if not preserved:return
    s=production_project.status(pid);engine=Path(s["engine_root"]);project_dir=Path(s["project_dir"]);music_path=project_dir/"MUSIC_ANALYSIS.json";state_path=project_dir/"PROJECT_STATE.json"
    music=production_analysis._read_json(music_path,{})
    if preserved.get("lyrics"):music["lyrics"]=preserved["lyrics"]
    if preserved.get("genre"):music["genre"]=preserved["genre"]
    production_analysis._write_json(music_path,music)
    state=production_analysis._read_json(state_path,{})
    if preserved.get("lyrics_status_resolved"):state["lyrics_status_resolved"]=True
    if preserved.get("genre_authority_resolved"):state["genre_authority_resolved"]=True
    production_analysis._write_json(state_path,state)
    production_project._git_commit_paths(engine,[music_path,state_path],"Preserve explicit music authority after signal analysis")
    production_project._clear_guard_marker(engine)

def analyze_production_job(job):
    pid=job["project"];base.update_job(job["id"],status="running",started_at=base.now(),progress=5,result="Starting canonical reference analysis…")
    def progress(index,total,message):base.update_job(job["id"],progress=min(90,10+int(index/max(1,total)*75)),result=message[:600])
    try:
        preserved=_capture_music_authority(pid);result=production_analysis.analyze_project(pid,progress=progress);_restore_music_authority(pid,preserved)
        if preserved:
            result=production_project.status(pid)|{"lyrics_status_resolved":bool(preserved.get("lyrics_status_resolved")),"genre_authority_resolved":bool(preserved.get("genre_authority_resolved"))}
        needs=[]
        if not result.get("lyrics_status_resolved"):needs.append("lyrics status")
        if not result.get("genre_authority_resolved"):needs.append("genre")
        suffix=f" · needs {', '.join(needs)}" if needs else "";base.update_job(job["id"],status="complete",progress=100,result=f"Reference/music analysis complete{suffix}",finished_at=base.now())
    except Exception as exc:base.update_job(job["id"],status="failed",progress=100,result=str(exc)[:600],finished_at=base.now())
def assemble_production_job(job):
    pid=job["project"];base.update_job(job["id"],status="running",started_at=base.now(),progress=10,result="Assembling accepted shot proofs…")
    try:
        result=production_assembly.assemble(pid,width=int(job.get("width") or 1280),height=int(job.get("height") or 720));asset=result.get("asset") or {};base.update_job(job["id"],status="complete",progress=100,result=f"Assembly ready · {asset.get('metadata',{}).get('duration_seconds','?')}s · {asset.get('id','')}",finished_at=base.now())
    except Exception as exc:base.update_job(job["id"],status="failed",progress=100,result=str(exc)[:900],finished_at=base.now())
def execute_job(job):
    handlers={"ffmpeg_check":lambda:base.run_ffmpeg_check(job["id"]),"analyze_media":lambda:base.analyze_asset(job["id"],job["asset_id"]),"make_proxy":lambda:base.make_proxy(job["id"],job["asset_id"]),"extract_review_frames":lambda:base.extract_review_frames(job["id"],job["asset_id"]),"qc_media":lambda:base.qc_asset(job["id"],job["asset_id"]),"sync_project":lambda:sync_project_job(job),"analyze_production":lambda:analyze_production_job(job),"assemble_production":lambda:assemble_production_job(job)}
    fn=handlers.get(job.get("type"))
    if not fn:return base.update_job(job["id"],status="failed",progress=100,result=f"unknown job type: {job.get('type')}",finished_at=base.now())
    try:fn()
    except Exception as exc:base.update_job(job["id"],status="failed",progress=100,result=str(exc)[:600],finished_at=base.now())
def worker_loop(index):
    while True:
        job=JOB_QUEUE.get()
        try:execute_job(job)
        finally:JOB_QUEUE.task_done()
def dispatch_job(job):JOB_QUEUE.put(job)
def start_workers():
    for index in range(WORKER_COUNT):threading.Thread(target=worker_loop,args=(index,),name=f"aive-worker-{index+1}",daemon=True).start()
def system_snapshot():
    usage=shutil.disk_usage(base.RUNTIME)
    with base.LOCK:
        running=sum(1 for j in base.STATE["jobs"] if j.get("status")=="running");queued=sum(1 for j in base.STATE["jobs"] if j.get("status")=="queued");stored=sum(int(a.get("size_bytes") or 0)+int(a.get("proxy_size_bytes") or 0) for a in base.STATE["assets"]);projects=len(base.STATE["projects"]);assets=len(base.STATE["assets"])
    return {"workers":WORKER_COUNT,"queue_depth":JOB_QUEUE.qsize(),"running_jobs":running,"queued_jobs":queued,"projects":projects,"assets":assets,"stored_bytes":stored,"disk":{"total":usage.total,"used":usage.used,"free":usage.free},"storage":storage.status(),"core":CORE.status(),"tool_count":len(all_tool_schemas()),"harness":harness_tools.status()}
def prepare_project(pid):
    created=[]
    with base.LOCK:assets=[dict(a) for a in base.STATE["assets"] if a.get("project")==pid and a.get("status")=="ready"]
    for asset in assets:
        m=asset.get("metadata") or {}
        if m.get("video_codec"):
            if not asset.get("proxy_url"):created.append(base.add_job("make_proxy",pid,asset["id"]))
            if not asset.get("review_frames"):created.append(base.add_job("extract_review_frames",pid,asset["id"]))
        if (asset.get("qc") or {}).get("status")!="pass":created.append(base.add_job("qc_media",pid,asset["id"]))
    for job in created:dispatch_job(job)
    return created
def _tool_call(name: str, args: dict):
    if name.startswith("harness."):
        return harness_tools.call(name,args)
    return tool_api.call_tool(name,args,dispatch_job=dispatch_job,prepare_project=prepare_project)


def _remote_auth(handler):
    ok,reason=remote_bridge.authorize(handler.headers)
    rid=remote_bridge.request_id(handler.headers)
    return ok,reason,rid


def _json_body(handler):
    length=int(handler.headers.get("Content-Length","0") or 0);raw=handler.rfile.read(length) if length else b"{}"
    try:
        data=json.loads(raw.decode("utf-8"));return data if isinstance(data,dict) else {}
    except Exception as exc:raise ValueError(f"invalid JSON: {exc}")

class StackHandler(base.Handler):
    server_version="AIVideoEditAlphaStack/0.8"
    def do_GET(self):
        path=urlparse(self.path).path
        if path=="/api/system":return self.send_json(system_snapshot())
        if path=="/api/storage":return self.send_json(storage.status())
        if path=="/api/core":return self.send_json(CORE.status())
        if path=="/api/tools":return self.send_json({"schema":"aivideoedit.tools.v1","tools":all_tool_schemas()})
        if path=="/api/remote/health":
            if not remote_bridge.enabled():
                return self.send_json({"ok":False,"error":"remote bridge disabled"},404)
            return self.send_json({"ok":True,"schema":"aivideoedit.remote-health.v1","bridge":"existing_stack_adapter"})
        if path=="/api/remote/capabilities":
            ok,reason,rid=_remote_auth(self)
            if not ok:return self.send_json({"ok":False,"error":reason,"request_id":rid},401)
            names=[x.get("name") for x in all_tool_schemas() if isinstance(x,dict) and x.get("name")]
            return self.send_json({"ok":True,"request_id":rid,"result":remote_bridge.capability_document(names,harness_enabled=harness_tools.status().get("enabled",False))})
        return super().do_GET()
    def do_POST(self):
        path=urlparse(self.path).path
        if path=="/api/core/bootstrap":
            try:
                data=_json_body(self);result=CORE.bootstrap(bool(data.get("offline",False)));return self.send_json(result,200 if result.get("bootstrapped") else 409)
            except Exception as exc:return self.send_json({"error":str(exc)},400)
        if path=="/api/tools/call":
            try:
                data=_json_body(self);name=str(data.get("name") or "");args=data.get("arguments") if isinstance(data.get("arguments"),dict) else {}
                if not name:return self.send_json({"error":"tool name is required"},400)
                result=_tool_call(name,args)
                return self.send_json({"ok":True,"tool":name,"result":result})
            except ValueError as exc:return self.send_json({"ok":False,"error":str(exc)},400)
            except Exception as exc:return self.send_json({"ok":False,"error":str(exc)},500)
        if path=="/api/remote/call":
            ok,reason,rid=_remote_auth(self)
            if not ok:return self.send_json({"ok":False,"error":reason,"request_id":rid},401)
            try:
                data=_json_body(self);name=str(data.get("name") or "");args=data.get("arguments") if isinstance(data.get("arguments"),dict) else {}
                valid={x.get("name") for x in all_tool_schemas() if isinstance(x,dict)}
                if name not in valid:return self.send_json({"ok":False,"error":"unknown or unapproved tool","request_id":rid},400)
                result=_tool_call(name,args)
                return self.send_json({"ok":True,"request_id":rid,"tool":name,"result":result})
            except ValueError as exc:return self.send_json({"ok":False,"error":str(exc),"request_id":rid},400)
            except Exception as exc:return self.send_json({"ok":False,"error":str(exc),"request_id":rid},500)
        if path.startswith("/api/projects/") and path.endswith("/prepare"):
            parts=path.strip("/").split("/");pid=parts[2]
            if not base.find_project(pid):return self.send_json({"error":"project not found"},404)
            jobs=prepare_project(pid);return self.send_json({"jobs":jobs,"count":len(jobs)},202)
        if path.startswith("/api/projects/") and path.endswith("/sync"):
            parts=path.strip("/").split("/");pid=parts[2]
            if not base.find_project(pid):return self.send_json({"error":"project not found"},404)
            if not storage.status().get("configured"):return self.send_json({"error":"external storage is not configured","storage":storage.status()},409)
            job=base.add_job("sync_project",pid,None);dispatch_job(job);return self.send_json(job,202)
        return super().do_POST()

if __name__=="__main__":
    base.load_state();base.dispatch_job=dispatch_job;start_workers();host=os.environ.get("AIVE_HOST","0.0.0.0");port=int(os.environ.get("AIVE_PORT","8080"));print(f"AIVideoEdit Alpha Stack: http://127.0.0.1:{port}");print(f"LAN bind: {host}:{port}");print(f"Workspace: {base.RUNTIME}");print(f"Workers: {WORKER_COUNT}");print(f"Storage: {storage.status()['detail']}");print(f"Canonical core: {'loaded' if CORE.status().get('bootstrapped') else 'not bootstrapped'}");print(f"Tool API: {len(all_tool_schemas())} tools")
    if os.environ.get("AIVE_CORE_AUTOBOOT","").strip().lower() in {"1","true","yes"}:threading.Thread(target=CORE.bootstrap,name="aive-core-bootstrap",daemon=True).start()
    ThreadingHTTPServer((host,port),StackHandler).serve_forever()
