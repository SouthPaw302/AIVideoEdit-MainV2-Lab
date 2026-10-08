# AIVideoEdit Generative Engine

A reusable music-driven runtime for AIVideoEdit. It turns a song into deterministic control signals, then lets spatial, atmospheric, lighting, particle and visualizer systems consume the same timing data.

## Canonical flow

`audio -> reactive control bus -> visual/spatial systems -> compositor/timeline -> final-file QC`

The control bus exposes smoothed 0-1 `rms`, `onset`, `low`, `mid`, and `high` values at render FPS. One musical event can therefore drive several effects without each effect re-analyzing the song differently.

## Included reference implementations

- `audio/reactive_core.py` — windowed-FFT band analysis, onset envelope, robust percentile normalization and smoothing.
- `visualizers/reactive_field.py` — CPU organic reactive field intended as a compositing plate. It is inspired by classic music visualizers but is not claimed to be projectM/MilkDrop-compatible.
- `spatial/living_parallax.py` — continuous 2.5D living-image renderer. Real depth input is preferred; synthetic radial depth is explicitly a fallback/proof mode.
- `control_schema.json` — machine-readable interchange contract.

Both video renderers stream frames into FFmpeg instead of retaining the full movie in RAM.

## Quick start

```bash
pip install -r requirements.txt
python audio/reactive_core.py song.wav controls.json --fps 30
python visualizers/reactive_field.py controls.json reactive.mp4 --width 960 --height 540
python spatial/living_parallax.py still.png parallax.mp4 --depth depth.png --frames 120
```

FFmpeg must be available on PATH (or passed via `--ffmpeg`).

## Production rules

1. Analyze audio once and preserve `controls.json` with the shot/project package.
2. Keep mappings song-specific: the bus is canonical, the artistic mapping is not.
3. Bound and smooth controls; avoid generic strobing.
4. Prefer real/generated depth maps over synthetic fallback depth.
5. Do not call a visual field 3DGS, NeRF, projectM or MilkDrop unless that actual technology is used.
6. Render a short representative proof and record QC before promoting a new mapping/effect to `render_proven`.
7. Scan the final exported movie to confirm the effect survived assembly and encoding.

## 3DGS relationship

This engine does not duplicate `SYS-SPATIAL-001`. Actual Gaussian-splat scenes remain the canonical 3DGS path. In future, a real 3DGS renderer may consume this control bus for camera, atmosphere, exposure or particle parameters.