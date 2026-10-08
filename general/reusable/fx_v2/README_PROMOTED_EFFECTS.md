# Effect-Centric Promoted FX Library

This is the live neutral-name compatibility layer for reusable effects recovered from earlier productions.

## Authority
- `effect_name_registry.json` lists callable promoted effects by neutral effect name.
- `promoted_effects.py` implements `apply_effect(name, frame, t, duration, energy, transient, second_frame)`.
- `effect_aliases.json` maps historical labels to neutral names only; project names are not effect identities and do not import art direction.
- `verify_promoted_effects.py` deterministically exercises every promoted effect at multiple times.
- `proofs/FX2_PROOF04_PROMOTED_EFFECT_LIBRARY.verification.json` records the per-effect verification metrics.

## Promotion rule
An effect may be marked approved in the effect-name registry only when the implementation is callable, produces a visible source delta, produces a temporal delta, has a stable neutral name, and is covered by CI verification. Production-specific semantic suitability remains the responsibility of the shot package and QC.

## Scope
This layer intentionally contains reusable visual, spatial, transition, audio-reactive and visualizer effects. Workflow/system capabilities such as cache invalidation, nested timelines, version branching, delivery architecture and general QC architecture remain system capabilities rather than being mislabeled as visual effects.
