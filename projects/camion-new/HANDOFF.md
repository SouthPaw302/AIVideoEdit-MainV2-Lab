# Director handoff

Boot and validate the current MainV2 Lab OS against `song/camion-new`. The user confirmed the genre/style authority as: “the same style as @MountainNoir but in Spanish.” Use the verified original WAV and exact lyrics as story authority. Use recovered generated stills and runner FX loops only with their recorded provenance; do not reuse the deleted branch's final picture.

Next order: run `.github/workflows/mainv2-director-parallel-real-render.yml` from `song/camion-new`. It boots the immutable MainV2 `main` engine, runs the live Director/Harness/JEV/FX/ONNX gate, fans out four verified picture shards, and muxes the original WAV once. Inspect the actual export, then run the mode-aware proof, FX lock, assembly, and final QC gates. Technical PASS is not human visual approval.
