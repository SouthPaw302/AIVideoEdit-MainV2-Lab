# Production Branch Template

Use only on `song/<slug>`. A new supplied audio master creates a fresh branch from current `main` unless the user explicitly names an existing branch to continue.

## Director Brain v3
All new productions use Director Brain v3. Set `"director_brain_version": 3` in `PROJECT_STATE.json` and create `OPERATING_ORDER.json` from `projects/OPERATING_ORDER_TEMPLATE.json`.

`OPERATING_ORDER.json` is the short project-level directing brief. It must answer, without searching old chats:
- What are we making now?
- Where does the directing authority come from?
- What production mode are we using?
- What is canon?
- Is there an accepted complete-edit baseline?
- Is there a separately accepted canonical source library whose pixels/world may be reused while the timeline remains editable?
- Is baseline refinement active, source-library recut active, or neither?
- What defects are actually named?
- What may change now?
- What must not change?
- What is the exact next action?

Do not put historical provenance or another project's identity into the Operating Order.

## Required branch-local package
- `PROJECT.md`
- `STATUS.md`
- `HANDOFF.md`
- `PROJECT_STATE.json`
- `OPERATING_ORDER.json` for Director Brain v3
- `SOURCE_AUTHORITY.json`
- `REFERENCE_MANIFEST.json`
- `MEDIA_PLAN.json`
- `ASSET_MANIFEST.json`
- `MUSIC_ANALYSIS.json`
- `STORAGE_MANIFEST.json` after remote media storage is initialized
- `LYRICS.md` when lyrics are present
- `VISUAL_DNA.md`
- `SHOT_LIST.md`
- `SCRIPT.md`
- `SCRIPT.json`
- FX plan/manifest and later `fx.lock.json`
- `RENDER_HISTORY.md`
- `QC.md`
- `shot_packages/`

Recovery/recut productions additionally use evidence files as applicable:
- `HERO_LIBRARY.json` when `canonical_hero_library` is selected or a source-library recut is active;
- `RENDER_RECIPE.json` when a recorded creative recipe/render implementation is used, especially when proof and production backends differ; music-led living-scene and hybrid v3 productions always require it;
- `MUSIC_CONTROL_MAP.json`, `SECTION_RENDER_MANIFEST.json`, and `FX_APPLICATION_PROOF.json` for music-directed section assembly;
- `REFINEMENT_QC.json` before a source-library recut may claim `FINAL_QC_PASSED`;
- `project_fx/*.json` plus matching `*.lock.json` for any project-local experimental FX.

The machine stage is recorded in `PROJECT_STATE.json` and validated by `general/reusable/tools/production_guard.py`, `general/reusable/tools/narrative_guard.py`, and, for Director Brain source-library/recut features, `general/reusable/tools/recut_guard.py`. Do not manually claim a later state unless its required evidence exists.

Historical chats/branches/media are excluded by default in `SOURCE_AUTHORITY.json`. Explicit user authorization is required to add any such source.

## Operating Order requirement
For Director Brain v3, before `APPROACH_ESTABLISHED`, `OPERATING_ORDER.json` must contain:
- `mission`
- `direction_authority`: `reference_led`, `music_led`, or `user_directed`
- `production_mode`: `living_scene`, `cinematic`, or `hybrid`
- `canon_lock`
- `accepted_baseline`
- `accepted_source_library`
- `refinement_scope`
- `recut_scope`
- `current_user_direction`
- `exact_next_action`

`accepted_baseline` keeps its established meaning: the complete picture/edit is accepted. Record its locator, SHA-256, and current-user acceptance statement. If baseline refinement is active, record the goal, allowed changes, forbidden changes, and whether a restart is explicitly authorized.

`accepted_source_library` is different. It authorizes canonical visual source material while leaving the edit/timeline rebuildable. When accepted it records:
- `status: "accepted"`;
- `role`: `hero_library`, `shot_library`, `visual_world`, or `reference_content`;
- `file_or_locator`;
- SHA-256;
- current-user acceptance statement;
- `content_reuse_authorized: true`;
- `timeline_locked: false`.

Do not infer source-library acceptance from the existence of a reference. Explicit current-user content-reuse authorization is required.

When `recut_scope.active=true`, record `named_defects`, non-empty allowed/forbidden changes, and keep `source_replacement_authorized=false` unless the user explicitly authorizes abandoning/replacing source canon. The normal defect-first rule is `CANON -> DIAGNOSE -> EXTRACT COVERAGE -> RE-EDIT -> COMPARE -> PROMOTE`.

## MUSIC_ANALYSIS requirement
Before `REFERENCES_ANALYZED`, resolve lyrics status, genre authority, and the musical section/cue map.

Minimum shape:

```json
{
  "schema": "aivideoedit.music-analysis.v1",
  "analysis_complete": true,
  "lyrics": {
    "status": "instrumental",
    "source": "audio_analysis",
    "text_file": null
  },
  "genre": {
    "status": "user_confirmed",
    "label": "Reggae Dubstep Mix",
    "source": "current_user_instruction",
    "confidence": 1.0,
    "user_declaration": "This is a Reggae Dubstep Mix"
  },
  "rhythm": {
    "tempo_status": "measured",
    "tempo_bpm": 76.0,
    "pulse_description": "half-time bass pulse with syncopated offbeat accents",
    "meter_or_groove": "4/4 reggae-derived offbeat groove with dubstep half-time weight"
  },
  "sections": [
    {
      "id": "A",
      "start_seconds": 0.0,
      "end_seconds": 20.0,
      "energy": "low/building",
      "musical_cues": ["filtered intro", "first bass entrance"],
      "narrative_function": "establish world and first dramatic question"
    },
    {
      "id": "B",
      "start_seconds": 20.0,
      "end_seconds": 40.0,
      "energy": "rising",
      "musical_cues": ["full groove", "widening bass"],
      "narrative_function": "commit protagonist to the journey"
    }
  ]
}
```

If the agent cannot identify the genre confidently, it must ask the current user before approach/story lock. A user-confirmed genre must preserve the user's declaration.

## No-reference MEDIA_PLAN requirement
When `REFERENCE_MANIFEST.json` contains no usable reference videos and no reference images, `MEDIA_PLAN.json` must contain a locked `visual_direction_gate` before `APPROACH_ESTABLISHED`.

Minimum shape:

```json
{
  "user_approach_established": true,
  "visual_direction_gate": {
    "required": true,
    "presented_in_chat": true,
    "options": [
      {
        "number": 1,
        "name": "Route name",
        "story_approach": "Distinct narrative interpretation",
        "rendering_route": "Distinct artistic/media treatment",
        "production_mode": "living_scene",
        "storyboard": [
          {"number": 1, "description": "Opening beat/frame"},
          {"number": 2, "description": "Development beat/frame"},
          {"number": 3, "description": "Climactic beat/frame"}
        ]
      }
    ],
    "user_selection": {
      "status": "selected",
      "selected_option_numbers": [1],
      "recorded_user_instruction": "User's explicit current-chat selection or modification"
    },
    "locked": true
  }
}
```

The real gate requires at least three materially distinct options. The routes should explore materially different production forms where appropriate instead of three cosmetic variants. `status` may be `selected` or `hybrid`; a hybrid records every selected option number plus the user's modification.

## SCRIPT requirement
After the storyboard/shot map is locked and before shot packages are built, create a readable `SCRIPT.md` and a machine-readable `SCRIPT.json`.

Minimum machine shape:

```json
{
  "schema": "aivideoedit.video-script.v1",
  "locked": true,
  "based_on_storyboard": true,
  "target_fps": 24,
  "duration_seconds": 180.64,
  "total_frames": 4335,
  "basis": ["storyboard", "music_analysis"],
  "entries": [
    {
      "shot_id": "S01",
      "start_frame": 0,
      "end_frame": 383,
      "production_mode": "living_scene",
      "story_action": "The protagonist encounters the first threshold.",
      "visual_media": "Approved hero environment with locked protagonist identity.",
      "animation_behavior": "Localized environmental motion with restrained depth-aware camera movement.",
      "motion_regions": ["rain", "reflections", "cloth", "practical light"],
      "protected_regions": ["face", "hands", "hero silhouette"],
      "music_cues": ["intro pulse", "first harmonic swell"],
      "lyric_cue": null,
      "transition": "environmental dissolve"
    }
  ]
}
```

Frame ranges must be contiguous from frame `0` through `total_frames - 1`. When lyrics are present, add `"lyrics"` to `basis` and map lyric cues into the relevant entries.

For Director Brain v3 `living_scene`, every entry requires semantic `motion_regions` and `protected_regions`. For `hybrid`, every entry declares its shot-level `production_mode` as `living_scene` or `cinematic`; living-scene entries carry the semantic region requirements.

## Asset lifecycle and source-derived provenance
Director Brain v3 generated/derived visual assets should record a `lifecycle_status` using:
- `exploratory`
- `candidate`
- `approved`
- `canonical`
- `derived`
- `rejected`
- `retired`

Do not regenerate or silently replace `canonical` assets while canon is locked.

Assets created from an accepted source library by crop/reframe, detail extraction, alternate framing, source-range reuse, conservative pan/scan, restrained depth/parallax, masks/layers, or source-derived environmental inserts are `origin: "source_derived"` and must carry provenance like:

```json
{
  "origin": "source_derived",
  "lifecycle_status": "derived",
  "provenance": {
    "kind": "source_derived",
    "source_library_sha256": "<accepted-source-sha256>",
    "source_range_seconds": [12.4, 13.1],
    "derivation": "alternate crop/reframe"
  }
}
```

Generated new content is not source-derived coverage and must never be mislabeled as such.

## Canonical hero-library extraction
Use `general/reusable/tools/hero_library_extract.py` when approved video is being treated as a canonical shot library. The tool may densely sample candidates but final selection is perceptual/quality/diversity-driven, rejects near-duplicates, records source/frame SHA evidence, measured visual signatures/tags, source ranges, lifecycle status, and explicitly identifies semantic dimensions it did not measure. `HERO_LIBRARY.json` may not be empty.

## Backend-independent render recipe
When proof and production backends differ, create `RENDER_RECIPE.json` with `schema: "aivideoedit.render-recipe.v1"`, a recipe identity, proof backend, production backend, parameter/backend mapping, hashed render implementation, and an `equivalence_proof` whose status is `PASS`, whose representative proof is hashed, and which records `behavior_preserved=true`, `effects_visible=true`, and `traceable=true`. Backend substitution without this evidence is invalid.

For music-led living-scene or hybrid Director Brain v3 work, add `execution_profile.id: "music_directed_section_assembly"` to that same recipe. It must point to a frame-aligned `MUSIC_CONTROL_MAP.json`, a `SECTION_RENDER_MANIFEST.json` that declares base/reactive/fill/transition passes and a neutral scene profile per music section, and `FX_APPLICATION_PROOF.json` that ties each locked effect to a hashed section output with visible-change evidence. A pass may be marked `not_applicable` only with a section-specific reason. The recipe must declare its intended variation; sparse treatment is a deliberate choice, never an accidental omission.

## Project-local FX
Canonical reusable FX authority remains `general/reusable/fx_v2/`. One-off project effects may live under `project_fx/`, but each manifest must pass `general/reusable/fx_v2/project_local_fx_gate.py` and have a current sibling `*.lock.json`. Require real implementation and inputs, truthful technology labeling, recorded deterministic parameters when applicable, hashed proof media, visible pixel change, PASS QC, and `placeholder=false`. A project-local lock never promotes the effect into canonical `fx_v2`.

## Before/after recut QC
For an active source-library recut, preserve pre-edit and post-edit QC with `general/reusable/tools/refinement_qc_compare.py` and `REFINEMENT_QC.json`. Evidence covers repetition/composition, runtime, black/freeze, framing/aspect, audio sync, continuity warnings, mode-aware QC, and source/canon integrity. Post-edit canon integrity must PASS and match the accepted source-library hash. Metrics are evidence, not the director.

## Shot-package media evidence
Every `shot_packages/Sxx/package.json` must include non-empty `media_evidence` with actual asset locators and hashes. Example:

```json
{
  "shot": "S01",
  "media_evidence": [
    {
      "kind": "generated_image",
      "path": "generated/S01_hero.png",
      "sha256": "<sha256>",
      "status": "generated"
    }
  ]
}
```

A metadata-only shot package is invalid. If generated-media capabilities are selected, `ASSET_MANIFEST.json` must also contain generated visual asset entries, using `origin: "generated"` or a generated kind/role.

## Delivery mastering
When platform packaging changes intros, outros, titles, or technical delivery without changing the accepted picture edit, preserve separate identities for:
- artistic master;
- platform/delivery master.

Do not overwrite the artistic master merely to satisfy platform packaging.

Large media may be stored in the song's GitHub Release through `general/reusable/storage/github_release_storage.py`. The branch-local `STORAGE_MANIFEST.json` remains the authoritative index of those remote assets.
