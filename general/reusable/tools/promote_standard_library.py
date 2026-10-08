#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REUSABLE = ROOT / "general/reusable"
FX = REUSABLE / "fx_v2"
TOOLS = REUSABLE / "tools"


def read_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError(f"{path} must contain a JSON object")
    return data


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def effect_family(name: str) -> str:
    if any(k in name for k in ("transition", "_to_", "portal", "pigment", "ghosted_memory")):
        return "transition"
    if any(k in name for k in ("reflection", "puddle", "shimmer", "water_region")):
        return "surface"
    if any(k in name for k in ("light", "halation", "glint", "grade")):
        return "light"
    if any(k in name for k in ("waveform", "oscilloscope", "frequency", "spectrum", "particle_tunnel", "plasma")):
        return "visualizer"
    if any(k in name for k in ("fog", "rain", "smoke", "ember", "flame", "fire", "atmospheric", "steam")):
        return "environment"
    if any(k in name for k in ("depth", "parallax", "orbit", "corridor", "camera")):
        return "spatial"
    if "disocclusion" in name:
        return "compositing"
    if "rms_" in name:
        return "audio_reactive"
    return "motion"


def verify_effect_identity(promoted, name_registry: dict, aliases: dict) -> None:
    names = list(promoted.EFFECT_NAMES)
    effects = name_registry.get("effects", {})
    if set(effects) != set(names):
        missing = sorted(set(names) - set(effects))
        extra = sorted(set(effects) - set(names))
        raise RuntimeError(f"effect-name registry mismatch; missing={missing}, extra={extra}")
    alias_records = aliases.get("aliases", {})
    if len(alias_records) != len(promoted.LEGACY_ALIASES):
        raise RuntimeError("effect alias count does not match promoted runtime aliases")
    for label, expected_name in promoted.LEGACY_ALIASES.items():
        resolved_name = alias_records.get(label)
        if not isinstance(resolved_name, str) or not resolved_name.strip():
            raise RuntimeError(f"alias {label!r} must resolve directly to a neutral effect name")
        if resolved_name != expected_name:
            raise RuntimeError(f"alias {label!r} resolves to {resolved_name!r}, expected {expected_name!r}")
        canonical = effects.get(expected_name)
        if not isinstance(canonical, dict) or not canonical.get("id"):
            raise RuntimeError(f"alias {label!r} resolves to effect without a canonical neutral ID")


def promote_effects_into_canonical_registry(promoted, name_registry: dict) -> None:
    registry_path = FX / "registry.json"
    registry = read_json(registry_path)
    effects = registry.setdefault("effects", {})
    canonical_names = name_registry["effects"]
    canonical_ids = {rec["id"] for rec in canonical_names.values()}

    # Remove only entries created by the superseded standardization pass. Existing
    # built-in FX2 entries and the established promoted IDs remain untouched.
    for eid in list(effects):
        rec = effects[eid]
        if isinstance(rec, dict) and rec.get("status") == "standard" and eid not in canonical_ids:
            del effects[eid]

    proof_id = "FX2_PROOF04_PROMOTED_EFFECT_LIBRARY"
    for name in promoted.EFFECT_NAMES:
        neutral = canonical_names[name]
        eid = neutral["id"]
        effects[eid] = {
            "name": name,
            "family": effect_family(name),
            "status": "standard",
            "gate_status": "approved",
            "implementation": {
                "kind": "adapter",
                "path": "general/reusable/fx_v2/promoted_effects.py",
                "symbol": "apply_effect",
                "effect_name": name,
            },
            "proofs": [proof_id],
            "quality": {
                "source_delta_min": 0.02,
                "temporal_delta_min": 0.01,
                "max_global_shift_px": 12.0,
            },
            "notes": "Project-neutral standard effect. Canonical identity is the established neutral FX2 id and effect name.",
        }
    write_json(registry_path, registry)


def ensure_manifest_files() -> None:
    path = REUSABLE / "AIVIDEOEDIT_OS_MANIFEST.json"
    manifest = read_json(path)
    additions = [
        {"path": "general/reusable/fx_v2/promoted_effects.py", "role": "neutral_standard_effect_runtime"},
        {"path": "general/reusable/fx_v2/effect_name_registry.json", "role": "neutral_standard_effect_name_registry"},
        {"path": "general/reusable/fx_v2/effect_aliases.json", "role": "neutral_effect_alias_compatibility"},
        {"path": "general/reusable/fx_v2/verify_promoted_effects.py", "role": "neutral_standard_effect_verifier"},
        {"path": "general/reusable/STANDARD_WORKFLOW_REGISTRY.json", "role": "neutral_standard_workflow_registry"},
        {"path": "general/reusable/STANDARD_WORKFLOWS.md", "role": "neutral_standard_workflow_contract"},
        {"path": "general/reusable/tools/workflow_resolver.py", "role": "standard_workflow_resolver"},
        {"path": "general/reusable/tools/workflow_guard.py", "role": "fail_closed_standard_workflow_guard"},
    ]
    files = manifest.setdefault("files", [])
    existing = {rec.get("path") for rec in files if isinstance(rec, dict)}
    for rec in additions:
        if rec["path"] not in existing:
            files.append(rec)
    write_json(path, manifest)


def verify_integration() -> None:
    required_files = [
        ROOT / "bootstrap.py",
        ROOT / "AGENTS.md",
        ROOT / "SYSTEM_INDEX.md",
        REUSABLE / "STANDARD_WORKFLOW_REGISTRY.json",
        REUSABLE / "STANDARD_WORKFLOWS.md",
        TOOLS / "workflow_resolver.py",
        TOOLS / "workflow_guard.py",
    ]
    missing = [str(p.relative_to(ROOT)) for p in required_files if not p.is_file()]
    if missing:
        raise RuntimeError("missing generated standard capability files: " + ", ".join(missing))

    bootstrap = (ROOT / "bootstrap.py").read_text(encoding="utf-8")
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    prod_guard = (TOOLS / "production_guard.py").read_text(encoding="utf-8")
    system_index = (ROOT / "SYSTEM_INDEX.md").read_text(encoding="utf-8")
    checks = {
        "bootstrap workflow guard": "standard workflow contract" in bootstrap and "resolve_standard_workflows" in bootstrap,
        "agent workflow law": "workflow_guard.py" in agents and "workflow_resolver.py" in agents,
        "production guard critical files": "STANDARD_WORKFLOW_REGISTRY.json" in prod_guard and "workflow_guard.py" in prod_guard,
        "system index standard selection": "Standard capability selection" in system_index,
    }
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        raise RuntimeError("standard capability integration incomplete: " + ", ".join(failed))


def main() -> None:
    promoted = load_module(FX / "promoted_effects.py", "aivideoedit_promoted_effects_standardization")
    name_registry = read_json(FX / "effect_name_registry.json")
    aliases = read_json(FX / "effect_aliases.json")
    verify_effect_identity(promoted, name_registry, aliases)

    # Preserve the established effect verifier/proof schema that is already live on
    # main, then add those same neutral IDs to the canonical callable FX registry.
    verify = subprocess.run(
        [sys.executable, str(FX / "verify_promoted_effects.py")],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if verify.returncode != 0:
        print(verify.stdout)
        print(verify.stderr, file=sys.stderr)
        raise SystemExit("promoted effect verification failed")
    verification = json.loads(verify.stdout)
    if verification.get("result") != "PASS" or int(verification.get("effect_count", 0)) != 52:
        raise SystemExit("promoted effect verification did not cover all 52 standard effects")

    promote_effects_into_canonical_registry(promoted, name_registry)

    # The standard workflow files are canonical generated assets. Their resolver
    # validates neutral naming, declared requirements, selection logic and regression
    # scenarios for living-scene, cinematic, hybrid, source-derived, 2.5D, NeRF and 3DGS use.
    resolver = subprocess.run(
        [sys.executable, str(TOOLS / "workflow_resolver.py"), "--verify", "--json"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if resolver.returncode != 0:
        print(resolver.stdout)
        print(resolver.stderr, file=sys.stderr)
        raise SystemExit("standard workflow verification failed")

    # Replace the old mixed project-labelled catalog with a neutral compatibility
    # index. Historical production names are neither identities nor selection inputs.
    write_json(REUSABLE / "CANONICAL_EFFECT_REGISTRY.json", {
        "schema": "aivideoedit.capability-index.v2",
        "status": "compatibility_index",
        "effect_authority": "general/reusable/fx_v2/registry.json",
        "effect_name_authority": "general/reusable/fx_v2/effect_name_registry.json",
        "effect_aliases": "general/reusable/fx_v2/effect_aliases.json",
        "workflow_authority": "general/reusable/STANDARD_WORKFLOW_REGISTRY.json",
        "policy": "Capabilities are identified and selected only by neutral effect/workflow names and IDs. Production provenance is not a runtime identity or selection input.",
        "verification": {
            "effects": "python general/reusable/fx_v2/verify_promoted_effects.py",
            "workflows": "python general/reusable/tools/workflow_resolver.py --verify --json",
            "workflow_guard": "python general/reusable/tools/workflow_guard.py --branch <branch>",
        },
    })

    ensure_manifest_files()
    verify_integration()
    print("PASS: 52 neutral effects use established FX2 identities; 31 neutral standard workflows verified and integrated")


if __name__ == "__main__":
    main()
