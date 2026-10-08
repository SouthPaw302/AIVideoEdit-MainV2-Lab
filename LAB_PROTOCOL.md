# MainV2 Lab — Production Proof Protocol

## Why this lab exists
The parent AIVideoEdit system has completed music-video work. Experimental MainV2 showed green automated tests but **no independently accepted, delivered visual production**. We must investigate **visual quality, deployability, and guards**, not count workflow success as artistic success.

## Isolation
- Never use source AIVideoEdit as a write destination.
- Test source is an **exact immutable SHA** from `SOURCE_LOCK.json`. Changing the pin requires review.
- No secrets or credentials from the production repo.
- Keep `main` in this lab as a small protected evaluation baseline. Test changes on PR branches.
- GitHub Settings must independently enable branch protection / rulesets for lab `main` (see below); branch protection is an account setting, **not enabled by a file**.

## Stage A — Technical smoke (NOT artistic evidence)
A CI smoke may execute the existing MainV2 six-second test-pattern probe. It can report *TECHNICAL_SMOKE_PASS*, **never VISUAL_ACCEPTED** or *PRODUCTION_COMPLETE*. Record source commit, workflow URL, final video SHA, rendered duration and stream geometry.

## Stage B — Genuine 30-second production
Select 30 seconds of **actual music** and approved real production stills/clips. In a `song/<slug>` lab work branch:
- Use the actual MainV2 stack; no substitute FFmpeg-only assembly that bypasses it.
- Freeze source audio and visual asset identities/hashes before rendering.
- Generate the exact video, contact sheet and technical report.
- Reject blank/placeholder scenes, unmotivated overlays, geometry/face/horizon drift, silent audio, broken titles or broken transitions.
- Publish a **persistent downloadable and playable MP4**, not merely an ephemeral Actions artifact.
- Invite explicit human visual approval; a model or workflow cannot approve its own creative output.

## Stage C — Complete film
Use an **entire, real song** (not synthetic six-second fixtures), then a long-form mix. Require locked source, no unauthorized substitutions, end-to-end output, actual download/playback, QC reports, and recorded human approval.

## Acceptance record (must accompany each candidate)
Create `reviews/<candidate-id>.md` documenting:
- Source repo SHA and lab code SHA; exact song / source visual hashes
- Render SHA256, codec, resolution, frame rate, duration, audio channels
- Persistent MP4 link + proof link to playback/test capture
- What was actually watched (entire candidate, normal speed)
- Visual findings (movement, story, continuity, image quality, source identity)
- Deployment/download result, including browser and device if applicable
- Human reviewer + review date + **ACCEPT** or **REJECT**
- Any rejected reason, reproduction steps and next bounded repair

**No review record = PENDING.** `CI success` does not substitute for visual approval.

## Deployment / proof storage
Temporary CI artifacts are supplementary only. Keep durable candidate files in a designated Drive folder or clearly labeled prerelease asset, with SHA and playback verification. Never promote prerelease proof as a finished canonical music video.

## Lab branch protection (manual GitHub account setting)
Settings → Rules → Rulesets (or Branches → Add branch protection rule):
- Target `main`
- Require pull request before merge
- Require relevant successful checks after workflow is proven functioning
- Block force pushes and deletion
- Require conversation resolution
- For code changes, enforce at least one independent reviewer when available

Note: account permissions or GitHub plan may limit some options. If a sole maintainer uses bypass, document bypasses; no unreviewed MainV2 promotion.

## Current gate
`SOURCE_PINNED` only. **VISUAL_REVIEW_PENDING** until a real-production candidate is accessible and human-reviewed.
