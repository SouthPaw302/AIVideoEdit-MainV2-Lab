# Optional Runtime Opt-In

AIVideoEdit production workflows are resolved first and remain authoritative. Optional execution runtimes are disabled unless the active project's `OPERATING_ORDER.json` explicitly enables them.

The browser scene runtime uses the stable runtime id `browser_scene_runtime`.

```json
{
  "optional_runtimes": ["browser_scene_runtime"]
}
```

Rules:

- Absence of `optional_runtimes` means no optional runtime is enabled.
- Runtime discovery, installed packages, repository files, or capability availability never count as opt-in.
- Enabling a runtime does not select or replace a standard workflow. It only permits that runtime to be used after normal workflow resolution and director/shot planning.
- Browser-runtime production entry points search upward from the composition/project path for `OPERATING_ORDER.json` and fail closed unless the runtime id is explicitly present.
- An agent must not add the opt-in merely because the runtime exists. It may add it only when the active production intentionally chooses that backend for an already-resolved workflow or approved shot/layer.
- Projects that need current behavior should boot from current `main`; no migration of older project branches is required.
