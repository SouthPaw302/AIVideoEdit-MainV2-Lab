# Production handoff — La Luna de Florida

**New immutable visual plan**: `STORYBOARD_CANON.json` is the authority for 50 B01–B05 stills. The image `STORYBOARD_CANON_B01-B05.png` is stored in Drive under `06 Canon Storyboard`. Verify its SHA256 equals `05b232452eebce56fb9c047a0f481a19e04cf2d13e364bee30255dd27c88703a` before any new still or FX.

**Scope:** theatrical film and lyric-story. Board locks composition sequence, protagonists, mise-en-scène and night-to-day trajectory. It does not accept final stills/animations/edits or permit reusing tiny thumbnails as high-resolution media.

**Existing assets:** original WAV under /01 Audio; Batch 01 /02 Stills Batch 01; prior FX /03 FX Batch 01; Candidate 01 and Candidate 02 workprints under /04 Render Candidates; QC contacts /05 QC and Handoff. Keep all prior bytes. B02–B05 require genuine separate clean 16:9 still generation, incremental hashes and Drive backups.

**Execution order:** (1) Boot current Lab OS; (2) read storyboard and exact 50-index; (3) reconcile existing B01 against canon without silent deletion; (4) create B02 source frames individually and back up Batch-10; (5) visually inspect continuity; (6) create derived motion/FX proofs with hashes and separate approval; (7) repeat B03–B05; (8) build a new film candidate only when ready and perform source-to-export Director scan. AI inference and technical tests never grant owner final release approval.

**Canonical production stage:** `INITIALIZED` until actual prerequisites pass. Nothing in this handoff asserts the larger stages are done.

## New FX and Gemini handoff

- Authoritative new experiment index: `B01_FX_DUPLICATES_INDEX.json` (10 original copies + A/B stills + A/B 2.5s loops; no human articulated motion).
- All individual hashes: https://drive.google.com/file/d/1UL6apXpmJoIdklVyX9QoDY1E7PV5V6ZK/view; QC: https://drive.google.com/file/d/1eYxL_4ABJltglAL2I849iESWVCOrga5T/view; preview: https://drive.google.com/file/d/1nLo_pUa6aSabWQaWik5O4j3c5C4BGJ7N/view.
- Gemini prompts: `GEMINI_2_CLIP_PLAN.md`; starts: https://drive.google.com/file/d/1Q5jXOmWkSxqwK01x3AmAE-S4F0njkraX/view and https://drive.google.com/file/d/1j4APw7JXepGQzU0LL0wr5JjkOIO-R0T_/view. **No Gemini outputs exist yet.** Wait for actual video uploads, hash/inspect before promotion.
- Source originals remain preserved; all new FX/AI media remain experimental. No main/canon pipeline promotion, no deletion, no false completed-film claim.

## New verified backup / continuation

Backup folder: https://drive.google.com/drive/folders/1AlqDTpBA0NLgRdWTF6o0et0_WsnQnfaZ. B03=9/10 recoverable (B03-S10 collision), B04=10/10, B05_NIGHT_EXTRA=10/10, all indexed. Do not overwrite them or count contact-sheet crop material as originals. Next standalone full-resolution still generation target is B05-S01..S10 (bridge, breakdown, daybreak and outro), then individual FX duplicates after original backup and visual QC.
