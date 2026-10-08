from __future__ import annotations

import json
from pathlib import Path

import pytest

from general.reusable.tools.model_registry import ModelRegistry, RegistryError


def registry(tmp_path: Path, models: list[dict]) -> ModelRegistry:
    return ModelRegistry(
        {"schema": "aivideoedit.model-registry.v1", "models": models},
        repo_root=tmp_path,
    )


def test_repo_model_resolves_when_source_exists(tmp_path: Path):
    source = tmp_path / "tools" / "worker.py"
    source.parent.mkdir(parents=True)
    source.write_text("pass\n", encoding="utf-8")
    r = registry(tmp_path, [{
        "id": "repo-v1", "capability": "x", "runtime": "repo_python",
        "source": "tools/worker.py", "enabled": True, "fallback": None,
    }])
    result = r.resolve("repo-v1")
    assert result.available is True
    assert result.resolved == "repo-v1"
    assert result.used_fallback is False


def test_missing_onnx_falls_back_to_repo_worker(tmp_path: Path):
    source = tmp_path / "fallback.py"
    source.write_text("pass\n", encoding="utf-8")
    r = registry(tmp_path, [
        {
            "id": "onnx-v1", "capability": "x", "runtime": "onnxruntime",
            "artifact_path": "models/missing.onnx", "enabled": True,
            "fallback": "repo-v1",
        },
        {
            "id": "repo-v1", "capability": "x", "runtime": "repo_python",
            "source": "fallback.py", "enabled": True, "fallback": None,
        },
    ])
    result = r.resolve("onnx-v1")
    assert result.available is True
    assert result.resolved == "repo-v1"
    assert result.used_fallback is True


def test_unknown_model_rejected(tmp_path: Path):
    r = registry(tmp_path, [{
        "id": "known", "capability": "x", "runtime": "repo_python",
        "source": "missing.py", "enabled": True, "fallback": None,
    }])
    with pytest.raises(RegistryError, match="unknown or unapproved"):
        r.resolve("unknown")


def test_disabled_model_rejected(tmp_path: Path):
    r = registry(tmp_path, [{
        "id": "disabled", "capability": "x", "runtime": "repo_python",
        "source": "missing.py", "enabled": False, "fallback": None,
    }])
    with pytest.raises(RegistryError, match="not approved/enabled"):
        r.resolve("disabled")


def test_default_registry_declares_cpu_first_authority():
    path = Path("general/reusable/intelligence/MODEL_REGISTRY.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    models = {x["id"]: x for x in data["models"]}
    onnx = models["music-beat-onnx-v1"]
    assert onnx["hardware"]["required"] == "cpu"
    assert onnx["fallback"] == "music-beat-micro-dsp-v1"
    assert onnx["authority"] == "evidence_only"
