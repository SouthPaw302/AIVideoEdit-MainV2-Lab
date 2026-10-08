# B03 Director shot-and-motion handoff — El Camión y la Carretera
## Locked visual route
La Carretera Recuerda — hybrid Appalachian noir. Existing weathered pickup, same interior, driver identity where visible, same letter and cold rainy mountain terrain. B03 moves from cobalt predawn to a tentative daylight, **not** a homecoming, porch concert, small-town excursion, or new subplot.

## Ten required source stills
21. **EC-21 — First cobalt sky**. Move mountain fog between fixed ridge lines; daylight appears gradually; truck and road geometry must remain rigid. Canonical FX loop can animate environmental motion.
22. **EC-22 — Rearview mirror**. All reflections confined to mirror glass; preserve reflection optic, no face/geometry shifting. True semantic continuation required separately; FX only atmospheric.
23. **EC-23 — Reservoir mist**. Only low-lying mist over water; shoreline and truck fixed. Canonical FX loop can animate environmental motion.
24. **EC-24 — Letter kept safe**. Folded letter unchanged; actual hand/glovebox action needs externally animated continuation. True semantic continuation required separately; FX only atmospheric.
25. **EC-25 — Still rolling**. Wheel must genuinely rotate in separate video; here only road spray/reflection changes. True semantic continuation required separately; FX only atmospheric.
26. **EC-26 — Bird line**. Fence and ridgeline fixed; true bird flight needs separately generated video. True semantic continuation required separately; FX only atmospheric.
27. **EC-27 — Temporary stop**. Mountain mist changes without altering parked truck or fixed overlook. Canonical FX loop can animate environmental motion.
28. **EC-28 — A human at dawn**. Realistic step-down motion requires true video; never warp limbs or cab door. True semantic continuation required separately; FX only atmospheric.
29. **EC-29 — The road goes on**. Mist in valley changes slowly; rock and road curvature cannot drift. Canonical FX loop can animate environmental motion.
30. **EC-30 — No fake resolution**. True vehicle departure is separate motion; no frozen truck masked by generic pan. True semantic continuation required separately; FX only atmospheric.

## Image-generator QC
Ten original **individual** independent 16:9 landscapes, not one 10-panel poster. Label images only by filename, not text inside pictures. Record generation model if known, actual dimensions, file SHA-256, and source/vehicle continuity reference. Reject composites, contact sheets, AI mush, divergent truck models, faces or props. Do not silently crop storyboard panels as substitutes.

## Source and runner status
The image generator returned storyboard **collages** rather than individual source plates during the first B03 request. Those remain **rejected for canonical input**. No B03 picture files or hashes were committed. `FX_BATCH_03.json` defines safe planned effects; `.github/workflows/camion-fx-batch-03.yml` is provisioned to run only when a future commit provides all 10 verified sources. Any manual dispatch before that must fail closed.
