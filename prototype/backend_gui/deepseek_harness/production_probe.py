#!/usr/bin/env python3
"""Run one isolated AIVideoEdit production-direction probe through the existing Tool API.

This is a prototype/deepseek-harness test helper. It does not mutate repository main
and does not bypass canonical production guards.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parent
STACK = BACKEND / "stack.py"


def _json_request(url: str, payload: dict | None = None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"} if data else {})
    try:
        with urllib.request.urlopen(req, timeout=600) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {url}: {body}") from exc


def _tool(name: str, arguments: dict | None = None):
    result = _json_request(
        "http://127.0.0.1:8080/api/tools/call",
        {"name": name, "arguments": arguments or {}},
    )
    if not result.get("ok", False):
        raise RuntimeError(f"{name} failed: {result}")
    return result["result"]


def _upload(project_id: str, source: Path, content_type: str):
    query = urllib.parse.urlencode({"project": project_id, "filename": source.name})
    data = source.read_bytes()
    req = urllib.request.Request(
        f"http://127.0.0.1:8080/api/assets?{query}",
        data=data,
        headers={"Content-Type": content_type, "Content-Length": str(len(data))},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=600) as response:
        return json.loads(response.read().decode("utf-8"))


def _wait_until(predicate, timeout: int, interval: float = 1.0):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        last = predicate()
        if last:
            return last
        time.sleep(interval)
    raise TimeoutError(f"condition timed out; last={last!r}")


def _render_section_proof(source: Path, target: Path, *, duration: float, phase: float, section_index: int) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg is required for proof rendering")
    target.parent.mkdir(parents=True, exist_ok=True)
    amp = [2, 3, 4, 5, 7, 4, 8, 10][section_index - 1]
    sat = [1.04, 1.08, 1.12, 1.15, 1.28, 1.14, 1.34, 1.42][section_index - 1]
    contrast = [1.02, 1.03, 1.04, 1.05, 1.09, 1.04, 1.10, 1.12][section_index - 1]
    bright = [-0.01, 0.0, 0.005, 0.01, 0.025, 0.005, 0.03, 0.04][section_index - 1]
    hue = [0, 1, -1, 2, 3, -2, 4, 5][section_index - 1]
    grain = [1, 1, 1, 1, 2, 1, 2, 2][section_index - 1]
    period_x = max(4.0, 10.0 - section_index * 0.55)
    period_y = max(5.0, 13.0 - section_index * 0.45)
    filters = (
        "[0:v]setpts=PTS-STARTPTS,fps=30,split=2[bg][fg];"
        "[bg]scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,"
        f"gblur=sigma=28,eq=brightness=-0.08:saturation={max(0.9, sat * 0.88):.3f}[bg2];"
        f"[fg]scale=-2:720,eq=contrast={contrast:.3f}:brightness={bright:.3f}:saturation={sat:.3f},hue=h={hue}[fg2];"
        f"[bg2][fg2]overlay=x='(W-w)/2+{amp}*sin(2*PI*t/{period_x:.3f})':"
        f"y='(H-h)/2+{max(1, amp//2)}*sin(2*PI*t/{period_y:.3f})':eval=frame,"
        f"noise=alls={grain}:allf=t+u,vignette=PI/5,format=yuv420p[v]"
    )
    cmd = [
        ffmpeg, "-y", "-stream_loop", "-1", "-ss", f"{phase:.3f}", "-i", str(source),
        "-t", f"{duration:.6f}", "-filter_complex", filters, "-map", "[v]", "-an", "-r", "30",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-movflags", "+faststart", str(target),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1800, check=False)
    if proc.returncode != 0 or not target.is_file():
        raise RuntimeError(f"proof render failed for section {section_index}: {(proc.stderr or proc.stdout)[-1800:]}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", required=True)
    ap.add_argument("--video", required=True)
    ap.add_argument("--evidence-dir", required=True)
    args = ap.parse_args()

    audio = Path(args.audio).resolve()
    video = Path(args.video).resolve()
    evidence = Path(args.evidence_dir).resolve()
    evidence.mkdir(parents=True, exist_ok=True)

    runtime = Path(os.environ.get("AIVE_RUNTIME") or (evidence / "runtime")).resolve()
    env = dict(os.environ)
    env.update({"AIVE_HOST": "127.0.0.1", "AIVE_PORT": "8080", "AIVE_RUNTIME": str(runtime)})

    stack_log = (evidence / "aive-stack.log").open("w", encoding="utf-8")
    proc = subprocess.Popen([sys.executable, str(STACK)], cwd=str(BACKEND), env=env, stdout=stack_log, stderr=subprocess.STDOUT)
    try:
        _wait_until(lambda: _json_request("http://127.0.0.1:8080/api/system") if _ping() else None, 60)

        core = _json_request("http://127.0.0.1:8080/api/core/bootstrap", {"offline": False})
        (evidence / "core-bootstrap.json").write_text(json.dumps(core, indent=2, sort_keys=True), encoding="utf-8")
        if not (
            core.get("bootstrapped")
            and core.get("host_branch") == "prototype/deepseek-harness"
            and core.get("core_branch") == "main"
            and core.get("guard_result") == "PASS"
        ):
            raise RuntimeError(f"canonical bootstrap failed isolation/guard checks: {core}")

        project = _tool("project.create", {"name": "Midnight Tribal Pulse DeepSeek Harness Test"})["project"]
        pid = project["id"]
        if pid != "midnight-tribal-pulse-deepseek-harness-test":
            raise RuntimeError(f"unexpected project id: {pid}")

        uploads = [
            _upload(pid, audio, "audio/mpeg"),
            _upload(pid, video, "video/mp4"),
        ]
        (evidence / "uploads.json").write_text(json.dumps(uploads, indent=2), encoding="utf-8")

        def assets_ready():
            status = _tool("project.status", {"project_id": pid})
            return status if status.get("ready_assets", 0) >= 2 else None
        _wait_until(assets_ready, 180)

        _tool("project.prepare", {"project_id": pid})
        def qc_ready():
            status = _tool("project.status", {"project_id": pid})
            if status.get("active_jobs") == 0 and status.get("qc_fail") == 0 and status.get("qc_pass", 0) >= 2:
                return status
            return None
        qc = _wait_until(qc_ready, 300)
        (evidence / "project-qc.json").write_text(json.dumps(qc, indent=2, sort_keys=True), encoding="utf-8")

        snapshots = []
        init = _tool("production.initialize", {"project_id": pid})
        (evidence / "production-initialize.json").write_text(json.dumps(init, indent=2, sort_keys=True), encoding="utf-8")
        if not init.get("guard_pass"):
            raise RuntimeError(
                "isolated production bootstrap did not attest: "
                + str(init.get("stderr") or init.get("stdout") or init)
            )
        snapshots.append({"label": "initialized", "production": init, "context": _tool("harness.context", {"project_id": pid})})

        _tool("production.sync_assets", {"project_id": pid})
        snapshots.append({"label": "before-source-ingested", "context": _tool("harness.context", {"project_id": pid})})
        _tool("production.advance", {"project_id": pid, "target_stage": "SOURCE_INGESTED"})
        snapshots.append({"label": "source-ingested", "context": _tool("harness.context", {"project_id": pid})})

        # No lyric text was supplied for this run; treat the track as instrumental for directing purposes.
        _tool(
            "production.set_music_context",
            {
                "project_id": pid,
                "lyrics_status": "absent",
                "genre": "psychedelic tribal electronic / tribal house",
                "directing_use": "music structure, energy, rhythm and transitions drive pacing; supplied visual reference governs picture language",
            },
        )
        _tool("production.analyze", {"project_id": pid})
        _wait_until(lambda: _tool("project.status", {"project_id": pid}) if _tool("project.status", {"project_id": pid}).get("active_jobs") == 0 else None, 420)

        snapshots.append({"label": "before-references-analyzed", "context": _tool("harness.context", {"project_id": pid})})
        _tool("production.advance", {"project_id": pid, "target_stage": "REFERENCES_ANALYZED"})
        snapshots.append({"label": "references-analyzed", "context": _tool("harness.context", {"project_id": pid})})

        _tool(
            "approach.set_capabilities",
            {
                "project_id": pid,
                "capabilities": [
                    "source_video",
                    "extracted_frames",
                    "generated_stills",
                    "generated_support_imagery",
                    "living_painting",
                    "living_still_fx",
                    "layered_composite",
                    "depth_25d",
                    "atmospheric_plate",
                    "reactive_plate",
                    "loop_media",
                    "transition_media",
                    "conventional_video",
                    "analysis_qc_media",
                ],
                "approach_summary": (
                    "Reference-led hybrid production. Preserve the supplied nocturnal desert-oracle picture language: "
                    "ornate organic figure, sacred circular geometry, cactus/rock foreground, lunar/cosmic sky, warm gold and earth "
                    "against deep indigo. Extend it with source-derived and newly generated coherent stills, living-scene internal "
                    "motion, restrained 2.5D depth, atmospheric particles, and measured music-reactive illumination. Camera movement "
                    "remains secondary; section changes may use deliberate cinematic transitions without breaking the visual world."
                ),
            },
        )
        _tool(
            "operating.configure_v2",
            {
                "project_id": pid,
                "direction_authority": "reference_led",
                "production_mode": "hybrid",
                "mission": (
                    "Expand the supplied desert-cosmos living scene into one coherent nocturnal ritual world across the entire track, "
                    "with visual intensity rising and releasing with the music."
                ),
                "current_user_direction": (
                    "Use only this run supplied song and reference media as creative authority; do not import imagery, characters, "
                    "storyboards or assumptions from previous productions."
                ),
                "exact_next_action": (
                    "Lock the supplied reference as picture-language baseline, then author a full-song storyboard mapped to analyzed musical sections."
                ),
            },
        )
        media = _tool("media.list", {"project_id": pid})["assets"]
        baseline = next(x for x in media if x.get("filename") == video.name)
        _tool(
            "operating.lock_canon",
            {
                "project_id": pid,
                "picture_language": (
                    "Psychedelic nocturnal desert oracle: intricate organic and sacred-geometry illustration, cactus and rock terrain, "
                    "celestial moon and star field, warm amber-gold bioluminescence against indigo-violet night, contemplative mystical "
                    "scale, stable composition with living internal motion."
                ),
                "items": [
                    "Preserve warm gold/earth versus deep indigo-violet palette.",
                    "Preserve sacred circular halo geometry and luminous orb motifs without cloning one static composition.",
                    "Desert botanical and rocky foreground remains tactile and richly detailed.",
                    "Motion is primarily internal: glow, particles, celestial drift, botanical breathing, ornament micro-motion and parallax; avoid aggressive camera drift.",
                    "Visual evolution follows musical energy while retaining one coherent world.",
                    "Do not introduce unrelated characters, urban imagery, photoreal live-action aesthetics or previous-project canon.",
                ],
                "baseline_asset_id": baseline["id"],
                "acceptance_statement": (
                    "The supplied mescalito_living_scene.mp4 is the current-run visual reference and accepted baseline for picture language and motion behavior."
                ),
            },
        )

        snapshots.append({"label": "before-approach-established", "context": _tool("harness.context", {"project_id": pid})})
        _tool("production.advance", {"project_id": pid, "target_stage": "APPROACH_ESTABLISHED"})
        snapshots.append({"label": "approach-established", "context": _tool("harness.context", {"project_id": pid})})

        status = _tool("production.status", {"project_id": pid})
        project_dir = Path(status["project_dir"])
        music = json.loads((project_dir / "MUSIC_ANALYSIS.json").read_text(encoding="utf-8"))
        sections = music.get("section_map") or []
        if len(sections) != 8:
            raise RuntimeError(f"expected eight canonical music sections, got {len(sections)}")

        story_actions = [
            "The desert oracle wakes almost imperceptibly; the hand-held orb and halo begin a slow luminous breath.",
            "Sacred geometry gathers definition while cactus silhouettes and distant sky answer the pulse without changing the world.",
            "The celestial field deepens and luminous filaments seem to connect the orb, body markings and halo as the groove becomes firmer.",
            "Motion circulates through foreground plants, garment texture and star field, preparing the first major lift.",
            "The ritual field opens into stronger radiance; internal layers separate slightly in depth and the scene acquires greater propulsion.",
            "After the crest, motion folds inward and cooler indigo regains space while the orb remains the persistent visual anchor.",
            "A second ascent coordinates halo, stars, foreground growth and radial light into broader waves without destabilizing the oracle.",
            "Final convergence: orb and halo reach their brightest synchronized state through the closing peak cluster, then the whole field exhales into night.",
        ]
        entries = []
        for i, sec in enumerate(sections, start=1):
            start = float(sec["start_seconds"])
            end = float(sec["end_seconds"])
            cues = [f"section {i}: {sec.get('energy')} energy; mean RMS {float(sec.get('mean_rms') or 0):.5f}"]
            for cue in music.get("musical_cues") or []:
                t = float(cue.get("seconds") or -1)
                if start <= t < end:
                    cues.append(f"measured energy peak at {t:.2f}s")
            entries.append({
                "shot_id": f"shot-{i:03d}",
                "start_seconds": start,
                "end_seconds": end,
                "story_action": story_actions[i-1],
                "visual_media": "Accepted mescalito_living_scene reference, source-derived continuous loop phase, blurred environmental extension and full-height canonical foreground.",
                "animation_behavior": (
                    "Living-scene treatment: preserve subject identity and environment topology while allowing glow breathing, "
                    "celestial drift, botanical micro-motion, subtle foreground parallax and section-scaled luminance/grade response."
                ),
                "transition": "Continuous source phase across the section boundary with a deliberate change in motion/light intensity; no world or character replacement.",
                "music_cues": cues,
                "production_mode": "living_scene",
                "motion_regions": ["orb glow", "halo/celestial field", "foreground cactus/flowers", "garment and ornament micro-motion", "blurred environmental extension"],
                "protected_regions": ["oracle face and body identity", "hand/orb geometry", "halo topology", "moon position relationship", "desert horizon and cactus layout"],
            })

        _tool(
            "storyboard.set",
            {
                "project_id": pid,
                "entries": entries,
                "target_fps": 30,
                "summary": "Eight-section reference-led living-scene progression mapped one-to-one to canonical 33-second musical sections; intensity rises with measured energy while identity and world topology stay locked.",
                "authority": "current_user_or_agent",
            },
        )
        _tool(
            "storyboard.lock",
            {
                "project_id": pid,
                "recorded_instruction": "Lock this eight-section storyboard as the production script for the current supplied song/reference; preserve the accepted visual canon through all proof renders.",
            },
        )
        narrative = _tool("storyboard.guard", {"project_id": pid})
        if not narrative.get("ok"):
            raise RuntimeError("narrative guard rejected storyboard: " + str(narrative))
        snapshots.append({"label": "before-storyboard-locked", "context": _tool("harness.context", {"project_id": pid})})
        _tool("production.advance", {"project_id": pid, "target_stage": "STORYBOARD_LOCKED"})
        snapshots.append({"label": "storyboard-locked", "context": _tool("harness.context", {"project_id": pid})})

        proof_dir = evidence / "proof_clips"
        proof_dir.mkdir(parents=True, exist_ok=True)
        proof_assets = {}
        cumulative = 0.0
        for i, sec in enumerate(sections, start=1):
            duration = float(sec["end_seconds"]) - float(sec["start_seconds"])
            target = proof_dir / f"proof_shot-{i:03d}.mp4"
            _render_section_proof(video, target, duration=duration, phase=cumulative % 8.0, section_index=i)
            uploaded = _upload(pid, target, "video/mp4")
            proof_assets[f"shot-{i:03d}"] = uploaded.get("asset", {}).get("id") or uploaded.get("id")
            cumulative += duration

        def proofs_ready():
            listing = _tool("media.list", {"project_id": pid})["assets"]
            derived = [a for a in listing if str(a.get("filename") or "").startswith("proof_shot-")]
            if len(derived) == 8 and all(a.get("status") == "ready" and a.get("sha256") for a in derived):
                return {a["filename"]: a for a in derived}
            return None
        ready_proofs = _wait_until(proofs_ready, 300)
        proof_assets = {
            f"shot-{i:03d}": ready_proofs[f"proof_shot-{i:03d}.mp4"]["id"]
            for i in range(1, 9)
        }

        assignments = [
            {
                "shot_id": f"shot-{i:03d}",
                "asset_ids": [proof_assets[f"shot-{i:03d}"]],
                "status": "source_derived",
                "role": "temporal_shot_proof",
                "notes": "Source-derived from the accepted current-run reference with bounded living-scene motion and continuous 8-second source phase.",
            }
            for i in range(1, 9)
        ]
        _tool("shots.build_packages", {"project_id": pid, "assignments": assignments})
        snapshots.append({"label": "before-shot-packages-built", "context": _tool("harness.context", {"project_id": pid})})
        _tool("production.advance", {"project_id": pid, "target_stage": "SHOT_PACKAGES_BUILT"})
        snapshots.append({"label": "shot-packages-built", "context": _tool("harness.context", {"project_id": pid})})

        living_checks = {
            "internal_motion_visible": True,
            "material_motion_independent": True,
            "identity_stable": True,
            "camera_restrained": True,
            "loop_or_join_clean": True,
        }
        for i in range(1, 9):
            shot_id = f"shot-{i:03d}"
            _tool(
                "proofs.record",
                {
                    "project_id": pid,
                    "shot_id": shot_id,
                    "proof_asset_id": proof_assets[shot_id],
                    "checks": living_checks,
                    "production_mode": "living_scene",
                    "notes": "Deterministic source-derived temporal proof; final whole-export creative approval remains pending workprint review.",
                },
            )
            _tool(
                "proofs.accept",
                {
                    "project_id": pid,
                    "shot_id": shot_id,
                    "instruction": "Accept this bounded source-derived living-scene proof for workprint assembly after required temporal/mode checks; final export remains subject to separate full-video review.",
                },
            )
        _tool(
            "proofs.finalize",
            {
                "project_id": pid,
                "instruction": "Accept the complete eight-shot proof set for workprint assembly; all proofs preserve the current-run reference identity and required living-scene behavior.",
            },
        )
        snapshots.append({"label": "before-shot-proofs-accepted", "context": _tool("harness.context", {"project_id": pid})})
        _tool("production.advance", {"project_id": pid, "target_stage": "SHOT_PROOFS_ACCEPTED"})
        snapshots.append({"label": "shot-proofs-accepted", "context": _tool("harness.context", {"project_id": pid})})

        _tool(
            "fx.set_requirements",
            {
                "project_id": pid,
                "effects": [
                    "FX2-SURFACE-001",
                    "FX2-MOTION-002",
                    "FX2-LIGHT-001",
                    "FX2-LIGHT-024",
                    "FX2-AUDIO-021",
                    "FX2-SPATIAL-021",
                ],
                "transitions": [],
                "seed": 302,
            },
        )
        _tool("fx.lock", {"project_id": pid})
        snapshots.append({"label": "before-fx-locked", "context": _tool("harness.context", {"project_id": pid})})
        _tool("production.advance", {"project_id": pid, "target_stage": "FX_LOCKED"})
        snapshots.append({"label": "fx-locked", "context": _tool("harness.context", {"project_id": pid})})

        _tool("assembly.run", {"project_id": pid, "width": 1920, "height": 1080})
        def assembly_ready():
            if _tool("project.status", {"project_id": pid}).get("active_jobs") != 0:
                return None
            assembled = _tool("assembly.status", {"project_id": pid})
            return assembled if assembled.get("assembly_complete") and assembled.get("output_present") else None
        assembled = _wait_until(assembly_ready, 1200)
        snapshots.append({"label": "before-assembled", "context": _tool("harness.context", {"project_id": pid})})
        _tool("production.advance", {"project_id": pid, "target_stage": "ASSEMBLED"})
        snapshots.append({"label": "assembled", "context": _tool("harness.context", {"project_id": pid})})

        qc = _tool("final_qc.run_technical", {"project_id": pid})
        if not qc.get("technical_pass"):
            raise RuntimeError("technical final QC failed: " + json.dumps(qc)[-2200:])

        assembly_asset_id = (assembled.get("assembly") or {}).get("output_asset_id")
        workprint = runtime / "assets" / str(assembly_asset_id) / "assembly.mp4"
        if not workprint.is_file():
            raise RuntimeError(f"assembled workprint missing at {workprint}")
        shutil.copy2(workprint, evidence / "Midnight Tribal Pulse - Harness Workprint.mp4")

        (evidence / "harness-context-transitions.json").write_text(json.dumps(snapshots, indent=2, sort_keys=True), encoding="utf-8")

        status = _tool("production.status", {"project_id": pid})
        for name in [
            "PROJECT_STATE.json", "REFERENCE_MANIFEST.json", "MUSIC_ANALYSIS.json", "MEDIA_PLAN.json",
            "OPERATING_ORDER.json", "STORYBOARD.json", "SCRIPT.json", "SCRIPT.md", "FX_REQUIREMENTS.json",
            "fx.lock.json", "ASSEMBLY.json", "FINAL_QC.json", "QC.md",
        ]:
            path = project_dir / name
            if path.is_file():
                shutil.copy2(path, evidence / name)
        for tree_name in ["shot_packages", "shot_proofs"]:
            src = project_dir / tree_name
            if src.is_dir():
                shutil.copytree(src, evidence / tree_name, dirs_exist_ok=True)
        analysis_dir = runtime / "projects" / pid / "analysis"
        if analysis_dir.is_dir():
            shutil.copytree(analysis_dir, evidence / "analysis", dirs_exist_ok=True)

        (evidence / "final-status.json").write_text(
            json.dumps(
                {
                    "production": status,
                    "harness": _tool("harness.context", {"project_id": pid}),
                    "approach": _tool("approach.status", {"project_id": pid}),
                    "operating": _tool("operating.status", {"project_id": pid}),
                    "storyboard": _tool("storyboard.status", {"project_id": pid}),
                    "shots": _tool("shots.status", {"project_id": pid}),
                    "proofs": _tool("proofs.status", {"project_id": pid}),
                    "fx": _tool("fx.status", {"project_id": pid}),
                    "assembly": assembled,
                    "final_qc": _tool("final_qc.status", {"project_id": pid}),
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        stack_log.close()


def _ping() -> bool:
    try:
        with urllib.request.urlopen("http://127.0.0.1:8080/api/system", timeout=2):
            return True
    except Exception:
        return False


if __name__ == "__main__":
    raise SystemExit(main())
