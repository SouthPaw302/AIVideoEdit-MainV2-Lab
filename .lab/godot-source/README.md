# Godot + MainV2 — source video technical experiment

Branch: `test/godot-render`. This is a technical experiment, **not** a production workflow, finished movie, accepted FX proof, approved source library, or 3D reconstruction.

## Two independent paths

- **Godot Movie Maker:** generates a deterministic 560×560 screen-blend overlay at 24 fps, frames 0–143, on Ubuntu GitHub Actions using Xvfb and Mesa's software OpenGL. Black is neutral.
- **Existing AIVideoEdit FXExecutor:** reads the actual existing approved `FX2-ATM-001` smoke effect from `general/reusable/fx_v2/registry.json` and `runtime.py`; applies only a far-right sky ROI, with other regions restored from source decoded pixels.
- **FFmpeg:** encodes the Godot/MainV2 hybrid into a 6-second H.264/AAC MP4 with *actual source audio*, not a synthesized soundtrack.
- **QC:** fail-closed SHA on source, exact geometry and FPS, 144-frame duration, effect-visible changed frames, exact original pixels restored in protected regions before encoding, MP4/frame/audio validation.

For the GitHub runner, the test uses the already present immutable SHA-pinned real video source from `.lab/fixtures/irish-eyes-real-source-30s.json` (first shot, not a generated stand-in). The supplied **WOmanCLouds.mp4** is user-provided source with SHA `3fc2192b4425dd87b6362a6a77aa29e0c54d93b8df14383ed7105063d77f7ab6`; it is **not** checked into the public repository or silently replaced. To process that private clip, pass its actual local path to `composite.py --source` with the exact matching SHA once the Godot overlay sequence is available.

### Local composition

```bash
python .lab/godot-source/composite.py \
  --source /path/to/WOmanCLouds.mp4 \
  --sha256 3fc2192b4425dd87b6362a6a77aa29e0c54d93b8df14383ed7105063d77f7ab6 \
  --overlay /path/to/godot-overlay/ \
  --output /tmp/godot-source-proof \
  --repo-root .
```

Never declare `VISUAL_ACCEPTED` from a runner. Never merge this optional runtime into `main` without representative backend-equivalence validation and explicit review. No automated full renders or productions.
