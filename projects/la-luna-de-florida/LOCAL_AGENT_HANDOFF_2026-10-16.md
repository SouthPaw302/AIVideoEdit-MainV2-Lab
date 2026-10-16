# La Luna de Florida — Local Agent Production Handoff (2026-10-16)

**Repository:** https://github.com/SouthPaw302/AIVideoEdit-MainV2-Lab  
**ONLY authorized production write branch:** `song/la-luna-de-florida`  
**At handoff, branch HEAD:** `07931e18be72a8e625b0e23d19b3841cd78106b8` (Gemini uncut edit correction).  
**Task:** Run the **actual existing AIVideoEdit-MainV2-Lab native pipeline**, not another standalone/sandbox FFmpeg assembly. Make the first honest complete ~5:21 review candidate at **480p (or 720p if appropriate)**, inspect/repair it, and deliver a real render receipt plus Drive review link. **Do not claim release.**

> This is a status relay and execution pointer to **already-existing** production contracts, not a replacement operating order, FX doctrine, invented rule set, or newly approved script. In any conflict, follow the current user's instructions and the current-main OS + this song branch's authoritative project files.

## 1. Mandatory existing authority / session boot

1. Read `projects/la-luna-de-florida/MASTER_FX_DIRECTOR_HANDOFF_2026-10-15.md` **in full**. Its B01–B05 shot details, source hashes, source-staging and render/final Director scan instructions remain operative.
2. Follow `PRIME_DIRECTIVE.md`, `SOUL.md`, `general/reusable/ZERO_DRIFT_DIRECTOR_DIRECTIVE.md`, `general/reusable/DIRECTOR_SCAN_CANON.md`, `general/reusable/DIRECTOR_SUPERVISION.md`; song-local `OPERATING_ORDER.json`, `FX_STAGE_CANON.json`, `SOURCE_AUTHORITY.json`, `STORYBOARD_CANON.json`, `LYRICS.md`, `SCRIPT.json`.
3. Use the documented bootstrap on the active song branch (the OS implementation is from **current `main`**, not an older exported copy):
   ```bash
   git checkout song/la-luna-de-florida
   git fetch --no-tags origin main
   python bootstrap.py boot --repo-root "$PWD" --branch song/la-luna-de-florida --offline
   python scripts/la_luna_fx_canon_guard.py
   ```
   Inspect `.aivideoedit/SECOND_BRAIN.md` created by boot, and verify the actual boot / guards rather than assuming a previously green workflow represents today's render.
4. `main` is read-only engine authority; only write this song branch. Do not modify other song projects or `SouthPaw302/AIVideoEdit`. Preserve user-approved source/shot/storyboard assets.

## 2. What is COMPLETE and preserved

- **B01–B05**: all **50** Director-selected moving-shot source proofs, each **96 frames at 24fps, 960×540** (200 seconds combined). Source index with each clip hash and ZIP member: `MASTER_50_SHOT_SOURCE_PREFLIGHT.json`. B01/B02 RC8, B03 RC2, B04 RC2, B05 RC1. No regeneration or re-approval of these five batches. The B03-S10 memory bridge is an approved **derivative** from S07/S09, not a tenth original B03 still.
- **Native batch FX**: existing **98** A/B variants across B01–B05; these are **per-shot batch FX**, distinct from the cinematic whole-film Master Director FX stage.
- **B06 extension**: **10 new independent 1672×941 stills**, ten motion proofs, **20 A/B FX variants**, ten GIF previews and a **52-second technical review reel**. B06 is **insert/cutaway material into B01–B05**, not a sixth chronological act, and it is **not** a license to say all eight still-based performers have articulated motion. See `B06_DIRECTOR_FX_STAGE_BATCH10_COMPLETE_RC1.json` and `B06_EXTENSION_ASSETS_FINALE_RC2_DIRECTOR_EVIDENCE.json`. Completed archive:
  - [Batch 06 archive](https://drive.google.com/file/d/1uWWQrlpMd1V3YJokxjZDdmrBD-Yv8kyE/view) — 77,244,073 bytes, SHA-256 `d525b60185214f0dbf81e6b3b03c4f00e35da3ac5980b8303195ff221e46e0be`.
  - [Batch 06 52s review](https://drive.google.com/file/d/1RrHfC27NNpd1NW7chkH0zxPotWbYa2if/view).
  - [B06 original stills](https://drive.google.com/drive/folders/16Vd3zLa19Bz3QJHDg0gUtIYBVlpsEhBy). A DIFFERENT older Drive folder named "10 Batch 06 Originals" also exists: don't silently substitute it.
- **Original WAV**: [Drive](https://drive.google.com/file/d/18DlMA-MUfdL5rO0DYmU0pTLlYdqsJdCX/view), **48 kHz stereo / 321.16 seconds**, SHA-256 `1a4bffef36930b504423d2653faff4cc5bfd9a15d44bdcf1083b27fbb0db1c10`. Use the original WAV as the music authority and mux it once; discard/isolate generated Gemini audio according to the project's source audio rules.
- **Original storyboard**: 50 canonical B01–B05 compositions in `STORYBOARD_CANON.json`; [approved board](https://drive.google.com/file/d/1cR6kUCti5UkS8zdXz5B56EfjyRr_1Fau/view), image SHA-256 `05b232452eebce56fb9c047a0f481a19e04cf2d13e364bee30255dd27c88703a`. B06 continuation is separately a candidate reference (`STORYBOARD_CONTINUATION_B06_SINGLE_CANDIDATE.json`); do not create rival storyboards.
- **Lyric / music evidence**: `MASTER_DIRECTOR_PASS_02_ASR_CUES_CANDIDATE.json` has **50 frame-indexed shot candidates summing to 7,708 frames**, generated from the verified original WAV; 126/129 lines matched by offline ASR **as estimates**, not independently ear-verified/locked cues. Real Beat This! ONNX run `38680169728` gave 510 beats/140 downbeats, not lyric timestamps. `SCRIPT.json` is **unlocked**.
- **Recent GitHub tests** at branch SHA `07931e18...`: Production Contract `38849226610` and MainV2 Lab Full Compile `38849226600` **PASS**. They verify tests/boot, **NOT a full native film render**.

## 3. Critical current-user corrections — do not ignore

1. The sandbox-produced 480p **5:21 diagnostic MP4 was rejected**. It was NOT run through the GitHub production pipeline, had poor editing, and does not qualify as a native master or accepted baseline. Don't promote, relabel, or cite it as a finished film.
2. **Gemini videos must play as intact cinematic footage, rather than being chopped up and interleaved with still/FX filler.** Where a pair is authored as adjacent scenes, play them **back to back** in their proper song location. Do cinematic editing/transitions **around** Gemini footage, not by distorting, internally interrupting, looping or retiming the actual performance. The latest song-local draft with hashes/windows is `GEMINI_UNCUT_MASTER_EDIT_CONTRACT_RC2.json`. That draft's placements are a **candidate**, not a locked picture or authorization to ignore actual sung timing.
3. **Gemini provenance/duplicate guard:** 
   - Early original `GEMINI_UPLOAD_952aed07_ORIGINAL_UNCUT.mp4` is an actual 10s performance/harbor source. Its earlier dance/harbor extracts are NOT multiple unique full videos.
   - `B05-S04_GEMINI_a6339758_original.mp4` is a real 10s musician source (beware repeated musician performance across old proofs).
   - [B06-S01 Gemini harbor, original 10s](https://drive.google.com/file/d/1ow3vrwVxAn4RCvWx6Znadv30mdFurfLg/view).
   - [B06-S10 upload, original 20s](https://drive.google.com/file/d/14dMiA2VTxf47Lco087DZHwBFzdtokF9r/view) contains about **10s duplicated harbor followed by a unique 10s sunrise dance**. Preserve the uncut archived upload, but don't count/replay its duplicated first half as a separate new harbor performance. The separately extracted 240-frame dance was a **review candidate**; do not interrupt those performance frames.
   - Duplicate/background hat-wearing protagonist lookalikes are still a visual QC risk (especially some B06 stills/dance backgrounds). Original files remain untouched; do not claim an identity defect repaired by a camera move.
4. **No further Gemini or still batches requested.** User says finish with existing source and actual repo runner. Batch 06 technical proof work is already complete; stop inventing new clip requests, extra storyboards, or rules.
5. **Only the user approves final picture/release.** A green technical gate, an FX loop, a review reel, and a rough cut do not grant full artistic acceptance.

## 4. Actual next work, following existing repository workflow

1. **Source stage / inspect:** Recover the exact 50 source MP4s, B06 media and intended Gemini originals, all with hash lineage. B01/B02 proof ZIP [Drive](https://drive.google.com/file/d/1rqMtkcCARkcwH0FqLx0tfwoo0JrA-AQ-/view); B03 [Drive](https://drive.google.com/file/d/1efo2t2xX6TKclhZ1I1hBWxhX1-z-62op/view); B04 [Drive](https://drive.google.com/file/d/10cF5tPLxGHxvGKZA7B091K53dGxctqTb/view); B05 [Drive](https://drive.google.com/file/d/1vps_qOmVKJy_96aTcQh0-tgjJlZmXLsJ/view). See authoritative `MASTER_50_SHOT_SOURCE_PREFLIGHT.json` for exact ZIP member paths and SHA per shot. B06 archive and Gemini Drive URLs listed above. Validate bytes, not filenames alone.
2. **Make the existing 50-shot 7,708-frame timeline honestly renderable.** Use `MASTER_DIRECTOR_PASS_02_ASR_CUES_CANDIDATE.json` as a candidate, listen/check lyric windows, and direct B06 insert locations and full Gemini scene blocks. It calls out **34 original shots requiring additional nonrepeating footage** (3,224 frames gross beyond trimmed four-second proofs). Existing 4s MP4s cannot become 5:21 by repeating or freezing them. Preserve scene identity, real motion and user-approved story. **Do not claim complete coverage just because total durations sum correctly.** Work with current-main project FX/comp pipeline for real authored extended-media proofs.
3. **Resolve source delivery for the existing native real-render pipeline.** The [original WAV](https://drive.google.com/file/d/18DlMA-MUfdL5rO0DYmU0pTLlYdqsJdCX/view) and many Drive files are owner-only; a `drive.google.com/file/d/.../view` link does **not** prove byte-serving access for GitHub runners. `main/scripts/render_lineage.py stage` uses the real renderer's SHA-pinned local-path or HTTPS byte-download contract and requires byte-verifiable source media. Verify a *real* WAV and representative clip can be staged/hash-checked inside the runner. Use the repo's supported auth/media staging, not an HTML /view page, secret exposure, a giant media commit, or unverified fallback.
4. **Use the existing MAIN native production workflow** `.github/workflows/mainv2-director-parallel-real-render.yml` (**workflow_dispatch**, not the green branch compile jobs). It has the Director gate, current-main bootstrap, `render_lineage.py stage/verify`, `plan_render_shards.py`, `director_harness_gate.py`, native real FX per-shard render, and full assembly. Supply its documented inputs:
   - `source_ref = song/la-luna-de-florida`
   - `project = projects/la-luna-de-florida`
   - `manifest =` the **actual committed** branch-relative `aivideoedit.real-render.v1` manifest, generated/verified under the authoritative handoff instructions; `MASTER_FX_REAL_RENDER_RC1.json` is an **example target filename** in the original handoff, **not confirmed to exist**.
   - `max_shots_per_shard = 8` (existing workflow default).
   The workflow itself lives on `main` as immutable engine authority; **all production file writes** belong to `song/la-luna-de-florida`. Do not invent a replacement renderer or report a native run until a real run ID and valid artifact/lineage receipt exist.
5. **Native Master Director FX & actual film:** Follow `FX_STAGE_CANON.json`, current-main resolver/registry, 50-shot original story and user Gemini correction. Batch A/B FX are *inputs*; Master Director cinematic scene/edit/grade, real music-led transitions and protected zero-drift motion are a **separate** render/review pass. Per-scene source SHA and FX IDs must be traceable. For first actual native film 480p (854×480) is user-allowed; 720p is also allowed, but do not claim 720p/4K source detail from existing 960×540 clips.
6. **Review output, don't assume PASS:** Run the **entire** complete 321-second normal-speed Director watch and current-main eleven-phase `DIRECTOR_SCAN_CANON.md`, then actual full decode/black/freeze/audio-source/frame-count/provenance checks. Assess bad character repeats, duplicate hat actor, articulating dance/violin motions, rhythmic and lyric alignment, nighttime vs road memory vs sunrise, Gemini full uninterrupted blocks, opening and outro. Do targeted versioned repairs and compare to the prior candidate. Place full actual movie, SHA, lineage, manifest, receipts and scan in Drive, with small pointers/notes on this branch. Seek the user's final film approval only after genuine candidate delivery.

## 5. Important truthful state / blocking points

- **No confirmed completed canonical 5:21 native workflow run or native render artifact as of this handoff.** Earlier 5:21 sandbox assembly is diagnostic/rejected.
- **No accepted complete-film baseline**, no locked `SCRIPT.json`, no full-film normal-speed Director acceptance, no user release approval.
- **Batch 06 is complete as a technical media/FX package**, not inherently full-film action or creative approval.
- `MASTER_DIRECTOR_PASS_02_ASR_CUES_CANDIDATE.json` is an **unlocked plan**; the Gemini `GEMINI_UNCUT_MASTER_EDIT_CONTRACT_RC2.json` is an **unlocked edit correction**. If placement/timing conflict, verify against original music and film; do not silently declare either locked.
- Repository `PROJECT_STATE.json` and `OPERATING_ORDER.json` can have historic stage/status fields. Preserve those as records until actual current-main stage gates accept changes; this handoff does not assert stage promotion.

## 6. What to report back

Report the **real GitHub Actions render run URL/ID** (or precise failed stage and error), engine-main SHA, song source SHA, native manifest SHA, WAV and source staging SHA receipts, complete picture frame count and format, actual FX/render/shard/assembly receipt links, complete-movie Director review findings, and Google Drive playable review-candidate URL. Clearly distinguish technical PASS, Director creative verdict and **user-held release approval**.

**Bottom line:** Stop building disconnected sandbox movies; **use the native MainV2-Lab production engine and the existing canon** to make a real complete La Luna de Florida film. Preserve all B01–B06 media, play unique Gemini performances uninterrupted and in the directed order, validate source staging and the full film, and do not invent any additional production rules.
