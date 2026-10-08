from pathlib import Path

def test_project_boot_supports_offline_mode():
    src=Path("prototype/backend_gui/production_project.py").read_text(encoding="utf-8")
    assert 'AIVE_OFFLINE' in src
    assert 'boot_cmd.append("--offline")' in src

def test_capsule_refresh_supports_offline_mode():
    src=Path("prototype/backend_gui/tool_api.py").read_text(encoding="utf-8")
    assert 'AIVE_OFFLINE' in src
    assert 'boot_cmd.append("--offline")' in src
