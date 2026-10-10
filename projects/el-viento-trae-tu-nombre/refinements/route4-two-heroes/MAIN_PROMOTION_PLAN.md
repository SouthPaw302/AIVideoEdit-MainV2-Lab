# Main Promotion Plan — Pending Scan

Status: PLAN ONLY — DO NOT PUSH TO MAIN YET

## Goal
Extract only reusable production intelligence into the neutral `general/reusable` system after review.

## Planned promotion areas
- Reusable FX recipes and combinations from the existing FX2 library.
- 10-image exploration batch workflow → selected hero set → clean loops → GIF previews → pre-FX motion → FX variants → shot lock.
- Long-hold scene-evolution editing: internal motion, transparent overlays, lighting/material FX, and restrained camera movement before changing major compositions.
- Artifact-salvage-before-regeneration rule using motivated light, atmosphere, masking, alpha feather, focus, crop/reframe, depth occlusion, or overlays.
- Proof ladder: single-shot proof → transition proof → section proof → full picture assembly.
- One authoritative shot/media/FX manifest with timing, provenance, acceptance state, and protected regions.
- Reusable FX library review gate before final creative lock.
- Preserve clean loop, pre-FX motion, and effected variant when practical.
- Harness owns deterministic mechanics/evidence; agent owns story, shot choice, continuity, repair judgment, and final visual review.
- Written bounded change list before rerendering; prefer section rerenders over full rerenders.
- Actual-export validation: verify encoded resolution, frame rate/count, codec/profile, duration, audio properties, decode integrity, black/freeze behavior, and hashes.
- Final creative-lock workflow: 1080p lock/QC → frame-exact chunking → upscale → reconstruct → untouched audio mux → final QC.
- Generic chunked handoff manifest, hashes, and reconstruction script conventions.
- Milestone-only status reporting during long jobs; avoid repeated unchanged polling/narration.
- Archive and verify durable backups continuously rather than waiting until the end.

## Efficiency rules
- Boot current canonical repo state before interpretation.
- Lock scope, forbidden references, deliverables, and branch before generation.
- Do not rescan unchanged media or reread unchanged documents.
- Reuse accepted timing, masks, media, and manifests unless a requested change invalidates them.
- Do not run expensive full renders until bounded proofs pass from first to final boundary.
- Promote decisions into project state once so later agents do not reconstruct them from chat.
- Never claim completion without a real artifact plus verification evidence.

## Promotion constraints
- No project/song/hero names in reusable assets.
- No production timestamps, Drive IDs, or project-specific filenames.
- Reuse existing FX IDs where capability already exists; do not duplicate effects.
- Keep production media on its production branch/Drive.
- Scan and compare against `main/general/reusable` before any implementation or merge.
- No changes to `main` until explicitly approved after the scan.


## Repo-wide FX harvest additions

Before any promotion to `main`, treat the full repository scan as part of the promotion gate. Do not rely only on canonical FX IDs; inspect project-local renderers, proof manifests, overlay assets, transition code, masks, and one-off compositing logic.

### New canonical FX candidates
- Threshold Prism Bleed: localized threshold-edge spectral separation, oriented rays, scatter/dust, and optional ghost-room exposure. Existing project implementation/proof should be generalized and re-proofed under a neutral FX2 identity.
- Matched-angle viewpoint shift: bounded source-locked 2D plate projection with tiny Y-axis viewpoint change, overscan, and reflected borders. Generalize only if proof confirms identity/topology remain stable.

### Reusable composition / recipe candidates
Promote as neutral recipes rather than duplicate low-level FX where primitives already exist:
- Ghosted narrative object overlay: independently drifting semi-transparent object/scene fragment used for memory, symbolism, foreshadowing, or handoff.
- Layered transparent scene handoff: base shot + masked alpha variation + independent motion + shared light/atmosphere + dominance transfer into destination.
- Transparent multiplane cutout composition using real foreground RGBA layers over an untouched base plate.
- Protected-subject environmental motion: surrounding architecture, crowd, atmosphere, particles, or room movement while face/hands/anatomy/instruments/critical props remain locked.
- Motivated transition completion: complete the handoff into the destination before the edit boundary; never snap back to the source.
- Artifact salvage with motivated light, fog/smoke, masks, alpha feather, depth occlusion, focus falloff, crop/reframe, foreground overlays, or shadow before regeneration.
- Long-hold scene evolution: internal motion -> variation -> transparent overlay -> light/material FX -> restrained camera movement -> transition.
- Instrument-axis audio visualizer: audio-reactive trace/glow integrated along an existing instrument/object axis rather than a generic screen-space waveform.
- Temporal painting / dusk-to-night evolution: scene palette, practicals, windows, and reflections change progressively rather than applying one static grade.
- Recursive object-portal / match-cut usage using existing portal primitives.
- Gaussian light sweep + fog/atmosphere overlay combinations.
- Embroidery/thread shimmer reveal.
- Map/ink reveal through textured or edge-derived masks.
- Pigment-mask travel / wet-paint scene transport.
- Ghost-silhouette emergence through opacity/mask evolution.
- Localized water/current displacement limited to plausible fluid regions.
- Jitter suppression before FX as a finishing utility when source motion contains high-frequency global translation.

### Rebuild / investigate before promotion
Do not copy these directly into canonical runtime until provenance and proof are rebuilt:
- custom ribbon / contour transport transitions
- generated ring / filament overlays
- temporal echo
- petals
- bounded perspective pulse
- any historical effect name present in proofs but absent from the current registry/runtime

### Harvest classification rule
Every discovered technique must be labeled as exactly one of:
1. already canonical in main
2. existing primitive but new reusable recipe
3. genuine new reusable FX candidate
4. experimental/rebuild-before-promotion
5. project-specific; leave on source branch

### Promotion discipline
- Prefer recipes and orchestration intelligence over duplicate FX IDs.
- Reuse current FX2 primitives whenever they already provide the underlying behavior.
- New FX IDs require neutral naming, implementation provenance, proof render, visual QC, encoded-output verification, and registry consistency.
- Preserve project-specific source media and narrative context on their branches; only the generalized capability may move to `main`.


## Implementation checkpoint — 2026-09-24

Status: IMPLEMENTED TO MAIN

Merged PR: #53
Main commit: `9fc16c16eae69514bf959170f96d6eb5ad4d9e56`

Implemented:
- deterministic batch/scene/still FX resolver that reads the canonical registry plus reusable recipe catalog;
- read-only `harness.fx_resolve` integration for agent workflows;
- reusable recipe catalog covering ghosted narrative overlays, transparent handoffs, protected-subject environmental motion, long-hold evolution, artifact salvage, multiplane alpha composition, temporal painting, pigment travel, instrument-axis visualization, and pre-FX jitter suppression;
- deterministic FX resolution added as a standard workflow and reusable-effects policy requirement;
- repo-harvest candidates `threshold_prism_bleed` and `matched_angle_viewpoint` generalized into neutral code and registered as `proof_required`, not production-approved;
- resolver tests and existing repository verification gates passed before merge.

All five PR verification workflows passed, including `production-contract`.
