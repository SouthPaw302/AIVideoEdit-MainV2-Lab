# Verification requirements

Each promoted effect must remain callable, deterministic for a fixed input/seed, visibly different from its source, visibly temporal across sampled times, and represented in the committed verification record. CI fails if the promoted effect count, alias coverage, or per-effect verification changes unexpectedly.
