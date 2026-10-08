# AIVideoEdit Reusable Tools

These utilities are intended to survive individual song chats and be reused by future production agents.

## Current tools

### `living_paint_transfer.py`

CPU still-image preparation for living-painting projects. Produces stable luminous pigment, split-toned palette families, canvas weave, fixed pigment granulation, restrained bloom, and 16:9 framing.

### `hybrid_painterly_fx.py`

Reusable deterministic effects for painterly animation and hybrid 2.5D/NeRF workflows:

- pseudo-depth and depth parallax
- advected fog/smoke
- scene-motivated rain/embers
- firelight breathing
- stable temporal canvas texture
- smooth mesh micro-motion
- wet reflection ripple
- localized heat haze
- depth-aware focus breathing
- motivated light shafts
- object-specific silver/metal glints
- bowed-string transient warp
- wet-pigment dissolve
- circular object/coin portal transition

### `render_living_painting.py`

Manifest-driven renderer that combines prepared stills with the effect library and writes H.264 MP4 through FFmpeg. Optional source audio can be muxed in the same render.

See `docs/PAINTERLY_MOTION_METHODS.md` for method definitions, examples, and QC rules.

## Dependency baseline

- Python 3
- NumPy
- OpenCV
- FFmpeg

The current tool set is deliberately CPU-capable. Projects may add GPU/ML renderers when available, but the repository must document which path was actually used.

## Persistence rule

When a production develops a technique that is useful beyond one song, promote it into this directory, document it, and checkpoint it before continuing. Project-specific wrappers, manifests, crop maps, and timing decisions remain inside the relevant `projects/<song>/` folder.
