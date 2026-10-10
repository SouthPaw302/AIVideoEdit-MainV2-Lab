# AIVideoEdit

Canonical production operating system for dynamic long-form music films.

## Universal start
**Every new agent/session starts by running the OS bootstrap:**

```bash
python bootstrap.py boot --repo-root <repo>
```

Do not begin production by merely reading docs. The bootstrap loads the entire exact current `main` into `.aivideoedit/os/`, runs the current-main production guard, and creates a session attestation plus generated second brain.

Portable entry point:
`bootstrap.py`

## Repository law
- `main` is system-only: doctrine, contracts, templates, reusable capabilities, proofs, QC, runtimes, and indexes.
- Every production lives on its own `song/<slug>` branch.
- A new supplied audio master creates a new `song/<slug>` from current `main` unless the user explicitly names an existing branch to continue.
- Production media/story/prompts/status/manifests/renders/QC stay on that branch.
- Reusable discoveries return to `main` only after project-neutral extraction, proof/QC, and canonical registration.
- Historical chats, unrelated song branches, prior storyboards, prior art direction, and production media are not production authority unless the current user explicitly authorizes them.

## Runtime authority
- `bootstrap.py` — portable sandbox bootstrap; materializes exact current-main OS.
- `SOUL.md` — permanent project identity/invariants.
- `general/reusable/AIVIDEOEDIT_OS_MANIFEST.json` — critical OS attestation manifest.
- `general/reusable/PRODUCTION_CONTRACT.json` — machine-readable production state/rules.
- `general/reusable/tools/production_guard.py` — fail-closed state/session validator.
- `general/reusable/MEDIA_CAPABILITY_MATRIX.json` — production media capability contract.
- `general/reusable/fx_v2/registry.json` — callable FX authority.

The docs explain the system. **The bootstrapped runtime and guard determine whether production may proceed.**

## Canonical Director scan
The production OS includes `general/reusable/DIRECTOR_SCAN_CANON.md`, a source-to-export investigative checklist made canonical after real-film recovery. It checks original assets and FX variants, source-vs-proof fidelity, real temporal action, music/FX relevance, accepted-baseline preservation, intro/outro/brand accuracy, audio and playable delivery. Records belong to the song branch; `general/reusable/tools/director_scan_gate.py` validates evidence claims but **cannot grant artistic or release approval**.

## MainV2 Lab implementation (2026-10-08)

This checkout is the **target** system: source lineage `AIVideoEdit/main → AIVideoEdit/MainV2 → AIVideoEdit-MainV2-Lab/main`. The original `MainV2` SHA is preserved as immutable import provenance; the **lab's own main** is now the bootstrap and render authority. The updated MainV2 models, FX, JEV, director system, GUI backend and tests are retained.

The inherited workflows remain available in `.github/workflows/`, but there is one operator-facing candidate route: **AIVideoEdit — Canonical Production Candidate (Director + Parallel)**. Run it with a locked `song/<slug>` or `project/<slug>` branch, project directory and SHA-pinned manifest. It resolves one immutable lineage, derives the shard matrix from the actual shot count, runs Director/Harness/JEV/FX/ONNX gates, and publishes a **review-only** prerelease. The single-runner, fixture, proof and harness workflows are compatibility or verification surfaces, not production entrypoints.

Read [Lab Render Operator](docs/LAB_RENDER_OPERATOR.md) for the exact input contract, Batch-10 + FX process, runner list and acceptance/delivery gates. `main` remains system-only; actual song work stays scoped to its own branch and approved media. Never modify the original AIVideoEdit repository from this lab.

## Production release authority (Issue #4)

No proof, technical PASS, short fixture, FX loop, or prerelease is a finished film. The full `general/reusable/PRODUCTION_CONTRACT.json` is the top-level authority. Final/master/archive/4K outputs are denied until `scripts/release_gate.py` verifies complete original-song and primary-media coverage, current source+engine and artifact hashes, measured time-varying music controls, visible locked-FX and motion evidence, transition continuity, actual decoded export, and authenticated human visual approval. Numeric visual QC is evidence only and can never grant artistic approval. The only GitHub final publish workflow is `.github/workflows/production-final-release.yml`, invoked manually after the proof and approval. GUI final QC and archives also require matching `RELEASE_GATE.json`. [Full release procedure](docs/PRODUCTION_RELEASE_GATE.md).
