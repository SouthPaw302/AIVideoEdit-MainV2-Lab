from __future__ import annotations

from general.reusable.tools.harness_router import route_jev


def test_jev_escalates_to_primary_agent_when_harness_disabled(monkeypatch):
    monkeypatch.delenv("AIVE_HARNESS_ENABLED", raising=False)
    result=route_jev({"decision":"ESCALATE"})
    assert result["route"]=="authorized_sandbox_agent"


def test_jev_escalates_to_optional_harness_when_enabled(monkeypatch):
    monkeypatch.setenv("AIVE_HARNESS_ENABLED","1")
    result=route_jev({"decision":"ESCALATE"})
    assert result["route"]=="optional_harness_specialist"


def test_non_escalation_does_not_invoke_harness(monkeypatch):
    monkeypatch.setenv("AIVE_HARNESS_ENABLED","1")
    result=route_jev({"decision":"CONTINUE"})
    assert result["route"]=="none"
