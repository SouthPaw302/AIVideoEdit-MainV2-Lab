# El Viento trae tu nombre — MainV2 Lab no-render staging handoff

**Status: Imported source canon / media staging and render preflight pending. Rendering is NOT authorized.**

- **New branch:** `song/el-viento-trae-tu-nombre` in [MainV2 Lab](https://github.com/SouthPaw302/AIVideoEdit-MainV2-Lab/tree/song/el-viento-trae-tu-nombre)
- **Original:** [SouthPaw302/AIVideoEdit — song/el-viento-trae-tu-nombre](https://github.com/SouthPaw302/AIVideoEdit/tree/song/el-viento-trae-tu-nombre) at `2f382a87ea646a024cecac98be070c44cfd010ed`
- **Exact-copy checkpoint:** `6d1931d739c42a2c0c9fe612d8a2c7c32ce42a25` — 218 source project files match every original Git blob; project-tree SHA `5ed9d342b432d8f957a5d06a319a40f2e12a99b7`.
- **Lab engine:** new stack protected `main` at `900e3e5749ed6fa13ad91524975a9e64661e6649` when branch was created. Before starting later, verify latest `main` and bootstrap anew.

## What remains canon

**Route 4 — Island Dream / Ancestral Memory — Two Heroes.** Keep male/female identity anchors, embroidered-thread imagery, island geography, camera language, intro/outro, original audio, shot order, accepted plates and timing. Continue this edit; do not invent a new visual route, replace the source library, create Batch 10, use obsolete storyboards, or overwrite archival masters.

Current picture: **3705 frames, 24 fps, 1920×1080, 154.375 seconds**. Original mux WAV: **154.480 seconds**. The source branch also retains **112.680-second archived** records and older S01–S11 shot packages; these are *not* the current script. Current `SCRIPT.json` contains **7 exact contiguous Route 4 timeline sections** (checked frame coverage 0–3704).

The last recorded candidate `El_Viento_Route4_1080p_FX_MASTER_v6.mp4` has reported SHA-256 `5fe93ef79d528a27cb7a15003aac9e9bc50a0db40a6719a102d36d5f10314af0`. Prior technical reports indicate PASS, but **the actual video was NOT downloaded or visually reviewed as part of this migration**. It remains explicitly **pending full normal-speed user creative review**. A historical `session:///mnt/data/...` path is not a valid portable runner source.

## Media and staging

Current audio is [private in Drive](https://drive.google.com/file/d/1M6uRTeYejXxn2rSDkTJu5H0_LiWrdwN4/view), titled `El Viento trae tu nombre.wav`. Source-recorded SHA-256: `8d967101c875868b64207bd43bfbc507c0a958989bbc560c2edb0024b15877cb`. Google Drive metadata confirmed the file exists, at 29,674,010 bytes, but **the byte hash has not been reverified** in this session. The imported `ASSET_MANIFEST.json` also has a different older remastered audio record (`bb26a35eaf2910531fc9ae057dd04c9315a6ad62425bd8267b9eb826a19c01e5`); do not silently use that in place of the 154.48-second current mux authority.

The source branch stores **50 asset metadata records and original Drive IDs**, not every binary WAV/still/loop/master. At least one hero still and the parent Drive folders were confirmed, but **GitHub-hosted runners cannot presently fetch these private Drive URLs as generic unauthenticated HTTPS sources**. Use approved authenticated staging to create immutable SHA-verified runner assets (or a documented local/self-hosted path); never substitute previews, fake frames or obsolete clips.

The original song-specific `.github/workflows/el-viento-fx-lock.yml` is archived here as *inert historical source*, not activated as a workflow. The new Lab's canonical [Director + parallel runner](https://github.com/SouthPaw302/AIVideoEdit-MainV2-Lab/actions/workflows/mainv2-director-parallel-real-render.yml) is the future execution entry point after preflight and explicit render approval.

## Mandatory NEXT ACTION (non-render)

1. On this branch, run `python bootstrap.py boot --repo-root <repo-root>`; follow the fresh Lab OS instructions and validate `production_guard`, `narrative_guard`, `recut_guard` and `workflow_guard`. Record any old-project schema incompatibilities; do not mutate accepted canon to make a dashboard green.
2. Recover/stage **original audio**, the **exact current Route 4 picture candidate** and **required verified layers/hero assets** with content SHA and stable access for the runner. Confirm source identity and geometry.
3. Reconcile only the runner-facing recipe: new engine FX registry and precompile proofs, 7-section/3705-frame current edit vs archived 112.68-second packages, and each real source-to-shot assignment. Generate a canonical `RENDER_MANIFEST.json` only when all media locators are real and validated. Do not write fake sources.
4. Run preflight-only validation (no picture encoding) and make a separate new candidate destination; preserve all previously accepted masters. Report exact commit hashes, assets staged and any blockers.
5. **STOP before render dispatch.** Only a later explicit user instruction may enable `render_authorization=explicit_user_render_request`. The new run requires Director gate, FX review, then full normal-speed human acceptance; 4K and publication remain blocked.

See `LAB_RUN_PREP.json` for machine-readable readiness and frame ranges. **Do not copy the original root engine, global workflows, or old FX executor over repaired Lab `main`.**
