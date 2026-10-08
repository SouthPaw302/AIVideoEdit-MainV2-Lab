# AIVideoEdit Canonical FX V2

Canonical location: `main/general/reusable/fx_v2/`

## Purpose

Unify the strongest proven AIVideoEdit effects behind one stable callable runtime while keeping song-specific timing, ROIs, mappings, and story decisions on song branches.

## Core rule

**Internal scene motion first. Camera motion second.**

The viewer should read a living image, not a still being shaken or zoomed.

## Runtime layers

1. `audio` — shared frame-aligned reactive controls from `general/reusable/generative-engine/`.
2. `surface` — stable canvas/pigment, local contrast, identity protection.
3. `motion` — depth parallax, cloth/hair/crowd breath, water/foliage flow.
4. `environment` — rain, rain glass, fog/smoke, spray, embers, fire.
5. `light` — firelight, moving practical light, shafts, glints, temporal palette migration.
6. `visualizer` — generated compositing plates consuming the shared control bus.
7. `transition` — pigment, fog/light, reflection, doorway/depth, object portal, perceptual gates.
8. `spatial` — honest 2.5D, NeRF atmosphere, and real 3DGS/SuperSplat integration when source geometry supports it.

## Stable IDs

Effects are addressed by stable IDs from `registry.json`. A song manifest calls IDs plus parameters; it does not copy implementation code.

For music-directed projects, prefer a single preserved `FX2-AUDIO-001` analysis pass and map its smoothed controls into several effects rather than independently re-analyzing the song inside every renderer.

The historical IDs in `generative-engine/registry_entries.json` are aliases only; the callable registry remains this directory's `registry.json`.

## Hard precompile gate

A project may not compile merely because an FX ID exists in JSON.

`precompile_gate.py` schema v2 verifies:

- production approval state;
- runtime wiring or real adapter implementation files;
- stub/placeholder rejection;
- human-approved proof records;
- proof-binary bytes when an addressable artifact is recorded;
- deterministic sample-output hashes plus pixel/temporal/global-shift smoke metrics for runtime effects;
- explicit hashed PASS preflight for conditional/external technology;
- exact production `render_inputs` that can alter the pixels.

The generated lock includes a complete evidence fingerprint. Lock verification reruns the live checks immediately before compile. Schema-v1 locks are obsolete and must be regenerated.

See `PRECOMPILE_FX_GATE.md`.

## Promotion gate

No effect is promoted merely because code exists. Candidates require deterministic implementation, representative rendered proof, native project cadence, measurable motion/pixel behavior where appropriate, visual QC, documented limitations, and truthful technology naming.

Adapter/external effects promoted to ordinary `approved` status additionally require byte-verifiable proof artifact evidence. Conditional technologies remain conditional and require project-specific preflight evidence.

## Design rules

- eliminate global shake as a default motion source;
- analyze song reactivity once and preserve a common control bus;
- cache static masks/fields once per shot;
- stream full-song procedural renders rather than buffering every frame in RAM;
- use loop-safe phase functions and advected fields instead of per-frame random noise;
- protect faces/hands/instruments from broad warps;
- support explicit ROIs/masks for fire, smoke, water, glass and reflective surfaces;
- separate flame geometry from firelight illumination;
- make transitions physically motivated by visible scene elements;
- expose song-agnostic presets instead of hard-coded song paths;
- keep real 3DGS clearly separate from 2D Gaussian light fields; see `../SPATIAL_3DGS_SUPERSPLAT.md`;
- keep custom reactive fields distinct from projectM/MilkDrop unless those actual engines are used.

## Historical lineage

FX V2 consolidates reusable implementation lineage from Silver Coin, Irish Eyes, IronFlame, Leave It by the Door, the shared Generative Engine, and genuine SuperSplat/3DGS workflows when real splat geometry exists. Historical integration branches remain provenance only; `main` is the current source of truth.


## Deterministic FX resolver

`fx_resolver.py` and `recipes.json` are the canonical selection layer for batch-, scene-, and still-level FX planning.

The resolver consumes explicit semantic facts from the accepted media or shot package (environment, visible materials/objects, narrative needs, constraints and protection requirements). It then:

1. loads the current canonical `registry.json` and reusable recipe catalog;
2. matches project-neutral recipes deterministically;
3. excludes physically or compositionally incompatible effects;
4. prefers approved canonical FX before proof-required/project-local/new work;
5. returns a bounded effect stack, protected regions, composition steps and rejected candidates with reasons.

Default resolution never selects `proof_required` effects. They can only be surfaced explicitly for proof work.

The resolver does not infer invisible scene facts and does not replace directorial judgment. Agents must describe the accepted scene truthfully before asking for a resolution.

Selection order:

`approved canonical FX -> approved reusable recipe -> proof-required existing FX -> project-local candidate -> new FX only if necessary`

Use the read-only harness tool `harness.fx_resolve` when working through the Studio/MCP harness. Production agents should resolve FX before authoring scene FX requirements and again when a still/scene materially changes.

## Reusable composition recipes

Not every successful production technique deserves a new FX ID. `recipes.json` preserves composition-level methods such as ghosted narrative object overlays, transparent scene handoffs, protected-subject environmental motion, artifact salvage, long-hold scene evolution, multiplane alpha compositing, instrument-axis audio visualization, temporal painting and pigment travel.

Recipes may combine existing primitives, protection rules and editorial steps. Prefer a recipe over duplicating the underlying FX implementations.


## Authored camera motion

The existing approved camera FX are the reusable camera layer. Do not create project-local crop/zoom code when these IDs can express the move:

- `FX2-CAMERA-023` — `narrative_camera_travel`: bounded push, pullback and lateral reframe using source-locked crop/resize.
- `FX2-CAMERA-021` — `corridor_push_focus_definition`: authored push plus restrained definition gain.
- `FX2-CAMERA-022` — `loopable_eased_orbit`: loop-safe micro-orbit.
- `FX2-CAMERA-024` — `rack_focus_heat_pulse`: focus/perception move with heat pulse.

`narrative_camera_travel` accepts `zoom_start`, `zoom_end`, `center_start`, `center_end`, `easing` (`smoothstep`, `cosine`, or `linear`) and `zoom_cap`. The crop is clamped inside the source frame and the canonical cap defaults to 1.40x, matching the stronger authored camera language proven by recent music-recut work without inventing border pixels.

Song/project timing stays on the production branch. Reusable profiles live in `presets.json -> camera_profiles`. Internal scene motion still precedes camera motion; these profiles are editorial/spatial controls, not a substitute for living-scene motion or real depth.
