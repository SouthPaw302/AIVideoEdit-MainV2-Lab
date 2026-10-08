# El Camión y la Carretera — MainV2 Lab

Route **2 — La Carretera Recuerda (hybrid)** is locked. Original stills remain byte-pinned and the attached WAV lineage is verified.

## Canonical FX inventory

- **Batch 01 / EC-01–EC-10**: 10 source stills, 10 24-fps MP4 loops, 10 GIFs, 90 derived PNGs. Technical PASS; visual QC pending.
- **Batch 02 / EC-11–EC-20**: 10 source stills, 10 24-fps MP4 loops, 10 GIFs, 90 derived PNGs. Technical PASS; visual QC pending.
- **Batch 03 / EC-21–EC-30**: 10 source stills, 10 24-fps MP4 loops, 10 GIFs, 90 derived PNGs. Technical PASS; visual QC accepted.
- Canonical artifact inventory: `FX_ARTIFACT_INVENTORY.json`
- Canonical runner IDs: 37745325544, 37745345877, 37757150942.

## Assembly gate

GitHub Actions run **37774234818** passed the all-batch assembly gate. It created a 30-second review assembly using all 30 FX plates, an editorial camera crop pass on environment-safe shots, and the verified original audio track.

- Review prerelease: https://github.com/SouthPaw302/AIVideoEdit-MainV2-Lab/releases/tag/lab-camera-review-37774234818
- Assembly receipt: `CAMERA_ASSEMBLY_37774234818_RECEIPT.json`
- Technical QC: **PASS**
- Human visual approval: **PENDING**
- Production complete: **NO**

## Motion boundary

FX loops cover environmental/practical-light motion. Shots marked continuation-required remain protected and do not receive false articulated motion. The final long-form film remains gated on human visual review and true-motion continuations or an approved assembly plan.

Current work remains isolated to `AIVideoEdit-MainV2-Lab`; the original `AIVideoEdit` repository is unchanged.
