# Canonical Director Scan — Evidence Before Artistic Judgment

**Status: current-main, project-neutral directing contract.** This file expands, and never overrides, \`PRIME_DIRECTIVE.md\`, \`DIRECTOR_SUPERVISION.md\`, Zero-Drift, FX v2, \`MODE_AWARE_QC.md\`, the active project's Operating Order, and the independent human final-release gate.

**Purpose:** Make the Director's actual-media investigation repeatable for *every* song and every agent. A green runner, valid manifest, visually attractive contact sheet, or correctly encoded file cannot establish that a film works. The Director diagnoses the actual output against the approved sources, song, script, motion intent, and accepted baseline.

## Boot, scope and authority (mandatory)

1. Bootstrap the exact current \`main\` and read Prime Directive, generated Second Brain, SOUL, and the active Operating Order.
2. Read this canonical scan contract **before selecting a recovery strategy or calling a render a success**.
3. Record which artifact is currently the approved baseline (locator and SHA), what the user actually accepted, the current user instructions, named defects, allowed and forbidden changes, and whether the request is *review*, *repair*, *finishing*, or *delivery*.
4. Production and song assets stay on \`song/<slug>\`; canonical methods belong to current-main. Never move a one-off renderer, stylistic preference, private asset ID, song script, or rejected media into reusable canon by association.
5. When the user locks a creative edit, further operations use a **separate candidate/output name**; never overwrite the accepted file, re-time protected core shots, regenerate the world, or alter music under the guise of polish.

## The eleven-phase Director scan

Record specific evidence, not generic "passed" claims. A scan is repeated at representative proof, rough cut, FX pass, post-render comparison, finishing, and delivery, with checks appropriate to scope.

### D01 — Inventory *everything* before creating replacements

List the active branch's actual source stills/videos/WAV, lyrics, shot list, FX manifest/registry, accepted production renders, and durable Drive/release assets. Inspect relevant **subfolders, ZIPs, derived PNGs, GIFs, MP4s, motion continuations, contact sheets, and QC receipts**, not just the first media directory. Preserve the source role and the status of every candidate: original / approved / proof / rejected / derived / backup. Inspect visual references only for their authorized role.

### D02 — Establish pixel provenance and exact duplicates

Compute SHA-256 for sources and rendered intermediates. Compare duplicate *contents* rather than concluding identity from matching filenames, matching sizes, or thumbnails. Keep legitimate backups; do not automatically delete or replace duplicates. Record per-shot source SHA, dimensions, frame count, fps, duration, fit/crop, and actual derived-media provenance. An asset being in a Drive folder is **not** proof a runner consumed it.

### D03 — Diagnose whether the picture source is truly suitable

A high-resolution source still, a two-second 640x360 FX proof, an FX-derived PNG variation, a real subject-motion clip, and a finished 1080p/4K shot are **different classes of asset**. A short low-resolution loop repeated over a long shot cannot masquerade as high-resolution sustained animation. Measure source-to-output scale, repetition period versus planned shot length, softness, encoded artifacts, seams, and effective pixel detail. Use the approved high-resolution source as the compositional foundation and FX proof assets as traceable motion/effect references when the current recipe authorizes that treatment; validate representative proof/backend equivalence. Do not silently upscale weak proofs and declare high-quality sources.

### D04 — Classify motion by semantic need

Inspect actual start/middle/end frames and temporal behavior **inside each shot**, not just a single timeline sample. Describe independently moving weather, practical lights, reflections, glass, hair/cloth, characters/props, vehicle wheels/road perspective, and camera. Test whether motion is coherent and genuinely progressive rather than low-amplitude flicker or fixed-period looping. Camera pan/zoom or global wobble is not proof that a subject drove, walked, handled a letter, or turned. Where real articulation is required, specify \`GENERATED_CONTINUATION\` (or actual authorized video) with zero-drift anchors, bounded actions, original audio disposition, and frame-by-frame continuity QC. Mark unresolved requirements truthfully.

### D05 — Inspect *executed* FX and artistic relevance

Compare FX recipe → registered implementation → executed pixel changes → final shot. Verify FX belongs to the material and story: rain on windows and road, clouds and sky, practical light, fog, reflection, memory, restrained transitions. An implemented canonical effect can still be **wrong for this film**. Reject gratuitous tunnels, spinning debris, fantasy particles, crowds, loud color pulses, and overbearing effects unless explicitly authorized by the current production. Prefer restrained, region-specific, partially transparent atmospheric layers when appropriate; protect faces, hands, text, truck geometry, horizons and authored composition. Visibility must be judged at *normal playback*, not by maximizing per-frame pixel-change scores.

### D06 — Verify music direction is real, not claimed

Pin the exact original song SHA, sample rate/channels, lyrics/music cue map, verified analysis evidence and beat/energy bus. Inspect whether FX/edits actually consume time-varying controls rather than fixed placeholder energy or repeated generic rhythms. The backend must not invent FX/music authority. Preserve original and any independently approved, byte-verified safety remaster as **separate** audio assets. Loudness and true peak are QC inputs; no automatic compression, EQ, stem changes, generated backing music, or soundtrack substitution.

### D07 — Watch the complete evolving edit

Audit full duration and shot boundaries against the locked script, narrative/music sections and accepted baseline. Check for repetitive long holds, identical shot cadence, weak emotional/visual progression, missing callbacks, broken axis/continuity, weak payoff, black/frozen/damaged frames, ghosting, flicker, changes at transitions, and inconsistent color/sun/weather. Use a frame-indexed contact sheet plus shot triptychs and measured motion/repetition as **diagnostic evidence**; they do not equal watching the entire film. Record whether review was sampled, segments, or entire film at normal speed. Never claim a complete watch if only samples or statistics were inspected.

### D08 — Compare candidates fairly and preserve a recoverable master

For any accepted baseline or defect-first recut, record PRE/POST visual and technical evidence with exact artifact locators/SHAs. Align *the same shot and same film time* for comparison. Compare source identity, protected regions, quality, musical timing, temporal motion and narrative quality; record both improvements and regressions. Do not promote a candidate solely because sharper pixels, more movement, a higher bitrate, or a cleaner numerical metric increased. If the user says "good with caveats", lock the accepted foundation; list caveats without silently escalating to a full restart.

### D09 — Direct the opening, closing, atmosphere and brand as first-class shots

Actual intro/outro frames must be watched and judged independently; generic placeholder title cards are not acceptable just because the film body works. Reuse approved project media, maintain authentic channel/artist names **exactly as user-supplied**, choose typography that suits the film, and leave a deliberate beat/pause only when authorized. No unrequested credit, thank-you message, ad, or unrelated landscape. If an intro delays the score or an outro extends playback, record the new absolute runtime and audio start/end, verify transition boundaries and silence policy, and protect the accepted core timeline. Restrained sky-light overlays must be spatially masked, translucent and consistent with source lighting, not a screen-wide spectacle.

### D10 — Export, sound and playable delivery are separate gates

Technical QC includes exact decoded frame count, nominal and actual fps, geometry, complete frame decode, audio coverage, intro offset, sample alignment, true peak/LUFS where relevant, unbroken end, hashes, and stable source-to-delivery lineage. Deliver one *directly playable* review copy of the **actual current candidate** with a durable URL, separate from the larger 4K master. Verify the link points to the right revision and that uploaded bytes/readback match when supported. If a provider enforces size limits, losslessly chunk the immutable master with per-part and joined SHA-256 plus a tested reassembly path; multipart packages alone do **not** satisfy the playable-review requirement. A later upscale is a new export requiring its own visual/audio QC, not automatically the identical approved MP4.

### D11 — Truthful verdict and handoff

Separate (a) automated technical PASS, (b) Director visual findings, (c) explicit user artistic acceptance/caveats, and (d) **authenticated production-release approval**, which remains governed by \`docs/PRODUCTION_RELEASE_GATE.md\`. A machine scan, assistant-generated review, or conversation message must not forge a user's GitHub acceptance token or whole-film-watch assertion. Report \`PENDING\`, \`REPAIR_REQUIRED\`, \`ACCEPTED_WITH_CAVEATS\`, or \`ACCEPTED\` only in the appropriate *artistic* context. Do not treat an independently reviewed local/FFmpeg master as a canonical runner-built release without the required backend equivalence and release evidence. The next executor receives exact input/output SHA, branch/commit, timing map, active caveats, permissible operations, checksum-verification steps, and a clear prohibition on modifying the locked film.

## Mechanical Director scan record

The reusable \`general/reusable/DIRECTOR_SCAN_RECORD.schema.json\` defines the **evidence structure** and \`general/reusable/tools/director_scan_gate.py\` validates completeness and internally consistent claims. The record belongs in the active song branch as \`DIRECTOR_SCAN.json\`, alongside receipts and actual-media proof. The gate is intentionally an **evidence validator, never an automated aesthetic judge or human-signoff simulator**.

Required checks: \`inventory\`, \`duplicates_and_provenance\`, \`source_fidelity\`, \`semantic_motion\`, \`fx_actual_and_relevance\`, \`music_and_audio\`, \`full_timeline\`, \`baseline_comparison\`, \`intro_outro_brand\`, \`delivery_playability\`, \`handoff_and_caveats\`. Every check carries a truthful status and concrete evidence for affirmative/negative findings. A PASS with no evidence, or a final acceptance claim made after only sampled viewing, must fail validation or remain explicitly pending.

## Decision table

| Observation | Director response |
|---|---|
| FX proofs exist but are low-resolution, 2 seconds, or loop-heavy | Audit original stills and all alternate media; source-led full-shot proof before rebuilding |
| Green workflow, weak picture progression | Keep technical PASS; creative \`REPAIR_REQUIRED\` with named scenes |
| Short transparent sky effect improves mood | Preserve approved geometry; region-mask and compare at normal speed |
| Motion demands vehicle/wheel/body articulation | Actual video or bounded continuation; no pretend zoom |
| Accepted full film has weak title card | Isolate intro/outro; protect core film and soundtrack |
| Source soundtrack already good | Optional conservative safety variant, source preserved and audibly compared |
| Correct master stored in pieces but review URL points to old candidate | Mark delivery pending, publish separate playable **current** review MP4 |
| User accepts with caveats and requests 4K | Lock artistic candidate, preserve caveats and hashes; 4K is a new separately QC'd delivery |

**Scope limit:** This canon is workflow law, not a default stylistic recipe. One production's night skies, truck, colors, brand, genre, prompts and story never become automatic authority for another production. Never silently choose artistic direction for a new song.
