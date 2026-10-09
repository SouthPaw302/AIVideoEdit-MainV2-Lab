#!/usr/bin/env python3
"""Adapter between the workstation stack and the canonical AIVideoEdit OS.

The workstation is not a production branch and must never pretend to be one.
This adapter installs a clean current `main` checkout into the runtime cache,
boots/attests that checkout as `main`, and reads canonical contracts,
capabilities and effects from its `.aivideoedit/os` snapshot.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
HOST_REPO = HERE.parents[1]
HOST_BOOTSTRAP = HOST_REPO / "bootstrap.py"
RUNTIME = Path(os.environ.get("AIVE_RUNTIME", str(HERE / ".runtime"))).resolve()
CORE_HOME = RUNTIME / "core"
CORE_REPO = CORE_HOME / "repo"
SESSION_ROOT = CORE_REPO / ".aivideoedit"
OS_ROOT = SESSION_ROOT / "os"
SESSION_FILE = SESSION_ROOT / "session.json"
CONTRACT = Path("general/reusable/PRODUCTION_CONTRACT.json")
CAPABILITY_MATRIX = Path("general/reusable/MEDIA_CAPABILITY_MATRIX.json")
FX_REGISTRY = Path("general/reusable/fx_v2/registry.json")


def _core_ref() -> str:
    value = os.environ.get("AIVE_CORE_REF", "main").strip()
    return value or "main"


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _host_branch() -> str:
    try:
        proc = subprocess.run(
            ["git", "-C", str(HOST_REPO), "branch", "--show-current"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    except Exception:
        pass
    return "unknown"


def _run(cmd: list[str], cwd: Path, timeout: int = 300, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        env=env,
    )


class CoreAdapter:
    def __init__(self) -> None:
        self.host_repo = HOST_REPO
        self.core_repo = CORE_REPO
        self.os_root = OS_ROOT
        self.session_file = SESSION_FILE

    def _install_core(self, offline: bool) -> subprocess.CompletedProcess:
        CORE_HOME.mkdir(parents=True, exist_ok=True)
        if CORE_REPO.exists():
            shutil.rmtree(CORE_REPO)

        if offline:
            if not shutil.which("git"):
                raise RuntimeError("offline core loading requires git")
            proc = _run(
                ["git", "clone", "--no-hardlinks", str(HOST_REPO), str(CORE_REPO)],
                HOST_REPO,
            )
            if proc.returncode != 0:
                return proc
            ref = _core_ref()
            target = f"origin/{ref}"
            check = _run(["git", "rev-parse", "--verify", target], CORE_REPO, timeout=30)
            if check.returncode != 0:
                host_ref = _run(
                    ["git", "-C", str(HOST_REPO), "rev-parse", f"refs/remotes/origin/{ref}"],
                    HOST_REPO,
                    timeout=30,
                )
                if host_ref.returncode == 0 and host_ref.stdout.strip():
                    target = host_ref.stdout.strip()
                    check = _run(["git", "cat-file", "-e", f"{target}^{{commit}}"], CORE_REPO, timeout=30)
                if check.returncode == 0:
                    return _run(["git", "checkout", "-B", ref, target], CORE_REPO, timeout=60)
                fetched = _run(
                    ["git", "fetch", "origin", f"refs/heads/{ref}:refs/remotes/origin/{ref}"],
                    CORE_REPO,
                    timeout=120,
                )
                check = _run(["git", "rev-parse", "--verify", target], CORE_REPO, timeout=30)
                if check.returncode != 0 and fetched.returncode != 0:
                    target = "FETCH_HEAD" if ref == "main" else ref
            return _run(["git", "checkout", "-B", ref, target], CORE_REPO, timeout=60)

        if not HOST_BOOTSTRAP.is_file():
            raise RuntimeError("host bootstrap.py not found")
        return _run(
            [sys.executable, str(HOST_BOOTSTRAP), "install", "--workspace", str(CORE_REPO)],
            HOST_REPO,
        )

    def bootstrap(self, offline: bool = False) -> dict:
        try:
            install = self._install_core(offline)
        except Exception as exc:
            return {"ok": False, "bootstrapped": False, "error": str(exc), **self.status()}
        if install.returncode != 0:
            return {
                "ok": False,
                "bootstrapped": False,
                "phase": "install",
                "stdout": (install.stdout or "")[-4000:],
                "stderr": (install.stderr or "")[-4000:],
                **self.status(),
            }

        bootstrap = CORE_REPO / "bootstrap.py"
        if not bootstrap.is_file():
            return {"ok": False, "bootstrapped": False, "error": "installed main lacks bootstrap.py", **self.status()}

        requested_ref = _core_ref()
        boot_branch = "main"
        cmd = [
            sys.executable,
            str(bootstrap),
            "boot",
            "--repo-root",
            str(CORE_REPO),
            "--branch",
            boot_branch,
        ]
        if offline:
            cmd.append("--offline")
        env = dict(os.environ)
        if requested_ref != "main":
            env["AIVIDEOEDIT_AUTHORITY_REF"] = requested_ref
            env["AIVIDEOEDIT_VALIDATION_MODE"] = "1"
        proc = _run(cmd, CORE_REPO, timeout=300, env=env)
        result = {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "phase": "boot",
            "stdout": (proc.stdout or "")[-4000:],
            "stderr": (proc.stderr or "")[-4000:],
        }
        result.update(self.status())
        return result

    def status(self) -> dict:
        session = _read_json(self.session_file, {})
        contract = _read_json(self.os_root / CONTRACT, {}) if self.os_root.is_dir() else {}
        matrix = _read_json(self.os_root / CAPABILITY_MATRIX, {}) if self.os_root.is_dir() else {}
        fx = _read_json(self.os_root / FX_REGISTRY, {}) if self.os_root.is_dir() else {}
        capabilities = self._records(matrix, ("capabilities", "media_capabilities", "items"))
        effects = self._records(fx, ("effects", "fx", "registry", "items"))
        ref = _core_ref()
        bootstrapped = bool(session) and self.os_root.is_dir() and session.get("branch") == "main"
        return {
            "ok": True,
            "bootstrapped": bootstrapped,
            "mode": "isolated-canonical-main" if ref == "main" else "isolated-validation-ref",
            "requested_core_ref": ref,
            "host_repo": str(self.host_repo),
            "host_branch": _host_branch(),
            "core_repo": str(self.core_repo) if self.core_repo.exists() else None,
            "core_branch": session.get("branch"),
            "os_root": str(self.os_root) if bootstrapped else None,
            "main_commit": session.get("os_main_commit"),
            "session_id": session.get("session_id"),
            "guard_result": session.get("guard_result"),
            "contract_schema": contract.get("schema"),
            "production_states": contract.get("states", []),
            "capability_count": len(capabilities),
            "fx_count": len(effects),
        }

    @staticmethod
    def _records(payload: Any, keys: tuple[str, ...]) -> list:
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            for key in keys:
                value = payload.get(key)
                if isinstance(value, list):
                    return value
                if isinstance(value, dict):
                    return [dict({"id": k}, **(v if isinstance(v, dict) else {"value": v})) for k, v in value.items()]
            records = []
            for key, value in payload.items():
                if isinstance(value, dict):
                    records.append(dict({"id": key}, **value))
            if records:
                return records
        return []

    def production_contract(self) -> dict:
        return _read_json(self.os_root / CONTRACT, {})

    def capabilities(self) -> list:
        payload = _read_json(self.os_root / CAPABILITY_MATRIX, {})
        return self._records(payload, ("capabilities", "media_capabilities", "items"))

    def effects(self) -> list:
        payload = _read_json(self.os_root / FX_REGISTRY, {})
        return self._records(payload, ("effects", "fx", "registry", "items"))


CORE = CoreAdapter()
