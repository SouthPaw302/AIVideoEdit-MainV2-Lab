#!/usr/bin/env python3
"""One-command bounded verifier for the MainV2-clean surgical stack."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


DEFAULT_TESTS = [
    "tests/test_bootstrap_capsule.py",
    "tests/test_runtime_gatekeeper.py",
    "tests/test_model_registry.py",
    "tests/test_music_beat_worker.py",
    "tests/test_jev_decision.py",
    "tests/test_harness_router.py",
    "tests/test_surgical_regression.py",
    "tests/test_remote_bridge.py",
    "tests/test_core_validation_ref.py",
    "tests/test_bootstrap_validation_ref.py",
    "tests/test_tool_api_gate_boundaries.py",
    "tests/test_operating_gate_path.py",
    "tests/test_fx_runtime_dependencies.py",
    "tests/test_archive_manifest_stability.py",
    "tests/test_execution_ledger.py",
    "tests/test_offline_boot_propagation.py",
]


def run_tests(repo: Path) -> dict:
    cmd=[sys.executable,"-m","pytest","-q",*DEFAULT_TESTS]
    proc=subprocess.run(cmd,cwd=str(repo),capture_output=True,text=True,check=False)
    return {
        "schema":"aivideoedit.surgical-verification.v1",
        "result":"PASS" if proc.returncode==0 else "FAIL",
        "returncode":proc.returncode,
        "tests":DEFAULT_TESTS,
        "stdout":proc.stdout[-12000:],
        "stderr":proc.stderr[-6000:],
    }


def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo-root",default=".")
    ap.add_argument("--json-out")
    args=ap.parse_args()
    repo=Path(args.repo_root).resolve()
    result=run_tests(repo)
    text=json.dumps(result,indent=2,sort_keys=True)
    print(text)
    if args.json_out:
        Path(args.json_out).write_text(text+"\n",encoding="utf-8")
    return 0 if result["result"]=="PASS" else 1


if __name__=="__main__":
    raise SystemExit(main())
