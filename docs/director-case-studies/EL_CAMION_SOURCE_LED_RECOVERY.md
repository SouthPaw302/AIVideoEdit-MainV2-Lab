# Director case study — the source-led rescue of a complete music film

**Provenance only, not art-direction authority for future songs.** Current-main canonical method: [Director Scan](../../general/reusable/DIRECTOR_SCAN_CANON.md). Recorded 2026-10-10 from the independent source, FX, full-output and delivery investigations undertaken on `song/camion-new`.

## Production and artifact lineage

- Branch: `song/camion-new`; Lab `main` is the production OS, untouched by the song's iterative rendering work.
- Original 48 kHz stereo WAV SHA-256: `6789e6f3ea52501a0d4a151296a6ef7f8abc8516acd1f6cec959213a028ec0d9`.
- Candidate 01 SHA `fea3ec58e8bda229e72fab816370a716dbae92911c3ad55e36c3d7e58ae85512`, 6788 frames, 282.833333s, 1080p/24. **Technically valid, Director-rejected.** Near-uniform nine-second intervals, poor progression, too few meaningful scene changes.
- Candidate 02 SHA `4cf9fa19793643f95f65de47572deb74b2240a95b8f03039a4c79e47fe9b006d`. Scene pacing improved, but the source clips were still short, low-motion proxies.
- Candidate 03 SHA was recorded in the runner's verified receipts; [review-only runner 38018792605](https://github.com/SouthPaw302/AIVideoEdit-MainV2-Lab/actions/runs/38018792605) succeeded after scene-appropriate FX and frame-varying music controls. Its strongest outcome was a cleaner picture; reduced distracting visual activity did **not** solve the underlying source-resolution and articulated-motion limitations.
- Source-led Candidate 04 SHA `7a712c8aa459e4911c7ccb70eab7fea01b6bfe58a203234c4a082df69fb1433c`, 6788 frames, 1080p/24, 282.833333s. Locally composed from all 30 original stills + authorized actual FX archives and two true-motion continuations. This was explicitly **not** a canonical runner or FX-v2 equivalence proof.
- Final 1080p artistic finishing copy SHA `1bc4a7c3acf6d65154de4a74fe6a295296cb5851bfde90b89b5e8a09ad967e6f`, 178,592,477 bytes, 6980 frames, 290.833333s, 1920×1080/24. Retains core song scene order/timing, replaces opening/closing, adds selectively masked semi-transparent sky-light on six night scenes and incorporates the separately verified optional safety-master audio with a four-second silent intro.
- The current finished candidate was made directly playable as a separate 720p review copy because provider upload limits required the immutable 1080p master to be transferred in six SHA-verified parts. [Current final streaming review](https://drive.google.com/file/d/1Rqd-UZ6MU8VHFCb2I_4YIo0NTdzuu5yu/view?usp=drivesdk). Its lower resolution is a **viewing derivative** and must not be substituted for the high-resolution 1080p master.
- Exact source/safety-master/transfer receipts and original stills remain in the private, pre-existing production Drive hierarchy. Their private per-file IDs do not belong in this reusable case study. Final compiled export QC explicitly reported `TECHNICAL_QC_PASS_PENDING_USER_FINAL_VIEW`; the subsequent user's in-chat wrap is artistic acceptance **with retained motion caveats**, not the authenticated GitHub release token.

## What the Director's real scan found

### Underused media library

The project already held **30 original 1672×941 PNG stills**, three FX batches containing 30 two-second **640×360/24fps** animated MP4 proofs, 30 corresponding GIFs, 270 FX-derived PNG frame variations and 30 execution ledgers. Additional previously generated 10-second actual-motion clips existed for two early truck/cab shots. These were **not missing assets**—they had been overlooked by the finishing route.

Scanning Drive folders alone did not establish consumption. The low-resolution loop SHA-256s were cross-checked against the exact referenced release sources. The original stills were byte-verified. The two repeated filenames in the first still batch were found to have **byte-identical content**, not meaningful alternate visual versions; copies were preserved. ZIP archives additionally duplicate source images intentionally as backups.

### Wrong source class in the full-film picture

All **30/30** loop clips were only two seconds and were being repeated over longer scenes. The full film scaled the 640×360 FX proofs to 1920×1080; that is a **3× source-resolution increase per axis**, not three times more detail. The standalone [Director FX source audit](https://github.com/SouthPaw302/AIVideoEdit-MainV2-Lab/actions/runs/38020413551) reproduced the issue: 30/30 low-resolution/repeated proofs and eight especially low motion results under the runner's metric. Machine audit PASS meant the evidence was collected, **not** that picture was approved.

The source-led repair restored the original still as the picture foundation and used short FX footage as an atmospheric reference, improving measured same-position detail by ~41% median over 14 sampled shots. The measured value is a texture indicator, **not** an aesthetic score.

### Scene-mismatched FX and fake movement

Earlier effects included overt crowd/particle/spinning/fire-like treatments unrelated to a restrained road narrative, even though many were registry-supported. The renderer also hard-coded a constant `energy=0.35` and `transient=0.1` for each frame, despite available verified music analysis. A later review aligned per-frame energy and transient with pinned original WAV and ONNX evidence and chose physically appropriate fog/rain/glow/reflections instead.

Optical pans and light effects were not misrepresented as walking, wheel rotation, moving road perspective, or body articulation. Six late-story shots still carried true-video requirements; those continued as named caveats after artistic acceptance.

### Titles, branding, audio and delivery

A technically successful export carried unacceptable title cards. After the user approved the body of Candidate 04, the Director protected the core edit and built a separate bounded finishing derivative: opening pause, correct user-provided channel spelling, subtle transparent outdoor-night-sky light and closing. Source WAV was already not clipped; an optional safety remaster added only conservative gain and was preserved separately with actual audio measurements. Original remained the unaltered source of truth.

A Drive link to **Candidate 04** was mistakenly offered when the user asked to watch the **new** final render. The Director corrected that by comparing title/outro boundary frames and providing a single directly playable current export, while keeping the 1080p original transferred losslessly. This is a delivery identity and human-verification failure, not a codec failure.

## Canon distilled from this case

1. Scan original source media and **all** derivatives/alternates before a regeneration decision.
2. Track source still versus FX proof versus complete temporal footage as different asset classes.
3. Verify native dimensions, loop duration, hashes, and actual effects **consumed** by the output.
4. Inspect subject-specific semantic motion, not just global pixel differences or camera drift.
5. Use music timing and lyric/section intent as actual controls, not static or unconsumed analysis.
6. Compare the same moments of baseline and candidate, preserve full film and original score when user says "good with caveats".
7. Treat titles, visual branding, mask-bounded atmosphere, timing and optional safety audio as controlled finishing.
8. Always verify the exact current version of a playable review link before claiming delivery.
9. Separately gate technical export, Director observations, user artistic acceptance, and authenticated final production release.
10. Promote only **method**, not this production's imagery, storytelling, aesthetic, or identity, into the permanent OS.

**Important status:** The user's conversational acceptance is not evidence of the GitHub release gate's required authenticated normal-speed whole-film watch, nor evidence that 4K upscale or YouTube upload occurred.
