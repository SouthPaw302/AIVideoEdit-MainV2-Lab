# MainV2 Lab — production operating instructions

## Correct lineage, authority and separation
- Development ancestry: `SouthPaw302/AIVideoEdit/main` → `SouthPaw302/AIVideoEdit/MainV2` → `SouthPaw302/AIVideoEdit-MainV2-Lab/main`.
- This repository's `main` is the active, self-contained production OS. `bootstrap.py` now resolves **this lab**, not the old AIVideoEdit/main.
- The audited upstream MainV2 pin is `316fe96c7316d76d14308d5f27293e071aa20943`; unchanged source mirror provenance remains in `SOURCE_LOCK.json` and `.lab/MIRROR_RECEIPT.json`.
- All 13 original MainV2 workflow definitions are preserved verbatim in `.lab/upstream-workflows/`. Active lab-adapted equivalents are registered in `.github/workflows/`. The newer FX/camera executor, JEV, ONNX registry, model provisioning, director supervision, harness and remote bridge are retained.
- Original `SouthPaw302/AIVideoEdit` must not be mutated. No production song branch is merged into lab `main` by default.

## Standard directing sequence
1. Boot the lab OS; read Prime Directive, generated Second Brain, SOUL, active Operating Order.
2. Ingest exact original WAV/video/image bytes; hash all assets, preserve lyrics, identify musical sections, genre and beat evidence.
3. Choose direction authority and production mode; lock approved visual direction, continuity anchors, script and timed shots.
4. Produce original imagery **in sets of 10**. For each accepted set, create distinct source-derived FX still variations and actual GIF/MP4 motion renders with hashes, proof media, and director QC. Never infer articulated vehicle/human movement from simple environmental FX.
5. Run approved true-video continuations where required. Protect identity, geometry, camera axis, locations and canon. Make shot media and accepted proof assets before assembly.
6. Select and precompile the **real** canonical FX implementation, preserve `FX_LOCK.json`, record execution in `PRODUCTION_EXECUTION_LEDGER.json`.
7. Build the whole frame-followable film with genuine original audio, full-frame coverage and no undisclosed placeholders.
8. Inspect decoded export, contact sheet, continuity, duration, audio, effects and frames. Publish to durable storage. Human acceptance and final archive are **separate gates**.

## Director verification (current-main canon)
Before calling a real production aesthetically complete, follow `general/reusable/DIRECTOR_SCAN_CANON.md`. Audit **all** approved originals, archived GIF/MP4/PNG FX variations and alternate motion clips, their native dimensions and SHA, source/shot duration compatibility, shot-level semantic motion, FX relevance and measured music controls. Inspect actual intro/outro and final cut, compare to the accepted baseline, log what was watched, and provide a playable link to the **exact** current candidate. Use `DIRECTOR_SCAN.json` plus the current-main evidence validator for auditable handoffs. This is additive to—not a replacement for—release-gate authentication.

## Actual render automation
GitHub Actions → **AIVideoEdit — Canonical Production Candidate (Director + Parallel)** → Run workflow.

- **source_ref:** repository branch containing the approved manifest and local input assets (typically `song/<slug>`; use `main` for the pinned real-source fixture).
- **manifest:** repository-relative JSON path (for example `projects/my-song/RENDER_JOB.json`).
- **require_onnx:** true means the pinned, byte-verified Beat This ONNX model must perform real inference; fallback stops the job.

The workflow resolves **lab main** and `source_ref` exactly once, stages the source bytes into one content-addressed bundle, and gives every dynamic shard the same immutable source/engine/project/manifest/toolchain identity. It boots canonical main, runs Director/Harness/JEV/FX/ONNX gates, renders real source picture to H.264/AAC with the original audio, verifies every shard and fan-in, and uploads the actual MP4. A separate least-privilege publish job creates a **prerelease** on **this lab repo** for independent review, never an accepted film.

The initial fixture `.lab/fixtures/irish-eyes-real-source-30s.json` uses verified **real** Irish Eyes WAV + 3 source-shot video releases with actual SHA-256s. It is a **30-second technical integration film**, not a complete long-form production or artistic acceptance. Real production manifests can supply an arbitrary approved shot timeline up to one hour per job; content coverage and independent approval remain required.

### Real manifest, abbreviated
```json
{
  "schema": "aivideoedit.real-render.v1",
  "production_id": "my-film",
  "render_authorization": "explicit_user_render_request",
  "audio": {"path": "projects/my-film/audio/master.wav", "sha256": "<real 64-hex digest>"},
  "output": {"fps": 24, "width": 1920, "height": 1080},
  "shots": [
    {
      "id": "shot-001",
      "source": {"path": "projects/my-film/media/shot-001.mp4", "sha256": "<real 64-hex digest>"},
      "duration_seconds": 5,
      "source_start_seconds": 0,
      "fit": "cover",
      "fx": [{"id": "FX2-LIGHT-001", "params": {"strength": 0.2}}]
    }
  ]
}
```

Media may instead specify `url` as a direct HTTPS link with the **exact** SHA-256. Only media with verified bytes is rendered; no synthetic replacement, missing-source fallback, silent shot substitution or source-image regeneration. Approved looped videos need `"loop": true` on that shot. Without that authorization a short source clip fails closed. Movie duration is the sum of exact approved frame durations. Missing soundtrack or short audio fails closed.

## Verification and delivery
- **MainV2 Surgical Verification** validates the new stack and regressions.
- **AIVideoEdit Production Contract** enforces the inherited OS gates.
- **AIVideoEdit Main System Verification**, **AIVideoEdit Promoted Effects Verification**, and **verify-living-still-fx** prove reusable FX and reject unapproved effects.
- **Compatibility — Single-runner technical proof**, **MainV2 ONNX Checkpoint**, **MainV2 Micro Production**, **DeepSeek Harness**, project-specific proof workflows and neutral-library generation are opt-in compatibility/verification jobs. They are not alternate production entrypoints. The micro probe is **synthetic technical smoke**, never a completed movie.
- The full real-render job is the actual media output path; its `real_music_film.mp4`, `render_receipt.json`, `FX_LOCK.json`, `PRODUCTION_EXECUTION_LEDGER.json`, `VISUAL_QC_EVIDENCE.json`, paired before/after `FX_VISIBILITY_PROOF.zip`, measured `MUSIC_BEAT_EVIDENCE.json`, and contact sheet provide evidence. Technical visual QC proves changing audio controls, visible FX, temporal motion, source quality, protected-ROI handling, and non-restarting transitions; it never grants human VISUAL_ACCEPTED.
- Do not add background auto-renders or uncontrolled workflow writes to main. No generated asset can be called canonical until director approval and provenance have been recorded.
