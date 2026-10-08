# Living-Scene Doctrine

This doctrine defines a reusable production pattern for turning strong authored imagery into stable, internally animated scenes and refining accepted work without drift. It also defines when a living scene should hand off to bounded true-video continuation for real temporal action.

## Core pattern
1. Establish a coherent authored visual world with a small set of strong hero images.
2. Treat approved hero imagery as canon, not disposable generation material.
3. Build coverage by deriving compatible shots from that canon rather than constantly reinventing the world.
4. Animate the scene internally before moving the camera: fire, candlelight, embers, smoke, rain, water, reflections, cloth, hair, atmosphere, and other semantic regions.
5. Protect faces, hands, anatomy, and the authored surface from broad regeneration or whole-frame deformation.
6. When a required action cannot be represented convincingly as localized living-scene motion, declare `GENERATED_CONTINUATION` instead of faking action with pan/zoom or deforming the plate.
7. Render at the target delivery cadence from the start. Do not create a low-frame-rate intermediate and fake final cadence with duplication/interpolation.
8. Render and validate shots independently so production is resumable and repairable.
9. Prove representative motion behavior before scaling the whole production.
10. When the user accepts a full baseline, lock it. Name remaining defects and refine only those defects unless the user authorizes a restart.
11. Compare refinements against the accepted baseline; promote only when the result is actually better.
12. Preserve the accepted master as a recoverable source of truth.
13. Keep artistic mastering separate from platform/delivery mastering when intros, outros, packaging, or platform requirements differ.

## Living-scene rule
A still image is a scene plate, not a finished shot. For each shot, explicitly decide:
- what must remain stable;
- what naturally moves;
- what environmental forces drive that motion;
- which regions need independent timing;
- how much camera/depth motion is actually necessary;
- what must be protected from deformation;
- whether the action remains suitable for living-scene treatment or requires true temporal continuation.

## True-continuation handoff rule
Use living-scene/source-derived methods for atmosphere, weather, reflections, light, subtle body/hair/cloth motion, depth, and restrained visual breathing.

Escalate to `GENERATED_CONTINUATION` when the shot requires real articulated temporal action such as:
- turning/walking through space;
- speaking with visible facial articulation;
- picking up/manipulating props;
- opening/closing doors;
- complex hand/body motion;
- sustained physically coupled cloth/curtain/object response;
- other action that would otherwise require whole-frame warping or fake camera movement.

A continuation starts from canonical visual state and may produce a candidate terminal frame. That terminal frame becomes a reusable anchor only after temporal/identity/world QC.

## Environmental-system rule
Weather and environmental motion must behave as coupled systems rather than independent overlays. A storm shares wind direction, rain behavior, cloud movement, haze, lightning response, wet-surface behavior, reflections, and physically plausible secondary motion. Interior regions remain dry unless physically exposed; weather may affect interiors through glass, light, sound, reflection, or actual openings.

## Loop rule
Living scenes should not advertise their loops. Prefer phase-continuous behavior, multiple overlapping periods, deterministic wrap/reseed behavior, and independent motion layers rather than one repeated global cycle.

## Music-directed section rule
For music-led living-scene or hybrid work, lock contiguous music sections before building the master. Give each section a neutral scene profile and explicit base, reactive, fill, and transition intent. Render short proofs for every non-absent pass, then assemble from proved handles. Selected effects must be recorded against the actual section outputs; an available or locked effect is not evidence that it reached the final picture.

## Refinement rule
Once a picture baseline is accepted, local repair is preferred over rebuild. Patch failed shots, weak effects, excessive camera motion, generated-continuation drift, or delivery defects without disturbing approved picture language, timing, identities, or hero assets.

## Operating principle
AI generates material. The production system makes the film. Living scenes preserve authored worlds; bounded continuations move those worlds forward in time.
