# Irish Eyes MainV2 Lab — visual review pending

## Source and isolation
- Parent production repository: `SouthPaw302/AIVideoEdit` (**untouched**).
- Parent MainV2 source SHA: `316fe96c7316d76d14308d5f27293e071aa20943`.
- Lab code branch: `song/irish-eyes-lab`.
- Music: Irish Eyes (Remastered), from original source release with SHA verification.
- Picture inputs: verified raw Irish road, candle-window, and dark-lake clips. Finished music videos not reused.

## Technical execution evidence
- Lab workflow: https://github.com/SouthPaw302/AIVideoEdit-MainV2-Lab/actions/runs/37728597253
- Technical MP4: 30 seconds, 1280×720, 24 fps, H.264/AAC.
- MP4 SHA256: `1f78058e5066a0dfd472267cf7b5b27fd39c034b8eb7a03852884764adb2085a`
- FX IDs executed and lock verified: `FX2-LIGHT-001`, `FX2-LIGHT-002`, `FX2-MOTION-003`, `FX2-TRANS-025`.
- GitHub Action *overall* failed to publish a Release because GitHub returned **403** for release creation. Video rendering and technical QC passed; independent recovery and permanent Drive delivery followed.
- Lab surgical fix: preserve `.aivideoedit/models` across OS bootstrap; previous code deleted ONNX model and fell back from Beat This.
- Separate full lab compile/gate workflow PASS: https://github.com/SouthPaw302/AIVideoEdit-MainV2-Lab/actions/runs/37728657311.

## Durable playback and evidence
- MP4: https://drive.google.com/file/d/10R7FqoFJPb7wNVmhYZLF_i1fLJutFOwX/view
- Contact sheet: https://drive.google.com/file/d/1Exz53M-vBnO9_qkBR4vcDste8EH5SL3N/view
- Full evidence ZIP: https://drive.google.com/file/d/1CfLY5hrXfZUnDDDACBTqdZVjIkvV9Uai/view
- Folder: https://drive.google.com/drive/folders/1lHESPtIEnnlkRA_VlI11WJwO2kHIv4Iq

## Visual human gate
**PENDING / UNREVIEWED / NOT PRODUCTION APPROVED.**

No automated runner or tool can infer human acceptance. Evaluate whole video at normal playback: music sync, cuts, frame drift, camera motion, scenery identity, temporal discontinuities, lack of generic fillers. Record explicit ACCEPT or REJECT. Failure remains actionable lab evidence, not a reason to touch original production main.

## Known reporting blemish
The inherited general-purpose `technical_report.json` mislabels the source as "synthetic smoke" even though this specific video uses real Irish Eyes source music and raw video clips. The source audit and `result.json` establish actual inputs. Correct this lab reporter separately; do not retroactively change hashed render evidence.
