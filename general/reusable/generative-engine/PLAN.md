# Generative Engine Upgrade Plan

## Goal

Turn AIVideoEdit's existing audio-reactive, living-image, spatial and visualizer ideas into one reusable music-driven runtime without duplicating established 2.5D, NeRF or 3DGS lineages.

## Phase 1 — implemented in this upgrade

1. Establish a canonical frame-aligned reactive control bus: RMS, onset, low, mid and high.
2. Replace crude band approximation with windowed FFT energy and robust percentile normalization.
3. Add deterministic JSON interchange schema so multiple effects can consume one analysis pass.
4. Add a CPU reference organic reactive-field renderer.
5. Add a CPU reference living-parallax renderer with real depth-map input and an explicitly labeled synthetic fallback.
6. Stream video frames directly into FFmpeg so full-song renders do not accumulate all frames in RAM.
7. Integrate the subsystem into the reusable-library and Bible documentation.
8. Preserve existing `SYS-SPATIAL-001` as the single canonical 3DGS system capability rather than adding duplicate GS entries.

## Phase 2 — proof-gated follow-up

- palette extraction from story frames;
- hybrid compositor adapters for atmosphere/light/particle layers;
- depth-estimation adapter when a supported model/backend is available;
- actual SuperSplat/gsplat wrapper consuming the same control bus;
- song-specific mapping presets only after proof/QC;
- proof-frame and temporal-QC helper integration.

## Acceptance rules

- New system capabilities stay `experimental` or `system_capability` until representative proof/QC exists.
- A rendered visual field must not be called projectM/MilkDrop unless that real engine is used.
- A depth warp must not be called NeRF or 3DGS.
- A real 3DGS integration must use real Gaussian scene primitives/data.
- Final-film QC remains mandatory; code existence alone does not prove an effect survived the final edit.

## Smoke-test record

The implementation was syntax-checked and exercised in the working sandbox on 2026-09-05 using the supplied prototype test tone/still:

- reactive control analysis: 120 frames at 30 fps;
- reactive field: 4.0-second H.264 proof at 320x180;
- living parallax: 1.0-second H.264 proof at source-derived dimensions, synthetic fallback depth explicitly reported.

These smoke tests validate execution, not artistic acceptance or final `render_proven` status.