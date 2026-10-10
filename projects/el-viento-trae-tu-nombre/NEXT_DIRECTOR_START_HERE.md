# NEXT DIRECTOR — BOOT CURRENT MAIN, DIRECT A NEW EL VIENTO FILM

## Authority: user's latest instruction (2026-10-10)

> The next Director can change the existing MP4, build a different storyline and make a NEW production. It must pull/fetch `main`, boot, and work on the song branch.

**This is not an FX-only repair or an attempt to recreate the previous movie.** There is no requirement to preserve the original 154.375s edit, Route 4 two-character story, shot order, image selection, camera language, or scene timing in the new candidate. Change whatever is needed to make a worthy new film. Existing assets are reusable but optional. The published result is a strong benchmark, not binding visual canon.

## Required first operation (before interpretation or changes)

Repository: `SouthPaw302/AIVideoEdit-MainV2-Lab`; branch: `song/el-viento-trae-tu-nombre`.

```bash
# In the Lab repository worktree; clone it first if absent:
git fetch origin main song/el-viento-trae-tu-nombre
git switch song/el-viento-trae-tu-nombre
git pull --ff-only origin song/el-viento-trae-tu-nombre
python bootstrap.py boot --repo-root . --branch song/el-viento-trae-tu-nombre
```

**Stop on anything except `AIVideoEdit OS BOOTSTRAP: PASS`.** The bootstrap retrieves exact current `main` and mounts it under `.aivideoedit/os`; do **not** copy old engine files, `git pull origin main` into a song commit, or push project assets to `main`. A fresh session requires a fresh boot.

Read in order after PASS: `.aivideoedit/os/PRIME_DIRECTIVE.md`, `.aivideoedit/SECOND_BRAIN.md`, `.aivideoedit/os/SOUL.md`, then `OPERATING_ORDER.json`, `NEXT_DIRECTOR_HANDOFF.json`, current-main `general/reusable/DIRECTOR_SCAN_CANON.md`. Run current-main production, narrative, recut and workflow guards after boot.

## The benchmark — study before you decide what to create

- Published film: **https://youtu.be/5bYgvrFJJ80**
- Attached finished-film reference was locally probed, not rendered: `El Viento trae tu nombre.mp4`, SHA-256 `4ecba2862c84b5a64bd5001eae308374c18c77cef6bafe815ab11a08b20548a7`, 34,209,452 bytes, 1280×720 at 24 fps, 3705 frames, 154.389478 seconds; H.264 + AAC. The embedded MP4 is a *user-uploaded reference*. Matching this hash to the published YouTube stream or a Drive file still requires independent proof.
- Prior Route 4 1080p candidate: `El_Viento_Route4_1080p_FX_MASTER_v6.mp4`, recorded original SHA `5fe93ef79d528a27cb7a15003aac9e9bc50a0db40a6719a102d36d5f10314af0`; 9 playable MP4 segments in [Drive](https://drive.google.com/drive/folders/1ojhQ1k4yDDA9o8h3bp2sP3YF5Cn-EuKu). These are not proven an exact byte-rebuild of the original single-file master.
- Music master: `El Viento trae tu nombre.wav` [Drive](https://drive.google.com/file/d/1M6uRTeYejXxn2rSDkTJu5H0_LiWrdwN4/view); record SHA `8d967101c875868b64207bd43bfbc507c0a958989bbc560c2edb0024b15877cb`, 154.48 seconds; verify bytes before new media encoding.
- 46/46 Drive-linked historical asset records were found via metadata. Detailed Drive IDs and the remaining four historical session-only locators: `LAB_MEDIA_STAGING_INDEX.json`.

Understand what makes the existing film effective, but **do not attempt to preserve every shot**. The user specifically authorizes a substantially different film. Assess its pacing, narrative motifs, atmosphere, character/world continuity and musical structure as useful research.

## Director's new production authority

1. Choose an original interpretation (new plot, storyworld, character roster and visual route) using the song lyrics/audio and your analysis. You may keep anything from Route 4, or abandon its plot, cut structure and visual approach altogether. Do not falsely portray the original as bad or claim a new treatment is better without review.
2. Rewrite the *active* `MEDIA_PLAN.json`, `SCRIPT.md` / `SCRIPT.json`, `SHOT_LIST.md`, FX plan and asset selection for the **new production**, passing the current-main gates in order. The old versions are recoverable from Git history/source pin and archived snapshots. Do not quietly reuse legacy `ASSEMBLED`/FX gate statuses as proof for new work.
3. Stage real Drive sources through the approved authenticated media path; verify SHA-256 before consumption. New images, videos, clean loops, pre-FX copies, effected variants, and new Batch-10-or-later segments are allowed if the selected concept needs them. Avoid inert metadata-only shot packages.
4. Use the **new Lab's current-main** Director/Harness, FX execution and QC, the actual audio and verified sources, with real short motion/transition proofs before expensive final rendering. Store assets in Drive, track hashes/manifests, use GitHub runners for heavy processing, and ensure cross-shard continuation. No throwaway microdeployments.
5. A new candidate may have different runtime/timing, subjects, composition, visual effects, camera path, story and render treatment. Record deviations deliberately. Do not overwrite the published movie, original V6, original accepted edits, or Drive canon in place. New output gets distinct media IDs/paths.
6. Final evaluation: compare the **actual viewed** new film to the published benchmark at normal speed. Technical PASS is not creative ACCEPT. Keep user visual approval and independent 4K/release controls; no premature publication.

## What's not negotiable

Only work in `song/el-viento-trae-tu-nombre` and its project folder. Never merge song-production data to protected Lab `main`, never modify the original `SouthPaw302/AIVideoEdit` repository, never override or delete historical accepted media/masters, and do not bypass bootstrap/guards/source verification. These are production-integrity rules, **not aesthetic limitations**.

**This handoff has not rendered anything.** The NEXT agent may begin production and later render authorized independent candidates through the canonical gated stack. The old "do not restart / FX-only" instructions were for a prior production task and are superseded.

## First agent report to user

Give the actual current-main OS SHA from bootstrap PASS, active song-branch SHA, media/reference findings, your new creative direction and how it differs from the published version, initial proof plan, and the next bounded step. Never claim to have watched, rendered or verified an artifact that was not actually inspected.
