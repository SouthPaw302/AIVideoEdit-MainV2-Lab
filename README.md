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
