# Local-agent status handoff — Batch 03 (EC-21–EC-30)

**Purpose:** Resume existing work without duplicating, regenerating, rerendering, re-uploading, or resetting anything already completed. This is a status-only handoff. Its commit does NOT approve visuals, lock media, or trigger a render.

## Authority and scope

- Repository: `SouthPaw302/AIVideoEdit-MainV2-Lab`
- Only working production branch: `song/el-camion-y-la-carretera`
- Project: `projects/el-camion-y-la-carretera/`
- Production: **El Camión y la Carretera**; locked route **La Carretera Recuerda**.
- No writes to `main`, `MainV2`, or original `SouthPaw302/AIVideoEdit`.
- Honor existing `LAB_PROTOCOL.md`, `PRIME_DIRECTIVE.md`, `SOUL.md`, project operating order, zero-drift and Batch-10 QC/approval gates.
- This handoff was assembled from GitHub/Drive connector readouts on 2026-10-08; **another local agent may already be ahead**. Reconcile actual current state, never downgrade it.

## Proven existing work; DO NOT REDO

1. Batch 01: EC-01–EC-10 original source stills; successful GIF/MP4 FX runner; user-approved 36-second Gemini-integrated workprint. Existing manifest, receipts, Drive artifacts and approvals remain authority.
2. Batch 02: EC-11–EC-20 source stills; FX technical PASS (10 MP4, 10 GIF, 90 derived PNG) at https://github.com/SouthPaw302/AIVideoEdit-MainV2-Lab/actions/runs/37745345877 ; durable proof ZIP, review reel and contact sheet on Drive; FX human visual QC last recorded as pending. Do not claim approval without user evidence.
3. Batch 03: **10 original individual PNGs (EC-21.png through EC-30.png) already exist on Google Drive**. Do not generate replacements. They are in:
   https://drive.google.com/drive/folders/14kXuEbIDQoSCtN22EgrFRumqiIaom314
   - Original PNG ZIP: https://drive.google.com/file/d/11LPdXgRHu-r9fqGtJgtukw67PrJlLVuG/view
   - Review sheet: https://drive.google.com/file/d/1I67cd_7iu16LBQ_b0IQUud_l8Hac21Ec/view
   - Per-shot instructions: `BATCH03_DIRECTOR_BRIEF.md`, `FX_BATCH_03.json`, `SHOT_PROMPTS_BATCHES.json`.
4. User states that another agent/runners have been working on Batch 03 and tasks may already be complete. **Check local working tree, existing artifacts, Drive, Actions and newest remote SHA before deciding anything is missing.**

## Last observed GitHub snapshot (not necessarily current local reality)

- Song-branch commit: `c470a34a115592298c70ec1041405050e56589da` (2026-10-08 07:57:08 UTC).
- Latest visible Batch-03 FX run: https://github.com/SouthPaw302/AIVideoEdit-MainV2-Lab/actions/runs/37746537832
- Run result: FAIL at pre-render source gate: `projects/el-camion-y-la-carretera/media/batch_03/source/EC-21.png` absent in that run's checkout, before animation or encoding. This is **not** a claim that the image does not exist: it is positively present in Drive.
- At that branch SHA, recursive Git tree showed no `media/batch_03/source/` files and `FX_BATCH_03.json` still had null source hashes. The connector listed no later Batch-03 FX run. These observations can be stale relative to local ongoing work.
- Batch 03 workflow: `.github/workflows/camion-fx-batch-03.yml` — auto-trigger on source directory changes, fail-closed if sources/hashes are not verified.
- Batch 03 FX proofs were not found in the inspected production Drive folder `05 FX and Motion Proofs` as of the connector read. Search other durable locations/local output before making any absence claim.

## Instructions for local agent (strictly surgical)

1. **Read first, no mutation:** Fetch remote, inspect current branch HEAD, Git status, pending work, relevant manifests, local output folders, GitHub Actions, and current Drive deliverables. Preserve uncommitted or ongoing changes. Compare with this dated snapshot.
2. **Inventory outputs:** For EC-21–EC-30, record which original PNGs, SHA-256 digests, canonical FX parameters, derived PNGs, MP4s, GIFs, QC receipts, contact sheet, review reel and Drive references already exist. Verify real bytes and QC reports, not just filenames or green CI.
3. **If complete:** DO NOTHING to assets or runners. Record confirmed technical and visual-gate state and supply links, job ID, source commit SHA and artifact SHA-256. Do not rerun or regenerate.
4. **Only if an actual missing integration step is proven:** Use *existing* individual Batch 03 originals (not collage crops) from the Drive source folder/ZIP; hash each; safely reconcile manifests and paths on the existing song branch without replacing any accepted image. Do not trigger FX until all 10 source hashes resolve. Avoid competing with an active local agent.
5. **Only if true FX outputs have not already been produced:** Allow the existing source-path workflow to run after correct source integration. Inspect runner logs/QC and save durable proofs on Drive. No placeholder green status, no self-signoff.
6. Respect the separate **human visual approval gate**. A technical FX PASS alone does not authorize final assembly or production acceptance.
7. Return a concise final report: exact current HEAD SHA, FX runner run ID/status, inventory counts (stills, derived PNG, GIF, MP4), source/proof paths, what was actually changed, any blockers, and the next *uncompleted* step.

**Non-negotiable:** No new images. No duplicate batch. No unnecessary commits, uploads or deployment. No original-main modifications. Resolve discrepancy between Drive assets and the previously inspected Git checkout, without assuming an earlier agent failed to finish.
