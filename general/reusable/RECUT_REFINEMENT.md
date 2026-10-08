# Canonical Source-Library Recovery / Recut

This is a specialization of the normal AIVideoEdit pipeline for productions where the user has approved the visual world or source pixels but has **not** locked the existing edit/timeline.

## Two different kinds of acceptance

`accepted_baseline` means the complete picture/edit is accepted. Its established Director Brain behavior does not change.

`accepted_source_library` means the user approves specific pixels, shots, identities, world, and visual canon as reusable production source material while the edit remains rebuildable. It must record a locator, SHA-256, user acceptance statement, explicit content-reuse authorization, role, and `timeline_locked=false`.

A visual reference never becomes an accepted source library by inference. Current-user authorization is required.

## Defect-first law

When canonical visual material already exists, do not regenerate by reflex. First identify the actual defects. Repair only those defects and preserve everything outside the authorized repair scope.

Canonical sequence:

`CANON -> DIAGNOSE -> EXTRACT COVERAGE -> RE-EDIT -> COMPARE -> PROMOTE`

Typical defect names include composition repetition, pacing, weak coverage, identity drift, continuity, insufficient internal motion, transition weakness, source leakage, black/frozen frames, effect invisibility, compression, and sync defects. Use a smaller set when that is all the evidence supports.

## Canonical hero library

An approved video may be mined into a reusable hero-shot library. Final selection must be driven by measured quality and perceptual/composition diversity, not by blindly keeping every Nth second.

Useful measured factors include visual-signature distance, scene-transition strength, frame usability/sharpness, low/active motion state, visual centroid, palette/luminance state, and supplied musical landmarks. Semantic shot scale, subject identity, or narrative meaning must not be claimed unless a real measurement/annotation supplies them.

The library manifest preserves source identity/hash, selected frame/time, frame hash, measured signature/diversity evidence, measured tags, nearby source range, lifecycle state, duplicate-heavy warnings, and dimensions that remain unmeasured.

## Source-derived coverage vs generated new content

**Source-derived coverage** remains traceably derived from the accepted source library: crops/reframes, close/detail extraction, alternate framing, source-range reuse, conservative pan/scan, restrained 2.5D/parallax when valid, masked/layered treatments, source-derived environmental inserts, and color/optical states already inherent in authorized material.

Every source-derived asset records the accepted source-library hash plus source time/range and the derivation performed. It may not silently replace locked source canon.

**Generated new content** is new synthetic content. It uses the existing generated-media rules and is never mislabeled as source-derived coverage.

## Backend-independent creative recipe

Creative behavior is separate from the implementation backend. A proof may be produced with one backend and production rendered with another only when the production records a recipe identity, both backends, parameter/backend mappings, render implementation identity, and a representative equivalence proof.

When backends differ, the equivalence proof must PASS and show that behavior is preserved, effects remain visible, and the result is traceable. "It should look the same" is not evidence.

## Project-local FX adapter

`general/reusable/fx_v2/` remains the only canonical reusable FX authority. A production may use a project-local experimental adapter under `project_fx/` only through the fail-closed project-local FX gate.

A project-local FX manifest requires a real implementation, real hashed render inputs, deterministic/recorded parameters when applicable, hashed proof media, visible pixel change, PASS QC with reviewer identity, truthful naming, `placeholder=false`, and a current precompile lock. The lock explicitly states that canonical promotion is false. Promotion into `main/general/reusable/fx_v2/` is a separate proven process.

## Before / after refinement QC

Preserve PRE-EDIT QC and compare it with POST-EDIT QC. Relevant evidence includes composition/repetition, runtime, black/freeze detection, framing/aspect, audio coverage/sync, continuity warnings, mode-aware QC, and source/canon integrity.

`export_variety_qc.py` preserves repeat-composition evidence and can compare a prior report. `refinement_qc_compare.py` preserves the broader before/after record. Numerical improvement is evidence, not an artistic verdict; the director/user still decides whether the result is better.

## Supported recovery / recut path

`BOOT -> INGEST -> ACCEPT/LOCK SOURCE LIBRARY -> ANALYZE MUSIC -> ANALYZE EXISTING EXPORT -> NAME DEFECTS -> EXTRACT DIVERSE HERO COVERAGE -> CHOOSE/CONFIRM PRODUCTION MODE -> LOCK RECUT SHOT MAP -> LOCK SCRIPT -> BUILD SOURCE-DERIVED SHOT PACKAGES -> MOVING PROOF -> FX LOCK -> ASSEMBLE -> BEFORE/AFTER QC -> ACCEPT -> ARCHIVE`

This path does not bypass normal script, evidence, proof, FX, assembly, or final-export QC gates.

## Hybrid coverage expansion

Hybrid work may expand one approved living visual world cinematically using source-derived coverage: a hero composition can yield environment/detail inserts, alternate framing, returns to the hero, canonical optical states, and progressively shorter coverage around musical acceleration. This is a supported directing strategy, not a mandatory rhythm.
