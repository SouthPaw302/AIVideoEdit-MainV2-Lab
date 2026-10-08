# AIVideoEdit — MainV2 Lab

**Isolated visual-production validation laboratory** for the experimental MainV2 engine.

The production system is [SouthPaw302/AIVideoEdit](https://github.com/SouthPaw302/AIVideoEdit). **Never push, merge, deploy, or write into that production repository from this lab.**

## Mission
Prove that MainV2 can produce a **watchable, approved, deliverable music film**. A green CI job, self-accepted creative QC, or a short synthetic test pattern is **not** a completed work.

## Baseline
- Original repository: `SouthPaw302/AIVideoEdit`
- Experimental source branch: `MainV2`
- Initial pinned source commit: `316fe96c7316d76d14308d5f27293e071aa20943` (2026-10-03)
- This repository is an isolated **lab harness**, not a replacement for the original `main`.
- Source pin changes only by reviewed pull request.

## Gate sequence
1. **SOURCE_PINNED** — exact SHA, source provenance, reproducible environment.
2. **TECHNICAL_RENDERED** — actual output decoded, duration/audio/resolution verified; logs and artifact retained.
3. **VISUAL_REVIEW_PENDING** — accessible playback/video submitted for independent human inspection.
4. **VISUAL_ACCEPTED** — explicit named human sign-off on visuals, pacing, continuity, motion and no placeholder substitution.
5. **DELIVERY_VERIFIED** — persistent download/playback link and SHA recorded outside transient CI artifacts.
6. **PRODUCTION_ACCEPTED** — complete music film meets all above gates.

Any missing gate is **NOT COMPLETE**. The rendering agent must not sign its own visual acceptance.

## Rules
- Use actual production footage and song source for acceptance tests, not just six-second synthetic probes.
- Keep rejected media and interim renders clearly labeled as non-canonical.
- Test as a song production in an isolated project; do not rewrite the existing Main song branches.
- Put evidence in `evidence/` as small metadata files. Store MP4s in durable external storage and link them from manifests.
- Lab workflows have read-only access to the original source; no source-repo write token.
- No automatic promotion to the original AIVideoEdit.
- Do not call something a release before its human visual approval and persistent delivery are verified.

## Current status
**LAB BOOTSTRAP** — no accepted MainV2 production has been established here.

See `LAB_PROTOCOL.md` and the workflows added on the setup branch.
