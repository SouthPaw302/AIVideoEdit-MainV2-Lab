from __future__ import annotations
from pathlib import Path


def test_operating_mutations_are_tool_api_gated():
    src=Path("prototype/backend_gui/tool_api.py").read_text(encoding="utf-8")
    for name in (
        "operating.configure_v2",
        "operating.update_next_action",
        "operating.lock_canon",
        "operating.set_refinement",
    ):
        assert f'"{name}":' in src
    assert 'if name.startswith("operating.")' in src
    assert '"operating.status"' in src


def test_stack_does_not_bypass_tool_api_for_operating_tools():
    src=Path("prototype/backend_gui/stack.py").read_text(encoding="utf-8")
    start=src.index("def _tool_call")
    block=src[start:start+500]
    assert 'name.startswith("operating.")' not in block
    assert "tool_api.call_tool" in block
