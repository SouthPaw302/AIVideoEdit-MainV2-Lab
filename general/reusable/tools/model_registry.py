#!/usr/bin/env python3
"""Provider-neutral embedded/external model registry resolver."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


REGISTRY_SCHEMA = "aivideoedit.model-registry.v1"
DEFAULT_REGISTRY = Path(__file__).resolve().parents[1] / "intelligence" / "MODEL_REGISTRY.json"


@dataclass(frozen=True)
class Resolution:
    requested: str
    resolved: str
    available: bool
    used_fallback: bool
    reason: str
    record: dict
    artifact_path: str | None = None


class RegistryError(ValueError):
    pass


class ModelRegistry:
    def __init__(self, data: dict, *, repo_root: Path):
        if data.get("schema") != REGISTRY_SCHEMA:
            raise RegistryError("invalid model registry schema")
        records = data.get("models")
        if not isinstance(records, list):
            raise RegistryError("model registry models must be a list")
        ids = [str(x.get("id") or "") for x in records if isinstance(x, dict)]
        if not ids or any(not x for x in ids) or len(ids) != len(set(ids)):
            raise RegistryError("model registry ids must be unique non-empty strings")
        self.repo_root = repo_root.resolve()
        self._records = {str(x["id"]): dict(x) for x in records}

    @classmethod
    def load(cls, path: Path = DEFAULT_REGISTRY, *, repo_root: Path | None = None):
        data = json.loads(path.read_text(encoding="utf-8"))
        root = (repo_root or Path(__file__).resolve().parents[3]).resolve()
        return cls(data, repo_root=root)

    def get(self, model_id: str) -> dict:
        if model_id not in self._records:
            raise RegistryError(f"unknown or unapproved model identifier: {model_id}")
        return dict(self._records[model_id])

    def list_for_capability(self, capability: str) -> list[dict]:
        return [
            dict(rec) for rec in self._records.values()
            if rec.get("capability") == capability and rec.get("enabled") is True
        ]

    def _availability(self, rec: dict) -> tuple[bool, str, str | None]:
        runtime = rec.get("runtime")
        if runtime == "repo_python":
            source = str(rec.get("source") or "")
            path = (self.repo_root / source).resolve()
            if self.repo_root != path and self.repo_root not in path.parents:
                return False, "repo_python source escaped repository root", None
            if not path.is_file():
                return False, f"repo_python source missing: {source}", None
            return True, "repo_python source available", str(path)

        if runtime == "builtin_python":
            source = str(rec.get("source") or "")
            path = (self.repo_root / source).resolve()
            if self.repo_root != path and self.repo_root not in path.parents:
                return False, "builtin_python source escaped repository root", None
            if not path.is_file():
                return False, f"builtin_python source missing: {source}", None
            return True, "builtin Python worker available", str(path)

        if runtime == "onnxruntime":
            artifact = str(rec.get("artifact_path") or "")
            if not artifact:
                return False, "ONNX model artifact_path is not declared", None
            path = (self.repo_root / artifact).resolve()
            if self.repo_root != path and self.repo_root not in path.parents:
                return False, "ONNX artifact escaped repository root", None
            try:
                import onnxruntime  # noqa: F401
            except Exception:
                return False, "onnxruntime is unavailable", str(path)
            if not path.is_file():
                return False, f"ONNX artifact unavailable: {artifact}", str(path)
            return True, "ONNX runtime and artifact available", str(path)

        return False, f"unsupported runtime: {runtime}", None

    def resolve(self, model_id: str) -> Resolution:
        requested = self.get(model_id)
        if requested.get("enabled") is not True:
            raise RegistryError(f"model is not approved/enabled: {model_id}")

        current_id = model_id
        seen: set[str] = set()
        used_fallback = False
        reasons: list[str] = []

        while current_id:
            if current_id in seen:
                raise RegistryError("model fallback cycle detected")
            seen.add(current_id)
            rec = self.get(current_id)
            if rec.get("enabled") is not True:
                raise RegistryError(f"fallback model is not approved/enabled: {current_id}")
            ok, reason, path = self._availability(rec)
            reasons.append(f"{current_id}: {reason}")
            if ok:
                return Resolution(
                    requested=model_id,
                    resolved=current_id,
                    available=True,
                    used_fallback=used_fallback,
                    reason="; ".join(reasons),
                    record=rec,
                    artifact_path=path,
                )
            next_id = rec.get("fallback")
            if not next_id:
                return Resolution(
                    requested=model_id,
                    resolved=current_id,
                    available=False,
                    used_fallback=used_fallback,
                    reason="; ".join(reasons),
                    record=rec,
                    artifact_path=path,
                )
            current_id = str(next_id)
            used_fallback = True

        raise RegistryError("model resolution failed")

    def resolve_capability(self, capability: str) -> Resolution:
        candidates = self.list_for_capability(capability)
        if not candidates:
            raise RegistryError(f"no approved model for capability: {capability}")
        return self.resolve(str(candidates[0]["id"]))
