# AIVideoEdit — Reusable Effects Policy

`main/general/reusable/` is the project-neutral shared technology system. Song branches are production laboratories.

## Runtime authority
`general/reusable/fx_v2/registry.json` is the single callable FX authority. Historical catalogs/provenance are not permission to use an effect and must never import another production's art direction.

## Mandatory reuse preflight
Before creating an effect, renderer, transition, loop, spatial treatment, reactive behavior, or QC utility:
1. search `fx_v2/registry.json` and `SYSTEM_INDEX.md` by technical need;
2. inspect the neutral implementation and gate status;
3. reuse/adapt an adequate implementation before inventing a weaker substitute;
4. record selected IDs/methods in the active project plan.

## Proof and visibility
Code or planning alone is not proof. A reusable technique requires representative rendered evidence, temporal/identity/edge QC, limitations, truthful naming, and a keep/revise/reject decision. Subtle is acceptable; functionally invisible is absent.

## Promotion
Develop on the active song branch using real production material -> prove/QC -> remove production media, paths, names, story assumptions and constants -> assign capability-based neutral naming -> create neutral proof/QC -> promote to `main/general/reusable/` -> register in FX V2 when callable.

## Source-derived tooling
Generic frame extraction, source-loop generation, optical flow, retiming, depth separation, stabilization, enhancement, compositing, alpha/matte generation and temporal QC belong here when project-neutral. Source footage and identity-specific data remain on the song branch/external archive.

## Spatial truth
3DGS only means real Gaussian scene primitives; NeRF only means an actual trained radiance field; 2.5D means depth/layer image-space motion. Never relabel approximations.


## Deterministic selection requirement
Before assigning FX to a batch, scene, or still, resolve the accepted scene semantics through `fx_v2/fx_resolver.py` (or `harness.fx_resolve` through the agent harness). The resolver must read the current canonical registry and recipe catalog; agents must not rely on remembered effect names or a stale project-local list.

Resolution input must be factual and bounded: visible environment/materials/objects, narrative need, known constraints, and protected regions. A recommendation is not permission to use an unapproved effect; the existing precompile/proof gate remains authoritative.

## Recipe-first reuse
A production technique that combines existing effects, masks, alpha layers, protection policy, editorial timing, or compositing steps belongs in `fx_v2/recipes.json` when no new primitive is required. Do not mint a new FX ID merely to preserve a successful combination.

Current recipe families include transparent/ghosted narrative overlays, layered scene handoffs, protected-subject environmental motion, long-hold scene evolution, localized artifact salvage, multiplane cutout composition, temporal painting, pigment travel, instrument-axis reactive visualization and pre-FX jitter suppression.

## Scene-evolution rule
Before replacing a strong accepted composition, attempt bounded internal evolution in this order when appropriate:

`internal material motion -> alternate state -> transparent overlay -> atmosphere/light -> restrained camera travel -> transition -> new composition`

Strong images may hold for extended durations when the internal state continues to evolve.

## Artifact salvage rule
Do not regenerate an accepted composition solely for a localized artifact until crop/reframe, mask repair, alpha feather, motivated light/shadow, atmosphere, depth occlusion, focus falloff or foreground overlay has been evaluated. Regeneration is the fallback after bounded salvage fails.

## Proof ladder and rerender scope
Use `single-shot proof -> transition proof -> section proof -> full assembly`. Before rerendering, record the bounded change list and preserve accepted timing, media and masks unless the requested change invalidates them. Prefer section/shot rerenders to full-production rerenders.

## Export truth
Final approval is based on the encoded artifact, not its filename or intended settings. Verify resolution, frame rate/count, codec/profile, duration, audio, decode integrity, black/freeze behavior and hashes before delivery.
