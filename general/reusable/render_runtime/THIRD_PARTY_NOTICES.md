# Third-Party Notices — Scene Runtime

This optional runtime integrates maintained open-source packages rather than rebranding or redistributing them as AIVideoEdit-owned code.

## heygen-com/hyperframes

Repository: `https://github.com/heygen-com/hyperframes`

Used concepts/components in the initial integration:

- deterministic HTML/browser video rendering through `@hyperframes/producer`
- composition checking/snapshot tooling through `@hyperframes/cli`
- WebGL transition implementation through `@hyperframes/shader-transitions`
- single-pass audio-map design concepts adapted into AIVideoEdit's own `audio_map.py`

The upstream repository is distributed under the Apache License 2.0. The shader-transition package documents an MIT license. AIVideoEdit must retain applicable upstream copyright/license notices when distributing copied or modified upstream source. Package dependencies installed from npm carry their own package license metadata.

The AIVideoEdit wrappers, contracts, naming, project state, branch logic, director rules, and production integration remain AIVideoEdit components.

## GSAP

The runtime also stages GSAP from the installed `gsap` npm package for local seek-safe browser animation. GSAP is used as a dependency and is not vendored into this repository by default; consult the package's current license terms for redistribution requirements before shipping a bundled public binary or hosted editor.
