# AIVideoEdit Production Modes

Production mode describes **what kind of finished visual experience is being made**. Direction authority describes **where the directing language comes from**. Shot behavior describes **how an individual shot is rendered**. These are separate decisions.

## Direction authority
- `reference_led` — supplied visual reference teaches the visual/motion language. It does not automatically authorize content reuse.
- `music_led` — song structure, lyrics when applicable, genre, energy, rhythm, and musical events lead the direction.
- `user_directed` — the current user explicitly defines the visual route or overrides the inferred route.

A production may be both reference-informed and user-modified; record the highest current authority in the project Operating Order and preserve the supplied reference roles in `REFERENCE_MANIFEST.json`.

## Production modes

### `living_scene`
A strong stable image or illustration behaves like a living world. The composition remains recognizable while selected regions move independently: fire, smoke, rain, water, reflections, atmosphere, light, particles, hair, cloth, environmental motion, or intentional articulated subject motion. Camera motion is restrained and secondary.

Primary proof questions:
- Does the image remain authored and stable?
- Is internal motion visible and materially appropriate?
- Are different materials moving independently?
- Are faces/hands/anatomy stable?
- Are loops and joins unobtrusive?
- Is the camera helping rather than replacing animation?

### `cinematic`
A conventional evolving film with deliberate shot changes, action, locations, staging, coverage, continuity, character behavior, and cinematic progression.

Primary proof questions:
- Is the story/action readable?
- Is coverage sufficient and non-repetitive?
- Are character/world continuity and screen direction controlled?
- Do shots evolve with the music rather than merely decorate it?
- Are transitions and pacing intentional?

### `hybrid`
A deliberate combination of cinematic progression and living-scene construction. Sections or shots declare which behavior they use. This is not permission to mix methods randomly; each section must have a reason and mode-appropriate proof criteria.

An accepted source library may be expanded inside hybrid mode through **source-derived coverage** without abandoning its visual world. One stable hero composition can yield environment/detail inserts, alternate framings, a return to the hero, canonical optical/effect states, source-range motion, and progressively shorter coverage around musical acceleration. Every derived shot remains traceable to accepted source hashes.

Hybrid production may also use bounded true-video continuation where real articulated action is required. The video-generation backend must inherit the same locked character/world state and may not become a new directing authority.

Primary proof questions:
- Does each section clearly serve living-scene, source-derived, conventional cinematic, or generated-continuation behavior?
- Do the methods share one visual world and continuity language?
- Are transitions between methods intentional?
- When canonical source pixels are reused, is source provenance intact and unauthorized replacement absent?
- Does complexity improve the film?

## Shot behaviors

### `LIVING_STILL`
Canonical plate plus semantic internal motion, 2.5D depth, localized atmosphere/light/material response, and restrained camera.

### `SOURCE_DERIVED`
Reframing, semantic compositing, inserts, optical states, or other traceable coverage derived from canonical source material without whole-scene regeneration.

### `CINEMATIC_COVERAGE`
Conventional shot coverage with authored staging and continuity control.

### `GENERATED_CONTINUATION`
True temporal video generated from a canonical start state when real articulated motion is required. It must declare:
- canonical start source/hash;
- immutable identity/world anchors;
- allowed character/prop/environment actions;
- camera envelope;
- environmental force state;
- duration/cadence;
- audio policy;
- terminal-frame handling.

The preferred chain is:
`canonical start -> bounded continuation -> temporal QC -> approved terminal frame -> next shot`.

Generated continuation is appropriate for walking, turning, speaking with visible articulation, manipulating props, doors opening, cloth/curtains reacting to wind, or other motions that cannot be convincingly represented as a living still. It is not appropriate merely because a provider can generate video.

## Generated audio behavior
If a video backend returns synchronized audio, classify it explicitly as `keep`, `duck`, `replace`, `isolate_sfx`, `isolate_ambience`, or `discard`. Generated audio never silently overrides locked score/dialogue.

## Selection rule
Before production media generation, record direction authority and production mode in the active project's `OPERATING_ORDER.json`. Each production shot must also declare its shot behavior before final render.

When there is no usable visual reference, the existing no-reference visual-direction gate still applies: present materially distinct routes to the user, let the user select or combine them, then record the resulting direction authority and production mode.

When there is a supplied visual reference, analyze it before selecting production mode. Do not assume that a moving reference implies cinematic production; it may demonstrate living-scene, generated-continuation, or hybrid motion language.

For recovery/recut productions with an accepted source library, diagnose the actual defect before considering regeneration. See `RECUT_REFINEMENT.md`.
