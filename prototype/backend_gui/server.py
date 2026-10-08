#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import re
import shutil
import subprocess
import threading
import time
import uuid
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
RUNTIME = Path(os.environ.get("AIVE_RUNTIME", str(ROOT / ".runtime"))).resolve()
ASSET_ROOT = RUNTIME / "assets"
PROJECT_ROOT = RUNTIME / "projects"
STATE_FILE = RUNTIME / "state.json"
MAX_UPLOAD = int(os.environ.get("AIVE_MAX_UPLOAD", str(2 * 1024 * 1024 * 1024)))
MAX_JOBS = 250
MAX_ASSETS = 500

LOCK = threading.RLock()
STATE = {"version": 1, "projects": [], "jobs": [], "assets": []}


def now() -> float:
    return time.time()


def safe_name(name: str, fallback: str = "item") -> str:
    name = Path(unquote(name or fallback)).name
    clean = re.sub(r"[^A-Za-z0-9._ -]+", "_", name).strip(" .")
    return clean[:180] or fallback


def slugify(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", (value or "project").lower()).strip("-")
    return value[:64] or "project"


def public_asset(asset: dict) -> dict:
    return {k: v for k, v in asset.items() if k not in {"local_path", "folder"}}


def save_state() -> None:
    with LOCK:
        RUNTIME.mkdir(parents=True, exist_ok=True)
        tmp = STATE_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(STATE, indent=2), encoding="utf-8")
        tmp.replace(STATE_FILE)


def ensure_default_project() -> None:
    if STATE["projects"]:
        return
    p = {"id": "prototype", "name": "Prototype", "created_at": now(), "updated_at": now()}
    STATE["projects"].append(p)
    (PROJECT_ROOT / p["id"]).mkdir(parents=True, exist_ok=True)


def load_state() -> None:
    RUNTIME.mkdir(parents=True, exist_ok=True)
    ASSET_ROOT.mkdir(parents=True, exist_ok=True)
    PROJECT_ROOT.mkdir(parents=True, exist_ok=True)
    if STATE_FILE.is_file():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                STATE["version"] = int(data.get("version", 1))
                STATE["projects"] = data.get("projects", [])[-100:]
                STATE["jobs"] = data.get("jobs", [])[-MAX_JOBS:]
                STATE["assets"] = data.get("assets", [])[-MAX_ASSETS:]
        except Exception as exc:
            print(f"WARN: state recovery failed: {exc}")
    for job in STATE["jobs"]:
        if job.get("status") in {"queued", "running"}:
            job["status"] = "interrupted"
            job["result"] = "Backend restarted before this job completed."
            job["finished_at"] = now()
    ensure_default_project()
    save_state()


def capability(name: str, command: list[str]) -> dict:
    found = shutil.which(command[0])
    if not found:
        return {"name": name, "available": False, "detail": "not found"}
    try:
        proc = subprocess.run(command, capture_output=True, text=True, timeout=3)
        text = (proc.stdout or proc.stderr).splitlines()
        detail = text[0] if text else found
        return {"name": name, "available": proc.returncode == 0, "detail": detail[:180]}
    except Exception as exc:
        return {"name": name, "available": False, "detail": str(exc)}


def capabilities() -> list[dict]:
    return [
        capability("Python", ["python3", "--version"]),
        capability("FFmpeg", ["ffmpeg", "-version"]),
        capability("FFprobe", ["ffprobe", "-version"]),
        capability("Git", ["git", "--version"]),
    ]


def find_project(project_id: str) -> dict | None:
    return next((p for p in STATE["projects"] if p["id"] == project_id), None)


def find_asset(asset_id: str) -> dict | None:
    return next((a for a in STATE["assets"] if a["id"] == asset_id), None)


def asset_source(asset: dict) -> Path:
    return Path(asset["local_path"])


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def add_job(job_type: str, project: str, asset_id: str | None = None) -> dict:
    job = {
        "id": uuid.uuid4().hex[:10], "type": job_type, "project": project or "prototype",
        "asset_id": asset_id, "status": "queued", "created_at": now(), "started_at": None,
        "finished_at": None, "progress": 0, "result": None,
    }
    with LOCK:
        STATE["jobs"].append(job)
        STATE["jobs"] = STATE["jobs"][-MAX_JOBS:]
        save_state()
    return job


def update_job(job_id: str, **changes) -> None:
    with LOCK:
        job = next((x for x in STATE["jobs"] if x["id"] == job_id), None)
        if job:
            job.update(changes)
            save_state()


def update_asset(asset_id: str, **changes) -> None:
    with LOCK:
        asset = find_asset(asset_id)
        if asset:
            asset.update(changes)
            asset["updated_at"] = now()
            save_state()


def ffprobe_metadata(source: Path) -> tuple[dict, dict]:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RuntimeError("FFprobe is not installed")
    proc = subprocess.run([ffprobe, "-v", "error", "-show_format", "-show_streams", "-of", "json", str(source)], capture_output=True, text=True, timeout=60, check=True)
    info = json.loads(proc.stdout)
    fmt = info.get("format", {})
    video = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), {})
    audio = next((s for s in info.get("streams", []) if s.get("codec_type") == "audio"), {})
    duration = float(fmt.get("duration") or video.get("duration") or audio.get("duration") or 0)
    metadata = {
        "duration_seconds": round(duration, 3), "format": fmt.get("format_name"),
        "size_bytes": int(fmt.get("size") or source.stat().st_size), "bit_rate": int(fmt.get("bit_rate") or 0),
        "video_codec": video.get("codec_name"), "width": video.get("width"), "height": video.get("height"),
        "fps": video.get("avg_frame_rate"), "pixel_format": video.get("pix_fmt"), "audio_codec": audio.get("codec_name"),
        "sample_rate": audio.get("sample_rate"), "channels": audio.get("channels"),
    }
    return metadata, info


def analyze_asset(job_id: str, asset_id: str) -> None:
    update_job(job_id, status="running", started_at=now(), progress=10)
    asset = find_asset(asset_id)
    if not asset:
        return update_job(job_id, status="failed", result="asset not found", finished_at=now())
    source = asset_source(asset)
    update_asset(asset_id, status="analyzing")
    try:
        metadata, _ = ffprobe_metadata(source)
        update_job(job_id, progress=55)
        thumb_url = None
        if metadata.get("video_codec"):
            ffmpeg = shutil.which("ffmpeg")
            if not ffmpeg:
                raise RuntimeError("FFmpeg is not installed")
            thumb = source.parent / "thumbnail.jpg"
            duration = metadata.get("duration_seconds") or 0
            seek = min(max(duration * 0.15, 0.0), 2.0) if duration else 0.0
            subprocess.run([ffmpeg, "-y", "-ss", f"{seek:.3f}", "-i", str(source), "-frames:v", "1", "-vf", "scale=640:-2", str(thumb)], capture_output=True, text=True, timeout=90, check=True)
            thumb_url = f"/media/{asset_id}/thumbnail.jpg"
        digest = sha256_file(source)
        source_url = f"/media/{asset_id}/{source.name}"
        update_asset(asset_id, status="ready", metadata=metadata, sha256=digest, source_url=source_url, thumbnail_url=thumb_url, error=None)
        summary = f"{metadata.get('width') or 'audio'}x{metadata.get('height') or '-'} · {metadata.get('duration_seconds')}s · {metadata.get('video_codec') or metadata.get('audio_codec') or metadata.get('format')}"
        update_job(job_id, status="complete", progress=100, result=summary, finished_at=now())
    except Exception as exc:
        message = str(exc)[:500]
        update_asset(asset_id, status="failed", error=message)
        update_job(job_id, status="failed", progress=100, result=message, finished_at=now())


def make_proxy(job_id: str, asset_id: str) -> None:
    update_job(job_id, status="running", started_at=now(), progress=5)
    asset = find_asset(asset_id)
    if not asset:
        return update_job(job_id, status="failed", result="asset not found", finished_at=now())
    source = asset_source(asset)
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return update_job(job_id, status="failed", result="FFmpeg is not installed", finished_at=now())
    metadata = asset.get("metadata") or {}
    if not metadata.get("video_codec"):
        return update_job(job_id, status="failed", result="proxy requires a video asset", finished_at=now())
    target = source.parent / "proxy.mp4"
    try:
        cmd = [ffmpeg, "-y", "-i", str(source), "-vf", "scale='min(1280,iw)':-2", "-c:v", "libx264", "-preset", "veryfast", "-crf", "24", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(target)]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        if proc.returncode != 0:
            raise RuntimeError((proc.stderr or "FFmpeg proxy failed")[-900:])
        update_asset(asset_id, proxy_url=f"/media/{asset_id}/proxy.mp4", proxy_size_bytes=target.stat().st_size)
        update_job(job_id, status="complete", progress=100, result=f"Proxy ready · {target.stat().st_size / 1048576:.1f} MB", finished_at=now())
    except Exception as exc:
        update_job(job_id, status="failed", progress=100, result=str(exc)[:600], finished_at=now())


def extract_review_frames(job_id: str, asset_id: str) -> None:
    update_job(job_id, status="running", started_at=now(), progress=5)
    asset = find_asset(asset_id)
    if not asset:
        return update_job(job_id, status="failed", result="asset not found", finished_at=now())
    source = asset_source(asset)
    ffmpeg = shutil.which("ffmpeg")
    metadata = asset.get("metadata") or {}
    if not ffmpeg or not metadata.get("video_codec"):
        return update_job(job_id, status="failed", result="review frames require FFmpeg and video", finished_at=now())
    duration = float(metadata.get("duration_seconds") or 0)
    frames_dir = source.parent / "review_frames"
    frames_dir.mkdir(exist_ok=True)
    urls = []
    try:
        points = [0.08, 0.25, 0.42, 0.58, 0.75, 0.92]
        for idx, ratio in enumerate(points, start=1):
            ts = max(0.0, duration * ratio) if duration else float(idx - 1)
            out = frames_dir / f"frame_{idx:02d}.jpg"
            proc = subprocess.run([ffmpeg, "-y", "-ss", f"{ts:.3f}", "-i", str(source), "-frames:v", "1", "-vf", "scale=480:-2", str(out)], capture_output=True, text=True, timeout=120)
            if proc.returncode == 0 and out.is_file():
                urls.append(f"/media/{asset_id}/review_frames/{out.name}")
            update_job(job_id, progress=min(90, 10 + idx * 13))
        if not urls:
            raise RuntimeError("FFmpeg could not extract review frames")
        update_asset(asset_id, review_frames=urls)
        update_job(job_id, status="complete", progress=100, result=f"{len(urls)} review frames ready", finished_at=now())
    except Exception as exc:
        update_job(job_id, status="failed", progress=100, result=str(exc)[:600], finished_at=now())


def qc_asset(job_id: str, asset_id: str) -> None:
    update_job(job_id, status="running", started_at=now(), progress=10)
    asset = find_asset(asset_id)
    if not asset:
        return update_job(job_id, status="failed", result="asset not found", finished_at=now())
    source = asset_source(asset)
    ffmpeg = shutil.which("ffmpeg")
    try:
        metadata, _ = ffprobe_metadata(source)
        update_job(job_id, progress=45)
        errors, warnings = [], []
        if source.stat().st_size <= 0:
            errors.append("empty file")
        if metadata.get("duration_seconds", 0) <= 0:
            errors.append("duration unavailable or zero")
        if metadata.get("video_codec") and (not metadata.get("width") or not metadata.get("height")):
            errors.append("video dimensions unavailable")
        decode_tail = ""
        if ffmpeg:
            proc = subprocess.run([ffmpeg, "-v", "error", "-i", str(source), "-map", "0:v?", "-map", "0:a?", "-f", "null", "-"], capture_output=True, text=True, timeout=3600)
            decode_tail = (proc.stderr or "").strip()[-1200:]
            if proc.returncode != 0:
                errors.append("decode verification failed")
            elif decode_tail:
                warnings.append("decoder reported non-fatal messages")
        else:
            warnings.append("FFmpeg unavailable; decode verification skipped")
        status = "pass" if not errors else "fail"
        qc = {"status": status, "checked_at": now(), "errors": errors, "warnings": warnings, "decode_log_tail": decode_tail}
        update_asset(asset_id, qc=qc)
        update_job(job_id, status="complete" if status == "pass" else "failed", progress=100, result=f"QC {status.upper()}" + (f" · {', '.join(errors)}" if errors else ""), finished_at=now())
    except Exception as exc:
        update_asset(asset_id, qc={"status": "fail", "checked_at": now(), "errors": [str(exc)[:400]], "warnings": []})
        update_job(job_id, status="failed", progress=100, result=str(exc)[:600], finished_at=now())


def run_ffmpeg_check(job_id: str) -> None:
    update_job(job_id, status="running", started_at=now(), progress=25)
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return update_job(job_id, status="failed", progress=100, result="FFmpeg is not installed.", finished_at=now())
    proc = subprocess.run([ffmpeg, "-version"], capture_output=True, text=True, timeout=5)
    result = (proc.stdout or proc.stderr).splitlines()[0]
    update_job(job_id, status="complete" if proc.returncode == 0 else "failed", progress=100, result=result, finished_at=now())


def dispatch_job(job: dict) -> None:
    handlers = {
        "ffmpeg_check": lambda: run_ffmpeg_check(job["id"]),
        "analyze_media": lambda: analyze_asset(job["id"], job["asset_id"]),
        "make_proxy": lambda: make_proxy(job["id"], job["asset_id"]),
        "extract_review_frames": lambda: extract_review_frames(job["id"], job["asset_id"]),
        "qc_media": lambda: qc_asset(job["id"], job["asset_id"]),
    }
    fn = handlers.get(job["type"])
    if not fn:
        update_job(job["id"], status="failed", progress=100, result=f"unknown job type: {job['type']}", finished_at=now())
        return
    threading.Thread(target=fn, daemon=True).start()


def project_manifest(project_id: str) -> dict:
    project = find_project(project_id)
    assets = [public_asset(a) for a in STATE["assets"] if a.get("project") == project_id]
    jobs = [j for j in STATE["jobs"] if j.get("project") == project_id]
    return {"schema": "aivideoedit.backend-project.v1", "generated_at": now(), "project": project, "assets": assets, "jobs": jobs[-100:]}


class Handler(SimpleHTTPRequestHandler):
    server_version = "AIVideoEditAlpha/0.1"

    def log_message(self, fmt, *args):
        print(f"[{self.log_date_time_string()}] {fmt % args}")

    def translate_path(self, path: str) -> str:
        parsed = urlparse(path).path
        if parsed == "/":
            parsed = "/index.html"
        return str(STATIC / parsed.lstrip("/"))

    def send_json(self, payload, status=200):
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8"))

    def runtime_target(self, asset_id: str, relative: str) -> Path | None:
        base = (ASSET_ROOT / asset_id).resolve()
        target = (base / unquote(relative)).resolve()
        try:
            target.relative_to(base)
        except ValueError:
            return None
        return target

    def serve_runtime_file(self, asset_id: str, relative: str):
        target = self.runtime_target(asset_id, relative)
        if not target or not target.is_file():
            return self.send_error(404)
        size = target.stat().st_size
        start, end, status = 0, size - 1, 200
        range_header = self.headers.get("Range")
        if range_header and range_header.startswith("bytes="):
            try:
                spec = range_header[6:].split(",", 1)[0]
                left, right = spec.split("-", 1)
                if left:
                    start = int(left)
                if right:
                    end = min(int(right), size - 1)
                if start > end or start >= size:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{size}")
                    self.end_headers()
                    return
                status = 206
            except Exception:
                start, end, status = 0, size - 1, 200
        length = end - start + 1
        self.send_response(status)
        self.send_header("Content-Type", mimetypes.guess_type(str(target))[0] or "application/octet-stream")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(length))
        if status == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        with target.open("rb") as fh:
            fh.seek(start)
            remaining = length
            while remaining > 0:
                chunk = fh.read(min(1024 * 1024, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)
        if path.startswith("/media/"):
            parts = path.strip("/").split("/", 2)
            if len(parts) == 3:
                return self.serve_runtime_file(parts[1], parts[2])
        if path == "/api/health":
            return self.send_json({"ok": True, "service": "aivideoedit-alpha", "version": "0.1.0-alpha", "pid": os.getpid(), "workspace": str(RUNTIME)})
        if path == "/api/capabilities":
            return self.send_json({"capabilities": capabilities()})
        if path == "/api/projects":
            with LOCK:
                return self.send_json({"projects": list(STATE["projects"])})
        if path == "/api/jobs":
            project = (params.get("project") or [None])[0]
            with LOCK:
                jobs = STATE["jobs"]
                if project:
                    jobs = [j for j in jobs if j.get("project") == project]
                return self.send_json({"jobs": list(reversed(jobs[-75:]))})
        if path == "/api/assets":
            project = (params.get("project") or [None])[0]
            with LOCK:
                assets = STATE["assets"]
                if project:
                    assets = [a for a in assets if a.get("project") == project]
                return self.send_json({"assets": [public_asset(a) for a in reversed(assets[-100:])]})
        if path.startswith("/api/assets/"):
            asset_id = path.rsplit("/", 1)[-1]
            with LOCK:
                asset = find_asset(asset_id)
                return self.send_json({"asset": public_asset(asset) if asset else None}, 200 if asset else 404)
        if path.startswith("/api/projects/") and path.endswith("/manifest"):
            parts = path.strip("/").split("/")
            project_id = parts[2]
            with LOCK:
                if not find_project(project_id):
                    return self.send_json({"error": "project not found"}, 404)
                return self.send_json(project_manifest(project_id))
        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            if path == "/api/projects":
                return self.create_project()
            if path == "/api/assets":
                return self.receive_asset(parsed)
            if path == "/api/jobs":
                return self.receive_job()
        except json.JSONDecodeError:
            return self.send_json({"error": "invalid json"}, 400)
        except Exception as exc:
            return self.send_json({"error": str(exc)[:600]}, 500)
        return self.send_json({"error": "not found"}, 404)

    def do_DELETE(self):
        path = urlparse(self.path).path
        if path.startswith("/api/assets/"):
            asset_id = path.rsplit("/", 1)[-1]
            with LOCK:
                asset = find_asset(asset_id)
                if not asset:
                    return self.send_json({"error": "asset not found"}, 404)
                folder = Path(asset["folder"])
                STATE["assets"] = [a for a in STATE["assets"] if a["id"] != asset_id]
                save_state()
            shutil.rmtree(folder, ignore_errors=True)
            return self.send_json({"ok": True})
        return self.send_json({"error": "not found"}, 404)

    def create_project(self):
        data = self.read_json()
        name = str(data.get("name") or "New Project").strip()[:100]
        base = slugify(name)
        project_id = base
        n = 2
        with LOCK:
            while find_project(project_id):
                project_id = f"{base}-{n}"
                n += 1
            project = {"id": project_id, "name": name, "created_at": now(), "updated_at": now()}
            STATE["projects"].append(project)
            (PROJECT_ROOT / project_id).mkdir(parents=True, exist_ok=True)
            save_state()
        return self.send_json({"project": project}, 201)

    def receive_asset(self, parsed):
        params = parse_qs(parsed.query)
        filename = safe_name((params.get("filename") or ["upload.bin"])[0], "upload.bin")
        project = (params.get("project") or ["prototype"])[0][:64]
        if not find_project(project):
            return self.send_json({"error": "project not found"}, 404)
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return self.send_json({"error": "empty upload"}, 400)
        if length > MAX_UPLOAD:
            return self.send_json({"error": "upload too large", "max_bytes": MAX_UPLOAD}, 413)
        asset_id = uuid.uuid4().hex[:12]
        folder = ASSET_ROOT / asset_id
        folder.mkdir(parents=True, exist_ok=False)
        target = folder / filename
        remaining = length
        try:
            with target.open("wb") as fh:
                while remaining:
                    chunk = self.rfile.read(min(1024 * 1024, remaining))
                    if not chunk:
                        raise IOError("upload ended early")
                    fh.write(chunk)
                    remaining -= len(chunk)
        except Exception:
            shutil.rmtree(folder, ignore_errors=True)
            raise
        asset = {
            "id": asset_id, "project": project, "filename": filename,
            "content_type": self.headers.get("Content-Type") or "application/octet-stream",
            "size_bytes": target.stat().st_size, "status": "uploaded", "created_at": now(), "updated_at": now(),
            "folder": str(folder), "local_path": str(target), "metadata": None, "sha256": None,
            "source_url": None, "thumbnail_url": None, "proxy_url": None, "review_frames": [],
            "qc": {"status": "unchecked"},
        }
        with LOCK:
            STATE["assets"].append(asset)
            STATE["assets"] = STATE["assets"][-MAX_ASSETS:]
            project_obj = find_project(project)
            if project_obj:
                project_obj["updated_at"] = now()
            save_state()
        job = add_job("analyze_media", project, asset_id)
        dispatch_job(job)
        return self.send_json({"asset": public_asset(asset), "job": job}, 202)

    def receive_job(self):
        data = self.read_json()
        job_type = str(data.get("type") or "ffmpeg_check")
        project = str(data.get("project") or "prototype")
        asset_id = data.get("asset_id")
        if not find_project(project):
            return self.send_json({"error": "project not found"}, 404)
        if job_type != "ffmpeg_check":
            asset = find_asset(str(asset_id or ""))
            if not asset:
                return self.send_json({"error": "asset not found"}, 404)
            if asset.get("project") != project:
                return self.send_json({"error": "asset does not belong to project"}, 400)
        job = add_job(job_type, project, asset_id)
        dispatch_job(job)
        return self.send_json(job, 202)


if __name__ == "__main__":
    load_state()
    host = os.environ.get("AIVE_HOST", "0.0.0.0")
    port = int(os.environ.get("AIVE_PORT", "8080"))
    print(f"AIVideoEdit Alpha: http://127.0.0.1:{port}")
    print(f"LAN bind: {host}:{port}")
    print(f"Workspace: {RUNTIME}")
    ThreadingHTTPServer((host, port), Handler).serve_forever()
