#!/usr/bin/env python3
"""Assemble accepted shot proofs into a verified production workprint."""
from __future__ import annotations
import hashlib,json,shutil,subprocess,uuid
from pathlib import Path
import server as base
import production_project

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
        a=base.find_asset(str(asset_id))
        return dict(a) if a else None
def _probe(path):
    ffprobe=shutil.which("ffprobe")
    if not ffprobe:raise RuntimeError("FFprobe is required for assembly verification")
    p=subprocess.run([ffprobe,"-v","error","-show_format","-show_streams","-of","json",str(path)],capture_output=True,text=True,timeout=120,check=False)
    if p.returncode!=0:raise RuntimeError("FFprobe failed: "+str(p.stderr or p.stdout)[-800:])
    return json.loads(p.stdout)
def assemble(pid,*,width:int=1280,height:int=720):
    current,engine,project_dir=_project(pid)
    if current.get("stage")!="FX_LOCKED":raise RuntimeError("assembly requires FX_LOCKED stage")
    state=_read(project_dir/"PROJECT_STATE.json",{})
    if not state.get("fx_lock_verified"):raise RuntimeError("FX lock is not verified")
    script=_read(project_dir/"SCRIPT.json",{});entries=script.get("entries") if isinstance(script.get("entries"),list) else []
    fps=float(script.get("target_fps") or 0);total_frames=int(script.get("total_frames") or 0)
    if not script.get("locked") or not entries or fps<=0 or total_frames<=0:raise RuntimeError("locked frame-followable SCRIPT.json is required")
    fx_lock=project_dir/"fx.lock.json"
    if not fx_lock.is_file():raise RuntimeError("verified fx.lock.json is missing")
    clips=[];inputs=[];evidence=[]
    for i,e in enumerate(entries):
        shot=str(e.get("shot_id") or "");proof=_read(project_dir/"shot_proofs"/f"{shot}.json",{})
        if proof.get("creative_status")!="accepted" or not proof.get("technical_and_mode_checks_passed"):raise RuntimeError(f"accepted proof missing for {shot}")
        pa=proof.get("proof_asset") or {};asset=_asset(pa.get("asset_id"))
        if not asset or asset.get("status")!="ready":raise RuntimeError(f"proof asset unavailable for {shot}")
        source=Path(asset.get("local_path") or "")
        if not source.is_file() or _sha(source)!=str(pa.get("sha256") or ""):raise RuntimeError(f"proof asset hash mismatch for {shot}")
        package=project_dir/"shot_packages"/shot/"package.json"
        if not package.is_file() or _sha(package)!=proof.get("package_sha256"):raise RuntimeError(f"shot package changed after proof acceptance: {shot}")
        frames=int(e.get("end_frame"))-int(e.get("start_frame"))+1;duration=frames/fps
        measured=float((asset.get("metadata") or {}).get("duration_seconds") or 0)
        if measured+0.08<duration:raise RuntimeError(f"proof video for {shot} is too short: {measured:.3f}s < {duration:.3f}s")
        inputs += ["-i",str(source)]
        clips.append((i,duration));evidence.append({"shot_id":shot,"asset_id":asset.get("id"),"sha256":asset.get("sha256"),"duration_used_seconds":round(duration,6),"package_sha256":proof.get("package_sha256")})
    music=_read(project_dir/"MUSIC_ANALYSIS.json",{});audio_asset=_asset(music.get("source_asset_id"))
    if not audio_asset:raise RuntimeError("analyzed source audio asset is unavailable")
    audio_path=Path(audio_asset.get("local_path") or "")
    if not audio_path.is_file():raise RuntimeError("analyzed source audio file is missing")
    audio_index=len(entries);inputs += ["-i",str(audio_path)]
    vf=[]
    for i,duration in clips:
        vf.append(f"[{i}:v]trim=duration={duration:.6f},setpts=PTS-STARTPTS,fps={fps:.6f},scale={int(width)}:{int(height)}:force_original_aspect_ratio=decrease,pad={int(width)}:{int(height)}:(ow-iw)/2:(oh-ih)/2,format=yuv420p[v{i}]")
    vf.append("".join(f"[v{i}]" for i,_ in clips)+f"concat=n={len(clips)}:v=1:a=0[vout]")
    total_duration=total_frames/fps
    out_id="assembly-"+uuid.uuid4().hex[:10];folder=base.ASSET_ROOT/out_id;folder.mkdir(parents=True,exist_ok=True);output=folder/"assembly.mp4"
    ffmpeg=shutil.which("ffmpeg")
    if not ffmpeg:raise RuntimeError("FFmpeg is required for assembly")
    cmd=[ffmpeg,"-y",*inputs,"-filter_complex",";".join(vf),"-map","[vout]","-map",f"{audio_index}:a:0","-t",f"{total_duration:.6f}","-c:v","libx264","-preset","medium","-crf","18","-c:a","aac","-b:a","192k","-movflags","+faststart",str(output)]
    p=subprocess.run(cmd,capture_output=True,text=True,timeout=7200,check=False)
    if p.returncode!=0 or not output.is_file():raise RuntimeError("assembly render failed: "+str(p.stderr or p.stdout)[-2000:])
    info=_probe(output);fmt=info.get("format",{});streams=info.get("streams",[]);video=next((x for x in streams if x.get("codec_type")=="video"),{});audio=next((x for x in streams if x.get("codec_type")=="audio"),{})
    measured=float(fmt.get("duration") or 0)
    if abs(measured-total_duration)>max(0.15,2.0/fps):raise RuntimeError(f"assembly duration mismatch: {measured:.3f}s vs {total_duration:.3f}s")
    if not video or not audio:raise RuntimeError("assembly must contain both video and audio")
    digest=_sha(output);metadata={"duration_seconds":round(measured,3),"format":fmt.get("format_name"),"size_bytes":output.stat().st_size,"video_codec":video.get("codec_name"),"width":video.get("width"),"height":video.get("height"),"fps":video.get("avg_frame_rate"),"audio_codec":audio.get("codec_name"),"sample_rate":audio.get("sample_rate"),"channels":audio.get("channels")}
    asset={"id":out_id,"project":pid,"filename":"assembly.mp4","folder":str(folder),"local_path":str(output),"content_type":"video/mp4","size_bytes":output.stat().st_size,"status":"ready","created_at":base.now(),"updated_at":base.now(),"metadata":metadata,"sha256":digest,"source_url":f"/media/{out_id}/assembly.mp4","thumbnail_url":None,"proxy_url":None,"review_frames":[],"qc":{"status":"pass","kind":"assembly_probe"},"origin":"rendered","kind":"assembly_workprint","role":"production_assembly"}
    with base.LOCK:
        base.STATE["assets"].append(asset);base.STATE["assets"]=base.STATE["assets"][-base.MAX_ASSETS:];base.save_state()
    assembly={"schema":"aivideoedit.assembly.v1","output_asset_id":out_id,"output_uri":f"aive://asset/{out_id}","sha256":digest,"duration_seconds":round(measured,6),"target_frames":total_frames,"target_fps":fps,"size":[video.get("width"),video.get("height")],"video_codec":video.get("codec_name"),"audio_codec":audio.get("codec_name"),"source_audio_asset_id":audio_asset.get("id"),"fx_lock_sha256":_sha(fx_lock),"shot_evidence":evidence,"qc":{"decode_probe":"PASS","duration_match":"PASS","video_present":True,"audio_present":True},"assembled_at":base.now()}
    assembly_path=project_dir/"ASSEMBLY.json";_write(assembly_path,assembly);state["assembly_complete"]=True;state["assembly_asset_id"]=out_id;state["assembly_sha256"]=digest;_write(project_dir/"PROJECT_STATE.json",state)
    commit=production_project._git_commit_paths(engine,[assembly_path,project_dir/"PROJECT_STATE.json"],"Record verified production assembly");production_project._clear_guard_marker(engine)
    return {**status(pid),"commit":commit,"asset":base.public_asset(asset)}
def status(pid):
    current,_engine,project_dir=_project(pid);assembly=_read(project_dir/"ASSEMBLY.json",{});state=_read(project_dir/"PROJECT_STATE.json",{});asset=_asset(assembly.get("output_asset_id")) if assembly else None
    valid=bool(asset and Path(asset.get("local_path") or "").is_file() and asset.get("sha256")==assembly.get("sha256")) if assembly else False
    return {**current,"assembly_complete":bool(state.get("assembly_complete")) and valid,"assembly":assembly,"asset":base.public_asset(asset) if asset else None,"output_present":valid}
