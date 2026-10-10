# AIVideoEdit MainV2 Lab — Audit #11 Agent Repair Handoff

**Status:** READY / NOT STARTED · **Date:** 2026-10-10  
**Authority:** [Audit #11](https://github.com/SouthPaw302/AIVideoEdit-MainV2-Lab/issues/11) and its [verbatim source assessment](https://github.com/SouthPaw302/AIVideoEdit-MainV2-Lab/issues/11#issuecomment-6094222179)  
**Snapshot:** protected `main` `c2d20d888316e6fdcbcfe23bed508867c711149f`  
**Related:** [Director canon PR #10](https://github.com/SouthPaw302/AIVideoEdit-MainV2-Lab/pull/10) (open, **not merged**); `song/camion-new` locked Candidate 04 and separately finished artistic master.

## Entry / non-negotiables

1. Boot the **current** `main` per `AGENTS.md`: `python bootstrap.py boot --repo-root <repo>`. Read `PRIME_DIRECTIVE.md`, generated `SECOND_BRAIN.md`, and `SOUL.md`. Verify current `main` against the snapshot; if it moved, reconcile before work.
2. Read Audit #11, this plan and `docs/MAINV2_REMOTE_BRIDGE.md`. The authenticated HTTP remote bridge offers **tool calls, not a persistent task inbox**: the durable GitHub issue/comment + this branch are the handoff bridge. Never assume a live remote-agent connection.
3. Work **one numbered packet at a time**, on a new isolated repair branch from current `main`. Reproduce issue, add regression tests, make minimal changes, run unit/integration and applicable GitHub Actions checks, then open a bounded PR. Report head SHA, failures, test URLs and next packet in Audit #11. Never push directly to protected `main` or bypass review. No blind large rewrite, dockerization, deployments or unrelated refactor.
4. **Do not touch** the approved El Camión Candidate 04, final-artistic 1080p master, safety WAV, Drive media, `song/camion-new` creative timeline, or source `SouthPaw302/AIVideoEdit`. The 4K master and YouTube upload are a separate local-agent delivery; no re-render or upload in this audit.
5. Report confirmed behavior separately from static risks. GitHub branch-protection required checks were **reported absent but API returns 403**; release YAML **does declare** `production-release`, but environment reviewer settings are unknown. Never make a false "verified" claim.

## Repair packets — execute in order

| Packet | Scope and minimal deliverable | Exit gate |
|---|---|---|
| **01 — Secure workstation** | Audit #11 `SEC-01/02`: default to loopback; protect all mutating/read-sensitive GUI endpoints consistently; deny static path escapes, encoded traversal and symlink escapes; preserve authenticated remote Tool API. | Negative unauthorized-client and traversal tests pass; authorized Studio + bridge still work; no internet exposure for tests. |
| **02 — Restore governance** | `GOV-01`, PR #10: verify required `main` status checks and `production-release` environment reviewers **in GitHub Settings**; record missing permissions; arrange independent approval of existing Director Scan PR. | Required checks, reviewer policy and merge status evidenced with authoritative settings; no self-approval or branch protection bypass. |
| **03 — Repair source-to-release lineage** | `REL-01/02/03`, `REN-03`: secure hash-pinned original-media staging; pin engine/project/manifest/toolchain SHA before shard fanout; validate each shard and join identity; correct audio SHA semantics; reconcile parallel receipt, release-tag and canonical release gate. | Representative read-only media test shows **same real source bytes and immutable SHAs** at gate → shard → fan-in → release preflight; negative stale/missing/wrong-hash tests fail closed. |
| **04 — Make render pipeline generic** | `REN-01/04/05`, `OPS-01/02/03`: manifest-derived arbitrary shot-count shards, isolated concurrency, non-destructive package rebuilding, one documented canonical workflow surface, pinned dependencies, least-privilege publishing. | 1/9/30/32/33-shot fixtures cover every frame exactly once; independent jobs don't cancel each other; failure retains prior accepted packages; no unreviewed write authority. |
| **05 — Prove music/FX/continuity** | `FX-01/02/03`, `REN-02`, `QC-01`: drive FX from measured time-varying audio controls, reject low-resolution short-loop substitution as finished footage, prove *visible and appropriate* FX and true subject motion, inspect every transition boundary. | Golden media tests for motion, source resolution, loop repetition, FX-before/after/protected masks, sound alignment, transitions; numerical measures **never** auto-grant artistic acceptance. |
| **06 — Close creative delivery gaps** | `DEL-01/02`, `OPS-04/05/06`: reconcile *metadata only* from approved Camión final 1080p into a song-specific handoff (without touching media), establish explicit artistic vs technical vs GitHub-authenticated release states, archive hashes/playable current review link, intro/outro/audio offset and later 4K derivative lineage. | Exact final-master SHA/format/audio/playback URL matches actual Drive files; no stale Candidate 04 link; 4K path can't reassemble core film; independent final human release authority remains mandatory. |

## Agent report contract (after each packet)

Post a concise progress comment to [Audit #11](https://github.com/SouthPaw302/AIVideoEdit-MainV2-Lab/issues/11):
`PACKET | STATUS (PASS/BLOCKED/FAIL) | repair branch | source/head SHAs | PR URL | reproduced evidence | regression/Actions links | unresolved risks | next action`.
Do **not** mark the parent audit solved until all six packets and cross-packet full-movie proof are reviewed. Don't silently promote experimental material to `main`.

**First task:** Packet **01** only. Inspect `prototype/backend_gui/stack.py` and `server.py`; reproduce endpoint access and path-boundary behavior in a safe isolated test; produce a narrowly scoped security PR.
