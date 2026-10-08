#!/usr/bin/env python3
"""Frame-followable storyboard/script evidence with Director Brain v3 mode support."""
from __future__ import annotations
import json,os,subprocess,sys
from pathlib import Path
import production_project

def _read_json(path,default):
    try:return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:return default
def _write_json(path,payload):Path(path).write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def _project(pid):
    current=production_project.status(pid)
    if not current.get("initialized"):raise RuntimeError("production workspace is not initialized")
    return current,Path(current["engine_root"]),Path(current["project_dir"])
def _music_to_canonical(project_dir):
    path=project_dir/"MUSIC_ANALYSIS.json";music=_read_json(path,{})
    if not music.get("analysis_complete"):raise RuntimeError("music analysis is incomplete")
    lyrics=music.get("lyrics") if isinstance(music.get("lyrics"),dict) else {};raw=str(lyrics.get("status") or "").strip().lower()
    if raw=="absent":raw="none_confirmed"
    if raw not in {"present","instrumental","none_confirmed"}:raise RuntimeError("lyrics status is not resolved in canonical form")
    directing=str(lyrics.get("directing_use") or "required").strip()
    if raw!="present":directing="required"
    elif directing=="default":directing="required"
    canonical=dict(lyrics);canonical.update({"status":raw,"directing_use":directing})
    if raw=="present":canonical.setdefault("text_file","LYRICS.md")
    music["lyrics"]=canonical
    genre=music.get("genre") if isinstance(music.get("genre"),dict) else {}
    if "label" not in genre and genre.get("value"):genre["label"]=genre.get("value")
    if genre.get("authority")=="explicit_current_user_or_agent_input" and genre.get("label"):
        genre["status"]="user_confirmed";genre["source"]="current_user_instruction";genre.setdefault("user_declaration",str(genre.get("label")))
    if genre.get("status") not in {"confident","user_confirmed"} or not str(genre.get("label") or "").strip():raise RuntimeError("genre authority is not resolved in canonical form")
    music["genre"]=genre
    if not isinstance(music.get("rhythm"),dict):
        pulse=music.get("rhythm_or_pulse") if isinstance(music.get("rhythm_or_pulse"),dict) else {};tempo=music.get("tempo_or_non_metric_status") if isinstance(music.get("tempo_or_non_metric_status"),dict) else {};bpm=pulse.get("estimated_bpm") if pulse.get("estimated_bpm") else tempo.get("estimated_bpm");confidence=float(pulse.get("confidence") or tempo.get("confidence") or 0);metric=isinstance(bpm,(int,float)) and not isinstance(bpm,bool) and bpm>0
        music["rhythm"]={"tempo_status":"measured" if metric and confidence>=.08 else "approximate" if metric else "non_metric","tempo_bpm":bpm if metric else None,"pulse_description":"Signal-derived onset/RMS pulse estimate." if metric else "No stable metric pulse resolved from signal analysis.","meter_or_groove":str((music.get("meter_or_groove") or {}).get("note") or "Meter/groove not asserted by signal analysis alone."),"confidence":confidence}
    if not isinstance(music.get("sections"),list) or len(music.get("sections",[]))<2:
        sm=music.get("section_map") if isinstance(music.get("section_map"),list) else [];peaks=music.get("musical_cues") if isinstance(music.get("musical_cues"),list) else [];sections=[]
        for i,s in enumerate(sm,1):
            if not isinstance(s,dict):continue
            start=float(s.get("start_seconds") or 0);end=float(s.get("end_seconds") or 0)
            if end<=start:continue
            cues=[f"energy peak at {float(c.get('seconds')):.2f}s" for c in peaks if isinstance(c,dict) and isinstance(c.get("seconds"),(int,float)) and start<=float(c.get("seconds"))<end] or [f"section {i} {str(s.get('energy') or 'measured')} energy"]
            sections.append({"index":i,"start_seconds":start,"end_seconds":end,"musical_cues":cues,"energy":str(s.get("energy") or "measured energy"),"narrative_function":"Timing and energy evidence for storyboard alignment; creative interpretation remains authored by the user/agent."})
        if len(sections)<2:raise RuntimeError("music analysis does not contain at least two usable sections")
        music["sections"]=sections
    music["schema"]="aivideoedit.music-analysis.v1";_write_json(path,music);return music
def _duration(music):
    d=float(music.get("duration_seconds") or 0)
    if d<=0 and music.get("sections"):d=max(float(x.get("end_seconds") or 0) for x in music["sections"] if isinstance(x,dict))
    if d<=0:raise RuntimeError("storyboard requires a positive song/video duration")
    return d
def _v2_mode(project_dir):
    state=_read_json(project_dir/"PROJECT_STATE.json",{});version=int(state.get("director_brain_version") or 0)
    if version<2:return 0,None
    order=_read_json(project_dir/"OPERATING_ORDER.json",{});mode=str(order.get("production_mode") or "")
    if mode not in {"living_scene","cinematic","hybrid"}:raise RuntimeError("Director Brain v3 production mode is unresolved")
    return version,mode
def _string_list(value):return [str(x).strip() for x in value if str(x).strip()] if isinstance(value,list) else []
def _normalize_entries(entries,duration,fps,music,project_dir):
    if not isinstance(entries,list) or not entries:raise ValueError("storyboard requires at least one entry")
    total=max(1,int(round(duration*fps)));normalized=[];expected=0;active=(music.get("lyrics") or {}).get("status")=="present" and (music.get("lyrics") or {}).get("directing_use","required")!="excluded_by_current_user";version,overall=_v2_mode(project_dir)
    for index,raw in enumerate(entries,1):
        if not isinstance(raw,dict):raise ValueError(f"storyboard entry {index} must be an object")
        start=raw.get("start_frame");end=raw.get("end_frame")
        if start is None and raw.get("start_seconds") is not None:start=int(round(float(raw["start_seconds"])*fps))
        if end is None and raw.get("end_seconds") is not None:end=int(round(float(raw["end_seconds"])*fps))-1
        if start is None:start=expected
        if end is None:
            if index==len(entries):end=total-1
            else:raise ValueError(f"storyboard entry {index} requires end_frame or end_seconds")
        start,end=int(start),int(end)
        if start!=expected:raise ValueError(f"storyboard entry {index} must start at frame {expected}")
        if end<start:raise ValueError(f"storyboard entry {index} ends before it starts")
        if index==len(entries):end=total-1
        if end>=total:raise ValueError(f"storyboard entry {index} exceeds total frame count")
        fields={}
        for key in ("story_action","visual_media","animation_behavior","transition"):
            value=str(raw.get(key) or "").strip()
            if not value:raise ValueError(f"storyboard entry {index} requires {key}")
            fields[key]=value
        cues=raw.get("music_cues")
        if not isinstance(cues,list) or not [x for x in cues if isinstance(x,str) and x.strip()]:raise ValueError(f"storyboard entry {index} requires at least one music cue")
        lyric=str(raw.get("lyric_cue") or "").strip();record={"shot_id":str(raw.get("shot_id") or f"shot-{index:03d}"),"start_frame":start,"end_frame":end,"start_seconds":round(start/fps,3),"end_seconds":round((end+1)/fps,3),**fields,"music_cues":[str(x).strip() for x in cues if isinstance(x,str) and x.strip()],"lyric_cue":lyric or None}
        if version>=2:
            mode=overall
            if overall=="hybrid":
                mode=str(raw.get("production_mode") or "").strip()
                if mode not in {"living_scene","cinematic"}:raise ValueError(f"hybrid storyboard entry {index} requires production_mode living_scene or cinematic")
                record["production_mode"]=mode
            elif overall in {"living_scene","cinematic"}:record["production_mode"]=overall
            if mode=="living_scene":
                motion=_string_list(raw.get("motion_regions"));protected=_string_list(raw.get("protected_regions"))
                if not motion:raise ValueError(f"living-scene storyboard entry {index} requires motion_regions")
                if not protected:raise ValueError(f"living-scene storyboard entry {index} requires protected_regions")
                record["motion_regions"]=motion;record["protected_regions"]=protected
        normalized.append(record);expected=end+1
    if expected!=total:raise ValueError(f"storyboard must cover every frame through {total-1}; coverage ends at {expected-1}")
    if active and not any(str(x.get("lyric_cue") or "").strip() for x in normalized):raise ValueError("active lyrics require at least one lyric_cue in the storyboard")
    if not active and any(str(x.get("lyric_cue") or "").strip() for x in normalized):raise ValueError("lyric cues are not allowed when lyrics are absent or excluded")
    return normalized
def set_storyboard(project_id,entries,*,target_fps=30.0,summary="",authority="current_user_or_agent"):
    current,engine,project_dir=_project(project_id)
    if current.get("stage") not in {"APPROACH_ESTABLISHED","STORYBOARD_LOCKED"}:raise RuntimeError("storyboard authoring requires APPROACH_ESTABLISHED stage")
    fps=float(target_fps)
    if fps<=0 or fps>240:raise ValueError("target_fps must be greater than 0 and at most 240")
    music=_music_to_canonical(project_dir);duration=_duration(music);normalized=_normalize_entries(entries,duration,fps,music,project_dir);total=max(1,int(round(duration*fps)));lyrics_active=(music.get("lyrics") or {}).get("status")=="present" and (music.get("lyrics") or {}).get("directing_use","required")!="excluded_by_current_user";basis=["storyboard","music_analysis"]+(["lyrics"] if lyrics_active else []);version,mode=_v2_mode(project_dir)
    storyboard={"schema":"aivideoedit.storyboard.v1","locked":False,"authority":str(authority or "current_user_or_agent"),"summary":str(summary or "").strip(),"target_fps":fps,"duration_seconds":duration,"total_frames":total,"director_brain_version":version,"production_mode":mode,"entries":normalized};storyboard_path=project_dir/"STORYBOARD.json";_write_json(storyboard_path,storyboard)
    script={"schema":"aivideoedit.video-script.v1","locked":False,"based_on_storyboard":True,"target_fps":fps,"duration_seconds":duration,"total_frames":total,"basis":basis,"director_brain_version":version,"production_mode":mode,"entries":normalized};script_path=project_dir/"SCRIPT.json";_write_json(script_path,script)
    md=["# Video Script","",f"Duration: {duration:.3f}s · {total} frames @ {fps:g} fps","",f"Basis: {', '.join(basis)}",f"Production mode: {mode or 'legacy'}",""]
    for item in normalized:
        md += [f"## {item['shot_id']} · frames {item['start_frame']}-{item['end_frame']}",f"- Story: {item['story_action']}",f"- Visual: {item['visual_media']}",f"- Motion: {item['animation_behavior']}",f"- Music: {'; '.join(item['music_cues'])}",f"- Lyric: {item['lyric_cue'] or 'none'}",f"- Transition: {item['transition']}"]
        if item.get("production_mode"):md.append(f"- Mode: {item['production_mode']}")
        if item.get("motion_regions"):md.append(f"- Motion regions: {'; '.join(item['motion_regions'])}")
        if item.get("protected_regions"):md.append(f"- Protected regions: {'; '.join(item['protected_regions'])}")
        md.append("")
    md_path=project_dir/"SCRIPT.md";md_path.write_text("\n".join(md),encoding="utf-8")
    state_path=project_dir/"PROJECT_STATE.json";state=_read_json(state_path,{});state.update({"storyboard_locked":False,"script_locked":False,"storyboard_entry_count":len(normalized),"storyboard_full_frame_coverage":True});_write_json(state_path,state)
    commit=production_project._git_commit_paths(engine,[storyboard_path,script_path,md_path,project_dir/"MUSIC_ANALYSIS.json",state_path],"Author mode-aware frame-followable production storyboard");production_project._clear_guard_marker(engine);return {**status(project_id),"commit":commit}
def lock_storyboard(project_id,recorded_instruction):
    current,engine,project_dir=_project(project_id)
    if current.get("stage")!="APPROACH_ESTABLISHED":raise RuntimeError("storyboard lock requires APPROACH_ESTABLISHED stage")
    instruction=str(recorded_instruction or "").strip()
    if not instruction:raise ValueError("recorded current-user/agent lock instruction is required")
    board_path=project_dir/"STORYBOARD.json";script_path=project_dir/"SCRIPT.json";board=_read_json(board_path,{});script=_read_json(script_path,{})
    if not board.get("entries") or not script.get("entries"):raise RuntimeError("author the storyboard before locking it")
    board.update({"locked":True,"lock_instruction":instruction,"locked_at":production_project.base.now()});script.update({"locked":True,"lock_instruction":instruction});_write_json(board_path,board);_write_json(script_path,script)
    state_path=project_dir/"PROJECT_STATE.json";state=_read_json(state_path,{});state["storyboard_locked"]=True;state["script_locked"]=True;_write_json(state_path,state);commit=production_project._git_commit_paths(engine,[board_path,script_path,state_path],"Lock storyboard and production script");production_project._clear_guard_marker(engine);return {**status(project_id),"commit":commit}
def run_narrative_guard(project_id):
    current,engine,project_dir=_project(project_id);session=_read_json(engine/".aivideoedit"/"session.json",{});os_root=Path(session.get("os_root") or "");guard=os_root/"general/reusable/tools/narrative_guard.py"
    if not guard.is_file():raise RuntimeError("bootstrapped canonical narrative guard is missing")
    env=dict(os.environ);env["AIVIDEOEDIT_REPO_ROOT"]=str(engine);env["AIVIDEOEDIT_OS_ROOT"]=str(os_root);env["AIVIDEOEDIT_PROJECT_DIR"]=f"projects/{project_dir.name}";proc=subprocess.run([sys.executable,str(guard),"--branch",str(current.get("branch") or "")],cwd=str(engine),env=env,capture_output=True,text=True,timeout=120,check=False);return {"ok":proc.returncode==0,"stdout":(proc.stdout or "")[-5000:],"stderr":(proc.stderr or "")[-5000:]}
def status(project_id):
    current,_engine,project_dir=_project(project_id);board=_read_json(project_dir/"STORYBOARD.json",{});script=_read_json(project_dir/"SCRIPT.json",{});state=_read_json(project_dir/"PROJECT_STATE.json",{})
    return {**current,"storyboard_exists":bool(board.get("entries")),"storyboard_locked":bool(board.get("locked")) and bool(state.get("storyboard_locked")),"script_locked":bool(script.get("locked")) and bool(state.get("script_locked")),"entry_count":len(script.get("entries",[])) if isinstance(script.get("entries"),list) else 0,"target_fps":script.get("target_fps"),"duration_seconds":script.get("duration_seconds"),"total_frames":script.get("total_frames"),"basis":script.get("basis",[]),"director_brain_version":script.get("director_brain_version",0),"production_mode":script.get("production_mode")}
