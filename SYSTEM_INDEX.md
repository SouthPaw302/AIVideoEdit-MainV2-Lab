# AIVideoEdit — System Index

Permanent-system index only. No active production names or unrelated song links belong here.

## Runtime bootstrap
- `bootstrap.py` — universal portable entry point; installs/loads the entire exact current `main` OS into a sandbox, runs current-main production/recut guards, and creates the session attestation plus rich Director Brain context.
- `PRIME_DIRECTIVE.md` — permanent short directing law: choose the right production form, approval creates canon, distinguish accepted baseline from accepted source library, preserve accepted work, diagnose before regeneration, refine instead of drifting.
- `SOUL.md` — permanent AIVideoEdit identity and invariant behavior.
- `general/reusable/AIVIDEOEDIT_OS_MANIFEST.json` — critical current-main files attested each session.
- `.aivideoedit/session.json` — ephemeral bootstrap attestation; never committed.
- `.aivideoedit/SECOND_BRAIN.md` — ephemeral generated branch/session context; never committed. Director Brain v2 surfaces mode, canon, accepted baseline, accepted source library, baseline refinement, recut scope, forbidden changes, and next action.

## Director Brain v2
- `general/reusable/PRODUCTION_MODES.md` / `.json` — separates direction authority from production mode and defines `living_scene`, `cinematic`, and `hybrid`.
- `projects/OPERATING_ORDER_TEMPLATE.json` — project-level directing brief template; keeps complete-edit baseline acceptance separate from canonical source-library acceptance.
- Active Director Brain v2 productions use `OPERATING_ORDER.json` in the project directory.
- `general/reusable/DOCTRINE_LIVING_SCENE.md` — generalized living-scene production doctrine.
- `general/reusable/ZERO_DRIFT_DIRECTOR_DIRECTIVE.md` — binding continuity law for multi-frame/multi-shot scene generation: immutable subject/environment anchors, bounded camera/parallax motion, canonical FX-only execution, deterministic zero-drift scene JSON, and fail-closed continuity handling.
- `general/reusable/RECUT_REFINEMENT.md` — canonical source-library recovery/recut doctrine, source-derived coverage rules, backend-equivalence rules, project-local FX path, and before/after QC.
- `general/reusable/MODE_AWARE_QC.md` — creative proof/QC requirements by production mode and source-library recut comparison.
- `general/reusable/DRIFT_TESTS.md` — expected agent behavior under common drift scenarios.

## Universal contract
- `AGENTS.md` — universal agent entry point; first action is bootstrap and then Prime Directive + Second Brain.
- `general/reusable/PRODUCTION_CONTRACT.json` — machine-readable production state/rules including Director Brain v2 and recut policies.
- `general/reusable/tools/production_guard.py` — fail-closed production-stage/bootstrap-session/director-state validator.
- `general/reusable/tools/narrative_guard.py` — fail-closed lyrics/genre/music/script/media-evidence validator.
- `general/reusable/tools/recut_guard.py` — fail-closed accepted-source-library, source-derived provenance, hero-library, render-equivalence, project-local FX, and before/after recut validator.
- `general/reusable/NARRATIVE_CONTRACT.md` — narrative/music/script/real-media doctrine enforced by the narrative guard.
- `general/reusable/MEDIA_CAPABILITY_MATRIX.json` / `.md` — media forms available to production, including canonical hero libraries and source-derived coverage.
- `projects/PROJECT_TEMPLATE.md` — required branch-local state/manifests and Director Brain v2 project rules.

## Doctrine
- `README.md`
- `AGENT_HANDOFF.md`
- `BIBLE.md`
- `PRIME_DIRECTIVE.md`
- `general/reusable/PRODUCTION_PIPELINE.md`
- `general/reusable/RECUT_REFINEMENT.md`
- `general/reusable/STYLE_CONTRACT.md`
- `general/reusable/NARRATIVE_CONTRACT.md`
- `general/reusable/DOCTRINE_LIVING_SCENE.md`
- `general/reusable/ZERO_DRIFT_DIRECTOR_DIRECTIVE.md`
- `general/reusable/MODE_AWARE_QC.md`

## Reusable capabilities
- `general/reusable/fx_v2/` — callable FX runtime/registry/proofs/gate; single canonical reusable-FX authority.
- `general/reusable/fx_v2/project_local_fx_gate.py` — fail-closed adapter/lock gate for production-local experimental FX; never promotes into canonical `fx_v2` by itself.
- `general/reusable/fx_v2/material_reactive_layers.py` — luminance-split living-material motion plus deterministic orbital/audio-reactive ember paths; registry-gated.
- `general/reusable/generative-engine/` — audio analysis, shared controls, reactive/spatial runtime.
- `general/reusable/painterly-motion/` — living/painterly motion and temporal QC.
- `general/reusable/memory-atmosphere/` — restoration/atmosphere treatments.
- `general/reusable/depth-parallax-25d/` — depth-assisted 2.5D motion.
- `general/reusable/storage/` — GitHub Releases media storage adapter and manifest schema.
- `general/reusable/tools/hero_library_extract.py` — quality/perceptual-diversity hero-frame extraction with measured evidence and near-duplicate rejection.
- `general/reusable/tools/export_variety_qc.py` — complete-export contact-sheet/perceptual repetition warning tool with before/after report comparison support.
- `general/reusable/tools/refinement_qc_compare.py` — preserves broad pre/post recut QC evidence; metrics are evidence, not directing authority.
- `general/reusable/tools/test_recut_system.py` — recovery/recut regression suite.
- `general/reusable/tools/` — generic utilities.
- `general/reusable/SPATIAL_3DGS_SUPERSPLAT.md` — truthful 3DGS doctrine.

## Branch selection
New supplied audio master -> new `song/<slug>` from current `main`. Explicit request to continue a named existing branch -> continue it. Otherwise never infer continuation from historical names.

## Standard capability selection
- `general/reusable/fx_v2/registry.json` — callable effect authority, including neutral standard effects promoted from prior technique work.
- `general/reusable/fx_v2/promoted_effects.py` — project-neutral runtime implementation for the standardized effect library.
- `general/reusable/fx_v2/verify_standard_effects.py` — per-effect visible/temporal/determinism verification and proof-report generator.
- `general/reusable/STANDARD_WORKFLOW_REGISTRY.json` — project-neutral non-effect workflow authority.
- `general/reusable/tools/workflow_resolver.py` — selects standard workflows from current production mode + media capabilities.
- `general/reusable/tools/workflow_guard.py` — fail-closed registry/project selection verification; bootstrap runs it when present.

Historical production names are not capability identities and are not used for automatic selection.
