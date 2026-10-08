from __future__ import annotations

from general.reusable.tools.jev_decision import ALLOWED, decide


def test_pass():
    result=decide({"gate":"PASS","checks":{"a":True}})
    assert result["decision"]=="PASS"


def test_fail_from_gatekeeper_deny():
    result=decide({"gate":"DENY","checks":{"a":True},"next_action_permitted":True})
    assert result["decision"]=="FAIL"


def test_retry():
    result=decide({"gate":"PASS","checks":{"a":True},"retryable_error":True})
    assert result["decision"]=="RETRY"


def test_continue():
    result=decide({"gate":"PASS","checks":{"a":True},"next_action_permitted":True})
    assert result["decision"]=="CONTINUE"


def test_escalate_ambiguous():
    result=decide({"gate":"PASS","checks":{"a":None}})
    assert result["decision"]=="ESCALATE"


def test_low_confidence_model_escalates():
    result=decide({
        "gate":"PASS",
        "checks":{"a":True},
        "model_observations":[{"authority":"evidence_only","confidence":0.2}],
        "next_action_permitted":True,
    })
    assert result["decision"]=="ESCALATE"


def test_identical_inputs_are_deterministic():
    evidence={
        "gate":"PASS",
        "checks":{"gatekeeper":True,"attestation":True},
        "model_observations":[{"authority":"evidence_only","confidence":0.9}],
        "next_action_permitted":True,
    }
    a=decide(evidence)
    b=decide(evidence)
    assert a==b
    assert a["decision"] in ALLOWED
