from __future__ import annotations
from pathlib import Path


def test_archive_manifest_does_not_hash_mutable_project_state():
    src=Path("prototype/backend_gui/production_archive.py").read_text(encoding="utf-8")
    canonical=src.split("canonical_files=",1)[1].split("\n",1)[0]
    assert '"PROJECT_STATE.json"' not in canonical


def test_archive_embeds_prearchive_state_snapshot():
    src=Path("prototype/backend_gui/production_archive.py").read_text(encoding="utf-8")
    assert 'state_before_archive=_read(project_dir/"PROJECT_STATE.json",{})' in src
    assert '"project_state_snapshot":state_before_archive' in src
