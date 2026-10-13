# Prototype AI — Qwen3-VL experiment (not canon)

**Branch:** `prototype/ai`. Main, all song branches, and the original
`AIVideoEdit` repository are unchanged.

## Goal

Replace the Director's artificial `harness.specialist_fixture: COMPLETE` on
this test branch with real, local, multimodal CPU inference. We selected
`Qwen/Qwen3-VL-2B-Instruct-GGUF` provisionally after a second opinion. This
is a feasibility experiment, **not** a claim of real-video QA accuracy.

- The prototype adapter is `scripts/prototype_ai_specialist.py`.
- The isolated Director gate requires a valid real-model receipt and refuses
  a missing model, projector, executable, source clip, or parseable result.
- The model examines 3 time-stamped real extracted frames from the **first
  authorized source clip**, before final render. It cannot thereby claim
  whole-film viewing, actual motion continuity, temporal coverage of every
  shot, or artistic approval.
- Evidence includes the input clip/frame hashes, model, projector and executable
  hashes, model stdout/stderr, and elapsed inference time.
- JEV receives a bounded model-observation check, not free-form authority.
- The original release gate and human normal-speed review remain mandatory.

## Model environment

The experimental branch of the existing registered
`.github/workflows/mainv2-director-parallel-real-render.yml` checks out
`prototype/ai` as the engine, builds llama.cpp's multimodal CPU CLI and
downloads the official GGUF Q4_K_M **and separate Q8 vision projector** at a
pinned Hugging Face revision. A new optional
`.github/workflows/prototype-ai-qwen-proof.yml` can independently evaluate
a SHA-256-verified 10–30 second GitHub release candidate if the workflow becomes
available for manual dispatch.

To execute the *actual film* workflow, use GitHub Actions, select the existing
Canonical Production Candidate workflow, choose the **prototype/ai ref** in the
Run workflow branch picker, and provide the exact authorized `song/<slug>` or
`project/<slug>` branch, project directory, manifest, and shard size.
This is an experimental prerelease route, never a final-film release.

## What counts as proof

1. Confirm all real input bytes match declared SHA-256.
2. Confirm both real Qwen weight files loaded and a process generated an actual,
   non-empty, non-canned model response.
3. Save raw runtime output, source frame hashes and executable/model hashes.
4. Independently inspect the response against the visual source. Confirm that
   **later frames**, not just the first, influenced the output; a historic
   llama.cpp multimodal CLI issue ignored subsequent images.
5. Report actual runner peak RAM, disk, elapsed seconds, throughput and any
   image-input limitations. Model file size is **not** peak RAM usage.
6. Complete a real short production and inspect the decoded MP4 before claiming
   visual success; JEV PASS means only a technical gate passed.
7. No automatic human approval; unsupported or inconclusive runs are failures
   or review-pending, never promoted.

## Verified so far

Only the **branch and implementation commits** are established by this work.
No new Qwen Actions inference run or full production render has been executed or
verified yet. The earlier main-branch model (Beat This!) and parallel render
receipts do not prove Qwen works.

Official source: https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct-GGUF
