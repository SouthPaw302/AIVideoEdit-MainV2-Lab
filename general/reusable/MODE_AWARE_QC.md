# Mode-Aware Proof and QC

Generic technical QC is necessary but not sufficient. A render can be valid media and still be the wrong kind of film.

## Universal checks
Every proof/final must verify:
- playable media, expected dimensions/fps/runtime;
- no black/damaged/frozen sections;
- audio sync and expected song coverage;
- claimed effects are visibly present;
- identity/anatomy stability where people are present;
- no accidental seams, ghosting, boiling, leakage, or repeated weak cadence;
- actual exported picture inspected at normal speed.

## `living_scene`
Required creative proof evidence:
- `internal_motion_visible`: meaningful motion exists inside the composition;
- `material_motion_independent`: fire/water/smoke/rain/light/etc. do not move as one global layer;
- `identity_stable`: hero artwork and protected anatomy remain recognizable and stable;
- `camera_restrained`: camera/depth movement supports rather than substitutes for animation;
- `loop_or_join_clean`: repeated or sustained motion does not expose an obvious seam;
- semantic motion regions are named in the shot plan.

Failure examples: held still + zoom; whole-frame shake; uniform warping; face drift; duplicated low-rate cadence; one global particle layer pretending to be scene motion.

## `cinematic`
Required creative proof evidence:
- `story_action_readable`;
- `coverage_sufficient`;
- `continuity_controlled`;
- `shot_progression_present`;
- `pacing_music_directed`.

Failure examples: unrelated beautiful shots; repeated composition with different prompts; story events missing from coverage; character/world discontinuity; montage that ignores the song's structure.

## `hybrid`
Each section/shot must declare whether it is using living-scene or cinematic behavior. Apply that mode's checks to the section, then verify:
- one coherent visual world;
- intentional transitions between methods;
- no complexity added merely to demonstrate capability.

When an accepted source library exists, hybrid coverage may expand the canonical living visual world with source-derived environment/detail inserts, alternate framing, source-range motion, canonical optical states, and shorter cinematic coverage where the music benefits. Verify source provenance and canon integrity for every such derived shot.

## Reference comparison
When direction authority is `reference_led`, proof evidence must also state what motion/composition behavior was taken from the reference and whether the proof reproduces that behavior without unauthorized content reuse.

## Source-library recut comparison
When `accepted_source_library.status=accepted` and a recut is active, preserve a PRE-EDIT QC snapshot and a POST-EDIT QC snapshot. At minimum compare:
- repetition/composition evidence (including `similar_runs_count` where export-variety QC is used);
- runtime;
- black/freeze result;
- framing/aspect result;
- audio coverage/sync result;
- continuity warnings;
- mode-aware QC result;
- source/canon integrity, including the accepted source-library SHA-256.

The post-edit source/canon integrity result must PASS before final recut acceptance. Numerical metrics are evidence, not the director: do not trade away artistic quality merely to improve a score.

## Acceptance rule
Technical pass never creates artistic acceptance. User acceptance may lock a baseline or may separately authorize a canonical source library. A locked baseline protects the complete edit. An accepted source library protects its approved source pixels/world while keeping the timeline editable. Later QC must verify the correct protection rule for the active workflow.
