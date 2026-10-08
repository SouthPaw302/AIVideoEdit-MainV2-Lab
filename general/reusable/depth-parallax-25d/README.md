# Depth-Field 2.5D Parallax

Reusable image/video effect developed during **Irish Eyes** after rejecting a hard-cutout parallax prototype that produced visible silhouette artifacts.

## Technique

This implementation uses a **continuous depth field** to drive backward texture warping, with a soft subject-protection matte only where a foreground subject needs stronger motion. This is closer in spirit to PlayCanvas parallax/height-map rendering than a simple cardboard-layer cutout.

Key ideas:

- continuous depth values rather than only two hard planes;
- conservative camera translation and zoom;
- far sky moves least;
- horizon/water move slightly more;
- shoreline/foreground moves more;
- protected human subject can move on a slightly nearer plane;
- background behind the subject is inpainted before camera travel;
- subject alpha is feathered with signed-distance smoothing to avoid sticker edges;
- camera movement is sinusoidal/eased so the shot can loop smoothly.

## Upstream technical reference

PlayCanvas Engine, MIT licensed:

- `examples/src/examples/materials/parallax-mapping.example.mjs`
- `src/scene/shader-lib/glsl/chunks/standard/frag/parallax.js`

The PlayCanvas implementation uses a height map plus view direction to offset UV lookup, including a parallax-occlusion ray march. Our reusable video/image implementation is original code adapted for offline cinematic rendering and does **not** copy the engine shader verbatim.

Upstream repository: `playcanvas/engine`

## Irish Eyes proof

The revised proof uses a real 2017 South Florida frame with:

- soft subject matte;
- inpainted background plate;
- continuous sky/water/shore depth field;
- foreground subject motion greater than background motion;
- a five-second eased camera orbit that returns to its start position.

The hard-mask prototype was rejected. The soft-depth version passed representative-frame QC for visible edge artifacts and is the approved direction for further Irish Eyes 2.5D shots.

## Promotion rule

Keep song-specific rectangles, horizon positions, masks, depth maps, and camera curves inside each song project. Keep reusable implementation code here on `main`.