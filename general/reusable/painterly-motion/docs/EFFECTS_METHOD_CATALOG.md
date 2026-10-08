# AIVideoEdit — Effects & Rendering Method Catalog

This file is a persistent reference for effects that have been implemented, tested, or deliberately rejected in production. It complements `VISUAL_STYLE_CATALOG.md`: the style catalog describes visual languages; this catalog describes reproducible motion, spatial, transition, lighting, compositing, QC, and delivery methods.

## Design rules

1. Prefer effects that preserve subject identity and painterly surface stability.
2. Every effect should have a motivated visual role; avoid random particles or constant motion.
3. CPU-safe implementations are valuable because they can run in a recovery environment without GPU dependencies.
4. Distinguish true neural methods from approximations. Never describe pseudo-depth or image warping as a full 3D reconstruction.
5. Save deterministic seeds and configuration with renders.
6. QC still frames and transitions before committing a full-song render.
7. Measure reference motion when possible instead of guessing animation intensity.

## Implemented CPU methods

### Pseudo-depth parallax

Derive a stable non-metric depth proxy from vertical perspective, local luminance contrast, edge salience, and saturation. Use the field to drive per-pixel camera displacement.

Use for: gentle camera travel through still paintings, foreground/background separation, layered occlusion.

Do not claim: monocular metric depth or reconstructed 3D geometry.

### Localized micro-warp / mesh breath

Apply low-frequency, sub-pixel mesh motion. One variant is depth-gated; another pins frame edges while letting the interior breathe. Both are designed to suggest breathing, cloth movement, crowd sway, leaves, and hair without high-frequency texture boiling.

### Temporal canvas lock

Generate one deterministic woven/pigment field per scene and reuse the same field on every frame. This restores a stable canvas/pigment micro-surface after remapping/compositing and prevents frame-randomized grain from crawling.

### Advected atmosphere

Create a low-frequency density field once, then advect/remap it over time instead of generating new random noise each frame. Tint and depth-gate it as fog, smoke, steam, or mist.

### Depth-gated volumetric light shafts

Generate soft radial/fan light volumes from a motivated source such as a tavern window, hearth, lantern, or dawn sun. Gate visibility using pseudo-depth so the light reads as occupying space instead of being painted uniformly over subjects.

### Motivated radial candle/window shafts

A lighter-weight variant generates soft warm radial shafts around a known source location. It is useful when depth gating is unnecessary or the source image already strongly establishes room depth.

### Motivated particle fields

Use deterministic particles only when justified by the scene:

- exterior: rain, occasional wet-air points
- tavern/hearth: embers and ash
- workshop/forge: sparks

Avoid decorative magical particles with no physical source.

### Firelight breath

Combine multiple low-amplitude temporal sine components to modulate warm luminance around hearth/candle scenes. The amplitude is intentionally small to avoid visible flicker artifacts.

### Heat haze

Apply a restrained refractive warp only within the region affected by hot candles/hearths. Avoid global wavy distortion.

### Puddle reflection shimmer / wet reflection ripple

Animate the lower exterior frame with restrained refractive displacement. The stronger variant builds a faint mirrored color memory from image content immediately above the road line and ripples it before blending it into the wet ground.

### Depth focus breath

Use the pseudo-depth field to move a shallow focus zone slowly through a portrait/subject shot. The background blur contribution stays low.

### Localized specular glint

Sweep a small specular highlight across a bounded metallic region such as a coin, buckle, blade, glass rim, or instrument fitting. It must not brighten the whole frame.

Silver Coin implementation: the glint is centered only on the coin/hat area.

### Performance transient warp

Apply a small impulse-shaped regional warp to a performance ROI. It can suggest bow strokes, drum hits, hand strikes, foot stamps, or other transients. When real audio is available, drive the impulse from the transient envelope.

Silver Coin implementation: the fiddler bow region receives a tiny transient warp.

### Chroma pigment transport

During a transition, move the LAB chroma channels toward the incoming scene before fully replacing luminance/geometry. This allows a cold exterior painting to begin warming into tavern amber before the scene itself changes.

### Pigment dissolve

Use a stable low-frequency field as a soft threshold mask, with a short mid-transition bloom. The result resembles wet pigment mixing more than a digital crossfade.

### Object portal / match-cut portal

Expand a circular mask from a real recurring object and reveal the next scene through it. Optional narrow optical glints can be added along the ring.

Silver Coin implementation: the coin becomes a reflective portal rather than a generic magical vortex.

### Edge-contamination reframe

When storyboard titles, labels, or lyric captions touch an image edge, crop/recompose the contaminated strip instead of asking an inpainting model to invent a large replacement region. This is safer for moving footage because no synthetic repair texture can shimmer later.

### Narrative-ribbon reframing

When a storyboard bridge or montage exists as a continuous multi-character strip, treat the strip as a painted panorama rather than cropping each subject into a separate portrait. Define focal windows along the ribbon and move the camera from subject to subject while preserving neighboring context.

Silver Coin V5.1 bridge path: farmer → smith → carter → maid → lovers → dawn → wine.

Benefit: preserves the original multi-character composition and prevents close crops from degrading into disconnected hands/torsos.

### Reference-motion envelope calibration

Measure optical flow on supplied style-reference clips at a fixed analysis scale and use the observed range as an animation envelope rather than guessing motion intensity.

Silver Coin measurements at 280 px analysis width:

- low-motion reference mean flow: ~0.428 px/frame
- high-motion reference mean flow: ~1.566 px/frame

Use this range to restrain quiet portraits and permit stronger chorus/dance motion without texture boiling.

### Painterly upscale

Lanczos enlargement + restrained smoothing/sharpening. Avoid aggressive sharpening that converts painted faces and cloth into plastic photographic texture.

Silver Coin delivery rule: when the validated render is lower resolution, a larger delivery encode may be produced and must be documented as an upscale, not a native high-resolution render.

## Compact CPU neural radiance field

`tools/video_fx/tiny_nerf_volume.py` implements a genuine compact MLP:

`(x, y, z, view_x, view_y, view_z) -> (density, red, green, blue)`

It uses Fourier positional features, deterministic training/validation samples, and ray volume rendering. The learned field is atmospheric/light volume, not a photogrammetric reconstruction of the detailed subject image.

Each production use should record family/config, seed, training sample count, step count, train/validation loss, rendered volume resolution/sample count, and composite opacity.

## Hybrid neural-radiance-field integration

A compact CPU NeRF may supply learned volumetric density/color and view-dependent atmosphere while detailed subjects remain painted multi-plane imagery. Pseudo-depth methods drive compositing masks, occlusion, and camera motion around that neural field.

Allowed description: **hybrid neural-radiance-field spatial rendering** when an actual trained radiance-field component is present.

Do not describe pseudo-depth, parallax, or noise volumes alone as a NeRF.

## Local audio edit-map method

`tools/audio/analyze_edit_map.py` derives signal-based section candidates, beat times, transient peaks, energy peaks, brightness, and high-value sync points. Semantic Verse/Chorus/Bridge labels still require narrative/listening verification.

Use the edit map for cut placement, performance transient effects, foot-stamp/crowd motion intensity, coin glints, firelight/camera response, and section-scale palette changes.

## Temporal QC scanner

`tools/video_qc/temporal_qc.py` samples a render, measures frame difference, optical-flow magnitude, and Laplacian sharpness, and scores outliers with robust median/MAD z-scores.

Important V5.1 refinement: robust z-score alone can over-flag tiny changes in very stable footage, so each detector also requires an absolute magnitude floor. Timeline scene boundaries are accepted as expected transition windows; unexplained outliers are the frames that require visual review.

Silver Coin V5.1 result: 50 expected transition/motion events and **0 unexplained risks** after applying absolute floors.

## Silver Coin production findings through V5.2

- Reframing is safer than large generative inpainting for storyboard label/caption cleanup.
- Rain stays mostly outside; tavern embers stay sparse and source-motivated.
- Low-frequency mesh motion is safer than frame-randomized deformation.
- Temporal canvas lock restores stable painterly material after repeated warps/composites.
- Light volumes and compact NeRF atmosphere increase perceived space without replacing subject painting.
- Heat haze stays localized and restrained.
- Performance transient warp works best on restricted ROIs driven by the real audio envelope.
- The silver-coin portal is brief and narrative, not a permanent fantasy vortex.
- Reference-motion calibration produces a more faithful living-painting cadence than arbitrary animation strength.
- Narrative-ribbon reframing substantially improved the bridge composition.
- Temporal QC must distinguish expected edit transitions from unexplained artifacts.

## Future method candidates

- optical-flow assisted interpolation between closely matched generated keyframes
- semantic masks for faces/hands/instruments to keep those regions more rigid than cloth/background motion
- multi-plane depth cards with foreground segmentation and explicit occlusion ordering
- learned depth maps when a reliable local model is available
- true Gaussian splatting or full NeRF reconstruction when an appropriate GPU/runtime and source views exist
- palette-consistent grain/brush restoration after heavy compositing
- automatic QC contact-sheet generation from unexplained risk timestamps

Update this file whenever a method becomes reproducible enough that another agent should be able to discover and reuse it.