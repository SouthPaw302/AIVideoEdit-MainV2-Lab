# Spatial 3DGS / SuperSplat Production Rule

This is the canonical cross-project rule for 3D Gaussian Splatting in AIVideoEdit.

## Technical truthfulness

A 2D Gaussian blur, glow, light field, splatter brush, depth warp, parallax pass, or painterly particle field is **not** 3D Gaussian Splatting.

True 3DGS requires actual Gaussian scene primitives/geometry produced from a valid reconstruction or spatial-generation pipeline. Use the terms `3DGS`, `Gaussian splat`, or `SuperSplat` only when that real scene representation exists and is rendered.

## Canonical role of SuperSplat

SuperSplat is the preferred open-source inspection/editing layer for genuine splat scenes. It may be used to inspect geometry, remove floaters, crop useful scene volume, validate occlusion/parallax, and prepare camera paths or assets for compositing.

Browser/WebGPU viewers such as `gsplat.js` or Luma's web player may be useful review surfaces. They do not by themselves create or prove a production 3DGS asset.

## Source requirements

A shot may enter the true-3DGS path only when at least one exists:

1. a real supported splat scene such as `.ply` produced by reconstruction;
2. sufficiently overlapping multi-view capture suitable for reconstruction;
3. a validated generated spatial representation exportable as real splat geometry.

A single flat still remains a 2.5D/depth-assisted asset unless additional geometry or views are produced.

## Spatial tiers

- Tier 0 — flat image: lighting, atmosphere, surface treatment only.
- Tier 1 — living painting: protected local warps, depth masks, water/reflection, fire, smoke, cloth/hair micro-motion.
- Tier 2 — depth-assisted spatial shot: explicit depth map or segmented planes with bounded camera travel.
- Tier 3 — true 3DGS: real Gaussian scene primitives with legitimate viewpoint-dependent parallax and occlusion.

## Production gate

`FX2-SPATIAL-003` remains `conditional`. A production manifest must explicitly opt in and provide a technology-specific preflight JSON whose `result` is `PASS`. That evidence is hashed into the FX lock.

A Tier-3 shot is acceptable only after:

- geometry is inspectable in SuperSplat or an equivalent real splat viewer;
- camera travel reveals genuine parallax/occlusion rather than 2D warp;
- floaters/reconstruction artifacts are controlled;
- faces, hands, instruments, and other identity-critical content remain stable;
- a native-cadence proof passes temporal/black/freeze QC;
- the result still matches the production's locked visual language.

If those conditions are not met, use the truthful Tier-1/Tier-2 path instead.
