from __future__ import annotations

from prototype.backend_gui import remote_bridge


def test_bridge_disabled_by_default(monkeypatch):
    monkeypatch.delenv("AIVE_REMOTE_ENABLED",raising=False)
    monkeypatch.delenv("AIVE_REMOTE_TOKEN",raising=False)
    ok,reason=remote_bridge.authorize({"Authorization":"Bearer x"})
    assert ok is False
    assert "disabled" in reason


def test_missing_token_config_fails_closed(monkeypatch):
    monkeypatch.setenv("AIVE_REMOTE_ENABLED","1")
    monkeypatch.delenv("AIVE_REMOTE_TOKEN",raising=False)
    ok,reason=remote_bridge.authorize({"Authorization":"Bearer x"})
    assert ok is False
    assert "not configured" in reason


def test_valid_bearer_authorizes(monkeypatch):
    monkeypatch.setenv("AIVE_REMOTE_ENABLED","1")
    monkeypatch.setenv("AIVE_REMOTE_TOKEN","secret")
    ok,_=remote_bridge.authorize({"Authorization":"Bearer secret"})
    assert ok is True


def test_invalid_bearer_rejected(monkeypatch):
    monkeypatch.setenv("AIVE_REMOTE_ENABLED","1")
    monkeypatch.setenv("AIVE_REMOTE_TOKEN","secret")
    ok,_=remote_bridge.authorize({"Authorization":"Bearer wrong"})
    assert ok is False


def test_capabilities_explicitly_forbid_arbitrary_shell():
    doc=remote_bridge.capability_document(
        ["production.status","production.advance"],harness_enabled=False
    )
    assert doc["arbitrary_shell"] is False
    assert doc["production_authority"]=="existing_aivideoedit_tool_api"
    assert "runtime_gatekeeper" in doc["mutation_enforcement"]
