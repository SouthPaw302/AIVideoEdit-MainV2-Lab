# AIVideoEdit — Agent Handoff

## First action in every new session
Run:

```bash
python bootstrap.py boot --repo-root <repo>
```

Do not continue a handoff, inspect production history, generate media, change state, select FX, or render before bootstrap passes.

After PASS, read in this order:
1. `.aivideoedit/os/PRIME_DIRECTIVE.md`
2. `.aivideoedit/SECOND_BRAIN.md`
3. `.aivideoedit/os/SOUL.md`

For Director Brain v2, the Second Brain is the immediate orientation surface. It must expose the active project mission, direction authority, production mode, canon, accepted baseline, refinement scope, forbidden changes, and exact next action.

## Authority
1. Current explicit user instruction.
2. Active `song/<slug>` branch state/manifests and `OPERATING_ORDER.json` when Director Brain v2 is active.
3. Current-main AIVideoEdit OS loaded into `.aivideoedit/os/`.

Historical chats/summaries, unrelated branches, old production imagery, and provenance are not automatic authority. Use them only when the current user explicitly authorizes them.

## Runtime
Before advancing state, run:
`python .aivideoedit/os/general/reusable/tools/production_guard.py --branch <current-branch>`

Also run the bootstrapped directing/media guard when present:
`python .aivideoedit/os/general/reusable/tools/narrative_guard.py --branch <current-branch>`

Do not substitute stale branch-local guards for current-main guards. Inspect relevant project-neutral reusable capabilities before inventing substitutes. Resolve callable FX only through the bootstrapped current-main `general/reusable/fx_v2/registry.json`.

## Director rule
Do not force every song into one filmmaking method. Separate direction authority from production mode and follow the active Operating Order.

If the user has accepted a baseline and refinement is active with `restart_authorized=false`, preserve the accepted foundation. Do not regenerate canon or reinterpret the production because a new idea is available. Repair the allowed defects and compare against the accepted baseline.

## Production rule
Build real media, not slides or metadata theater. Inspect short finished mode-aware proofs before scaling. For living-scene work, internal scene motion comes before camera motion. For cinematic work, prove action, coverage, continuity, progression, and music-directed pacing. Protect identity. Never accept invisible effects or command success as QC.

## Final QC
Inspect the actual exported media for damaged/black frames, freezes, repetition, loop seams, ghosting, missing effects, flicker/boiling, identity drift, source leakage, continuity, framing/aspect, runtime, and audio sync. Apply `MODE_AWARE_QC.md`, record specs/SHA/storage/QC, and preserve artistic masters separately from platform packaging when they differ.
