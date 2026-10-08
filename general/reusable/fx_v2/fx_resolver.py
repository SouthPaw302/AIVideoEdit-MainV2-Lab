#!/usr/bin/env python3
"""Deterministic FX resolver for AIVideoEdit.

Reads the canonical FX registry plus reusable recipe catalog and produces a
bounded, stable recommendation from explicit batch/scene/still semantics.
It does not inspect pixels or invent scene facts. Agents must supply truthful
semantic tags derived from the accepted media/shot package.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path

HERE=Path(__file__).resolve().parent
DEFAULT_REGISTRY=HERE/"registry.json"
DEFAULT_RECIPES=HERE/"recipes.json"

DIRECT_RULES={
    "fire":["FX2-FIRE-001","FX2-LIGHT-023","FX2-FIRE-002"],
    "hearth":["FX2-FIRE-001","FX2-LIGHT-023"],
    "forge":["FX2-FIRE-001","FX2-FIRE-002","FX2-ATM-001"],
    "rain":["FX2-ATM-002"],
    "smoke":["FX2-ATM-001"],
    "fog":["FX2-ATM-021"],
    "water":["FX2-MOTION-003"],
    "wet_ground":["FX2-SURFACE-023"],
    "reflection":["FX2-SURFACE-023"],
    "crowd":["FX2-MOTION-021"],
    "memory":["FX2-TRANS-025"],
    "threshold":["FX2-LIGHT-026"],
    "glass":["FX2-SURFACE-003"],
    "instrument":["FX2-LIGHT-003"],
    "parallax":["FX2-SPATIAL-021"],
    "heat":["FX2-DISTORT-021"],
    "camera":["FX2-CAMERA-023"],
    "camera_travel":["FX2-CAMERA-023"],
    "slow_push":["FX2-CAMERA-023"],
    "push_in":["FX2-CAMERA-023"],
    "forward_push":["FX2-CAMERA-023"],
    "reframe":["FX2-CAMERA-023"],
    "lateral_reframe":["FX2-CAMERA-023"],
    "pullback":["FX2-CAMERA-023"],
    "reverse_reveal":["FX2-CAMERA-023"],
    "orbit":["FX2-CAMERA-022"],
    "camera_orbit":["FX2-CAMERA-022"],
    "detail_push":["FX2-CAMERA-021"],
    "rack_focus":["FX2-CAMERA-024"],
}
INCOMPATIBLE={
    "interior_dry":{"FX2-ATM-002","FX2-MOTION-003","FX2-SURFACE-023"},
    "no_fire":{"FX2-FIRE-001","FX2-FIRE-002","FX2-LIGHT-023"},
    "no_weather":{"FX2-ATM-002","FX2-ATM-003"},
    "no_global_warp":{"FX2-MOTION-026"},
}

def _load(path:Path):
    return json.loads(path.read_text(encoding="utf-8"))

def _tokens(context:dict)->set[str]:
    out=set()
    for key in ("environment","materials","objects","needs","motifs","tags","constraints"):
        value=context.get(key,[])
        if isinstance(value,str): value=[value]
        for item in value or []:
            token=str(item).strip().lower().replace(" ","_").replace("-","_")
            if token: out.add(token)
    return out

def _eligible(effect:dict,allow_proof_required:bool)->bool:
    gate=str(effect.get("gate_status") or "")
    if gate=="approved": return True
    return bool(allow_proof_required and gate=="proof_required")

def _recipe_score(recipe:dict,tokens:set[str]):
    sel=recipe.get("select_if") or {}
    all_tags={str(x).lower() for x in sel.get("all",[])}
    any_tags={str(x).lower() for x in sel.get("any",[])}
    none_tags={str(x).lower() for x in sel.get("none",[])}
    if all_tags and not all_tags.issubset(tokens): return None
    if none_tags & tokens: return None
    if any_tags and not (any_tags & tokens): return None
    hits=len(all_tags & tokens)+len(any_tags & tokens)
    return int(recipe.get("priority",0))*100+hits

def resolve(context:dict,registry_path:Path=DEFAULT_REGISTRY,recipes_path:Path=DEFAULT_RECIPES,*,allow_proof_required:bool=False,max_effects:int|None=None)->dict:
    reg=_load(Path(registry_path)); recipes_doc=_load(Path(recipes_path))
    effects=reg.get("effects") or {}; tokens=_tokens(context)
    limit=int(max_effects or recipes_doc.get("policy",{}).get("max_default_effects",6))
    excluded=set()
    for tag,ids in INCOMPATIBLE.items():
        if tag in tokens: excluded.update(ids)
    selected_recipes=[]; candidates=[]
    for recipe in recipes_doc.get("recipes",[]):
        score=_recipe_score(recipe,tokens)
        if score is None: continue
        selected_recipes.append((score,recipe))
        for rank,eid in enumerate(recipe.get("effects",[])):
            candidates.append((score-rank,eid,f"recipe:{recipe.get('id')}"))
    for token in sorted(tokens):
        for rank,eid in enumerate(DIRECT_RULES.get(token,[])):
            candidates.append((5000-rank,eid,f"semantic:{token}"))
    selected_recipes.sort(key=lambda x:(-x[0],str(x[1].get("id"))))
    candidates.sort(key=lambda x:(-x[0],x[1],x[2]))
    chosen=[]; seen=set(); rejected=[]
    for score,eid,reason in candidates:
        if eid in seen: continue
        seen.add(eid)
        if eid in excluded:
            rejected.append({"id":eid,"reason":"context_exclusion"}); continue
        item=effects.get(eid)
        if not isinstance(item,dict):
            rejected.append({"id":eid,"reason":"not_in_canonical_registry"}); continue
        if not _eligible(item,allow_proof_required):
            rejected.append({"id":eid,"reason":f"gate:{item.get('gate_status')}"}); continue
        chosen.append({"id":eid,"name":item.get("name"),"family":item.get("family"),"gate_status":item.get("gate_status"),"reason":reason})
        if len(chosen)>=limit: break
    protect=[]; steps=[]
    for _,recipe in selected_recipes:
        for x in recipe.get("protect",[]):
            if x not in protect: protect.append(x)
        for x in recipe.get("steps",[]):
            if x not in steps: steps.append(x)
    return {
        "schema":"aivideoedit.fx-resolution.v1",
        "level":str(context.get("level") or "scene"),
        "tokens":sorted(tokens),
        "selection_policy":recipes_doc.get("policy",{}).get("selection_order",[]),
        "recipes":[{"id":r.get("id"),"name":r.get("name")} for _,r in selected_recipes],
        "effects":chosen,
        "protect":protect,
        "composition_steps":steps,
        "rejected":rejected,
        "requires_proof":any(x.get("gate_status")=="proof_required" for x in chosen),
        "source":{"registry":str(Path(registry_path)),"recipes":str(Path(recipes_path))},
    }

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--context",type=Path,required=True)
    p.add_argument("--registry",type=Path,default=DEFAULT_REGISTRY)
    p.add_argument("--recipes",type=Path,default=DEFAULT_RECIPES)
    p.add_argument("--allow-proof-required",action="store_true")
    p.add_argument("--max-effects",type=int)
    a=p.parse_args()
    context=_load(a.context)
    print(json.dumps(resolve(context,a.registry,a.recipes,allow_proof_required=a.allow_proof_required,max_effects=a.max_effects),indent=2,sort_keys=True))
    return 0
if __name__=="__main__": raise SystemExit(main())
