from __future__ import annotations

from pathlib import Path
import importlib.util


def _source():
    return Path("prototype/backend_gui/tool_api.py").read_text(encoding="utf-8")


def test_project_prepare_is_preproduction_bootstrap_operation():
    src=_source()
    block=src.split("_UNGATED_BOOTSTRAP_TOOLS =",1)[1].split("}",1)[0]
    assert '"project.prepare"' in block


def test_capsule_refresh_preserves_validation_authority():
    src=_source()
    assert 'os.environ.get("AIVE_CORE_REF", "main")' in src
    assert 'env["AIVIDEOEDIT_AUTHORITY_REF"] = core_ref' in src
    assert 'env["AIVIDEOEDIT_VALIDATION_MODE"] = "1"' in src
