#!/usr/bin/env python3
"""Fast structural/self-consistency checks for the browser workstation.

This intentionally avoids fabricating production media. It validates code-level
contracts that can be proven without running a full render project.
"""
from __future__ import annotations

import ast
import importlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]


def check(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def parse_python(path: Path, failures: list[str]) -> ast.Module | None:
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except Exception as exc:
        failures.append(f"python parse failed: {path.relative_to(REPO)}: {exc}")
        return None


def source_contains(path: Path, *needles: str) -> bool:
    text = path.read_text(encoding="utf-8")
    return all(x in text for x in needles)


def main() -> int:
    failures: list[str] = []
    required = [
        "server.py", "stack.py", "tool_api.py", "core_adapter.py",
        "production_project.py", "production_analysis.py", "production_approach.py",
        "production_storyboard.py", "production_shots.py", "production_generated.py",
        "production_proofs.py", "production_fx.py", "production_assembly.py",
        "production_final_qc.py", "production_archive.py", "production_stage.py",
        "production_operating_order.py", "operating_tools.py",
    ]
    for name in required:
        path = ROOT / name
        check(path.is_file(), f"missing module: {name}", failures)
        if path.is_file(): parse_python(path, failures)

    try:
        tool_api = importlib.import_module("tool_api")
        operating_tools = importlib.import_module("operating_tools")
        schemas = list(tool_api.schemas()) + list(operating_tools.schemas())
        names = [str(x.get("name")) for x in schemas if isinstance(x, dict)]
        check(len(names) == len(set(names)), "duplicate Tool API names", failures)
        expected_tools = {
            "core.status", "project.create", "production.initialize", "production.analyze",
            "approach.set_capabilities", "storyboard.set", "shots.template", "shots.build_packages",
            "generated.request", "generated.register", "generated.accept", "generated.reject",
            "proofs.record", "proofs.accept", "proofs.finalize", "proofs.reject",
            "fx.registry", "fx.set_requirements", "fx.lock", "fx.verify",
            "assembly.status", "assembly.run", "final_qc.status", "final_qc.run_technical",
            "final_qc.accept_creative", "final_qc.reject", "archive.status", "archive.build",
            "archive.verify", "operating.status", "operating.configure_v2", "operating.configure_v3",
        }
        missing = sorted(expected_tools - set(names))
        check(not missing, "missing Tool API contracts: " + ", ".join(missing), failures)
    except Exception as exc:
        failures.append(f"Tool API import/schema check failed: {exc}")

    stage = ROOT / "production_stage.py"
    if stage.is_file():
        check(source_contains(stage,
            'target_stage=="SHOT_PROOFS_ACCEPTED"', 'target_stage=="FX_LOCKED"',
            'target_stage=="ASSEMBLED"', 'target_stage=="FINAL_QC_PASSED"',
            'target_stage=="ARCHIVED"'),
            "stage controller does not visibly gate the late production stages", failures)

    generated = ROOT / "production_generated.py"
    if generated.is_file():
        check(source_contains(generated, '"creative_status":"rejected"', 'state["stage"]="STORYBOARD_LOCKED"', '"shot_packages_built"'),
              "generated-media rejection does not visibly roll dependent state back", failures)

    proofs = ROOT / "production_proofs.py"
    if proofs.is_file():
        check(source_contains(proofs, '"technical_and_mode_checks_passed":True', '"creative_status":"needs_review"', '"creative_status":"accepted"'),
              "proof system does not visibly separate technical checks from creative acceptance", failures)
        check("video" in proofs.read_text(encoding="utf-8").lower(), "proof module lacks visible temporal/video proof constraint", failures)

    final_qc = ROOT / "production_final_qc.py"
    if final_qc.is_file():
        check(source_contains(final_qc, "assembly_sha256", "script_sha256", "fx_lock_sha256"), "final QC is not visibly bound to assembly/script/FX hashes", failures)

    archive = ROOT / "production_archive.py"
    if archive.is_file(): check("sha256" in archive.read_text(encoding="utf-8").lower(), "archive manifest lacks content hash binding", failures)

    project = ROOT / "production_project.py"
    if project.is_file():
        text = project.read_text(encoding="utf-8")
        check("verified_state_sha256" in text and "verified_head" in text, "guard marker is not bound to state + git head", failures)
        if "--porcelain" not in text: print("WARN: guard marker does not yet visibly bind to a clean tracked worktree")

    analysis = ROOT / "production_analysis.py"
    if analysis.is_file() and "preserve" not in analysis.read_text(encoding="utf-8").lower():
        print("WARN: music analysis explicit-context preservation still needs hardening")

    print(json.dumps({"schema":"aivideoedit.workstation-selftest.v1","result":"PASS" if not failures else "FAIL","failures":failures}, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__": raise SystemExit(main())
