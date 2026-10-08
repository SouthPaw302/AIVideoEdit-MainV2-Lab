# FX V2 — Agent Handoff

## What this is

`general/reusable/fx_v2/` centralizes existing AIVideoEdit effect technology that had become fragmented across Silver Coin, Irish Eyes, IronFlame and Leave It by the Door renderers.

Do not treat this as a claim that every effect is newly invented. Much of the value is consolidation, stable IDs, better implementations, proof lineage, and hard validation before production use.

## Read order

1. `README.md`
2. `registry.json`
3. `presets.json`
4. `PRECOMPILE_FX_GATE.md`
5. `precompile_gate.py`
6. `runtime.py`
7. `proofs/`

Then inspect the legacy lineage when changing an effect:
- `../silver-coin-tools/`
- `../silver-coin-docs/`
- `../irish-eyes-tools/`
- song-specific Magic Gate / IronFlame docs on their branches

## Core architecture

Song manifests call stable effect IDs and parameters. They must not silently reimplement weaker local substitutes.

Primary runtime families:
- internal/living motion
- water/reflection motion
- rain / rain glass / smoke / spray
- living flame / embers
- practical and moving light
- temporal palette / surface stability
- perceptual transitions
- honest 2.5D / NeRF / real 3DGS integration

Design law: **internal scene motion first; camera motion second.** Global shake is not a default animation technique.

## Hard precompile gate

Production use requires `precompile_gate.py`.

The gate checks that each requested effect:
- exists in `registry.json`;
- is approved for production use;
- resolves to a real runtime implementation;
- is actually wired through the callable runtime rather than merely named;
- contains no placeholder/TODO/pass/NotImplemented path;
- has an effect proof that covers that exact FX ID;
- has proof metadata including native cadence, sufficient frames, checksum and visual KEEP/PASS/APPROVED QC;
- changes pixels meaningfully in a runtime smoke test;
- changes temporally when it is a temporal effect;
- does not introduce unintended whole-frame shake for ordinary living-image effects;
- satisfies transition endpoint/evolution tests for transition families.

A successful gate writes an FX lock containing hashes of the manifest, registry and runtime. Final compile/render must verify that lock again. Changed code or configuration invalidates the lock.

GitHub Actions workflow: `.github/workflows/fx-v2-precompile-gate.yml`.

CI includes both:
- a positive approved-core test;
- a negative test that deliberately asks for an unapproved effect and requires rejection.

The negative test exists to prove the gate is fail-closed rather than ceremonial.

## Current proof state

`FX2_PROOF01_LIVING_TAVERN` is the first native-cadence engine proof. It verifies independent internal motion with locked camera: fire, embers, smoke, rain, water/reflection, localized living flow, light and stable surface treatment.

Effects still marked `proof_required` or `conditional` remain blocked even if code exists. Do not promote them by editing status alone; render and QC them first.

## SuperSplat / 3DGS rule

SuperSplat is an approved editor/render path for genuine Gaussian-splat scene data. It is not permission to call 2D Gaussian light/noise fields '3DGS'. Use the 3DGS ID only when actual splat geometry exists and is rendered.

## Active integration

Current production integration target is `song/leave-it-by-the-door` V3.

That revision keeps native-24 V2 as the picture baseline while:
- reducing camera/global shake;
- increasing loop-safe internal movement;
- strengthening animated flame/candle/ember/smoke/reflection behavior;
- preserving character identity and painterly stability;
- adding YouTube intro/outro;
- passing the FX precompile gate before final render;
- delivering the final upload package in a ZIP.

## Promotion rule

Once the integration pass is clean and the reusable stack is stable, promote the generic FX V2 system to `main/general/reusable/fx_v2/`. Song-specific manifests/timing stay on song branches.
