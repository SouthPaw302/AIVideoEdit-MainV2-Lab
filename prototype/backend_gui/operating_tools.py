#!/usr/bin/env python3
"""Tool-family adapter for Director Brain v3 operating-order controls."""
from __future__ import annotations
import production_operating_order

SCHEMAS=[
{"name":"operating.status","description":"Show Director Brain version, direction authority, production mode, canon and refinement state.","input_schema":{"type":"object","required":["project_id"],"properties":{"project_id":{"type":"string"}}}},
{"name":"operating.configure_v2","description":"Legacy compatibility alias for the Director Brain v3 operating-order configuration.","input_schema":{"type":"object","required":["project_id","direction_authority","production_mode","mission","current_user_direction","exact_next_action"],"properties":{"project_id":{"type":"string"},"direction_authority":{"type":"string","enum":["reference_led","music_led","user_directed"]},"production_mode":{"type":"string","enum":["living_scene","cinematic","hybrid"]},"mission":{"type":"string"},"current_user_direction":{"type":"string"},"exact_next_action":{"type":"string"}}}},
{"name":"operating.configure_v3","description":"Explicitly enable Director Brain v3 with mission, current-user direction, direction authority and production mode.","input_schema":{"type":"object","required":["project_id","direction_authority","production_mode","mission","current_user_direction","exact_next_action"],"properties":{"project_id":{"type":"string"},"direction_authority":{"type":"string","enum":["reference_led","music_led","user_directed"]},"production_mode":{"type":"string","enum":["living_scene","cinematic","hybrid"]},"mission":{"type":"string"},"current_user_direction":{"type":"string"},"exact_next_action":{"type":"string"}}}},
{"name":"operating.update_next_action","description":"Update the exact next action and optionally the current user direction without changing production mode.","input_schema":{"type":"object","required":["project_id","exact_next_action"],"properties":{"project_id":{"type":"string"},"exact_next_action":{"type":"string"},"current_user_direction":{"type":"string"}}}},
{"name":"operating.lock_canon","description":"Lock the accepted picture language/canon and optionally bind it to a ready hashed baseline asset.","input_schema":{"type":"object","required":["project_id","picture_language","items"],"properties":{"project_id":{"type":"string"},"picture_language":{"type":"string"},"items":{"type":"array","items":{"type":"string"}},"baseline_asset_id":{"type":"string"},"acceptance_statement":{"type":"string"}}}},
{"name":"operating.set_refinement","description":"Constrain later refinement to explicit allowed/forbidden changes around an accepted baseline.","input_schema":{"type":"object","required":["project_id","goal","allowed_changes","forbidden_changes"],"properties":{"project_id":{"type":"string"},"goal":{"type":"string"},"allowed_changes":{"type":"array","items":{"type":"string"}},"forbidden_changes":{"type":"array","items":{"type":"string"}},"restart_authorized":{"type":"boolean"}}}},]

def schemas():return SCHEMAS

def call(name,args):
    args=args or {};pid=str(args.get("project_id") or "")
    if name=="operating.status":return production_operating_order.status(pid)
    if name in {"operating.configure_v2","operating.configure_v3"}:return production_operating_order.configure(pid,direction_authority=str(args.get("direction_authority") or ""),production_mode=str(args.get("production_mode") or ""),mission=str(args.get("mission") or ""),current_user_direction=str(args.get("current_user_direction") or ""),exact_next_action=str(args.get("exact_next_action") or ""))
    if name=="operating.update_next_action":return production_operating_order.update_next_action(pid,exact_next_action=str(args.get("exact_next_action") or ""),current_user_direction=str(args.get("current_user_direction") or ""))
    if name=="operating.lock_canon":return production_operating_order.lock_canon(pid,picture_language=str(args.get("picture_language") or ""),items=args.get("items") if isinstance(args.get("items"),list) else [],baseline_asset_id=str(args.get("baseline_asset_id") or ""),acceptance_statement=str(args.get("acceptance_statement") or ""))
    if name=="operating.set_refinement":return production_operating_order.set_refinement(pid,goal=str(args.get("goal") or ""),allowed_changes=args.get("allowed_changes") if isinstance(args.get("allowed_changes"),list) else [],forbidden_changes=args.get("forbidden_changes") if isinstance(args.get("forbidden_changes"),list) else [],restart_authorized=bool(args.get("restart_authorized",False)))
    raise ValueError(f"unknown operating tool: {name}")
