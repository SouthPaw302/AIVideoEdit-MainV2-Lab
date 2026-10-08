# Standard Workflow Library

These are project-neutral production workflows available to every production. The resolver selects them from the active production mode and `MEDIA_PLAN.json` capabilities. Historical production names are not runtime identities and are intentionally absent.

Authority: `STANDARD_WORKFLOW_REGISTRY.json`. Resolver: `tools/workflow_resolver.py`. Guard: `tools/workflow_guard.py`.

Default workflows always preserve reversible project state, cache invalidation, deterministic resumable delivery, machine-readable QC, and professional audio post/QC. Conditional workflows cover reference-motion calibration, restoration, source-derived looping, music-directed section assembly, profile-driven living-scene treatment, generated cinema, 2.5D/NeRF/3DGS, compositing/mattes/rotoscoping/tracking/cleanup/stabilization, procedural FX, retiming, localized master repair, and nested timelines.


FX resolution is a default workflow. Before scene-level FX requirements are authored, agents should run the accepted batch/scene/still semantics through `fx_v2/fx_resolver.py` or the harness `harness.fx_resolve` tool. The result is advisory for creative judgment but authoritative for registry discovery: agents must not skip the current canonical library and invent project-local substitutes merely because they did not look.

For music-led Director Brain v3 living-scene or hybrid work, the section-assembly workflow is mandatory after approach lock. It is evidenced through `RENDER_RECIPE.json`, `MUSIC_CONTROL_MAP.json`, `SECTION_RENDER_MANIFEST.json`, and `FX_APPLICATION_PROOF.json`; those artifacts prove that selected effects reached actual section outputs rather than remaining declared-only capabilities.
