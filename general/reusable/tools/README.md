# Reusable Tools

Canonical home for small project-neutral command-line helpers, validators, converters, inspectors, and recovery utilities.

Before adding a tool, check whether it belongs in `fx_v2/`, `generative-engine/`, `painterly-motion/`, `memory-atmosphere/`, or `depth-parallax-25d/`.

- `production_guard.py` — universal production-state/bootstrap/Director Brain validator.
- `narrative_guard.py` — directing/music/script/media-evidence validator; historical filename retained for compatibility.
- `recut_guard.py` — accepted-source-library/recut validator for hashes, editable timelines, source-derived provenance, hero-library evidence, backend equivalence, project-local FX locks, and before/after QC.
- `test_director_brain.py` — regression tests for existing Operating Order, production-mode, canon/baseline/refinement, semantic-motion, and mode-aware acceptance rules.
- `test_recut_system.py` — regression tests for canonical source-library recovery/recut rules.
- `hero_library_extract.py` — extracts a non-empty, perceptually diverse hero-frame library from approved video; dense time sampling is only a candidate pool, not the final selection rule, and unmeasured semantic properties are reported as unmeasured.
- `export_variety_qc.py` — full-export repetition/composition warning tool with stable before/after summary fields and optional prior-report comparison.
- `refinement_qc_compare.py` — builds/validates broad PRE/POST refinement evidence including repetition, runtime, freeze/black, framing, sync, continuity, mode-aware QC, and source/canon integrity.
- `audio_map.py` — deterministic single-pass music analysis producing canonical `audiomap.json` timing, energy, onset, roll, silence, and phrase-candidate layers for audio-driven productions.
- `scene_timeline.py` — validates director-authored scene timelines and can snap explicit cut/transition timestamps to nearby canonical audio anchors without changing scene order.
- `test_scene_timeline.py` — regression tests for audio-anchor selection, boundary snapping, and transition-effect validation.
- `audio_mix.py` — validates project-neutral track/bus effect chains and compiles declared voice timing into deterministic music-bed ducking automation without guessing spectral carve settings.
- `test_audio_mix.py` — regression tests for deterministic ducking, voice-source enforcement, and effect-automation safety.

Project-local experimental FX live under the active project's `project_fx/` directory and are validated/locked by `general/reusable/fx_v2/project_local_fx_gate.py`. They do not become canonical reusable FX without a separate promotion into `general/reusable/fx_v2/`.

Song-specific scripts stay on the relevant `song/<slug>` branch.

Do not create production-named reusable directories and do not recreate the superseded `general/reusable/embedded-tools/` tree.

## Standard workflow tools
- `workflow_resolver.py` — validates the neutral workflow registry and resolves the workflow set for a project from its current mode/media capabilities.
- `workflow_guard.py` — fail-closed bootstrap/stage guard for standard workflow selection.
- `recipe_execution_guard.py` — validates music-directed section controls, pass declarations, hashed proof outputs, effect application coverage, and final assembly evidence for Director Brain v3 productions.
- `test_recipe_execution_guard.py` — regression tests for missing recipe, valid complete evidence, and locked-effect coverage failures.
- `promote_standard_library.py` — idempotent migration/generator used to build the neutral standard effect/workflow registries and proofs.

## Optional scene runtime

`general/reusable/render_runtime/` contains the isolated deterministic browser-render/QC adapter, AIVideoEdit transition bridge, audio-mix bridge, and local runtime asset staging. It is additive and does not replace agent boot, project state, production guards, or existing GitHub Actions. See `general/reusable/SCENE_RUNTIME_CONTRACT.md` and `general/reusable/render_runtime/README.md`.
