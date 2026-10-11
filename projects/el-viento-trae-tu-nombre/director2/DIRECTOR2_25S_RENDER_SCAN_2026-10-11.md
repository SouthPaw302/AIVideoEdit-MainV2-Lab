# Director2 — Actual MP4 Scan (2026-10-11)

**Decision: REJECT for final-film use. Technical FX concept is proven, but visual gate fails.**

### Media identity
- File: `Director2_Canonical_FX2_LowRes_to_HiRes_Memory_10Shots_25s.mp4`
- SHA-256: `9d33f20c0a42e60ecf36e2417830f88cbd486077b243e25c278c39553bd80614`
- Proof: https://drive.google.com/file/d/14sVFqGUxGH-daWdoAS9Y7eyLfEG1iP0i/view
- 25 s, 600 decoded frames, 24 fps, H.264 640×360, stereo AAC 48 kHz

### Scope: what was ACTUALLY checked
- Decoded **all 600 frames** programmatically for near-static frame runs, black frames, and frame-to-frame changes
- Inspected **50 displayed image samples** spanning all 10 source/transition/destination shots
- Compared the 10 endpoint images pairwise for duplicates
- Analyzed audio stream levels and silence; did **not** conduct full normal-speed audiovisual listening
- Did **not** inspect original 1080p source files to prove any detail recovery

### Findings
1. **FAIL: near-frozen tails on all 10 transitions.** Each 2.5 s segment contains approximately **0.83–0.88 s of near-static destination frame**. This violates the living-scene motion expectation.
2. **FAIL: destination-frame repetition.** Ten transitions resolve into only **approximately three visibly distinct endpoint compositions**:
   - S01, S02, S03, S08, S09
   - S04, S07
   - S05, S06, S10
   Matched groups have low endpoint image MAE, about 2–4 grayscale levels at reduced sampling, despite different opening scenes.
3. **FAIL: compositing across protected figures.** Coastline/architecture/bright horizon layers visibly cut across faces and bodies during multiple memory dissolves. This is not identity-safe masked compositing.
4. **NOT FINAL RESOLUTION.** Though transitions end on photos originating at higher resolution, **the exported video remains 640×360**. It is not a 1080p detail restoration.
5. **PASS technical sanity:** all frames decoded; no entirely black frames; audio codec/stream present, approximate audio peak -3.9 dBFS, RMS -16.5 dBFS.

### Director2 mandatory fixes
- Replace repeated endpoints with unique, shot-specific, continuity-safe high-resolution plates.
- Sustain appropriate environmental motion to the last frame or shorten holds; do not solve freeze with whole-frame zoom.
- Use semantic/protected-region masking: no coastline, horizon, or structures projected across faces and anatomy.
- Render new real FX2 execution receipts and proof; inspect actual exported picture, including a full normal-speed viewing pass, before declaring an artistic pass.

**Creative approval:** NO. **User visual intervention:** NOT YET NEEDED. **Protected main and published master:** untouched.
