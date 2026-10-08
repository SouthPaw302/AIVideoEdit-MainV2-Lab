#!/usr/bin/env python3
"""Fail-closed precompile gate for AIVideoEdit FX v2.

The gate proves more than registry membership. It binds a production render to:
- the exact manifest, FX registry, runtime and declared renderer inputs;
- concrete runtime methods or adapter implementation files;
- human-approved proof records, with proof binaries byte-verified when addressable;
- deterministic runtime smoke output fingerprints and temporal/pixel metrics;
- explicit preflight evidence for conditional/external technologies.

Lock verification reruns the live checks and compares the complete evidence fingerprint.
Old schema-v1 locks are intentionally rejected and must be regenerated.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

HEX64 = re.compile(r"^[0-9a-f]{64}$")
BAD_TOKENS = ("TODO", "FIXME", "PLACEHOLDER", "NotImplementedError", "pass #", "raise NotImplemented")
GOOD_QC = ("KEEP", "APPROVED", "PASS")
SCHEMA_VERSION = 2
GATE_NAME = "aivideoedit-fx-precompile-v2"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_json_hash(obj: Any) -> str:
    return sha256_bytes(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"cannot parse JSON {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"{path} must contain a JSON object")
    return data


def repo_root_from_runtime(runtime_path: Path) -> Path:
    path = runtime_path.resolve()
    try:
        return path.parents[3]
    except IndexError as exc:
        raise RuntimeError(f"cannot determine repository root from {runtime_path}") from exc


def resolve_repo_path(repo_root: Path, raw: str, label: str) -> Path:
    p = Path(raw)
    if p.is_absolute():
        resolved = p.resolve()
    else:
        resolved = (repo_root / p).resolve()
        try:
            resolved.relative_to(repo_root.resolve())
        except ValueError as exc:
            raise RuntimeError(f"{label} escapes repository root: {raw}") from exc
    if not resolved.is_file():
        raise RuntimeError(f"{label} missing: {raw}")
    return resolved


def load_runtime(runtime_path: Path):
    name = "aivideoedit_fx_v2_runtime_gate"
    spec = importlib.util.spec_from_file_location(name, runtime_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import runtime from {runtime_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    if not hasattr(module, "FXRuntime") or not hasattr(module, "FXContext"):
        raise RuntimeError("runtime.py must export FXRuntime and FXContext")
    return module


def runtime_ast(runtime_path: Path):
    source = runtime_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    fx_class = next((n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "FXRuntime"), None)
    if fx_class is None:
        raise RuntimeError("runtime.py does not define FXRuntime")
    methods = {n.name: n for n in fx_class.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    return source, methods


def method_text(source: str, methods: dict[str, ast.AST], name: str) -> str:
    node = methods.get(name)
    if node is None:
        raise RuntimeError(f"runtime method missing: FXRuntime.{name}")
    text = ast.get_source_segment(source, node) or ""
    if len(text.strip().splitlines()) < 2:
        raise RuntimeError(f"runtime method is empty: FXRuntime.{name}")
    if any(tok.lower() in text.lower() for tok in BAD_TOKENS):
        raise RuntimeError(f"placeholder/stub token found in FXRuntime.{name}")
    for child in ast.walk(node):
        if isinstance(child, ast.Pass):
            raise RuntimeError(f"pass statement found in FXRuntime.{name}")
        if isinstance(child, ast.Raise):
            txt = ast.get_source_segment(source, child) or ""
            if "NotImplemented" in txt:
                raise RuntimeError(f"NotImplemented raise found in FXRuntime.{name}")
    return text


def requested_entries(manifest: dict) -> list[dict]:
    out: list[dict] = []
    for key, kind in (("effects", "frame"), ("transitions", "transition")):
        vals = manifest.get(key, [])
        if vals is None:
            continue
        if not isinstance(vals, list):
            raise RuntimeError(f"manifest {key} must be a list")
        for raw in vals:
            if isinstance(raw, str):
                raw = {"id": raw}
            if not isinstance(raw, dict) or not raw.get("id"):
                raise RuntimeError(f"invalid manifest entry in {key}: {raw!r}")
            item = dict(raw)
            item["_kind"] = kind
            out.append(item)
    if not out:
        raise RuntimeError("manifest requests no effects or transitions")
    ids = [x["id"] for x in out]
    if len(ids) != len(set(ids)):
        dupes = sorted({x for x in ids if ids.count(x) > 1})
        raise RuntimeError(f"duplicate FX ids in manifest: {dupes}")
    return out


def render_input_hashes(manifest: dict, repo_root: Path, engine_test: bool) -> list[dict]:
    vals = manifest.get("render_inputs", [])
    if not isinstance(vals, list):
        raise RuntimeError("manifest render_inputs must be a list")
    if not vals and not engine_test:
        raise RuntimeError("production manifest must declare render_inputs; use --engine-test only for isolated engine CI")
    out = []
    for raw in vals:
        if not isinstance(raw, str) or not raw.strip():
            raise RuntimeError(f"invalid render_inputs entry: {raw!r}")
        path = resolve_repo_path(repo_root, raw, "render input")
        out.append({"path": raw, "sha256": sha256_file(path)})
    return out


def proof_record(proof_dir: Path, proof_id: str, effect_id: str, repo_root: Path) -> tuple[dict, dict]:
    path = proof_dir / f"{proof_id}.json"
    if not path.exists():
        raise RuntimeError(f"approved proof record missing: {path}")
    proof = load_json(path)
    if effect_id not in proof.get("effects", []):
        raise RuntimeError(f"proof {proof_id} does not cover {effect_id}")
    qc = str(proof.get("visual_qc", "")).upper()
    if not any(word in qc for word in GOOD_QC):
        raise RuntimeError(f"proof {proof_id} is not visually approved: {proof.get('visual_qc')!r}")
    if int(proof.get("frames", 0)) < 24:
        raise RuntimeError(f"proof {proof_id} is too short to prove temporal behavior")
    if float(proof.get("fps", 0)) < 24:
        raise RuntimeError(f"proof {proof_id} is below 24 fps")
    size = proof.get("size", [0, 0])
    if not (isinstance(size, list) and len(size) == 2 and int(size[0]) >= 320 and int(size[1]) >= 180):
        raise RuntimeError(f"proof {proof_id} resolution is too small or missing")
    declared = str(proof.get("sha256", "")).lower()
    if not HEX64.match(declared):
        raise RuntimeError(f"proof {proof_id} does not contain a valid declared binary SHA-256")

    artifact = proof.get("artifact_path") or proof.get("binary_path")
    evidence = {
        "id": proof_id,
        "record_sha256": sha256_file(path),
        "declared_binary_sha256": declared,
        "artifact_path": artifact,
        "artifact_verified": False,
    }
    if artifact:
        artifact_path = resolve_repo_path(repo_root, str(artifact), f"proof artifact for {proof_id}")
        actual = sha256_file(artifact_path)
        if actual != declared:
            raise RuntimeError(f"proof {proof_id} binary checksum mismatch: declared={declared} actual={actual}")
        evidence["artifact_verified"] = True
        evidence["artifact_sha256"] = actual
    return proof, evidence


def synthetic_frame(np, cv2, width=320, height=180):
    yy, xx = np.mgrid[0:height, 0:width]
    im = np.zeros((height, width, 3), np.uint8)
    im[..., 0] = np.clip(25 + xx * 185 / width, 0, 255).astype(np.uint8)
    im[..., 1] = np.clip(22 + yy * 190 / height, 0, 255).astype(np.uint8)
    im[..., 2] = np.clip(45 + ((xx + yy) % 145), 0, 255).astype(np.uint8)
    cv2.circle(im, (int(width * .30), int(height * .52)), int(height * .24), (28, 165, 236), -1, cv2.LINE_AA)
    cv2.rectangle(im, (int(width * .58), int(height * .20)), (int(width * .90), int(height * .84)), (184, 74, 42), -1)
    cv2.line(im, (0, int(height * .66)), (width - 1, int(height * .58)), (225, 225, 225), 2, cv2.LINE_AA)
    return im


def mean_delta(np, cv2, a, b) -> float:
    return float(np.mean(cv2.absdiff(a, b)))


def global_shift(cv2, np, a, b) -> float:
    ga = np.float32(cv2.cvtColor(a, cv2.COLOR_BGR2GRAY))
    gb = np.float32(cv2.cvtColor(b, cv2.COLOR_BGR2GRAY))
    (dx, dy), _ = cv2.phaseCorrelate(ga, gb)
    return float((dx * dx + dy * dy) ** .5)


def smoke_frame_effect(module, runtime, effect: dict, quality: dict) -> dict:
    import cv2
    import numpy as np

    src = synthetic_frame(np, cv2)
    times = (0.11, 0.37, 0.73, 1.19, 1.83, 2.41)
    outs = []
    for t in times:
        ctx = module.FXContext(t=t, duration=3.0, frame_index=round(t * 24), fps=24, energy=.64, transient=.58, brightness=.55)
        out = runtime.apply(src.copy(), effect, ctx)
        if out is None or out.shape != src.shape or out.dtype != src.dtype:
            raise RuntimeError(f"{effect['id']} returned an invalid frame")
        outs.append(out)

    source_deltas = [mean_delta(np, cv2, src, out) for out in outs]
    temporal_deltas = [mean_delta(np, cv2, outs[i], outs[j]) for i in range(len(outs)) for j in range(i + 1, len(outs))]
    shifts = [global_shift(cv2, np, src, out) for out in outs]
    source_delta = max(source_deltas)
    temporal_delta = max(temporal_deltas) if temporal_deltas else 0.0
    shift = max(shifts)
    smin = float(quality.get("source_delta_min", .01))
    if source_delta < smin:
        raise RuntimeError(f"{effect['id']} is effectively a no-op: source delta {source_delta:.4f} < {smin:.4f}")
    if bool(quality.get("temporal_required", True)):
        tmin = float(quality.get("temporal_delta_min", .005))
        if temporal_delta < tmin:
            raise RuntimeError(f"{effect['id']} is not visibly temporal: delta {temporal_delta:.4f} < {tmin:.4f}")
    max_shift = quality.get("max_global_shift_px")
    if max_shift is not None and shift > float(max_shift):
        raise RuntimeError(f"{effect['id']} causes excessive global shift {shift:.3f}px > {float(max_shift):.3f}px")
    sample_digest = sha256_bytes(b"".join(out.tobytes() for out in outs))
    return {
        "source_delta_max": round(source_delta, 6),
        "temporal_delta_max": round(temporal_delta, 6),
        "global_shift_px_max": round(shift, 6),
        "sample_output_sha256": sample_digest,
    }


def smoke_transition(runtime, effect: dict, impl: dict, quality: dict) -> dict:
    import cv2
    import numpy as np

    a = synthetic_frame(np, cv2)
    b = cv2.GaussianBlur(255 - a, (0, 0), 1.3)
    method_name = impl.get("method")
    method = getattr(runtime, method_name, None)
    if method is None or not callable(method):
        raise RuntimeError(f"transition implementation missing: FXRuntime.{method_name}")
    params = dict(effect.get("params", {}))
    samples = []
    for p in (0.0, .20, .40, .60, .80, 1.0):
        out = method(a.copy(), b.copy(), p, **params)
        if out is None or out.shape != a.shape:
            raise RuntimeError(f"{effect['id']} transition returned invalid output")
        samples.append(out)
    endpoint_a = mean_delta(np, cv2, a, samples[0])
    endpoint_b = mean_delta(np, cv2, b, samples[-1])
    if endpoint_a > float(quality.get("endpoint_delta_max", .01)):
        raise RuntimeError(f"{effect['id']} fails outgoing endpoint: delta={endpoint_a:.4f}")
    if endpoint_b > float(quality.get("endpoint_delta_max", .01)):
        raise RuntimeError(f"{effect['id']} fails incoming endpoint: delta={endpoint_b:.4f}")
    temporal = max(mean_delta(np, cv2, samples[i], samples[j]) for i in range(len(samples)) for j in range(i + 1, len(samples)))
    if temporal < float(quality.get("temporal_delta_min", .5)):
        raise RuntimeError(f"{effect['id']} transition does not visibly evolve")
    return {
        "endpoint_a_delta": round(endpoint_a, 6),
        "endpoint_b_delta": round(endpoint_b, 6),
        "temporal_delta_max": round(temporal, 6),
        "sample_output_sha256": sha256_bytes(b"".join(out.tobytes() for out in samples)),
    }


def conditional_preflight(manifest: dict, eid: str, repo_root: Path) -> dict:
    mapping = manifest.get("conditional_preflight", {})
    if not isinstance(mapping, dict):
        raise RuntimeError("manifest conditional_preflight must be an object")
    raw = mapping.get(eid)
    if not isinstance(raw, str) or not raw:
        raise RuntimeError(f"{eid} requires a technology-specific conditional_preflight JSON path")
    path = resolve_repo_path(repo_root, raw, f"conditional preflight for {eid}")
    data = load_json(path)
    if str(data.get("result", "")).upper() != "PASS":
        raise RuntimeError(f"conditional preflight for {eid} does not contain result=PASS")
    if data.get("effect_id") not in (None, eid):
        raise RuntimeError(f"conditional preflight {raw} is for {data.get('effect_id')}, not {eid}")
    return {"path": raw, "sha256": sha256_file(path)}


def verify_project(manifest_path: Path, registry_path: Path, proof_dir: Path, runtime_path: Path, static_only: bool = False, engine_test: bool = False) -> dict:
    manifest = load_json(manifest_path)
    registry = load_json(registry_path)
    if manifest.get("runtime") != registry.get("runtime"):
        raise RuntimeError(f"runtime mismatch: project={manifest.get('runtime')!r} registry={registry.get('runtime')!r}")

    repo_root = repo_root_from_runtime(runtime_path)
    render_inputs = render_input_hashes(manifest, repo_root, engine_test)
    source, methods = runtime_ast(runtime_path)
    runtime_apply_text = method_text(source, methods, "apply")
    reg_effects = registry.get("effects", {})
    if not isinstance(reg_effects, dict):
        raise RuntimeError("registry effects must be an object")

    module = runtime = None
    if not static_only:
        module = load_runtime(runtime_path)
        runtime = module.FXRuntime(seed=int(manifest.get("seed", 302)))

    approved_conditional = set(manifest.get("allow_conditional", []))
    lock_effects = []
    for req in requested_entries(manifest):
        eid = req["id"]
        entry = reg_effects.get(eid)
        if entry is None:
            raise RuntimeError(f"unknown FX id requested by project: {eid}")
        gate_status = entry.get("gate_status")
        if gate_status == "conditional":
            if eid not in approved_conditional:
                raise RuntimeError(f"{eid} is conditional and requires explicit allow_conditional opt-in")
        elif gate_status != "approved":
            raise RuntimeError(f"{eid} is not production-approved (gate_status={gate_status!r})")

        impl = entry.get("implementation") or {}
        kind = impl.get("kind")
        impl_hash = None
        impl_file = None
        if kind == "runtime_apply":
            if req["_kind"] != "frame":
                raise RuntimeError(f"{eid} is registered as frame effect but requested as transition")
            if eid not in runtime_apply_text:
                raise RuntimeError(f"{eid} exists in registry but is not wired into FXRuntime.apply")
            method_name = impl.get("method") or ("apply_canvas" if eid == "FX2-SURFACE-001" else entry.get("name"))
            impl_hash = sha256_bytes(method_text(source, methods, method_name).encode("utf-8"))
        elif kind == "runtime_transition":
            if req["_kind"] != "transition":
                raise RuntimeError(f"{eid} is registered as transition but requested as frame effect")
            method_name = impl.get("method") or entry.get("name")
            impl_hash = sha256_bytes(method_text(source, methods, method_name).encode("utf-8"))
        elif kind == "adapter":
            raw_path = impl.get("path")
            if not raw_path:
                raise RuntimeError(f"{eid} adapter has no implementation path")
            path = resolve_repo_path(repo_root, raw_path, f"adapter implementation for {eid}")
            impl_hash = sha256_file(path)
            impl_file = raw_path
        elif kind == "external":
            impl_hash = canonical_json_hash(impl)
        else:
            raise RuntimeError(f"{eid} has no concrete implementation kind")

        proof_evidence = []
        proof_ids = entry.get("proofs") or []
        if gate_status == "approved" and not proof_ids:
            raise RuntimeError(f"{eid} is marked approved without proof records")
        for proof_id in proof_ids:
            _, evidence = proof_record(proof_dir, proof_id, eid, repo_root)
            proof_evidence.append(evidence)

        if gate_status == "approved" and kind in ("adapter", "external"):
            if not proof_evidence or not all(p.get("artifact_verified") for p in proof_evidence):
                raise RuntimeError(f"approved {kind} effect {eid} requires byte-verified proof artifact(s)")

        preflight = None
        if gate_status == "conditional":
            preflight = conditional_preflight(manifest, eid, repo_root)

        metrics = {"static_only": True}
        if not static_only:
            quality = entry.get("quality") or {}
            if kind == "runtime_apply":
                metrics = smoke_frame_effect(module, runtime, req, quality)
            elif kind == "runtime_transition":
                metrics = smoke_transition(runtime, req, impl, quality)
            else:
                metrics = {"external_or_adapter": True, "implementation_sha256": impl_hash}

        lock_effects.append({
            "id": eid,
            "name": entry.get("name"),
            "family": entry.get("family"),
            "gate_status": gate_status,
            "implementation": impl,
            "implementation_path": impl_file,
            "implementation_sha256": impl_hash,
            "proofs": proof_evidence,
            "conditional_preflight": preflight,
            "smoke": metrics,
        })

    result = {
        "schema_version": SCHEMA_VERSION,
        "gate": GATE_NAME,
        "project": manifest.get("project"),
        "runtime": registry.get("runtime"),
        "manifest_sha256": sha256_file(manifest_path),
        "registry_sha256": sha256_file(registry_path),
        "runtime_sha256": sha256_file(runtime_path),
        "render_inputs": render_inputs,
        "effects": lock_effects,
        "result": "PASS",
    }
    result["evidence_fingerprint_sha256"] = canonical_json_hash({"render_inputs": render_inputs, "effects": lock_effects})
    return result


def verify_lock(lock_path: Path, manifest_path: Path, registry_path: Path, proof_dir: Path, runtime_path: Path, engine_test: bool = False) -> dict:
    lock = load_json(lock_path)
    if int(lock.get("schema_version", 0)) != SCHEMA_VERSION or lock.get("gate") != GATE_NAME:
        raise RuntimeError("FX lock uses obsolete schema; regenerate with the current precompile gate")
    if lock.get("result") != "PASS":
        raise RuntimeError("FX lock does not contain PASS result")
    current = verify_project(manifest_path, registry_path, proof_dir, runtime_path, static_only=False, engine_test=engine_test)
    for key in ("manifest_sha256", "registry_sha256", "runtime_sha256", "evidence_fingerprint_sha256"):
        if lock.get(key) != current.get(key):
            raise RuntimeError(f"FX lock invalid: {key} changed after precompile gate")
    if lock.get("render_inputs") != current.get("render_inputs") or lock.get("effects") != current.get("effects"):
        raise RuntimeError("FX lock invalid: live evidence differs from locked evidence")
    return lock


def main() -> int:
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True, help="project FX requirements JSON")
    ap.add_argument("--registry", default=str(here / "registry.json"))
    ap.add_argument("--proof-dir", default=str(here / "proofs"))
    ap.add_argument("--runtime", default=str(here / "runtime.py"))
    ap.add_argument("--lock-out", help="write immutable FX lock JSON")
    ap.add_argument("--static-only", action="store_true", help="skip pixel smoke tests; code/index checks only")
    ap.add_argument("--engine-test", action="store_true", help="allow isolated engine CI manifest without production render_inputs")
    ap.add_argument("--verify-lock", help="verify an existing lock instead of generating one")
    args = ap.parse_args()

    manifest = Path(args.manifest)
    registry = Path(args.registry)
    proof_dir = Path(args.proof_dir)
    runtime = Path(args.runtime)
    try:
        if args.verify_lock:
            lock = verify_lock(Path(args.verify_lock), manifest, registry, proof_dir, runtime, engine_test=args.engine_test)
            print(json.dumps({"result": "PASS", "verified_lock": args.verify_lock, "project": lock.get("project"), "schema_version": SCHEMA_VERSION}, indent=2))
            return 0
        result = verify_project(manifest, registry, proof_dir, runtime, static_only=args.static_only, engine_test=args.engine_test)
        if args.lock_out:
            out = Path(args.lock_out)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"result": "FAIL", "error": str(exc)}, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
