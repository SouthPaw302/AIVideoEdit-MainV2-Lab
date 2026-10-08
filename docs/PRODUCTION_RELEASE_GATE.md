# AIVideoEdit MainV2-Lab — full production release gate

**Top-level authority:** `general/reusable/PRODUCTION_CONTRACT.json`. The MainV2 runtime, ONNX, FX locks, JEV, artifacts and technical Actions are subordinate. No workflow result or lab prerelease by itself is an approved film.

## Technical proof versus finished film

- `mainv2-real-render.yml` runs byte-verified source video/audio + FX and publishes **only a prerelease** under `lab-real-film-<run-id>`. It records `render_receipt.json` with the exact source/engine SHAs and ledger hash. Its `human_visual_approval=false` and `production_complete=false` are intentional.
- The six-second smoke and 30-second Irish Eyes fixture are always **non-promotable**. Their partial timeline, looping clips and/or undeclared primary-media coverage cannot pass the production release gate.
- `production-final-release.yml` is **manual only**, never triggered by technical workflow success. It checks the complete source master, every production timeline shot, real source media, immutable source and engine SHAs, actual MP4 SHA-256 and full frame decode, FX/ledger provenance, and independent human playback approval. Any absent, contradictory, altered or stale evidence stops before upload. No local/FFmpeg-only substitute or post-approval 4K transformation is made.

## Production branch contract

Use a `song/<slug>` or explicitly declared `project/<slug>` branch. Supply a full-song `aivideoedit.real-render.v1` manifest, not `.lab/fixtures/*30s.json`.

Every shot needs `media_role: "real_source"` and its byte-verified source. Source-derived primary shots may instead use `media_role: "canonical_source_derived"`, `canonical_source_sha256` (64 hex), and a meaningful `derivation` declaration. Every shot needs continuous frame duration and actual source sha256. FX may augment those shots, but FX-only or `loop:true` shots do **not** count as approved full-song source. The total duration of the timeline must equal the entire original untrimmed master audio within frame tolerance.

To generate a candidate, run **MainV2 Lab — REAL Music Film Render** using that production branch and manifest. Download/play the generated video from the *lab prerelease* and review its entire duration at normal speed. The proof tag and receipt must identify the source commit that created it. Add the human review JSON in the production branch. This can be committed after rendering: the final workflow re-checks that the manifest is byte-for-byte unchanged and inspects the exact original immutable source checkout.

## Actual human acceptance (not an agent boolean)

The owner **SouthPaw302** must personally post an issue comment in this lab repository with exact token:

```text
AIVE-RELEASE-ACCEPT <production_id> <export_sha256> <source_commit_sha> — watched entire film at normal speed
```

Record its numeric GitHub comment ID in `RELEASE_REVIEW.json` on the production branch. For example:

```json
{
  "production_id": "my-song",
  "source_branch": "song/my-song",
  "source_commit_sha": "<40-hex SHA in render receipt>",
  "engine_commit_sha": "<40-hex SHA in render receipt>",
  "approved_export_sha256": "<64-hex MP4 SHA in render receipt>",
  "decision": "ACCEPT",
  "watched_entire_film": true,
  "normal_speed_playback": true,
  "reviewed_duration_seconds": 200.0,
  "reviewed_at": "2026-10-08T18:00:00-04:00",
  "reviewer": "SouthPaw302",
  "approval_comment_id": 1234567890,
  "playback_url": "https://github.com/SouthPaw302/AIVideoEdit-MainV2-Lab/releases/download/lab-real-film-123456789/real_music_film.mp4"
}
```

Replace every sample digest, duration, comment ID and URL with the **actual verified values**. A model or workflow cannot manufacture/approve this comment. The CI job authenticates its author through GitHub, verifies it belongs to this repository, and binds the exact file digest and source commit.

## Finalization

Manually dispatch **AIVideoEdit — Human-gated final production release** with `source_ref`, `manifest`, `review`, and the existing `lab-real-film-<run-id>` `proof_tag`. No final release happens unless the gate emits `RELEASE_GATE.json` with `status: PASS`. The output is the *identical previously reviewed MP4 bytes* and its evidence. To archive in the GUI or mark `FINAL_QC_PASSED`/`ARCHIVED`, save that gate report as `projects/<slug>/RELEASE_GATE.json`, and bind these current `PROJECT_STATE.json` fields to it: `release_gate_status: "PASS"`, `human_visual_approval: true`, `release_gate_export_sha256`, `release_gate_manifest_sha256`, `release_gate_source_commit_sha`, and `release_gate_engine_commit_sha`. A mismatched assembly/master hash blocks GUI archiving.

For additional human separation of duties, configure **GitHub Settings → Environments → production-release → Required reviewers**. Repository code cannot create that GitHub account setting. This additional environment protection is not a substitute for the authenticated review comment.

Run `python scripts/validate_contract.py` and `python -m pytest tests/test_release_gate.py` to validate policy and the positive/negative fail-closed cases; full media decode happens in the release Action. No test fixture or synthetic export is used as a finished film.
