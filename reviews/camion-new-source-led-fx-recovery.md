# Director finding — Source-led FX recovery (2026-10-09)

**User correction:** The original stills must be enhanced with the FX loop pass and extra media already present in the Google Drive production folders. Do not substitute still references with invented media.

**Drive sources inspected:** 30 original 1672×941 PNG stills (dimension sampled on EC-05 and EC-22); Batch 01/02/03 ZIP proof archives containing 30 MP4 loops, 30 GIFs, 270 derived PNGs and per-shot FX execution ledgers. Each archived MP4 is exactly **2.0 seconds, 640×360, 24fps**, not a full-resolution production shot. Existing Lab final exports upscale these to 1920×1080 and repeat them for longer intervals.

**Motion sampling:** 30 decoded proof loops evaluated at quarter-second intervals (320×180 grayscale). 11/30 exhibited average inter-sample motion under 0.5/255. These are watchlist measurements, not universal artistic failure criteria. Batch 03 explicitly reports human visual QC pending and true-video-required for EC-22, EC-24, EC-25, EC-26, EC-28, EC-30.

**Root cause:** Lab's real renderer consumes short, low-resolution FX proofs as the final scene picture, then applies additional FX/transition overlays on 1080p frames. No high-resolution, source-led full-shot motion pass is present in the actual approved render path.

**Recovery direction:** Freeze Candidate 03 and all hashes. Audit exact source provenance; stage private original stills securely to runner (never publish their Drive IDs or assume public Drive access); execute high-resolution canonical FX at full shot duration with mode-aware Director constraints. Reuse existing derived FX variations for reference. Integrate available EC-03/EC-04 true-motion continuations only after preserving source provenance and visual continuity. No claim that optical parallax supplies actual truck/wheel/character articulation. Reject automatic final artistic acceptance.

**Local representative proof:** 14 seconds from privately retrieved high-resolution EC-05 and EC-22 originals, proportional source-derived camera motion and bounded practical-light treatment; independently inspect against release 640×360 proof. **It is an exploratory proof only**, not an authorized replacement or finished production.

**Quality gate:** New `director_fx_source_audit.py` runner job verifies 30 SHA-pinned release loops and measures dimensions, repetition, motion indicators. It records the exact deficiency. A release mode can fail closed on low-resolution source. The complete source-led render cannot claim PASS until authenticated high-resolution Drive originals have been staged into the execution environment.
