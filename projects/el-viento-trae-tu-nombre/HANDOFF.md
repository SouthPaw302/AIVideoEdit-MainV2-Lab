# El Viento — NEW DIRECTOR handoff (active)

This replaces all prior preservation-only / missing-FX-only instructions on this Lab song branch.

**The user wants an entirely NEW PRODUCTION, not a faithful re-edit.** The next Director has full freedom over story, editing, shots, characters, artwork, motion, FX, and even a radically different picture. The finished published film is a high-quality creative **reference / benchmark**, not a locked script. The old Route 4 original remains preserved in Git and Drive and must not be overwritten.

## Mandatory boot first

```bash
git fetch origin main song/el-viento-trae-tu-nombre
git switch song/el-viento-trae-tu-nombre
git pull --ff-only origin song/el-viento-trae-tu-nombre
python bootstrap.py boot --repo-root . --branch song/el-viento-trae-tu-nombre
```

**Require `AIVideoEdit OS BOOTSTRAP: PASS`.** The bootstrap fetches and materializes the exact current `main` into `.aivideoedit/os/`, while all writes remain on this **song branch**. Do not merge `main` into the branch merely to get a fresh OS, and never edit `main` for this production.

Read `.aivideoedit/os/PRIME_DIRECTIVE.md`, `.aivideoedit/SECOND_BRAIN.md`, and `.aivideoedit/os/SOUL.md` in order. Then read **[NEXT_DIRECTOR_START_HERE.md](NEXT_DIRECTOR_START_HERE.md)** and **[NEXT_DIRECTOR_HANDOFF.json](NEXT_DIRECTOR_HANDOFF.json)**.

Run bootstrapped project production/narrative/recut/workflow guards before state-changing work. **Stage is INITIALIZED for the new film**; legacy Route 4 statuses and original shot files are historic material, not proof of the new film.

No render, new media, or publication was started by this handoff. The NEXT agent is empowered to begin new production under normal system gates. Do not destroy the original film or replace its published Drive masters.

**Do not follow the archived 2026-09-25 "no restart / FX-only" instruction; the user's explicit 2026-10-10 new-Director order supersedes it.**
