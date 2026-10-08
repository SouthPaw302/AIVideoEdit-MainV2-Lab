# AIVideoEdit — Canonical Effect / Loop Package Standard

Every reusable loop, transition, effect, spatial treatment, or animation method created in a song project must be exported into a recoverable canonical package when it proves useful.

## Required package fields

A reusable package should preserve, as applicable:

- stable effect ID and human-readable name;
- category: loop / transition / spatial / atmosphere / lighting / motion / audio-reactive / compositing / QC / render utility;
- source project and first validating shot/sequence;
- validation status;
- implementation file(s), shader(s), node graph(s), or exact recipe;
- source requirements;
- masks, mattes, alpha plates, depth inputs, ROIs, or tracking inputs;
- deterministic seed when randomness is used;
- key parameters and safe ranges;
- audio-control inputs when reactive;
- expected duration/FPS/aspect constraints when relevant;
- entry/exit behavior for loops/transitions;
- preview/proof render location or checksum;
- QC result and known failure modes;
- fallback implementation;
- license/provenance for external effect assets;
- version and change history.

## Loop-specific requirements

Every loop must record:

1. source clip/frame range;
2. source FPS and dimensions;
3. loop duration;
4. whether motion is real, synthesized, generated, or hybrid;
5. entry/exit similarity or seam method;
6. whether a crossblend is used and its duration;
7. whether the loop returns exactly to its starting camera/effect state;
8. seam QC result;
9. duplicate/freeze/ghosting QC result;
10. intended musical use: quiet bed, verse, chorus, transition, bridge, accent, etc.

Do not call a mathematically similar endpoint a good loop until visual seam QC passes.

## Transition-specific requirements

Record outgoing/incoming source, mask/object/depth logic, transition duration, midpoint behavior, exposure/color continuity, identity protection, and whether the transition can be reversed.

Long full-body dissolves that produce identity double exposure should normally fail. Prefer motivated object, reflection, pigment, atmospheric, depth, or geometry transitions when appropriate.

## Spatial-effect requirements

For 2.5D, NeRF, or Gaussian-splat work, record what is actually being rendered. Do not collapse these terms:

- 2.5D = depth-aware layer/field displacement without full reconstructed geometry;
- hybrid NeRF = actual learned radiance/density field combined with image layers;
- 3DGS = actual Gaussian-splat scene data and renderer.

Never claim NeRF or Gaussian use because a visual merely resembles volumetric rendering.

## Audio-reactive requirements

Save the measured control signal and mapping, not only the visual result. Preferred reusable controls include energy, transient, brightness, low, mid, and high bands. Smooth and bound all controls to avoid generic strobing.

## Proof gate

A new package can be registered immediately, but must remain `project_direction` or `experimental` until a representative proof renders successfully. A proof should be short enough to iterate rapidly and strong enough to show the effect clearly.

## Promotion gate

Before a song reaches final assembly, any technique that is useful beyond that song should be:

1. registered in `CANONICAL_EFFECT_REGISTRY.json`;
2. summarized in `CANONICAL_EFFECT_REGISTRY.md`;
3. copied or generalized into `general/reusable/` when implementation exists;
4. linked back to its source project and proof/QC record.

## Final-film gate

A planned effect is not considered present merely because its code or package exists. Scan the actual exported movie and verify that the effect survived final assembly, encoding, scaling, grading, and timeline integration.
