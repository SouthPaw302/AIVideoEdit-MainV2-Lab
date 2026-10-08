# DeepSeek Harness adapter prototype

This folder contains an optional provider-neutral Harness adapter for AIVideoEdit Studio. It does not replace the AIVideoEdit production
engine, contracts, guards, GUI, or branch model.

## Architecture

```
DeepSeek Harness session / agent loop
        |
        | MCP stdio
        v
prototype/backend_gui/aivideo_mcp.py
        |
        +-- harness.context / harness.status
        +-- provider-neutral AIVideoEdit Tool API
        +-- Director Brain operating tools
        |
        v
canonical AIVideoEdit core + project guard + media/render workers
```

The MCP server exposes the same operations used by Studio. Tool names are made
MCP-safe by replacing dots with double underscores, so `production.status`
becomes `production__status`. DeepSeek Harness adds its own server namespace,
for example `mcp__aivideo__production__status`.

## Safety / isolation rules

- Harness is opt-in (`AIVE_HARNESS_ENABLED=1`) and is not required for normal production.
- It must not mutate repository `main`.
- AIVideoEdit remains authoritative for production state.
- Canonical production guards remain in force.
- Harness state is orchestration/session state, not production truth.
- `harness__context` should be called before stage-changing work and after a
  successful stage transition so the agent re-anchors to current project state.
- No DeepSeek package is imported by the AIVideoEdit Python runtime. If DeepSeek
  Harness changes its plugin internals, the AIVideoEdit Tool API remains intact.

## DeepSeek Harness configuration

External Harness hosts may use the provider-neutral MCP stdio bridge. This dependency-free prototype bridge
intentionally serves the stable 2025-era MCP handshake over stdio; current Harness
clients can probe the 2026 era and fall back to supported legacy negotiation. Copy the adjacent
`cordis.patch.yml.example` into an experimental Harness profile and replace
`/absolute/path/to/AIVideoEdit` with the checkout path.

The adapter assumes Python can run the existing Studio backend. The Studio GUI
and the Harness may run at the same time, but they must point at the same
`AIVE_RUNTIME` if they are expected to see the same local workstation state.

Example Studio launch:

```bash
python prototype/backend_gui/stack.py
```

Example MCP smoke test:

```bash
python prototype/backend_gui/harness_selftest.py
```

The MCP process is normally spawned by DeepSeek Harness rather than started
manually.

## Why MCP instead of embedding DeepSeek APIs

MCP keeps the seam provider-neutral. DeepSeek Harness gets durable sessions,
agent-loop orchestration, permissions, and tool history while AIVideoEdit keeps
ownership of project state and rendering. Another compatible agent host can use
the same bridge later without changing the production engine.
