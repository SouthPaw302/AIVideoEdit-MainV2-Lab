# Director FX surgery — Candidate 03
Candidate 01 render SHA `fea3ec58e8bda229e72fab816370a716dbae92911c3ad55e36c3d7e58ae85512`; Candidate 02 render SHA `4cf9fa19793643f95f65de47572deb74b2240a95b8f03039a4c79e47fe9b006d`. Both full soundtrack and runtime unchanged.

## Actual Candidate 02 audit
- Full 282.833333s video assembled, 6788 frames at 1920x1080 24fps; decoded soundtrack PCM matches Candidate 01.
- Pacing revised, but long static/low-motion road and interior holds remain. Some shot movement was only 2–4 grayscale levels per 2 seconds.
- The original FX manifest attached indiscriminate rotating genre-mismatched effects: **crowd_sway** on driver/truck, **rotating_architecture_debris** on road/mirror, **particle_tunnel**, **runic_oscilloscope**, **radial_frequency_ring**, **spectrum_energy_flame** in narrative footage, and arbitrary fire/lightning transitions. They are individually registered effects but dramatically unsuitable here.
- Canonical render loop used constant `FXContext.energy=0.35` and `transient=0.1` even after ONNX analysis. This is an actual control-bus defect, not a music aesthetic preference.

## Candidate 03 bounded repairs
- Preserve all 32 original shot sources/URLs/hashes, their order, soundtrack WAV hash, title/end card, 24fps 6788-frame edited timeline, source library, and Lab main engine untouched.
- Replace shot-specific FX combinations with **approved** camera movement, nocturnal practical lights, atmospheric fog, rainy road reflections, bounded memory modulation, and restrained blue-hour grade shift, respecting protected identity and geometry.
- Use **structural morph / blend** transition generally, ghosted memory only on intentionally remembered passages, smoke-to-storm only on storm entry. Eliminate decorative overlays and unrelated spectacle.
- Replace constant energy/transient inputs with verified PCM frame RMS and pinned Beat This ONNX positions, bounded to [0.22,0.68] and [0.06,0.48]. Record music dynamics receipts in shard artifacts with hashes. No inference fallback and no source mutation.
- Require source-lock and unit-test gate before dispatching runner render. Following render, compare actual decoded film to both candidate baselines, including soundtrack, motion, continuity, story and effect visibility.

**Still NOT visually accepted, nor released.** This is source-locked director correction, not a claim of new footage or human acceptance.
