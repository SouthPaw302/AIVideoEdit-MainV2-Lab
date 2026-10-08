# FX V2 Precompile Gate

## Why this exists

An effect name in a manifest is not evidence that the effect is actually present in the render path. AIVideoEdit treats FX verification as a hard compile dependency.

> This gate verifies that effects are real, wired, deterministic, and evidence-backed.
> A passing gate is necessary but not sufficient — it does not mean a shot is artistically finished or alive.

## Production render order

1. project declares exact FX IDs in a project `.fx.json` manifest;
2. production manifests declare `render_inputs`: the actual renderer/source-code files whose changes can alter the final pixels;
3. `precompile_gate.py` resolves every ID against `registry.json`;
4. the gate verifies implementation wiring/files, rejects stubs/placeholders, checks proof/QC records, verifies proof binaries when an addressable artifact path is recorded, and runs deterministic pixel/temporal smoke tests for runtime effects;
5. conditional/external technology requires explicit `allow_conditional` opt-in plus a technology-specific preflight JSON with `result: PASS`;
6. the gate writes schema-v2 `fx.lock.json` containing manifest/registry/runtime hashes, renderer-input hashes, implementation hashes, proof-record evidence, preflight hashes, smoke metrics, deterministic sample-output digests, and one complete evidence fingerprint;
7. immediately before the real render starts, the renderer verifies the lock again;
8. lock verification reruns the live checks and rejects any evidence mismatch.

Any schema-v1 lock is obsolete and must be regenerated.

## Proof truthfulness

A 64-character checksum stored in JSON is a declaration, not cryptographic verification of a binary that is unavailable.

Proof records therefore distinguish:

- declared proof checksum — preserved historical identity;
- byte-verified proof artifact — the referenced binary is addressable and its bytes match the declared SHA-256;
- live deterministic runtime evidence — the gate renders fixed samples from the current implementation and hashes the resulting pixels.

Approved runtime effects may use a human-approved historical proof record plus live runtime evidence. Approved adapter/external effects require byte-verified proof artifact(s), because the gate cannot substitute a synthetic runtime probe for an external implementation.

## Canonical runtime proof

`FX2_PROOF02_LIVING_SCENE_CANONICAL` is the active engine-level proof for the currently approved FX2 runtime effects. Its MP4 and contact sheet are stored under `general/reusable/fx_v2/proofs/`, the actual MP4 bytes are hashed by the gate, and the proof contains isolated locked-camera segments for each approved runtime effect followed by the combined stack.

`FX2_PROOF01_LIVING_TAVERN` remains historical lineage only. Its declared checksum is preserved, but its original binary is not addressable on `main`, so it is not active canonical evidence.

Proof02 approval is scoped to the reusable engine. It does **not** approve a song shot or final film; production shots still require their own artistic and exported-film QC.

## Fail-closed rules

The gate fails when any requested effect:

- does not exist in the canonical registry;
- is `proof_required`, experimental, rejected, or otherwise not `approved`;
- is conditional without explicit project opt-in and a PASS preflight record;
- exists in the registry but is not routed through the real runtime dispatcher or a real implementation file;
- resolves to empty/stub/placeholder/NotImplemented code;
- lacks an approved proof record when approval requires one;
- has an addressable proof binary whose SHA-256 does not match the proof record;
- is an approved adapter/external effect without byte-verified proof artifact evidence;
- produces effectively no pixel change in the runtime smoke test;
- is supposed to animate but does not change over time;
- causes excessive whole-frame translation when it is not a camera/spatial effect;
- is a transition that fails endpoint preservation or visible temporal evolution;
- uses a production manifest with no declared `render_inputs`;
- changes any locked manifest, registry, runtime, renderer input, implementation, proof, preflight, or deterministic sample-output evidence.

## What this does not automate

Pixel metrics cannot decide whether an effect is artistically good. Human visual QC remains mandatory before `gate_status` becomes `approved`, and final exported-film QC remains mandatory after assembly.

## Production command

```bash
python general/reusable/fx_v2/precompile_gate.py \
  --manifest projects/<song>/FX_REQUIREMENTS.fx.json \
  --lock-out projects/<song>/fx.lock.json
```

Then immediately before compile:

```bash
python general/reusable/fx_v2/precompile_gate.py \
  --manifest projects/<song>/FX_REQUIREMENTS.fx.json \
  --verify-lock projects/<song>/fx.lock.json
```

A non-zero exit code means **do not render**.

## Engine-test mode

`--engine-test` exists only for isolated reusable-system CI. It allows a fixture manifest without production `render_inputs`. Song production must not use it.

## Approval states

- `approved` — may compile after the gate passes.
- `proof_required` — implementation may exist, but production use is blocked until proof and visual/technical QC satisfy the promotion requirements.
- `conditional` — external/spatial technology such as real SuperSplat/3DGS; requires explicit opt-in and a hashed PASS preflight. It is never silently replaced by a 2D imitation.

## Camera rule

Ordinary environment/light/surface effects are checked for unintended global translation. Camera movement belongs to explicit camera/spatial logic and must be independently QC'd.
