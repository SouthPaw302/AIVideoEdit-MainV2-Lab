# Godot rendering and movie-writer technical research (isolated)

**Scope:** branch `test/godot-render` only. No user-approved music, stills, shots, canonical FX, production story or final release. All visuals are explicitly procedural **test fixtures**; no production claims or substitution of source media.

## Objective
Compare Godot's CanvasItem/2D painter and the simple OpenGL-compatibility 3D renderer; exercise the engine's built-in Movie Maker PNG+WAV writer, then create decodable H.264/AAC technical MP4s with FFmpeg. Verify changing image frames, audio-file presence, geometry, duration, and hashes. Test the actual rendering path (not a no-op/headless dummy renderer).

## Runtime and isolation
- Godot **4.7.2-stable**, Linux x86_64 official release, SHA-256 checked before execution.
- GitHub Actions runner Ubuntu 24.04 + **Xvfb** + Mesa llvmpipe (`LIBGL_ALWAYS_SOFTWARE=1`), **not** Godot's dummy headless renderer.
- Workflow boots the unmodified lab's `main` operating system **in a separate checkout**, then runs this synthetic experiment in its own checkout. It does not stage-change or run any canonical song production.
- One push-scoped CI job for this branch only; no scheduled renders, no publishing, no changes to other workflows or main. The manual workflow trigger is optional (GitHub only exposes branch-only workflow dispatch after the workflow exists on the default branch).
- PNG sequence and WAV created by Godot; MP4 assembled by FFmpeg. Unapproved audio is not fabricated as a production soundtrack. Audio from the synthetic test is expected to be silent and is **not** a sound-fidelity proof.
- `technical_report.json` states **TECHNICAL_SMOKE_PASS**, not artistic acceptance. Artifacts expire after seven days.

## Interpretation
Success demonstrates that software-rendered 2D and 3D frames can be produced on this runner under the pinned toolchain, and that the Godot Movie Maker exports are usable by FFmpeg. It does **not** validate 4K performance, GPU acceleration, existing MainV2 FX equivalence, timeline coverage, artistically suitable renders, or browser/Web export.

## Follow-on experiment (separate authorization)
Only after technical proof, evaluate whether Godot can serve as a subordinate optional renderer in the *existing* MainV2 workflow. Protect locked assets and faces/geometry, use exact source hashes, demonstrate before/after scene-equivalence, and retain full production release/human-review gates.
