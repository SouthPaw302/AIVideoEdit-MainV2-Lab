#!/usr/bin/env python3
"""Run one tiny end-to-end production through the actual MainV2 stack."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path

HERE=Path(__file__).resolve().parent
BACKEND=HERE.parent
STACK=BACKEND/"stack.py"


def request(url:str,payload:dict|None=None,timeout=600):
    data=None if payload is None else json.dumps(payload).encode()
    req=urllib.request.Request(url,data=data,headers={"Content-Type":"application/json"} if data else {})
    try:
        with urllib.request.urlopen(req,timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as exc:
        body=exc.read().decode("utf-8",errors="replace")
        raise RuntimeError(f"HTTP {exc.code} {url}: {body}") from exc


def tool(name:str,args:dict|None=None):
    out=request("http://127.0.0.1:8099/api/tools/call",{"name":name,"arguments":args or {}})
    if not out.get("ok"):
        raise RuntimeError(f"{name}: {out}")
    return out["result"]


def upload(pid:str,path:Path,ctype:str):
    q=urllib.parse.urlencode({"project":pid,"filename":path.name})
    data=path.read_bytes()
    req=urllib.request.Request(
        f"http://127.0.0.1:8099/api/assets?{q}",data=data,
        headers={"Content-Type":ctype,"Content-Length":str(len(data))},method="POST"
    )
    with urllib.request.urlopen(req,timeout=120) as r:
        return json.loads(r.read().decode())


def wait_until(fn,timeout=180,interval=.5):
    end=time.time()+timeout
    last=None
    while time.time()<end:
        last=fn()
        if last:
            return last
        time.sleep(interval)
    raise TimeoutError(f"timeout; last={last!r}")


def make_media(root:Path):
    ffmpeg=shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg required")
    video=root/"probe_video.mp4"
    audio=root/"probe_audio.wav"
    subprocess.run([
        ffmpeg,"-y","-f","lavfi","-i","testsrc2=size=320x180:rate=10:duration=6",
        "-vf","hue=H=2*PI*t:s=1.2","-an","-c:v","libx264","-pix_fmt","yuv420p",str(video)
    ],check=True,capture_output=True)
    subprocess.run([
        ffmpeg,"-y","-f","lavfi","-i",
        "aevalsrc=0.35*sin(2*PI*220*t)*(0.65+0.35*gt(mod(t\,0.5)\,0.42)):s=22050:d=6",
        "-ac","1","-c:a","pcm_s16le",str(audio)
    ],check=True,capture_output=True)
    return video,audio


def main():
    evidence=Path(os.environ.get("AIVE_PROBE_EVIDENCE","/tmp/aive-probe"))
    evidence.mkdir(parents=True,exist_ok=True)
    runtime=evidence/"runtime"
    media=evidence/"media"
    media.mkdir(parents=True,exist_ok=True)
    video,audio=make_media(media)

    env={**os.environ,
         "AIVE_HOST":"127.0.0.1","AIVE_PORT":"8099",
         "AIVE_RUNTIME":str(runtime),
         "AIVE_CORE_REF":os.environ.get("AIVE_CORE_REF", "MainV2")}
    log=(evidence/"stack.log").open("w")
    proc=subprocess.Popen([sys.executable,str(STACK)],cwd=str(BACKEND),env=env,stdout=log,stderr=subprocess.STDOUT)
    snapshots=[]
    try:
        wait_until(lambda: request("http://127.0.0.1:8099/api/system") if _ping() else None,60)
        core=request("http://127.0.0.1:8099/api/core/bootstrap",{"offline":True})
        if not core.get("bootstrapped") or core.get("requested_core_ref")!=env["AIVE_CORE_REF"] or core.get("core_branch")!="main":
            raise RuntimeError(f"validation core bootstrap failed: {core}")
        snapshots.append({"core":core})

        project=tool("project.create",{"name":"MainV2 Micro Production"})["project"]
        pid=project["id"]
        uv=upload(pid,video,"video/mp4")
        ua=upload(pid,audio,"audio/wav")
        video_id=uv["asset"]["id"]; audio_id=ua["asset"]["id"]
        wait_until(lambda: _assets_ready(pid,2),120)
        tool("project.prepare",{"project_id":pid})
        wait_until(lambda: _jobs_done(pid),180)

        init=tool("production.initialize",{"project_id":pid})
        if not init.get("guard_pass"):
            raise RuntimeError(f"production init guard failed: {init}")
        tool("production.sync_assets",{"project_id":pid})
        ingest=tool("production.advance",{"project_id":pid,"target_stage":"SOURCE_INGESTED"})
        snapshots.append({"source_ingested":ingest})
        if not ingest.get("advanced"):
            raise RuntimeError("SOURCE_INGESTED advance failed: "+json.dumps(ingest,sort_keys=True))
        tool("production.set_music_context",{
            "project_id":pid,"lyrics_status":"absent","genre":"synthetic verification pulse",
            "directing_use":"music timing only"
        })
        tool("production.analyze",{"project_id":pid})
        wait_until(lambda: _jobs_done(pid),240)
        tool("production.advance",{"project_id":pid,"target_stage":"REFERENCES_ANALYZED"})

        tool("operating.configure_v2",{
            "project_id":pid,"direction_authority":"reference_led","production_mode":"cinematic",
            "mission":"Verify the MainV2 stack with one tiny moving synthetic production.",
            "current_user_direction":"Synthetic verification fixture only; no external project canon.",
            "exact_next_action":"Use the supplied moving test pattern as the only visual source."
        })
        tool("approach.set_capabilities",{
            "project_id":pid,"capabilities":["source_video"],
            "approach_summary":"Single-source cinematic verification using the supplied moving synthetic video."
        })
        tool("operating.lock_canon",{
            "project_id":pid,"picture_language":"Moving synthetic test pattern used only as a verification fixture.",
            "items":["preserve source identity","preserve timing","no unrelated imagery"],
            "baseline_asset_id":video_id,
            "acceptance_statement":"Automated agent acceptance for synthetic verification fixture only."
        })
        tool("production.advance",{"project_id":pid,"target_stage":"APPROACH_ESTABLISHED"})

        tool("storyboard.set",{
            "project_id":pid,"target_fps":10,
            "summary":"One-shot six-second synthetic verification production.",
            "authority":"authorized_sandbox_agent_fixture",
            "entries":[{
                "shot_id":"shot-001","start_seconds":0,"end_seconds":6,
                "story_action":"The moving test pattern evolves continuously for the full micro-production.",
                "visual_media":"Supplied synthetic moving video only.",
                "animation_behavior":"Native continuous source motion with no identity substitution.",
                "transition":"Hard start and clean end; no inter-shot transition required.",
                "music_cues":["Follow the measured pulse and full six-second duration."]
            }]
        })
        tool("storyboard.lock",{"project_id":pid,"recorded_instruction":"Lock synthetic verification storyboard."})
        tool("production.advance",{"project_id":pid,"target_stage":"STORYBOARD_LOCKED"})

        tool("shots.build_packages",{"project_id":pid,"assignments":[{"shot_id":"shot-001","asset_ids":[video_id],"status":"ingested"}]})
        tool("production.advance",{"project_id":pid,"target_stage":"SHOT_PACKAGES_BUILT"})
        tool("proofs.record",{
            "project_id":pid,"shot_id":"shot-001","proof_asset_id":video_id,"production_mode":"cinematic",
            "checks":{
                "story_action_readable":True,"coverage_sufficient":True,"continuity_controlled":True,
                "shot_progression_present":True,"pacing_music_directed":True
            },
            "notes":"Synthetic verification proof."
        })
        tool("proofs.accept",{"project_id":pid,"shot_id":"shot-001","instruction":"Agent accepts synthetic verification proof only."})
        tool("proofs.finalize",{"project_id":pid,"instruction":"Finalize synthetic verification proof set."})
        tool("production.advance",{"project_id":pid,"target_stage":"SHOT_PROOFS_ACCEPTED"})

        fx=tool("fx.registry",{"project_id":pid})
        chosen=next((x for x in fx.get("effects",[]) if x.get("gate_status") not in {"unavailable","proof_required"} and (x.get("implementation") or {}).get("kind")!="runtime_transition"),None)
        if not chosen:
            raise RuntimeError("no production-approved non-transition FX available")
        tool("fx.set_requirements",{"project_id":pid,"effects":[{"id":chosen["id"]}],"transitions":[],"seed":302})
        tool("fx.lock",{"project_id":pid})
        tool("production.advance",{"project_id":pid,"target_stage":"FX_LOCKED"})

        tool("assembly.run",{"project_id":pid,"width":320,"height":180})
        wait_until(lambda: _jobs_done(pid),240)
        assembly=tool("assembly.status",{"project_id":pid})
        if not assembly.get("assembly_complete"):
            raise RuntimeError(f"assembly incomplete: {assembly}")
        source_url=str((assembly.get("asset") or {}).get("source_url") or "")
        if not source_url:
            raise RuntimeError(f"assembly source URL missing: {assembly}")
        with urllib.request.urlopen("http://127.0.0.1:8099"+source_url, timeout=120) as r:
            (evidence/"final_video.mp4").write_bytes(r.read())
        tool("production.advance",{"project_id":pid,"target_stage":"ASSEMBLED"})

        qc=tool("final_qc.run_technical",{"project_id":pid})
        if not qc.get("technical_pass"):
            raise RuntimeError(f"technical QC failed: {qc}")
        tool("final_qc.accept_creative",{
            "project_id":pid,"verified_shot_ids":["shot-001"],
            "mode_aware_checks":{
                "scripted_visuals_present":True,"production_mode_visible":True,
                "no_placeholder_substitution":True,"pacing_and_transitions_accepted":True,
                "full_export_reviewed_normal_speed":True
            },
            "instruction":"Automated agent acceptance of synthetic verification export only."
        })
        tool("production.advance",{"project_id":pid,"target_stage":"FINAL_QC_PASSED"})
        tool("archive.build",{"project_id":pid,"note":"Synthetic MainV2 micro-production verification."})
        av=tool("archive.verify",{"project_id":pid})
        if not av.get("ok"):
            raise RuntimeError(f"archive verify failed: {av}")
        final=tool("production.advance",{"project_id":pid,"target_stage":"ARCHIVED"})
        snapshots.append({"project_id":pid,"video_asset_id":video_id,"audio_asset_id":audio_id,"fx_id":chosen["id"],"final":final})
        (evidence/"result.json").write_text(json.dumps({"result":"PASS","snapshots":snapshots},indent=2),encoding="utf-8")
        print(json.dumps({"result":"PASS","project_id":pid,"stage":final.get("stage"),"fx_id":chosen["id"]},indent=2))
        return 0
    except Exception as exc:
        (evidence/"result.json").write_text(json.dumps({"result":"FAIL","error":str(exc),"snapshots":snapshots},indent=2),encoding="utf-8")
        raise
    finally:
        proc.terminate()
        try: proc.wait(10)
        except Exception: proc.kill()
        log.close()


def _ping():
    try:
        request("http://127.0.0.1:8099/api/system",timeout=2); return True
    except Exception:
        return False


def _assets_ready(pid,count):
    try:
        assets=request(f"http://127.0.0.1:8099/api/assets?project={pid}").get("assets",[])
        return assets if len([a for a in assets if a.get("status")=="ready" and a.get("sha256")])>=count else None
    except Exception:
        return None


def _jobs_done(pid):
    try:
        st=tool("project.status",{"project_id":pid})
        return st if int(st.get("active_jobs") or 0)==0 else None
    except Exception:
        return None


if __name__=="__main__":
    raise SystemExit(main())
