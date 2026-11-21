# Distributed Neural Mesh — v0 experimental runner brain

This is an **isolated technical experiment**, not a production video director, human brain simulation, consciousness system, or proof of collective intelligence.

## Purpose

Six individually trained, lightweight nonlinear-basis neural readouts each see a *different noisy four-frame track* of the same moving 2D point. Each readout predicts the next position. Each runs on an **independent GitHub Actions runner** during round 1. An integration runner learns a directed signal-routing graph from independently measured node reliability and live prediction disagreement. In round 2, the original six runners are recreated, read the peer messages, and revise their predictions with recurrent feedback.

The final evaluation job alone reads the withheld target. It compares the round-1 consensus, round-2 consensus, and best standalone specialist on the *same* held-out scene. **The reported comparisons can be worse or better**; there is no automatic success label. A candidate adaptive reliability/routing checkpoint is published but not auto-committed.

## Topology

```text
       Synthetic motion fixture / trained model weights
                           |
                prepare (1 runner)
                 /            \
     model+noisy tracks       withheld target
              |
    round-1: 6 worker runners IN PARALLEL
              |
       synapse-1: consensus + 6x5 routing graph
              |
    round-2: 6 worker runners IN PARALLEL
              |       ^ each receives weighted peer forecasts
       synapse-2: updated consensus
              |
        evaluation runner <--- withheld target
              |
     metrics.json + candidate-checkpoint.json
```

At most **six** of the specialist workers run simultaneously. Two rounds require twelve specialist job executions, **not** twelve continuously running agents. GitHub Actions artifacts supply stage-to-stage messages; they are high-latency snapshots, not a low-latency neural interconnect.

## Files

- `prototype/neural_mesh/mesh.py`: deterministic synthetic fixture generator, six independently fitted neuron modules, recurrent message passing, adaptive routing, and external evaluation.
- `tests/test_neural_mesh.py`: offline end-to-end exchange, deterministic training, rejection of missing receipts, and incompatible seed/feedback checks.
- `.github/workflows/neural-mesh-proof.yml`: pull-request tests and an isolated two-round six-runner workflow.

## Run / inspect

1. The **branch-specific first push** containing the workflow is configured to launch one full, bounded distributed experiment.
2. Pull requests run **offline protocol tests only**, avoiding repeated multi-runner spending.
3. `workflow_dispatch` exists for later use **once GitHub can see this workflow on the repository's default branch**. It may not be available from an unmerged experiment branch. The initial push trigger is intentionally branch-scoped.
4. Download the `mesh-evidence-<run_id>` artifact and read `metrics.json`, `round1.json`, `round2.json`, and `candidate-checkpoint.json`.

Local offline validation (Python 3.11+, no third-party packages):

```bash
python -m unittest discover -s tests -p test_neural_mesh.py -v
python prototype/neural_mesh/mesh.py prepare --seed 314159 --out /tmp/mesh
```

## What is implemented vs. not implemented

**Implemented:** learned per-node numerical parameters, genuine message passing in separate jobs, directed weighted peer routing, round-two feedback, separate evaluation data, evaluation without self-certification, and a versioned candidate plasticity checkpoint.

**Not implemented yet:** real video input or AR features, full Qwen3-VL multimodal inference inside mesh workers, tensor/model parallelism, continuous online learning, persistent shared memory across workflow runs, low-latency communication, or autonomous production decisions.

The existing `prototype/ai` Qwen3-VL proof workflow is **unchanged**. Connecting its verified frame/embedding outputs as real specialist observations is the next technical integration after synthetic and runner evidence. Large-model downloads are deliberately absent from this first proof.

## Integrity and isolation

- No workflow has write permissions to the repository; no model promotes itself.
- Outputs include model and observation SHA-256 digests. The evaluator refuses missing workers, duplicate IDs, wrong stages, and incompatible seeds.
- The withheld target is placed in a separate artifact that worker jobs do not download. It is **not a security boundary** against collaborators with source-code or artifact access.
- Candidate memory is an artifact within one workflow run, not a durable global brain. For long-lived learning, move weights/routing to an explicit versioned state store with approval and rollback.
- This technical experiment does **not** create or modify production assets and cannot declare visual or artistic acceptance.
