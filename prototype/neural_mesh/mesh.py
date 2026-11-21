"""Bounded distributed neural-mesh experiment. Stdlib only; no production media."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from pathlib import Path

NODES = ("position", "velocity", "acceleration", "short_horizon", "long_horizon", "stabilizer")
NOISE = dict(zip(NODES, (0.07, 0.12, 0.15, 0.10, 0.17, 0.09)))
MASKS = {
    "position":      (1.0, 0.15, 0.45),
    "velocity":      (1.1, 0.20, 0.25),
    "acceleration":  (0.8, 1.40, 0.60),
    "short_horizon": (1.3, 0.25, 0.15),
    "long_horizon":  (0.5, 0.40, 1.40),
    "stabilizer":    (0.8, 0.40, 0.90),
}


def save(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n")


def load(path):
    return json.loads(Path(path).read_text())


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def scene(rng):
    x, y = rng.uniform(-2, 2), rng.uniform(-2, 2)
    vx, vy = rng.uniform(-0.9, 0.9), rng.uniform(-0.9, 0.9)
    ax, ay = rng.uniform(-0.16, 0.16), rng.uniform(-0.16, 0.16)
    return [[x + vx*t + ax*t*t/2, y + vy*t + ay*t*t/2] for t in range(5)]


def sensor(points, name, rng):
    if name not in NODES:
        raise ValueError("unknown sensor")
    sigma = NOISE[name]
    bias = [rng.gauss(0, sigma/3), rng.gauss(0, sigma/3)]
    return [[p[k] + bias[k] + rng.gauss(0, sigma) for k in range(2)] for p in points[:4]]


def features(track, name):
    if len(track) != 4 or any(len(v) != 2 for v in track):
        raise ValueError("expected four 2D observations")
    d = [track[3][i] - track[2][i] for i in (0, 1)]
    acc = [track[3][i] - 2*track[2][i] + track[1][i] for i in (0, 1)]
    mean = [(track[3][i] - track[0][i])/3 for i in (0, 1)]
    a, b, c = MASKS[name]
    z = [d[0]*a, d[1]*a, acc[0]*b, acc[1]*b,
         mean[0]*c, mean[1]*c, math.tanh(2*acc[0]), math.tanh(2*acc[1]), 1.]
    return z


def predict(track, name, params):
    z = features(track, name)
    return [track[-1][j] + sum(w*v for w, v in zip(params[j], z)) for j in range(2)]


def squared_error(a, b):
    return sum((float(x)-float(y))**2 for x, y in zip(a, b)) / 2


def learn(name, rng, train_count=750):
    # A genuinely fitted nonlinear-basis neural readout, one per specialist.
    params = [[0.0]*9 for _ in range(2)]
    params[0][0] = 1.0/MASKS[name][0]
    params[1][1] = 1.0/MASKS[name][0]
    for epoch in range(4):
        for _ in range(train_count):
            p = scene(rng)
            observed = sensor(p, name, rng)
            z = features(observed, name)
            forecast = predict(observed, name, params)
            target = p[4]
            for j in range(2):
                error = max(-4., min(4., forecast[j] - target[j]))
                for k in range(len(z)):
                    params[j][k] -= 0.014 * error * z[k]
                    params[j][k] = max(-3., min(3., params[j][k]))
    losses = []
    for _ in range(120):
        p = scene(rng)
        observed = sensor(p, name, rng)
        losses.append(squared_error(predict(observed, name, params), p[4]))
    return {"readout": params, "validation_mse": sum(losses)/len(losses)}


def prepare(seed, out):
    if not 0 <= seed <= 2**31-1:
        raise ValueError("seed must be a nonnegative 31-bit integer")
    rng = random.Random(97211)
    nodes = {name: learn(name, rng) for name in NODES}
    held_out = scene(random.Random(seed))
    sensory = {name: sensor(held_out, name, random.Random(seed+int(1000+i*1729)))
               for i, name in enumerate(NODES)}
    weights = {"schema": "neural-mesh-v0", "seed": seed, "nodes": nodes}
    observations = {"schema": "neural-mesh-v0", "seed": seed, "tracks": sensory}
    truth = {"schema": "neural-mesh-v0", "seed": seed, "future_position": held_out[4]}
    out = Path(out)
    save(out/"weights.json", weights)
    save(out/"observation.json", observations)
    save(out/"truth.json", truth)


def run_node(name, stage, observation, weights, message=None):
    if name not in NODES or stage not in (1, 2):
        raise ValueError("invalid node or stage")
    if observation.get("seed") != weights.get("seed"):
        raise ValueError("scene/model seed mismatch")
    forecast = predict(observation["tracks"][name], name, weights["nodes"][name]["readout"])
    if stage == 2:
        if message is None or message.get("stage") != 1 or message.get("seed") != observation["seed"]:
            raise ValueError("stage 2 requires stage 1 messages from same scene")
        peer = message["routing"][name]
        if set(peer) != set(NODES) - {name} or abs(sum(peer.values())-1) > 1e-6:
            raise ValueError("invalid peer topology")
        neighbor = [sum(peer[n]*message["predictions"][n][k] for n in peer) for k in (0, 1)]
        forecast = [0.72*forecast[k] + 0.28*neighbor[k] for k in (0, 1)]
    return {"schema": "neural-mesh-v0", "node": name, "stage": stage,
            "seed": observation["seed"], "model_sha256": digest(weights["nodes"][name]),
            "input_sha256": digest(observation), "embedding": features(observation["tracks"][name], name),
            "prediction": forecast}


def integrate(stage, weights, folder):
    folder = Path(folder)
    files = sorted(folder.glob("node-*.json"))
    if len(files) != len(NODES):
        raise ValueError(f"expected {len(NODES)} worker receipts, found {len(files)}")
    receipts = [load(p) for p in files]
    unique = {r["node"]: r for r in receipts}
    if set(unique) != set(NODES) or any(r.get("stage") != stage or r.get("seed") != weights["seed"] for r in receipts):
        raise ValueError("missing, duplicated, wrong-stage, or cross-scene worker receipt")
    if any(r.get("model_sha256") != digest(weights["nodes"][r["node"]]) for r in receipts):
        raise ValueError("worker model checksum mismatch")
    pred = {n: unique[n]["prediction"] for n in NODES}
    prior = {n: 1.0 / max(weights["nodes"][n]["validation_mse"], 1e-6) for n in NODES}
    center = [sum(pred[n][k] for n in NODES)/len(NODES) for k in (0, 1)]
    score = {n: prior[n] / (1.0 + 2.0*squared_error(pred[n], center)) for n in NODES}
    z = sum(score.values())
    attention = {n: score[n]/z for n in NODES}
    consensus = [sum(attention[n]*pred[n][k] for n in NODES) for k in (0, 1)]
    edges = {}
    for receiver in NODES:
        peers = {n: score[n] for n in NODES if n != receiver}
        norm = sum(peers.values())
        edges[receiver] = {n: peers[n]/norm for n in peers}
    return {"schema": "neural-mesh-v0", "seed": weights["seed"], "stage": stage,
            "predictions": pred, "attention": attention, "routing": edges,
            "consensus": consensus, "worker_input_sha256": unique[NODES[0]]["input_sha256"]}


def evaluate(round1, round2, truth, weights):
    if any(p.get("seed") != weights["seed"] for p in (round1, round2, truth)):
        raise ValueError("evaluation data from incompatible scenes")
    if (round1.get("stage"), round2.get("stage")) != (1, 2):
        raise ValueError("requires both ordered stages")
    target = truth["future_position"]
    individual = {n: squared_error(round1["predictions"][n], target) for n in NODES}
    first = squared_error(round1["consensus"], target)
    second = squared_error(round2["consensus"], target)
    # Plasticity is recorded as a proposed checkpoint, never silently committed to main.
    checkpoint = json.loads(json.dumps(weights))
    for n in NODES:
        old = checkpoint["nodes"][n]["validation_mse"]
        checkpoint["nodes"][n]["validation_mse"] = 0.8*old + 0.2*individual[n]
    checkpoint["learned_routing"] = round2["routing"]
    metrics = {"schema": "neural-mesh-v0", "seed": weights["seed"],
               "experiment": "synthetic_2d_motion_forecast",
               "baseline_best_single_mse": min(individual.values()),
               "baseline_per_node_mse": individual,
               "round1_consensus_mse": first, "round2_consensus_mse": second,
               "round2_better_than_round1": second < first,
               "round2_better_than_best_single": second < min(individual.values()),
               "status": "MEASURED_SYNTHETIC_EXPERIMENT_NOT_VIDEO_OR_ARTISTIC_QC",
               "model_state_sha256": digest(weights)}
    return metrics, checkpoint


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    a = sub.add_parser("prepare")
    a.add_argument("--seed", type=int, default=314159)
    a.add_argument("--out", required=True)
    a = sub.add_parser("node")
    a.add_argument("--name", choices=NODES, required=True)
    a.add_argument("--stage", type=int, choices=(1, 2), required=True)
    a.add_argument("--observations", required=True)
    a.add_argument("--weights", required=True)
    a.add_argument("--messages")
    a.add_argument("--out", required=True)
    a = sub.add_parser("integrate")
    a.add_argument("--stage", type=int, choices=(1, 2), required=True)
    a.add_argument("--weights", required=True)
    a.add_argument("--outputs", required=True)
    a.add_argument("--out", required=True)
    a = sub.add_parser("evaluate")
    a.add_argument("--round1", required=True)
    a.add_argument("--round2", required=True)
    a.add_argument("--truth", required=True)
    a.add_argument("--weights", required=True)
    a.add_argument("--out", required=True)
    args = p.parse_args()
    if args.command == "prepare":
        prepare(args.seed, args.out)
    elif args.command == "node":
        save(args.out, run_node(args.name, args.stage, load(args.observations),
                                load(args.weights), load(args.messages) if args.messages else None))
    elif args.command == "integrate":
        save(args.out, integrate(args.stage, load(args.weights), args.outputs))
    elif args.command == "evaluate":
        scores, checkpoint = evaluate(load(args.round1), load(args.round2),
                                      load(args.truth), load(args.weights))
        save(args.out, scores)
        save(Path(args.out).with_name("candidate-checkpoint.json"), checkpoint)


if __name__ == "__main__":
    main()
