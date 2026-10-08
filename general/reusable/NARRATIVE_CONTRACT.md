# Directing / Music / Media Evidence Contract

This file retains its historical path for compatibility, but its contract is production-mode neutral. It closes failures where technically valid media passes while the intended visual experience was never created.

## 1. Resolve lyrics status and directing use
Every production must explicitly record one of:
- `present`
- `instrumental`
- `none_confirmed`

If lyrics are present, preserve a verified `LYRICS.md`.

By default, present lyrics are active directing authority and must be used with musical analysis unless the current user explicitly excludes them.

A current user may explicitly exclude otherwise-present lyrics from directing. In that case `MUSIC_ANALYSIS.json` must keep `lyrics.status = "present"` and record:
- `lyrics.directing_use = "excluded_by_current_user"`
- `lyrics.exclusion_source = "current_user_instruction"`
- the current user's exclusion instruction

When lyrics are explicitly excluded, they remain archived source material but must not appear in `SCRIPT.basis` or `lyric_cue` fields. Music analysis becomes the primary directing authority unless the current user supplies a stronger current direction.

If lyrics are absent, the music itself remains a directing source. Instrumental music still requires deliberate visual structure, but that structure may be living-scene, cinematic, or hybrid. It does not automatically require a conventional narrative.

## 2. Resolve genre authority
The agent may infer genre only when it is reasonably confident. `MUSIC_ANALYSIS.json` uses:
- `genre.status = "confident"` with confidence >= 0.65; or
- `genre.status = "user_confirmed"` when the user supplies the song type.

If the agent cannot identify the type confidently, it must ask the current user before visual-direction lock. Do not silently choose a cultural/genre language.

## 3. Analyze musical directing cues
`MUSIC_ANALYSIS.json` must preserve:
- tempo/pulse or explicit non-metric status;
- meter/groove;
- section boundaries;
- energy changes;
- meaningful instrument/texture entrances and exits;
- drops/builds/tension/release/recurring motifs;
- per-section musical cues;
- per-section directing/visual function.

For compatibility, a project may store the last item as `narrative_function` or `visual_function`. The meaning is: what this musical section should make the picture do.

These cues control visual development, shot/scene timing, animation intensity, transition timing, and FX escalation according to the declared production mode.

## 4. Choose directing authority and production mode
Director Brain v3 separates:

Direction authority:
- `reference_led`
- `music_led`
- `user_directed`

Production mode:
- `living_scene`
- `cinematic`
- `hybrid`

A reference video does not automatically imply cinematic production. No-reference work uses the visual-direction selection gate before production media is generated.

## 5. Script after storyboard
The storyboard establishes the route. The production script makes it executable.

Before shot packages:
- create `SCRIPT.md` for humans;
- create `SCRIPT.json` for machines;
- cover the entire target frame range without gaps;
- map each frame span to visual/action intent, actual visual media, animation behavior, musical cues, lyric cues when applicable, and transition.

For compatibility, `story_action` remains valid. Director Brain v3 may use `visual_action` when a conventional story action would misdescribe a living-scene section.

For `living_scene`, declare semantic `motion_regions` and `protected_regions`. For `hybrid`, declare the shot-level mode and apply the corresponding requirements.

The render/assembly process follows the script; it may not invent a substitute visual direction at compile time.

## 6. Real media is mandatory
A declared capability is not an asset.

If the media plan selects generated stills/support imagery/living paintings, actual generated visual assets must appear in `ASSET_MANIFEST.json`.

Every shot package must include hashed `media_evidence` for actual source/generated/derived media. A folder containing only README/JSON metadata is not a shot package.

Procedural geometry, gradients, particles, or placeholder shapes can be support FX, but they cannot silently replace required characters, environments, actions, compositions, locations, or other required picture media.

## 7. Preview semantics
A user may ask to keep chat light, avoid intermediate downloads, or avoid reviewing every preview. That instruction does **not** mean “do not generate images.”

If the active generation runtime necessarily exposes generated-image previews in chat, those previews are allowed as part of creating real production assets. Keep surrounding chatter minimal.

## 8. Final creative QC
Technical checks such as duration, decode success, freeze detection, and black-frame detection are necessary but insufficient.

Before `FINAL_QC_PASSED`, compare the full export to the locked `SCRIPT.json` and `MODE_AWARE_QC.md`. The project fails creative QC if major scripted visual sections are absent, the declared production mode is not actually visible in the result, or required media is replaced by placeholders.

## 9. Reference-role separation
A visual reference must have an explicit production role. Examples include motion language, palette, lighting, composition, effect behavior, source footage, or source stills.

A reference authorized for **style or motion language only** teaches those properties only. It does **not** authorize reuse of its subject, scene, source frames, or footage as final-picture content.

Reusing reference content in the final picture requires an explicit current-user instruction authorizing that content role. Do not convert “make it move like this” into “make the movie out of this.”

Generated companion media must materially serve the selected production world rather than merely reproduce the reference subject with minor stylistic changes.

## 10. Creative rejection and accepted canon
A technical or contract pass never outranks current-user creative judgment.

If the current user rejects a proof, media set, visual direction, or final export:
- mark the affected proof/assets/export as `rejected`;
- clear dependent acceptance/final-QC booleans for the affected scope;
- repair or roll back only as far as necessary;
- preserve unrelated accepted canon;
- do not promote rejected media or techniques as accepted canon.

If the current user accepts a full baseline, record and lock that baseline. Later criticism of a named defect is not automatically rejection of the whole production.
