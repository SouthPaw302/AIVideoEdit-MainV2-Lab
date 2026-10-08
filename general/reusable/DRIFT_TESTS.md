# Director Brain Drift Tests

These scenarios test whether the operating system keeps an agent on the intended production path. A system change is incomplete if an agent can still legally drift through one of these cases.

## 1. New music-only project, no visual reference
Expected behavior:
- bootstrap current `main`;
- create Director Brain v3 project state and Operating Order;
- analyze music/lyrics/genre;
- present at least three materially distinct visual routes before production media;
- include genuinely different production modes where appropriate;
- wait for the user's route selection or modification;
- record direction authority + production mode before generating production media.

Drift failure:
- silently choosing a cinematic route;
- presenting three cosmetic variants of the same route;
- generating final production imagery before route selection.

## 2. Supplied living-scene reference
Expected behavior:
- analyze the reference's composition and internal motion;
- recognize that a moving reference may imply `living_scene`, not automatically `cinematic`;
- record `direction_authority=reference_led` and the selected production mode separately;
- plan semantic motion regions and protected regions.

Drift failure:
- treating every reference video as source footage;
- forcing the project into a cinematic-shot pipeline solely because the reference is a video;
- replacing internal animation with whole-frame zoom/shake.

## 3. Supplied cinematic reference
Expected behavior:
- analyze continuity, coverage, action, camera, pacing, and visual language;
- select `cinematic` when the requested result truly calls for evolving cinematic coverage;
- use the reference as teaching material unless content reuse is explicitly authorized.

Drift failure:
- reducing a cinematic reference to a single living still;
- copying source frames without authorization;
- creating unrelated beautiful shots that do not preserve the learned directing language.

## 4. Accepted baseline under refinement
Operating Order conditions:
- `canon_lock.locked=true`;
- `accepted_baseline.status=accepted`;
- `refinement_scope.active=true`;
- `restart_authorized=false`.

Expected behavior:
- Second Brain displays a prominent DO NOT RESTART instruction;
- agent preserves baseline timing, canon, and forbidden items;
- agent repairs only `allowed_changes`;
- new result is compared against the accepted baseline before promotion.

Drift failure:
- regenerating hero images;
- replacing the visual world;
- changing timing/shot architecture outside scope;
- restarting production because a new idea seems interesting.

## 5. User says “keep everything except this defect”
Expected behavior:
- update Operating Order refinement goal and allowed/forbidden changes;
- preserve everything outside the named defect;
- prefer local repair/re-render/splice over full rebuild.

Drift failure:
- interpreting criticism as rejection of the whole production;
- rolling back unrelated accepted work;
- generating a new concept without explicit authorization.

## 6. Technical render passes but wrong film type
Expected behavior:
- technical QC may pass;
- mode-aware creative QC must still fail if the result does not behave like its declared production mode.

Examples:
- `living_scene`: held still + camera zoom passes encoding checks but fails internal-motion QC;
- `cinematic`: technically valid montage fails because story/action/coverage are absent;
- `hybrid`: random mixing of techniques fails coherence checks.

## 7. Lost intermediate media after an accepted master exists
Expected behavior:
- treat the accepted master as recoverable production truth;
- analyze/reconstruct shot boundaries or structure when practical;
- do not restart solely because intermediates disappeared.

Drift failure:
- discarding an accepted picture and beginning from zero when the master can support recovery.

## 8. Platform delivery change
Expected behavior:
- preserve the accepted artistic master;
- create a separate platform/delivery master when titles, intros, outros, packaging, or platform-specific requirements differ.

Drift failure:
- overwriting the accepted artistic master with platform packaging.

## Pass condition
Director Brain v3 passes when an agent can immediately answer:
1. What am I making?
2. Who/what is directing it?
3. What production mode is active?
4. What is canon?
5. What baseline is accepted?
6. What may I change?
7. What must I not change?
8. What is my exact next action?

If those answers are unavailable, production should not advance by guesswork.
