# Director Supervision and Execution Proof

MainV2 does not replace proven Main editing/rendering workflows. It supervises them.

## Roles
- Current user: executive producer and final creative authority.
- Sandbox agent: Director / Editor / VFX Supervisor / visual QC.
- Jev: production coordinator and canonical workflow/FX resolver.
- Existing Main workflows: editing, MUX, music-directed rendering, transitions, FX and finishing machinery.
- GitHub runner: disposable render compute.
- GitHub + Drive: durable production state.

## Required control chain
Director intent -> Jev workflow/FX selection -> canonical gate -> actual execution -> execution receipt -> Director review.

A selection, registry lookup, precompile PASS, model load, or harness self-test is not proof that the selected system affected the output.

## Director checkpoints
New Director Brain v4 productions require media_selection, representative_proof, rough_cut, fx_pass, and final_review. The sandbox Director inspects real media/render evidence at each checkpoint. A technical PASS cannot substitute for creative approval.

## Execution ledger
PRODUCTION_EXECUTION_LEDGER.json records selected, verified, executed, consumed, or explicitly waived systems.
Selected FX require an executed receipt or an explicit waiver with a reason. Analysis/model outputs that claim editorial influence require a downstream consumption receipt. The runner executes approved plans but must not silently choose artistic direction. Hidden secondary FX authorities are forbidden. Canonical FX should execute through general/reusable/fx_v2/executor.py so the canonical FX ID is receipted only after pixels are actually produced.

## Preservation rule
Proven Main workflows are preserved. MainV2 adds supervision, routing, and evidence around them rather than replacing them with one-off render engines.
