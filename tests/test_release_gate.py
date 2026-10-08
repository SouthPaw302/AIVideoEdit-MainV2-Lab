"""Issue #4: production release is impossible from partial/loop proofs or stale state."""
import copy
from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

from scripts.release_gate import GateError, preflight

CONTRACT = json.loads((Path(__file__).resolve().parents[1] /
                       "general/reusable/PRODUCTION_CONTRACT.json").read_text())
S = "a" * 40
E = "b" * 40
V = "c" * 64
A = "d" * 64
C = "e" * 64
F = "f" * 64


def payload():
    manifest = {
        "schema": "aivideoedit.real-render.v1",
        "production_id": "full-song",
        "render_authorization": "explicit_user_render_request",
        "audio": {"path": "song.wav", "sha256": A, "start_seconds": 0},
        "output": {"fps": 24, "width": 1920, "height": 1080},
        "shots": [
            {"id": "s1", "source": {"path": "shot1.mp4", "sha256": C},
             "media_role": "real_source", "duration_seconds": 60},
            {"id": "s2", "source": {"path": "shot2.mp4", "sha256": F},
             "media_role": "real_source", "duration_seconds": 60},
        ],
    }
    receipt = {
        "schema": "aivideoedit.real-render-receipt.v1",
        "production_id": "full-song",
        "source_commit_sha": S, "engine_commit_sha": E,
        "status": "TECHNICAL_RENDER_PASS_VISUAL_REVIEW_PENDING",
        "human_visual_approval": False, "production_complete": False,
        "render_sha256": V, "audio_sha256": A,
        "clip_sha256": {"s1": C, "s2": F},
        "duration_seconds": 120, "render_frames": 2880, "fps": 24,
        "fx": {"lock_sha256": F}, "ledger_sha256": C,
    }
    review = {
        "production_id": "full-song", "source_branch": "song/full-song",
        "source_commit_sha": S, "engine_commit_sha": E,
        "approved_export_sha256": V, "decision": "ACCEPT",
        "watched_entire_film": True, "normal_speed_playback": True,
        "reviewed_duration_seconds": 120,
        "reviewed_at": "2026-10-08T18:30:00-04:00",
        "reviewer": "SouthPaw302", "approval_comment_id": 987,
        "playback_url": "https://github.com/SouthPaw302/AIVideoEdit-MainV2-Lab/releases/download/approved/real_music_film.mp4",
    }
    comment = {"id": 987,
               "body": "AIVE-RELEASE-ACCEPT full-song " + V + " " + S +
                       " — watched entire film at normal speed",
               "user": {"login": "SouthPaw302", "type": "User"}}
    return manifest, receipt, review, comment


def check(data, duration=120):
    m, r, v, c = data
    return preflight(m, r, v, CONTRACT, source_sha=S, engine_sha=E,
                     audio_duration=duration, comment=c)


def rejects(transform, *, duration=120, pattern=None):
    data = payload()
    transform(data)
    with pytest.raises(GateError, match=pattern):
        check(data, duration=duration)


def test_full_length_real_source_and_verified_human_approval_pass():
    e = check(payload())
    assert e["frames"] == 2880
    assert e["duration_seconds"] == 120


def test_real_30_second_bounded_integration_fixture_cannot_be_released():
    rejects(lambda d: [s.update(duration_seconds=15) for s in d[0]["shots"]],
            duration=120, pattern="partial timeline|stale")


def test_30_second_manifest_even_when_receipt_claims_complete_fails():
    def fake_receipt(d):
        d[0]["shots"] = [dict(d[0]["shots"][0], duration_seconds=30)]
        d[1].update(duration_seconds=30, render_frames=720,
                    clip_sha256={"s1": C})
        d[2]["reviewed_duration_seconds"] = 30
    rejects(fake_receipt, duration=120, pattern="partial timeline")


@pytest.mark.parametrize("mutation", [
    lambda d: d[0]["shots"][0].update(loop=True),
    lambda d: d[0]["shots"][0].update(media_role="fx_loop"),
    lambda d: d[0]["shots"][0].pop("media_role"),
    lambda d: d[0]["shots"][0].update(media_role="canonical_source_derived"),
    lambda d: d[0]["audio"].update(start_seconds=30),
    lambda d: d[0]["audio"].update(sha256="1"*64),
    lambda d: d[1].update(source_commit_sha="0"*40),
    lambda d: d[1].update(engine_commit_sha="0"*40),
    lambda d: d[1].update(render_frames=2),
    lambda d: d[1].update(production_complete=True),
    lambda d: d[1]["fx"].update(lock_sha256=None),
    lambda d: d[2].update(approved_export_sha256="9"*64),
    lambda d: d[2].update(decision="REJECT"),
    lambda d: d[2].update(watched_entire_film=False),
    lambda d: d[2].update(source_branch="main"),
    lambda d: d[2].update(reviewed_duration_seconds=30),
    lambda d: d[3]["user"].update(type="Bot"),
    lambda d: d[3]["user"].update(login="other-human"),
    lambda d: d[3].update(body="LGTM"),
])
def test_bypasses_fail_closed(mutation):
    rejects(mutation)


def test_contract_cannot_omit_required_release_authority():
    m, r, v, c = payload()
    weakened = copy.deepcopy(CONTRACT)
    weakened["release_gate_policy"]["human_verified_comment_required"] = False
    with pytest.raises(GateError, match="mandatory"):
        preflight(m, r, v, weakened, source_sha=S, engine_sha=E,
                  audio_duration=120, comment=c)
