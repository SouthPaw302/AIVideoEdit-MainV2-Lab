from __future__ import annotations
from pathlib import Path


def test_fx_runtime_dependencies_are_declared():
    req=Path("general/reusable/fx_v2/requirements-runtime.txt").read_text(encoding="utf-8")
    assert "numpy" in req
    assert "opencv-python-headless" in req


def test_fx_runtime_imports_match_dependency_manifest():
    runtime=Path("general/reusable/fx_v2/runtime.py").read_text(encoding="utf-8")
    assert "import cv2" in runtime
    assert "import numpy as np" in runtime
