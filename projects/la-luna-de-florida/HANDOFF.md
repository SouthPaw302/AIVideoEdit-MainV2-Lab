# Production handoff — La Luna de Florida

## B01/B02 RC5 full moving-shot proof library — reviewed technical scope

**LATEST PRIORITY before B03-B05:** [80s RC5 Director review](https://drive.google.com/file/d/1z6KpMw3WljbtWajHDVV1e02mzCLQjfFA/view), [20 native-cadence shot videos, all RC3/4/5 compositor source scripts, and SHA/QC receipts](https://drive.google.com/file/d/1J3dmI4nO_3TK601rvI8wdEulmW8czkBe/view). See `B01_B02_MOVEMENT_DIRECTOR_STATUS.json.latest_RC5_provisional` for per-shot classification. New RC5 sandbox movie 1920 frames/80s, zero detected black and >=0.5s frozen events. 15 shots have genuine same-film actor/instrument/reaction motion candidates, 4 are environment/no character action, B02-S02 dock-to-interior cut has moving musicians but not literal door-crossing feet. **No human/Director creative acceptance yet.** High risk of repeated underlying B05 Gemini musician footage over many shot reframings: normal-speed review required. B01/B02 originals/FX preserved, user song WAV/50-shot board/other repo unaffected. This is NOT the 5m21 film. No expansion to B03/B04/B05 until owner/Director acceptance of B01/B02 movement/coverage. All new evidence goes to production Drive directly, not persistent native ChatGPT Library.


## New RC3 source-performance handoff — 2026-10-15

Read [B01_B02_MOVEMENT_DIRECTOR_STATUS.json](B01_B02_MOVEMENT_DIRECTOR_STATUS.json) latest_RC3_provisional. The 80-second [RC3 review export](https://drive.google.com/file/d/1-nbQnQvvoSOnU_hEn4P8YPQOrFFqJ2q8/view) replaces neither original nor RC2: genuine actor/instrument motion candidates for 9 shots, preserved other 11 as pre-existing motion layers, nocturnal B01-S10 visual option. This RC3 was rendered in the sandbox; original 20 moving clips still trace to GitHub Actions run #38684398752. Both exact-original video hashes, 20-shot complete candidate archive and reproducible Python source, full QC and source receipts are archived in [Drive](https://drive.google.com/drive/folders/19fPAokHiMzdwD0FqTHVlW_VhBAe6RFet).

**Still OPEN:** B01 S04/05/06 genuine action, B02 S04/06/08 genuine action, B02 S01/S02 entrance/interior source mismatch, 6 actual encoded >0.5s freeze events. Creative review/user approval NOT granted; don't infer 4s per shot is the film script. Director should first review RC3 at normal speed, then author **new source-derived pose/real-performance variants** against each outstanding shot, preserve still and FX provenance, and independently pass the complete character/action and picture-QC gates before B03–B05 progress. Never import anything from other projects; B05 source is same film, separately logged cross-act provisional footage only.


## Director movement pass B01/B02 — next exact action (2026-10-15)

Read `B01_B02_MOVEMENT_DIRECTOR_STATUS.json` and see [the 80s RC2 review](https://drive.google.com/file/d/1VTshGBSTdKKNf87PaH3wfNzLUn47AJ-x/view), [all 20 real 4s clips](https://drive.google.com/file/d/1wC2qxvCZAPgQR0AZ9w94T9sKPVnf6NIN/view) and successful [GitHub run 38684398752](https://github.com/SouthPaw302/AIVideoEdit-MainV2-Lab/actions/runs/38684398752). `scripts/la_luna_b01b02_movement_compile.py` and `.github/workflows/la-luna-b01b02-moving-scenes.yml` are branch-local reproducible source-hash-checked job entrypoints. Both light-FX input runs are unchanged, and no source, storyboard or audio replacement is accepted.

**Do not confuse real rendered 2.5D proof with completed full-film character action.** RC2 uses one genuine user-supplied Gemini dance segment for B01-S07 and one harbor segment for B01-S09, not repeatedly as synthetic input to every shot. 14 other storyboard shots need their real performer/instrument/conversation action, 3 mismatches need new matching source treatment, and 7 freeze periods require temporal repair. Stage must remain pending until real video output is visually reviewed and approved. Do not advance to B03/B04/B05 or Master FX merely because 10 jobs succeeded. Don't use other song branches' visuals.


## Current user-canon FX workflow — per-song only (2026-10-15)

**Read [FX_STAGE_CANON.json](FX_STAGE_CANON.json) before any B01–B05 FX or assembly action.** Explicit current-user direction locks three distinct stages: **(1) Batch Light FX** = environmental/practical-light A/B motion proofs; **(2) Batch Character FX** = separate genuine articulated people/instruments/actions, shot-specific and Zero-Drift-gated (or reasoned NOT_APPLICABLE); **(3) Master FX + Assembly** = combine inspected per-shot layers against the full-song ONNX beat/downbeat evidence, independently verified lyric cues, frame-timed script and 50-shot storyboard. This is a workflow canon, **not a grant of individual picture/film acceptance**.

**Already done at the *light-FX technical* gate:** B01 [Actions #38675807521](https://github.com/SouthPaw302/AIVideoEdit-MainV2-Lab/actions/runs/38675807521) and B02 [Actions #38673490212](https://github.com/SouthPaw302/AIVideoEdit-MainV2-Lab/actions/runs/38673490212), each 10 originals × A/B = 20 motion proofs. Their character-action gates and Master FX remain separate/unpassed. B01's earlier `B01_FX_REPAIR_DIRECTOR_REVIEW.json` artistic verdict applied to a *full-animation expectation* and does not negate the technical success of the Light FX preparation gate; do not rewrite its historical evidence. This policy does not approve the B01/B02 pixels, replace originals, or unlock film release.

**Story and sound authority:** locked `STORYBOARD_CANON.json` (50 B01–B05 shots, SHA256 `05b232452eebce56fb9c047a0f481a19e04cf2d13e364bee30255dd27c88703a`), source WAV (SHA256 `1a4bffef36930b504423d2653faff4cc5bfd9a15d44bdcf1083b27fbb0db1c10`), `LYRICS.md`, `SCRIPT.md` / `SCRIPT.json`, and pinned Beat This! ONNX run [#38680169728](https://github.com/SouthPaw302/AIVideoEdit-MainV2-Lab/actions/runs/38680169728) (93.75 BPM, 510 beats, 140 downbeats). **The full-song beat inference passed; frame-followable screenplay/lyric-line sync are not locked.** No new storyboard and no inferred approval.

**External movie example isolation:** User plans to nominate a different repo solely for studying the other agent's *production process*. Do not inspect/import external story, characters, media, visual DNA, accepted sources, settings, manifests, branches or state as La Luna authority. Do not modify that example repo. Record methodological lessons as references only; **ask for explicit user authorization before adopting a specific method into this branch**. Keep `SOURCE_AUTHORITY.json` exclusions intact and never modify `main` or unrelated song branches as part of this exercise.


**New immutable visual plan**: `STORYBOARD_CANON.json` is the authority for 50 B01–B05 stills. The image `STORYBOARD_CANON_B01-B05.png` is stored in Drive under `06 Canon Storyboard`. Verify its SHA256 equals `05b232452eebce56fb9c047a0f481a19e04cf2d13e364bee30255dd27c88703a` before any new still or FX.

**Scope:** theatrical film and lyric-story. Board locks composition sequence, protagonists, mise-en-scène and night-to-day trajectory. It does not accept final stills/animations/edits or permit reusing tiny thumbnails as high-resolution media.

**Existing assets:** original WAV under /01 Audio; Batch 01 /02 Stills Batch 01; prior FX /03 FX Batch 01; Candidate 01 and Candidate 02 workprints under /04 Render Candidates; QC contacts /05 QC and Handoff. Keep all prior bytes. B02–B05 require genuine separate clean 16:9 still generation, incremental hashes and Drive backups.

**Execution order:** (1) Boot current Lab OS; (2) read storyboard and exact 50-index; (3) reconcile existing B01 against canon without silent deletion; (4) create B02 source frames individually and back up Batch-10; (5) visually inspect continuity; (6) create derived motion/FX proofs with hashes and separate approval; (7) repeat B03–B05; (8) build a new film candidate only when ready and perform source-to-export Director scan. AI inference and technical tests never grant owner final release approval.

**Canonical production stage:** `INITIALIZED` until actual prerequisites pass. Nothing in this handoff asserts the larger stages are done.

### Original AIVideoEdit film learning — methodology only

Read [REFERENCE_METHOD_STUDY.md](REFERENCE_METHOD_STUDY.md) for the 29-branch reference inventory, six detailed song-method examples, exact current-Lab main FX comparisons, and the corrected character/scene motion compile recipe. User instruction: **build La Luna moving characters/scenes from source duplicates, variant stills, GIF/MP4 loops, transparent alpha, depth/parallax, valid Gaussian light/spatial effects, current-main neutral FXRuntime/recipes, and bounded Director camera cuts/moves**. Real dance/instrument articulated action still requires actual credible changing poses/source motion or authorized continuation; do not claim a fixed hand/string pose was animated by lights/camera. Use the Lab current main 91-entry FX registry; don't copy any prior song's source material. True 3DGS remains conditional, whereas 2D Gaussian light is ordinary image-space FX.

Other repo: https://github.com/SouthPaw302/AIVideoEdit/tree/song/el-viento-trae-tu-nombre — **READ ONLY**. Our writable production is only `SouthPaw302/AIVideoEdit-MainV2-Lab`, branch `song/la-luna-de-florida`. No external master/hero/lyric/story/shot constraints or code automatically become La Luna authority.

## New FX and Gemini handoff

- Authoritative new experiment index: `B01_FX_DUPLICATES_INDEX.json` (10 original copies + A/B stills + A/B 2.5s loops; no human articulated motion).
- All individual hashes: https://drive.google.com/file/d/1UL6apXpmJoIdklVyX9QoDY1E7PV5V6ZK/view; QC: https://drive.google.com/file/d/1eYxL_4ABJltglAL2I849iESWVCOrga5T/view; preview: https://drive.google.com/file/d/1nLo_pUa6aSabWQaWik5O4j3c5C4BGJ7N/view.
- Gemini prompts: `GEMINI_2_CLIP_PLAN.md`; starts: https://drive.google.com/file/d/1Q5jXOmWkSxqwK01x3AmAE-S4F0njkraX/view and https://drive.google.com/file/d/1j4APw7JXepGQzU0LL0wr5JjkOIO-R0T_/view. **One actual 10s Gemini upload is now archived**: https://drive.google.com/file/d/1xC18cxLZrPgdXyUn9o8jt8hEAN0WP3p9/view (SHA-256 e9335abaad0d9ee7d62131c66eab1d6626c53e3b035b4bb1b9a0362477a102c2), with two separate silent extracted candidates in the same Gemini Drive folder. Do not claim two independent Gemini-generated videos or artistic approval.
- Source originals remain preserved; all new FX/AI media remain experimental. No main/canon pipeline promotion, no deletion, no false completed-film claim.

## New verified backup / continuation

Backup folder: https://drive.google.com/drive/folders/1AlqDTpBA0NLgRdWTF6o0et0_WsnQnfaZ. B03=9/10 recoverable (B03-S10 collision), B04=10/10, B05_NIGHT_EXTRA=10/10, all indexed. Do not overwrite them or count contact-sheet crop material as originals. Next standalone full-resolution still generation target is B05-S01..S10 (bridge, breakdown, daybreak and outro), then individual FX duplicates after original backup and visual QC.

## Sandbox backup and clean handoff (2026-10-13)

Drive audit: https://drive.google.com/file/d/1lro4XA-PSjuGxbFsc_JJDOcxEs9Vd58Z/view. The 79 current sandbox project entries were assessed: 16 direct Drive objects with matching sizes, 59 source/duplicate entries backed by SHA-matched members of CRC-tested ZIPs on Drive, and 4 noncanonical storyboard/playback images explicitly excluded from media retention as previously ordered. Remote SHA verification was **not** performed; source local hashes and exact Drive file IDs are in the audit. Original canon locked unchanged. Before local deletion, all recoverable media was backed up. The sandbox is **not a persistent source of truth**; reconstruct exclusively from Drive and the repo, and never assume local paths from historic chat handoffs still exist.

## B01 REAL FX runner — completed / Director QC pending

- [Real render run 38458305189](https://github.com/SouthPaw302/AIVideoEdit-MainV2-Lab/actions/runs/38458305189), all five parallel 2-shot jobs successful. Exact source SHA `2cf2cdddd4728e3a1f93ba1b748240baa2639d85`.
- [Individual Drive media](https://drive.google.com/drive/folders/14Mm6Y6FQ5ka8hk_0MMnSt24y-xWfxnXp): 10 unchanged source copies, 20 source-derived A/B FX stills, 20 actual 2.5s H.264 loops (24fps, 640×360), five hashed runner receipts, one backup audit. All 56 items remotely listed at matching sizes. All five ZIP artifacts passed CRC plus reported source/output file SHA-256 verification locally before backup.
- Canonical effects: `FX2-MOTION-003` water flow or `FX2-LIGHT-023` practical light. These are **small experimental motion proofs**, not full-resolution theatrical shots or real animated characters, not FX-locked and not accepted as film canon.
- The Director's pre-production approval/protection plan is `B01_DIRECTOR_PREFLIGHT.json`; Director's final visual acceptance, protected-ROI review, source-to-output movie check and any human release approval are still PENDING. Preserve all older B01 files and workprints.
