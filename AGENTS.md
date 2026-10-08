# AIVideoEdit Universal Agent Contract

This applies to **every agent, model, automation, connector, local process, and human-operated workflow** that works in this repository.

## Mandatory first action — bootstrap the OS
Before reading project history, generating media, changing production state, selecting FX, rendering, or inspecting unrelated branches:

```bash
python bootstrap.py boot --repo-root <repo>
```

If the repository is not present in the sandbox, `bootstrap.py install --workspace <path>` can install `main`, then `boot` must run.

A session is not production-capable until bootstrap prints `AIVideoEdit OS BOOTSTRAP: PASS`.

Bootstrap materializes the **entire exact current `main` commit** into `.aivideoedit/os/`, runs the current-main production and recut guards against the active working branch, then writes:
- `.aivideoedit/session.json` — session attestation
- `.aivideoedit/SECOND_BRAIN.md` — generated current-session director context

After bootstrap, read in this order:
1. `.aivideoedit/os/PRIME_DIRECTIVE.md`
2. `.aivideoedit/SECOND_BRAIN.md`
3. `.aivideoedit/os/SOUL.md`

For Director Brain v3 projects, `SECOND_BRAIN.md` must surface the active `OPERATING_ORDER.json`; do not begin production until you know the direction authority, production mode, canon state, accepted baseline, accepted source library, baseline-refinement scope, source-library recut scope, forbidden changes, named defects, and exact next action.

## Authority
1. Current explicit user instruction.
2. Active `song/<slug>` branch state/manifests and Director Brain Operating Order.
3. Current-main AIVideoEdit OS loaded by bootstrap.

Nothing else is automatically authoritative. Historical chats, summaries, unrelated production branches, old visual DNA/storyboards, prior generated media, and project-specific provenance are prohibited as production inputs unless the current user explicitly authorizes them.

## Prime Directive law
`PRIME_DIRECTIVE.md` is the short universal directing law. It is mandatory authority, not optional guidance.

In particular:
- choose direction authority and production mode before production media generation;
- approval creates canon, but acceptance scope matters;
- preserve an accepted complete-edit baseline;
- preserve an accepted source library as canonical visual source material while keeping its timeline editable;
- if the user says “keep this, fix that,” change only the named defect unless broader change is explicitly authorized;
- when canonical source material exists, diagnose first and prefer editorial/source-derived repair over unnecessary regeneration;
- do not restart, replace source canon, or reinterpret locked canon by habit;
- internal scene motion precedes camera motion for living-scene work;
- visible production quality outranks metadata completion.

## Production form decision
Direction authority and production mode are separate decisions.

Direction authority:
- `reference_led`
- `music_led`
- `user_directed`

Production mode:
- `living_scene`
- `cinematic`
- `hybrid`

A supplied reference can lead any of the three production modes. Never assume “reference video” means “cinematic.” Analyze the reference motion/composition language first. A reference does not authorize content reuse; `accepted_source_library` requires explicit current-user authorization.

## Runtime law
- Do not bypass bootstrap by manually copying rules into a sandbox.
- Do not use a stale branch copy of the guard when the bootstrapped current-main guard differs.
- Before stage-changing work, run:
  - `python .aivideoedit/os/general/reusable/tools/production_guard.py --branch <current-branch>`
  - `python .aivideoedit/os/general/reusable/tools/narrative_guard.py --branch <current-branch>`
  - `python .aivideoedit/os/general/reusable/tools/recut_guard.py --branch <current-branch>` when present in the current-main OS (it is mandatory for current-main versions that provide it).
  - `python .aivideoedit/os/general/reusable/tools/workflow_guard.py --branch <current-branch>` when present; this resolves and validates the project-neutral standard workflow set for the active production.
- Use `python .aivideoedit/os/general/reusable/tools/workflow_resolver.py --project <project-dir> --json` to inspect the selected standard workflows; do not substitute historical production names for capability names.
- If the session attestation is missing, branch-mismatched, or its critical OS hashes changed, the guard must fail.
- Start every new agent/session with a fresh bootstrap, even when reusing the same sandbox.
- For a Director Brain v3 project, do not perform an action outside `refinement_scope.allowed_changes` while baseline refinement is active unless the current user updates authorization.
- For an active source-library recut, do not act outside `recut_scope.allowed_changes`, do not violate `forbidden_changes`, and do not replace source canon when `source_replacement_authorized=false`.

## Non-negotiable sequence
Source ingest -> reference + music analysis -> resolve lyrics status -> resolve genre authority -> choose direction authority + production mode -> visual/media approach -> storyboard -> frame-followable video script -> shot packages with real media evidence -> short finished mode-aware proofs -> FX lock -> assembly -> actual-export mode-aware QC -> archive.

Short reference videos are fully extracted. Long references use recorded meaningful sampling.

A supported recovery/recut specialization for productions with already-good canonical visual source material is documented in `general/reusable/RECUT_REFINEMENT.md`. It does not bypass the normal sequence; it specializes ingest/coverage/edit/QC around an accepted source library.

### Music / lyrics / genre authority gate
Before story direction is locked:
1. determine whether lyrics are present;
2. if lyrics are present, preserve verified lyrics and use **lyrics + music analysis** as story authority unless the current user excludes lyrics;
3. if there are no lyrics, use **music analysis as the primary narrative authority** — tempo/pulse, groove, section changes, energy, instrument entrances/exits, tension/release and recurring motifs must shape the story;
4. identify the song type/genre with confidence;
5. if genre is unclear, **ask the current user** instead of guessing; the user's answer becomes authoritative and must be recorded in `MUSIC_ANALYSIS.json`.

No lyrics does not force a cinematic story and does not force a visualizer. Production mode is chosen deliberately.

### No-reference visual-direction gate
If there is no usable user-supplied visual reference, the agent **must not silently choose an artistic direction** and must not generate production media yet.

Before `APPROACH_ESTABLISHED`, the agent must:
1. derive **at least three materially distinct numbered artistic-rendering routes** from the current song, verified lyrics when present, music analysis, genre authority, and available capabilities;
2. ensure the routes genuinely explore different production forms when appropriate, including living-scene, cinematic, and/or hybrid approaches rather than three cosmetic variants of one idea;
3. present those routes to the user in chat;
4. give every route a name, interpretation, rendering/media treatment, production mode, and a numbered mini-storyboard with at least three beats/frames;
5. accept a single route, a hybrid of numbered routes, or explicit user modifications;
6. record the presented options and the user's explicit current-chat selection in `MEDIA_PLAN.json`; and
7. lock the resulting direction authority + production mode in `OPERATING_ORDER.json` for Director Brain v3 projects before production media is generated.

Concept/storyboard previews created solely to let the user choose a route are decision artifacts, not production media. They may not be silently promoted into the production unless the user-selected direction authorizes them.

### Script gate
After the storyboard/shot map is locked and **before shot packages are built**, create:
- `SCRIPT.md` — human-readable directing script.
- `SCRIPT.json` — machine-readable, frame-followable production script.

The script must cover the complete target frame range and map each span to: shot ID, story action, planned visual media, animation behavior, musical cues, lyric cue when applicable, and transition.

For Director Brain v3 `living_scene` work, every script entry must identify semantic `motion_regions` and protected regions. For `hybrid`, every entry must declare whether that shot is using `living_scene` or `cinematic` behavior and meet the corresponding requirements.

### Canon, baseline refinement, and source-library recut law
For Director Brain v3 projects:
- canonical assets are never disposable source material;
- asset lifecycle is `exploratory -> candidate -> approved -> canonical -> derived`, with `rejected` and `retired` terminal/side states as appropriate;
- an accepted baseline must record its locator, hash, and current-user acceptance statement and protects the complete edit;
- an accepted source library is separate and must record role, locator, hash, current-user acceptance statement, `content_reuse_authorized=true`, and `timeline_locked=false`;
- reference presence alone never creates source-library authorization;
- an active baseline refinement scope must name the goal, allowed changes, and forbidden changes; `restart_authorized=false` means do not rebuild/reinterpret the accepted foundation;
- an active source-library recut must name actual defects plus allowed and forbidden changes; `source_replacement_authorized=false` means preserve approved source pixels/world and solve defects with traceable coverage/editing instead of silently regenerating the canon;
- source-derived assets must record the accepted source-library hash, source time/range, and the derivation performed;
- generated new content must never be mislabeled as source-derived coverage.

### Canonical hero-library gate
When an approved source video is used as a hero/shot library, use `general/reusable/tools/hero_library_extract.py` or an equivalent implementation that produces the same evidence. Do not simply keep every Nth second as final coverage. The selected library must be non-empty, reject/warn on near-duplicates, record source/frame hashes and measured diversity evidence, and avoid semantic claims that were not actually measured.

### Backend-equivalence gate
Creative recipe and render backend are separate. If the proof backend and production backend differ, `RENDER_RECIPE.json` must record both backends, parameter mappings, the render implementation, and a representative PASS equivalence proof demonstrating preserved behavior, visible effects, and traceability. "It should look the same" is not a valid proof.

### Project-local FX gate
Canonical reusable FX remain under `general/reusable/fx_v2/`. A one-off production effect may live under the active project's `project_fx/` only if `general/reusable/fx_v2/project_local_fx_gate.py` validates its real implementation/inputs, deterministic or recorded parameters where applicable, proof media/hash, visible pixel change, truthful naming, PASS QC, and current precompile lock. Project-local validation never promotes an effect into canonical `fx_v2`.

### Real-media evidence gate
A storyboard is never a substitute for shot production. A successful command is never artistic QC.

- A shot package consisting only of `README.md`, JSON metadata, or procedural placeholders is invalid.
- Every shot package needs hashed `media_evidence` pointing to actual source/generated/derived visual media.
- If `MEDIA_PLAN.json` selects generated stills/support imagery/living paintings, `ASSET_MANIFEST.json` must contain actual generated visual asset evidence.
- If source-derived coverage is selected, `ASSET_MANIFEST.json` must preserve its accepted-source provenance.
- A request to keep chat light or avoid previews **must never** be interpreted as permission to skip real image generation. If the active generation runtime necessarily surfaces image previews in chat, those previews are allowed and should be kept concise.

Effects must be visible and traceable. Technology names must be truthful.

### Mode-aware proof and QC
Use `general/reusable/MODE_AWARE_QC.md`.
- `living_scene`: prove internal motion, independent material behavior, identity stability, restrained camera, clean loops/joins.
- `cinematic`: prove readable action, sufficient coverage, continuity, progression, music-directed pacing.
- `hybrid`: apply the correct checks per section and prove the methods belong to one coherent film; source-derived coverage may expand an accepted living world while remaining traceable to source canon.
- `reference_led`: also compare the proof's actual behavior against the authorized reference language.
- source-library recut: preserve PRE and POST QC for repetition/composition, runtime, black/freeze, framing/aspect, audio sync, continuity warnings, mode-aware QC, and source/canon integrity. Post-edit canon integrity must PASS.

Technical success never creates artistic acceptance. Numerical improvement is evidence, not the director.
