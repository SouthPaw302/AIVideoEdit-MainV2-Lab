# Painterly Motion and Living-Image Methods

This document records reusable production methods added while developing **Silver Coin**. They are repository-wide tools, not Silver Coin-only rules.

The central principle is **surface continuity**: a painting may move, breathe, refract, glow, and change viewpoint, but the pigment/canvas identity should remain stable from frame to frame. Randomly regenerated texture causes boiling and destroys the illusion of a living painting.

## Tooling

- `tools/living_paint_transfer.py` — prepares stills for a stable living-painting surface.
- `tools/hybrid_painterly_fx.py` — reusable deterministic motion/effect functions.
- `tools/render_living_painting.py` — JSON-manifest-driven renderer with optional FFmpeg audio muxing.

CPU dependencies: Python, NumPy, OpenCV, FFmpeg. No external model or GPU is required for these methods.

## Methods

### Stable pigment / temporal canvas lock

Create a woven canvas plus low-frequency pigment field once per shot and reuse the exact same field for every frame. The image may move underneath it slightly, but the texture itself is never randomly regenerated.

**Use for:** painterly footage, illustrated music videos, old-canvas looks, any sequence where diffusion or grain must not crawl.

**Reject:** per-frame random noise masquerading as brush texture.

### Luminous pigment preparation

Before animation, process stills with restrained bilateral smoothing, local luminance contrast, split-toned shadows/highlights, selective highlight bloom, and a fixed woven/pigment texture. The objective is handcrafted depth, not a cartoon filter.

Silver Coin palette families:

- `village` — slate/cool shadows with modest warm natural highlights.
- `threshold` — cool exterior crossing into window/candle amber.
- `tavern` — warm gold/umber with deep shadow retention.
- `coin` — comparatively neutral silver with controlled highlights.
- `dawn` — softened warm resolution.

These names are convenient presets; other projects can define their own palette families.

### Depth-proxy parallax

When a true depth map or reconstruction is unavailable, derive a stable pseudo-depth field from vertical perspective, local luminance contrast, and softened edge salience. Use it only for gentle displacement.

This is **not metric depth** and must never be described as a captured or reconstructed 3D scene. It is a 2.5D motion method.

### Hybrid neural-radiance overlay

A compact NeRF or other learned volumetric field may be composited with painterly planes. The neural field supplies fog, smoke, view response, light volume, and spatial travel; the painting carries the detailed characters, instruments, props, and architecture.

Allowed description: **hybrid neural-radiance-field spatial rendering**.

Do not mislabel it as full photogrammetric NeRF reconstruction when no captured multi-view scene exists.

### Advected atmosphere

Fog/smoke uses a fixed seeded low-frequency field that is advected across time rather than regenerated. This gives coherent drift and avoids texture boiling.

**Use for:** fog, smoke, dust haze, breath-like atmospheric expansion.

### Motivated particles

Particles must belong to the scene.

- exterior -> rain, mist points, road splash
- tavern/hearth -> embers, ash, smoke motes
- forge -> sparks
- forest -> leaves/pollen only when environmentally plausible

Do not add generic magical particles simply to make the frame look active.

### Mesh breath

Use a tiny smooth displacement field over the image to imply cloth, hair, crowd posture, and environmental movement. Pin displacement toward frame edges so the entire image does not appear to swim.

This is useful before or underneath more specific character animation.

### Wet-reflection ripple

For roads, puddles, lakes, wet floors, or polished surfaces, create a restrained reflected-color band and displace it with low-amplitude waves. The reflection should be motivated by the visible scene above it and should never look like an unrelated water simulation pasted onto the frame.

### Firelight breath

Vary warmth and luminance using low-amplitude multi-frequency oscillation. This produces living candle/hearth light without obvious periodic flashing.

### Heat haze

Apply a localized, low-amplitude refractive warp near candles, hearths, hot machinery, or forge regions. Never wave-distort an entire frame unless the narrative calls for surrealism.

### Motivated light shafts

Generate soft radial shafts from a defined practical source such as a window, candle cluster, doorway, or sun position. Keep intensity low. Generic full-frame “god rays” are discouraged.

### Depth-focus breath

Use pseudo-depth to shift focus gently through a shot. Good for vocal emphasis, portraits, hands, objects, and moments when attention should move without cutting.

### Object-specific specular sweep

For coins, blades, jewelry, wet metal, glass, or instrument varnish, apply a localized moving glint restricted to a known object region. Do not brighten the entire shot for one object highlight.

### Performance transient warp

A tiny ROI-specific displacement can accent a bow stroke, drum hit, foot stamp, hammer strike, or similar rhythmic action. It should be subordinate to the performance image and tied to musical transients once the edit is audio-synced.

### Pigment dissolve

Transition between frames using a seeded low-frequency mask with softened boundaries and brief pigment bloom. The transition should resemble wet pigment mixing rather than a digital crossfade.

### Object portal transition

A meaningful circular object — Silver Coin uses the coin itself — can expand into the next scene. The object should be narratively justified and should not become a repeated gimmick on every edit.

## Manifest-driven rendering

`tools/render_living_painting.py` accepts a JSON scene manifest. Each scene can define:

- `image`
- `duration`
- `family`
- `effects`
- `transition`
- strengths and object/ROI coordinates for selected effects

Example:

```json
{
  "fps": 24,
  "width": 1280,
  "height": 720,
  "seed": 302,
  "scenes": [
    {
      "image": "assets/stills/road.jpg",
      "duration": 3.0,
      "family": "village",
      "effects": ["parallax", "micro", "reflection", "atmosphere", "particles", "canvas"],
      "transition": "pigment"
    },
    {
      "image": "assets/stills/coin.jpg",
      "duration": 2.0,
      "family": "coin",
      "effects": ["parallax", "glint", "canvas"],
      "transition": "coin"
    }
  ]
}
```

## QC rules

Reject a shot or effect if it introduces:

- crawling canvas texture
- random object creation/disappearance
- face/hand/instrument deformation
- unmotivated particles or light sources
- repeated mechanical looping that is obvious to the viewer
- excessive parallax that exposes flat-card geometry
- reflections inconsistent with the scene
- heat haze outside a motivated hot region
- global brightness flashes for a local object glint
- painterly processing that turns faces into cartoon outlines

## Development rule

When a new method proves useful in production:

1. implement it in `tools/` if it is reusable;
2. document the method here or in the appropriate catalog;
3. record project-specific use in that song's `EFFECTS_PLAN.md` / `DECISIONS.md`;
4. checkpoint to GitHub before continuing to the next major production phase.
