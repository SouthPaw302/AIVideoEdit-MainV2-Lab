import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("fx_resolver",ROOT/"fx_resolver.py")
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

def test_fire_selection_is_deterministic_and_approved():
    ctx={"level":"still","environment":["tavern"],"objects":["fire"],"constraints":["no_weather"]}
    a=mod.resolve(ctx);b=mod.resolve(ctx)
    assert a==b
    assert a["effects"]
    assert all(x["gate_status"]=="approved" for x in a["effects"])
    assert "FX2-ATM-002" not in {x["id"] for x in a["effects"]}

def test_memory_overlay_recipe_is_found():
    out=mod.resolve({"level":"scene","needs":["memory","ghost_overlay"]})
    ids={x["id"] for x in out["effects"]}
    assert "RCP-GHOSTED-OBJECT" in {x["id"] for x in out["recipes"]}
    assert "FX2-TRANS-025" in ids

def test_proof_required_is_rejected_by_default():
    out=mod.resolve({"level":"still","objects":["glass"]})
    assert "FX2-SURFACE-003" not in {x["id"] for x in out["effects"]}
    assert any(x["id"]=="FX2-SURFACE-003" for x in out["rejected"])


def test_effect_limit_is_bounded():
    out=mod.resolve({"level":"scene","environment":["tavern"],"objects":["fire","instrument"],"needs":["audio_reactive","long_hold"]},max_effects=3)
    assert len(out["effects"]) <= 3


def test_camera_semantics_select_approved_camera_fx():
    cases={
        "slow_push":"FX2-CAMERA-023",
        "lateral_reframe":"FX2-CAMERA-023",
        "pullback":"FX2-CAMERA-023",
        "orbit":"FX2-CAMERA-022",
        "detail_push":"FX2-CAMERA-021",
        "rack_focus":"FX2-CAMERA-024",
    }
    for token,eid in cases.items():
        out=mod.resolve({"level":"scene","needs":[token]})
        ids={x["id"] for x in out["effects"]}
        assert eid in ids
        assert all(x["gate_status"]=="approved" for x in out["effects"])
