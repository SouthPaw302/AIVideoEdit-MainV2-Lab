"""MainV2 Lab must bootstrap its own main, preserving upstream source pin."""
import json
from pathlib import Path
import bootstrap

def test_lab_main_is_runtime_authority():
    assert bootstrap.REPOSITORY == "SouthPaw302/AIVideoEdit-MainV2-Lab"
    assert bootstrap.DEFAULT_REF == "main"
    root = Path(__file__).resolve().parents[1]
    lock = json.loads((root / "SOURCE_LOCK.json").read_text())
    assert lock["source_repository"] == "SouthPaw302/AIVideoEdit"
    assert lock["source_branch"] == "MainV2"
    assert lock["source_sha"] == "316fe96c7316d76d14308d5f27293e071aa20943"
