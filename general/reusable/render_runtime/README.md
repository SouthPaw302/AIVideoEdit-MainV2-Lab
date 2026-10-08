# AIVideoEdit Scene Runtime

Optional deterministic rendering/QC support for AIVideoEdit productions. This directory is deliberately isolated from `bootstrap.py` and existing GitHub Actions. Installing its Node dependencies does not alter the repository's Python environment or agent boot sequence.

## Invocation authority

This runtime is **not** a workflow selector and must never become the default production path merely because this directory exists.

The authoritative order is:

1. Agent boot and production guards.
2. `general/reusable/tools/workflow_resolver.py` resolves the approved standard workflow set from the active project.
3. The director/storyboard/shot plan establishes what is being produced.
4. Only then may this runtime be used as an implementation backend for a resolved workflow or an explicitly declared project capability.

A production must not switch itself to browser composition, create a composition root, or replace normal assembly/rendering solely because `render_runtime/` is available. If the active project does not explicitly opt in to the scene runtime, use the resolved standard workflow exactly as before this runtime was added.

The scene runtime may complement standard workflows for deterministic 2D/2.5D motion, overlays, particles, typography, reusable transparent layers, transitions, or local browser-rendered shots. It does not replace source extraction, hero-frame selection, generated-media creation, living-scene assembly, conventional video editing, FFmpeg assembly, project state, or delivery/QC.

## Requirements

- Node.js 22+
- FFmpeg + ffprobe on PATH
- Chrome/Chromium is managed by the rendering dependency

Install once in this directory:

```bash
npm install
node runtime_doctor.mjs
```

## Render

```bash
node render_scene.mjs /path/to/composition.html /path/to/output.mp4 --fps 30 --quality standard
```

Transparent editor intermediate:

```bash
node render_scene.mjs /path/to/composition.html /path/to/overlay.mov --transparent --format mov
```

The renderer also supports `webm`, `gif`, `png-sequence`, and `hls` where the underlying engine supports them.

## Scene QC + snapshots

For a browser-composition project accepted by the runtime checker:

```bash
node scene_qc.mjs /path/to/composition-project
```

This is an **additional** quality check. Existing AIVideoEdit production, narrative, branch, drift, continuity, and export guards remain authoritative.

## Local browser animation assets

Do not rely on CDNs in final renders. Stage pinned local copies into a composition project:

```bash
node stage_runtime_assets.mjs /path/to/composition-project
```

Then reference the AIVideoEdit-facing assets:

```html
<script src="vendor/aivideoedit-gsap.min.js"></script>
<script src="vendor/aivideoedit-transition-core.js"></script>
<script src="vendor/aivideoedit-transitions.js"></script>
<script src="vendor/aivideoedit-audio-mix.js"></script>
```

Production compositions call `AIVideoEditTransitions`, not the implementation dependency directly:

```html
<script>
  const timeline = gsap.timeline({ paused: true });
  // Add scene animation to timeline here.

  AIVideoEditTransitions.init({
    compositionId: 'main',
    bgColor: '#090909',
    scenes: ['scene-01', 'scene-02'],
    transitions: [
      { time: 8.0, effect: 'light_leak', duration: 0.7 }
    ],
    timeline
  });
</script>
```

Available experimental transition names are in `effects_catalog.json`. Every imported transition remains `proof_required` until it passes the existing FX2 promotion gate.

## Audio-driven timing

Create one canonical machine timing analysis per source hash:

```bash
python ../tools/audio_map.py song.wav -o /path/to/project/audiomap.json --print
```

Validate a director-authored timeline without changing it:

```bash
python ../tools/scene_timeline.py /path/to/project/timeline.json --check-only
```

Optionally snap explicit transition/cut boundaries to nearby canonical audio anchors:

```bash
python ../tools/scene_timeline.py /path/to/project/timeline.json \
  --audio-map /path/to/project/audiomap.json \
  --snap-window 0.25 \
  --snap-all-boundaries \
  -o /path/to/project/timeline.snapped.json
```

This operation never changes scene order and does not invent shots. It only moves explicit cut/transition timestamps within the requested snap window.

## Audio mixing and ducking

AIVideoEdit can carry a project-neutral audio mix plan with track gain, effect chains, automation, submix groups, and deterministic voice-over ducking.

Start from `audio_mix.example.json`, then validate/compile it:

```bash
python ../tools/audio_mix.py /path/to/project/audio_mix.json \
  -o /path/to/project/audio_mix.compiled.json
```

The compiler converts declared voice timing into deterministic volume automation on the target bed. It does **not** guess a spectral voice carve; that requires measured voice analysis and remains a separate future capability.

Apply the compiled mix inside the composition after the media elements exist:

```html
<script>
  fetch('audio_mix.compiled.json')
    .then(r => r.json())
    .then(plan => AIVideoEditAudioMix.apply(plan));
</script>
```

Supported effect families are gain, filters/EQ, compressor, limiter, gate, saturation, delay, reverb, chorus, phaser, and bitcrush. Automation is validated before render; unsupported automation targets fail closed in the mix planner.

## Operational boundary

- No modification of agent boot.
- No modification of existing GitHub Actions.
- No automatic effect promotion.
- No replacement of `PRIME_DIRECTIVE.md`, project state, storyboard, narrative contracts, Zero-Drift, the workflow resolver, or standard assembly/rendering.
- Rendering, timing, transitions, audio mixing, and QC are optional tools called by the existing director/agent workflow after workflow selection.
- Presence of this directory is never sufficient authority to select the runtime.

## Third-party implementation dependencies

Third-party open-source packages are used behind AIVideoEdit-native entry points and may be replaced later. Their package identities and licenses are recorded only where required for dependency transparency and attribution. See `THIRD_PARTY_NOTICES.md`.
