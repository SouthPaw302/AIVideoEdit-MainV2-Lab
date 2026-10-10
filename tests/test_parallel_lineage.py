"""Packet 03: exact source bytes and immutable identities survive fan-out/fan-in."""
from __future__ import annotations

import copy
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import subprocess

import pytest

from scripts.release_gate import GateError, preflight, validate_parallel_lineage
from scripts.assemble_parallel_music_film import load_verified_shards
from scripts.render_real_music_film import stage
from scripts.render_lineage import (
    LineageError,
    build_bundle,
    receipt_identity,
    require_receipt_identity,
    verify_bundle,
)


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads((ROOT / "general/reusable/PRODUCTION_CONTRACT.json").read_text())


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


@pytest.fixture()
def locked_run(tmp_path):
    source = tmp_path / "source"
    project = source / "projects" / "demo"
    media = source / "media"
    project.mkdir(parents=True)
    media.mkdir()
    audio_bytes = b"RIFF-real-audio-bytes"
    clip_a = b"real-video-source-a"
    clip_b = b"real-video-source-b"
    (media / "song.wav").write_bytes(audio_bytes)
    (media / "a.mp4").write_bytes(clip_a)
    (media / "b.mp4").write_bytes(clip_b)
    manifest = {
        "schema": "aivideoedit.real-render.v1",
        "production_id": "lineage-proof",
        "render_authorization": "explicit_user_render_request",
        "audio": {"path": "media/song.wav", "sha256": digest(audio_bytes), "start_seconds": 0},
        "output": {"fps": 24, "width": 160, "height": 90},
        "shots": [
            {"id": "a", "source": {"path": "media/a.mp4", "sha256": digest(clip_a)},
             "media_role": "real_source", "duration_seconds": 2},
            {"id": "b", "source": {"path": "media/b.mp4", "sha256": digest(clip_b)},
             "media_role": "real_source", "duration_seconds": 2},
        ],
    }
    manifest_path = project / "RENDER_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (project / "OPERATING_ORDER.json").write_text('{"direction_authority":"user_directed"}\n')
    git(source, "init", "-q")
    git(source, "config", "user.email", "lineage@example.invalid")
    git(source, "config", "user.name", "Lineage Test")
    git(source, "add", ".")
    git(source, "commit", "-qm", "locked production source")
    bundle = tmp_path / "bundle"
    lineage = build_bundle(manifest_path, source, ROOT, project, bundle)
    return source, project, manifest_path, manifest, bundle, lineage


def test_same_real_bytes_and_shas_reach_release_preflight(locked_run):
    source, project, manifest_path, manifest, bundle, lineage = locked_run
    checked = verify_bundle(
        bundle / "RUN_LINEAGE.json", bundle / "STAGED_MANIFEST.json", bundle,
        source_root=source, engine_root=ROOT, project=project,
        original_manifest=manifest_path,
    )
    shard = {
        "audio_sha256": lineage["audio_sha256"],
        "clip_sha256": lineage["clip_sha256"],
        **receipt_identity(lineage, bundle / "RUN_LINEAGE.json"),
    }
    require_receipt_identity(shard, checked, bundle / "RUN_LINEAGE.json")

    export_sha = "c" * 64
    ledger_sha = "d" * 64
    fx_sha = "e" * 64
    receipt = {
        "schema": "aivideoedit.real-render-receipt.v1",
        "production_id": "lineage-proof",
        "status": "TECHNICAL_RENDER_PASS_VISUAL_REVIEW_PENDING",
        "human_visual_approval": False,
        "production_complete": False,
        "render_sha256": export_sha,
        "audio_sha256": lineage["audio_sha256"],
        "clip_sha256": lineage["clip_sha256"],
        "duration_seconds": 4,
        "render_frames": 96,
        "fps": 24,
        "fx": {"lock_sha256": fx_sha},
        "ledger_sha256": ledger_sha,
        "fx_visibility_proof_sha256": fx_sha,
        **receipt_identity(lineage, bundle / "RUN_LINEAGE.json"),
    }
    validate_parallel_lineage(receipt, bundle / "RUN_LINEAGE.json")
    reviewed_at = datetime.now(timezone.utc).isoformat()
    review = {
        "production_id": "lineage-proof",
        "source_branch": "project/lineage-proof",
        "source_commit_sha": lineage["source_commit_sha"],
        "engine_commit_sha": lineage["engine_commit_sha"],
        "approved_export_sha256": export_sha,
        "decision": "ACCEPT",
        "watched_entire_film": True,
        "normal_speed_playback": True,
        "reviewed_duration_seconds": 4,
        "reviewed_at": reviewed_at,
        "reviewer": "SouthPaw302",
        "approval_comment_id": 42,
        "playback_url": "https://github.com/SouthPaw302/AIVideoEdit-MainV2-Lab/releases/download/proof/real_music_film.mp4",
    }
    comment = {
        "id": 42,
        "body": "AIVE-RELEASE-ACCEPT lineage-proof " + export_sha + " " +
                lineage["source_commit_sha"] + " — watched entire film at normal speed",
        "user": {"login": "SouthPaw302", "type": "User"},
    }
    evidence = preflight(
        manifest, receipt, review, CONTRACT,
        source_sha=lineage["source_commit_sha"],
        engine_sha=lineage["engine_commit_sha"],
        audio_duration=4,
        comment=comment,
        visual_qc={
            "schema": "aivideoedit.visual-qc-evidence.v1", "status": "PASS",
            "candidate_sha256": export_sha,
            "fx_visibility_proof_sha256": fx_sha,
            "checks": {"source": True, "audio": True, "fx": True, "motion": True, "seams": True},
            "human_visual_approval": False, "artistic_approval": False, "release_authority": False,
        },
    )
    assert evidence["frames"] == 96


def test_fan_in_consumes_exact_shard_and_source_identities(locked_run, tmp_path):
    _source, _project, _manifest_path, _manifest, bundle, lineage = locked_run
    shard_root = tmp_path / "shards" / "render-shard-0"
    output = shard_root / "output"
    output.mkdir(parents=True)
    staged = json.loads((bundle / "STAGED_MANIFEST.json").read_text())
    shard_manifest = {**staged, "shots": staged["shots"]}
    manifest_path = shard_root / "manifest.json"
    manifest_path.write_text(json.dumps(shard_manifest), encoding="utf-8")
    video = output / "shard_video.mp4"
    video.write_bytes(b"encoded-shard-bytes")
    ledger = output / "PRODUCTION_EXECUTION_LEDGER.json"
    ledger.write_text('{"schema":"aivideoedit.production-execution-ledger.v1","events":[]}')
    gate = {"fx_lock_sha256": "f" * 64}
    receipt = {
        "start_index": 0,
        "end_index": 2,
        "video_sha256": digest(video.read_bytes()),
        "shard_manifest_sha256": digest(manifest_path.read_bytes()),
        "ledger_sha256": digest(ledger.read_bytes()),
        "fx_lock_sha256": gate["fx_lock_sha256"],
        "audio_sha256": lineage["audio_sha256"],
        "clip_sha256": lineage["clip_sha256"],
        **receipt_identity(lineage, bundle / "RUN_LINEAGE.json"),
    }
    (output / "shard_receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
    records = load_verified_shards(tmp_path / "shards", gate, lineage, bundle / "RUN_LINEAGE.json")
    assert [(record[0], record[1]) for record in records] == [(0, 2)]
    receipt["audio_sha256"] = "0" * 64
    (output / "shard_receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(RuntimeError, match="audio byte identity"):
        load_verified_shards(tmp_path / "shards", gate, lineage, bundle / "RUN_LINEAGE.json")


def test_wrong_media_bytes_fail_closed(locked_run):
    source, project, manifest_path, _manifest, bundle, _lineage = locked_run
    target = next((bundle / "objects").glob("*.mp4"))
    target.write_bytes(b"substituted proxy")
    with pytest.raises(LineageError, match="wrong-hash"):
        verify_bundle(
            bundle / "RUN_LINEAGE.json", bundle / "STAGED_MANIFEST.json", bundle,
            source_root=source, engine_root=ROOT, project=project,
            original_manifest=manifest_path,
        )


def test_stale_or_missing_lineage_fails_closed(locked_run, tmp_path):
    _source, _project, _manifest_path, _manifest, bundle, lineage = locked_run
    receipt = receipt_identity(lineage, bundle / "RUN_LINEAGE.json")
    stale = copy.deepcopy(receipt)
    stale["engine_commit_sha"] = "0" * 40
    with pytest.raises(LineageError, match="engine_commit_sha"):
        require_receipt_identity(stale, lineage, bundle / "RUN_LINEAGE.json")
    with pytest.raises(GateError, match="missing"):
        validate_parallel_lineage(receipt, tmp_path / "missing.json")


def test_changed_lineage_artifact_fails_release_binding(locked_run):
    _source, _project, _manifest_path, _manifest, bundle, lineage = locked_run
    receipt = {**lineage, **receipt_identity(lineage, bundle / "RUN_LINEAGE.json")}
    path = bundle / "RUN_LINEAGE.json"
    data = json.loads(path.read_text())
    data["toolchain_sha256"] = "0" * 64
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(GateError, match="changed"):
        validate_parallel_lineage(receipt, path)


def test_authenticated_media_staging_sends_secret_only_to_allowlisted_host(tmp_path, monkeypatch):
    payload = b"private-original-media"
    expected = digest(payload)
    seen = {}

    class Response(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            self.close()

    def fake_open(request, timeout):
        seen["authorization"] = request.get_header("Authorization")
        seen["timeout"] = timeout
        return Response(payload)

    monkeypatch.setenv("AIVE_MEDIA_AUTH_HOSTS", "media.example")
    monkeypatch.setenv("AIVE_MEDIA_TOKEN", "runner-secret")
    monkeypatch.setattr("urllib.request.urlopen", fake_open)
    result = stage(
        {"url": "https://media.example/original.wav", "sha256": expected},
        input_root=tmp_path, cache=tmp_path / "cache",
    )
    assert result.read_bytes() == payload
    assert seen["authorization"] == "Bearer runner-secret"


def test_parallel_workflow_uses_one_lock_and_canonical_release_tag():
    workflow = (ROOT / ".github/workflows/mainv2-director-parallel-real-render.yml").read_text()
    assert "ref: ${{ needs.director-gate.outputs.engine_sha }}" in workflow
    assert "ref: ${{ needs.director-gate.outputs.source_sha }}" in workflow
    assert "python source/scripts/" not in workflow
    assert 'gh release create "lab-real-film-${GITHUB_RUN_ID}"' in workflow
    assert "lab-parallel-real-film" not in workflow
