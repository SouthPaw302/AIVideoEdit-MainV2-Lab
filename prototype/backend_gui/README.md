# AIVideoEdit Studio — Browser-First Alpha Stack

A single-user browser-controlled production workstation. The browser is the normal human interface; the execution service can run on any suitable host. GitHub remains source control and the canonical AIVideoEdit system authority. Runtime media, processing, QC and optional external mirroring stay outside GitHub Actions storage.

## Architecture

Browser Studio / External Agent / Future ChatGPT App
-> Provider-neutral Tool API
-> Local workstation service
-> Isolated canonical AIVideoEdit core from current `main`
-> Per-project canonical `song/<slug>` production workspace
-> Worker queue / FFmpeg / reusable FX / guards / QC / storage

The browser is optional for agent-native use. An external agent with Git/sandbox access can still clone the public repository and operate AIVideoEdit directly.

## Run the browser workstation

From a host with Python, Git and FFmpeg:

```bash
python prototype/backend_gui/stack.py
```

Then open `http://127.0.0.1:8080`, or the host's LAN address from another device. `stack.py` binds to `0.0.0.0` by default.

Termux can host the same browser workstation:

```bash
cd AIVideoEdit/prototype/backend_gui
bash start_termux.sh
```

`server.py` remains the bare-alpha fallback. `stack.py` is the full runtime.

Environment overrides:

- `AIVE_HOST` (default `0.0.0.0`)
- `AIVE_PORT` (default `8080`)
- `AIVE_RUNTIME` (default `prototype/backend_gui/.runtime`)
- `AIVE_MAX_UPLOAD` (default 2 GiB)
- `AIVE_WORKERS` (default `2`)
- `AIVE_RCLONE_REMOTE` (optional external mirror target)
- `AIVE_CORE_AUTOBOOT=1` (optional background canonical-core load at startup)

## Canonical core adapter

The workstation branch is **not** treated as a production branch. Loading the production engine creates an isolated runtime checkout of exact current `main`, then runs that checkout's own `bootstrap.py` and current-main guard as `main`.

This provides the workstation with the canonical:

- production contract
- media capability matrix
- FX v2 registry
- reusable system files
- current production/narrative guards

The core cache lives under the runtime directory, not in the prototype source tree.

## Canonical project bridge

A browser project can be connected to the original production system without switching branches in the workstation repository.

`production.initialize` creates a separate local engine checkout for that project, creates its isolated `song/<slug>` branch, writes only a minimal `INITIALIZED` compatibility scaffold, and then runs the **real current-main production guard**. Later stage progression remains governed by the canonical project files and guards.

Unchecked or invalid production state is not promoted by the bridge.

## Tool API

`stack.py` exposes a provider-neutral machine interface intended to remain stable across browser, agent, hosted API and ChatGPT integrations:

- `GET /api/tools`
- `POST /api/tools/call`
- `GET /api/core`
- `POST /api/core/bootstrap`

Current tool families include:

- `core.status`, `core.bootstrap`
- `capabilities.list`
- `fx.list`
- `project.list`, `project.create`, `project.status`, `project.prepare`
- `production.initialize`, `production.status`, `production.guard`
- `media.list`, `media.prepare`
- `storage.status`, `storage.sync`

Tool call shape:

```json
{
  "name": "project.status",
  "arguments": {"project_id": "my-video"}
}
```

This is the seam a future ChatGPT App/plugin, external agent, MCP adapter or private hosted API can use without depending on Studio internals.

## Workstation features

- multiple persistent projects
- direct browser media ingest
- restart-safe project/asset/job state
- bounded configurable worker queue
- project-wide preparation
- SHA-256 asset identity
- FFprobe metadata inspection
- thumbnails and byte-range browser playback
- H.264/AAC proxy generation
- six-point review-frame extraction
- decode/integrity QC
- asset deletion with derivative cleanup
- project-scoped job history
- storage/disk/queue telemetry
- optional external project mirror through rclone
- canonical current-main core loading
- isolated canonical production workspace per browser project
- provider-neutral Tool API
- runtime media excluded from Git

## External storage

Local media remains authoritative during alpha. External storage is an optional mirror. Install/configure `rclone` and set `AIVE_RCLONE_REMOTE` to an R2/B2/S3-compatible or other rclone-supported target. Credentials remain outside browser JavaScript and Git.

## Verified work

The media path was exercised end-to-end in the development sandbox with H.264/AAC media: ingest, SHA-256, metadata probe, thumbnail, H.264/AAC proxy, six review frames, HTTP 206 playback, decode/integrity QC and project manifest all completed successfully. The bounded worker runtime was separately exercised with three preparation jobs submitted together; proxy, review-frame extraction and QC completed through two workers.

The new canonical-core/project bridge is deliberately fail-closed. This development sandbox could not DNS-resolve GitHub for a fresh branch clone during its final smoke test, so the repository does **not** claim that the new isolated current-main bootstrap/project initialization path has been externally executed here yet. It must pass its real bootstrap/guard on a networked host before that claim is made.

## Next build layers

- canonical source-ingest synchronization from Studio assets into the production project manifests
- stage-transition API that edits evidence first and then runs the guard
- scene/shot model and shot-package operations
- reusable FX execution through canonical registry IDs
- render/assembly orchestration
- final production QC/export
- agent chat/provider adapter in Studio
- MCP / ChatGPT App surface over the same Tool API
- authentication/TLS for public or monetized hosted use
