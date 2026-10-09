# Render history

The first three branch-only real-render attempts were rejected before completion while correcting canonical FX IDs and transition/effect namespace collisions. Run `37873177058` was deliberately cancelled after confirming that the serial renderer did not consume the live Director/Harness path; it produced no accepted candidate.

Next render target: full source-length candidate through the Director-gated parallel workflow using the exact original WAV, verified media storage, shared canonical FX lock, four picture shards with boundary transitions, and MainV2 engine checked out from `main` read-only by every job.
