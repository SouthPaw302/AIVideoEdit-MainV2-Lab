# Live Effect Policy

Reusable effects are identified by neutral effect name, not by the production where they first appeared.

`effect_name_registry.json` is the live name index for promoted historical techniques. `promoted_effects.py` is the callable implementation. `effect_aliases.json` is compatibility lineage only. Every live promoted effect must pass deterministic source-delta and temporal-delta verification in `verify_promoted_effects.py` and remain covered by the promoted-effects CI workflow.

Project provenance must never be required to call an effect and must never import historical art direction into a new production.
