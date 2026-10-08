# Music-Directed Living Painting

This is the reusable production method validated during Silver Coin V6.

## Core principle

Start with artwork that is strong enough to stand alone. Motion and effects should make the painting feel alive **without replacing, deforming, or distracting from the image**.

The music determines when the camera moves harder, when light breathes, when transitions occur, and when the image should simply hold.

## Signal-to-visual mapping

Use the real source master, not guessed timing.

Derive inexpensive deterministic envelopes:

- smoothed absolute amplitude / RMS-like energy
- transient/onset strength
- optional spectral-brightness or zero-crossing proxy
- verified semantic section boundaries: verse, chorus, bridge, final chorus, outro

Map them conservatively:

- **energy** -> camera amplitude, practical-light strength, atmospheric opacity
- **transients** -> tiny zoom impulses, glints, foot-stamp/fiddle/camera accents
- **brightness** -> highlight/atmosphere lift
- **section identity** -> camera grammar, palette family and transition vocabulary

Do not drive every frame directly from raw audio. Smooth and qualify signals so the visual field does not jitter.

## Camera grammar

### Verse

- slow push or pull
- lateral crop drift
- sub-degree angle change
- long dwell time
- minimal transient response

### Chorus

- wider crop travel
- stronger push/lift
- more decisive angle path
- higher practical-light/atmosphere response
- still avoid handheld-style random shake

### Bridge

- slower exploratory movement
- cooler or more separated palette
- fog/mist/shadow transitions
- allow visual breathing room

### Final chorus

- strongest controlled movement amplitude
- wider/livelier framing
- stronger light response
- resolve to a calm final image rather than ending at maximum motion

## Loop library

Loops should be low-frequency, deterministic and scene-motivated.

Validated examples:

- 2D Gaussian atmosphere drift
- fire/candle practical-light breath
- wet-road or water reflection shimmer
- slow camera crop/angle loop
- restrained fog drift
- restrained foliage/hair/garland motion where masks are reliable

The Silver Coin V6 Gaussian atmosphere is **2D image-space Gaussian compositing**, not 3D Gaussian Splatting.

## Transition vocabulary

Use different transitions for different musical jobs rather than one transition everywhere.

Validated V6 transitions:

- clean music-bound dissolve
- candle flare into warm chorus
- pigment soften between tonal worlds
- shadow wipe into bridge
- fog bridge into reflective/forest material
- light lift into final chorus

Keep transition windows short. If a beautiful face is blurred for long enough to become the main visual event, the transition is too long.

## Strong-image reuse

Do not lower image quality just to increase shot count.

A strong painting may legitimately return later if it receives a different:

- crop path
- scale direction
- focal subject framing
- angle path
- palette response
- effect intensity
- narrative context

The viewer experiences a new shot language while the visual identity stays coherent.

## Global-time section rendering

For CPU/recovery environments, render long films in chunks using **global song timestamps**.

Each chunk receives the same absolute frame/time coordinates as the full film. Therefore:

- audio envelopes remain identical
- camera curves remain identical
- deterministic loops remain phase-continuous
- transition halves remain continuous across chunk boundaries

After chunk rendering:

1. concatenate intermediate video chunks without a second visual transform
2. perform one delivery resize/encode
3. mux the canonical audio once
4. validate duration/container/hash

This is safer than rerendering the entire film after a late failure and allows one musical section to be replaced independently.

## QC

Before delivery:

- inspect contact sheets at representative times in every section
- inspect both sides of major transitions
- verify face/hands/instrument/coin geometry remains stable
- verify no effect creates sustained double images unless intentionally designed
- validate MP4 container and audio stream
- record SHA-256 and render configuration

Technical QC is necessary but does not replace aesthetic review.

## Silver Coin V6 reference files

- `projects/silver-coin/V6_MUSIC_CAMERA_GRAMMAR.md`
- `projects/silver-coin/V6_EFFECT_PRESETS.json`
- `projects/silver-coin/V6_FULL_TIMELINE.json`
- `projects/silver-coin/V6_FULL_RENDER_META.json`
- `projects/silver-coin/V6_SECTION_RENDER_RECOVERY.md`
- `projects/silver-coin/render_v6_full.py`
- `projects/silver-coin/render_v6_chunk.py`

Future projects should reuse the method, not blindly reuse Silver Coin's exact timings or palette.