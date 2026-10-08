#!/usr/bin/env python3
"""Fail-closed AIVideoEdit production-state validator.

Normal mode requires a valid bootstrap session attestation. The portable
bootstrap invokes `--bootstrap-phase` once to validate the active branch using
the freshly materialized current-main OS; only then is a session attestation
written.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

from branch_policy import resolve_production_project
from recipe_execution_guard import validate as validate_recipe_execution
from execution_ledger import verify_ledger
from director_checkpoint import verify_checkpoints

SCRIPT_ROOT = Path(__file__).resolve().parents[3]
if os.environ.get("AIVIDEOEDIT_REPO_ROOT"):
    ROOT = Path(os.environ["AIVIDEOEDIT_REPO_ROOT"]).resolve()
elif SCRIPT_ROOT.name == "os" and SCRIPT_ROOT.parent.name == ".aivideoedit":
    ROOT = SCRIPT_ROOT.parent.parent.resolve()
else:
    ROOT = SCRIPT_ROOT.resolve()
if os.environ.get("AIVIDEOEDIT_OS_ROOT"):
    OS_ROOT = Path(os.environ["AIVIDEOEDIT_OS_ROOT"]).resolve()
elif SCRIPT_ROOT.name == "os" and SCRIPT_ROOT.parent.name == ".aivideoedit":
    OS_ROOT = SCRIPT_ROOT.resolve()
else:
    OS_ROOT = ROOT

CONTRACT_PATH = OS_ROOT / "general/reusable/PRODUCTION_CONTRACT.json"
MEDIA_PATH = OS_ROOT / "general/reusable/MEDIA_CAPABILITY_MATRIX.json"
MODES_PATH = OS_ROOT / "general/reusable/PRODUCTION_MODES.json"
SESSION_PATH = ROOT / ".aivideoedit/session.json"


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        try:
            display = path.relative_to(ROOT)
        except ValueError:
            display = path
        raise SystemExit(f"FAIL: missing {display}")
    except Exception as e:
        try:
            display = path.relative_to(ROOT)
        except ValueError:
            display = path
        raise SystemExit(f"FAIL: invalid JSON {display}: {e}")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def truthy(v):
    return v is True


def nonempty_string(v):
    return isinstance(v, str) and bool(v.strip())


def string_list(v, *, nonempty=False):
    if not isinstance(v, list) or not all(isinstance(x, str) and x.strip() for x in v):
        return False
    return bool(v) if nonempty else True


def fail(msg, errors):
    errors.append(msg)


def discover_project(branch: str):
    project, error = resolve_production_project(ROOT, branch)
    if error:
        raise SystemExit(f"FAIL: {error}")
    if project is None:
        raise SystemExit("FAIL: production project could not be resolved")
    return project


def verify_bootstrap_session(branch: str):
    if not SESSION_PATH.is_file():
        return [
            "bootstrap session missing; run `python bootstrap.py boot --repo-root <repo>` before production work"
        ]
    session = load_json(SESSION_PATH)
    errors = []
    if session.get("schema") != "aivideoedit.session.v1":
        fail("invalid bootstrap session schema", errors)
    if session.get("guard_result") != "PASS":
        fail("bootstrap session does not contain guard_result=PASS", errors)
    if session.get("branch") != branch:
        fail(f"bootstrap branch mismatch: {session.get('branch')} != {branch}", errors)

    os_root = Path(session.get("os_root") or "")
    if not os_root.is_absolute():
        os_root = (ROOT / os_root).resolve()
    if not os_root.is_dir():
        fail(f"bootstrapped OS root missing: {os_root}", errors)
        return errors

    recorded = session.get("os_files", {})
    critical = [
        "AGENTS.md",
        "PRIME_DIRECTIVE.md",
        "SOUL.md",
        "general/reusable/PRODUCTION_CONTRACT.json",
        "general/reusable/PRODUCTION_MODES.json",
        "general/reusable/MODE_AWARE_QC.md",
        "general/reusable/MEDIA_CAPABILITY_MATRIX.json",
        "general/reusable/tools/production_guard.py",
        "general/reusable/fx_v2/registry.json",
        "general/reusable/fx_v2/promoted_effects.py",
        "general/reusable/STANDARD_WORKFLOW_REGISTRY.json",
        "general/reusable/tools/workflow_resolver.py",
        "general/reusable/tools/workflow_guard.py",
        "general/reusable/tools/recipe_execution_guard.py",
        "general/reusable/tools/execution_ledger.py",
        "general/reusable/tools/director_checkpoint.py",
        "general/reusable/fx_v2/executor.py",
        "general/reusable/fx_v2/execution_guard.py",
    ]
    for rel in critical:
        p = os_root / rel
        expected = recorded.get(rel)
        if not p.is_file():
            fail(f"bootstrapped OS file missing: {rel}", errors)
        elif not expected:
            fail(f"bootstrap attestation missing hash for: {rel}", errors)
        elif sha256_file(p) != expected:
            fail(f"bootstrapped OS file changed after attestation: {rel}", errors)

    os_guard = os_root / "general/reusable/tools/production_guard.py"
    if os_guard.is_file():
        this_hash = sha256_file(Path(__file__).resolve())
        os_hash = sha256_file(os_guard)
        if this_hash != os_hash and Path(__file__).resolve() != os_guard.resolve():
            fail(
                "stale branch production_guard.py invoked; run the guard from "
                ".aivideoedit/os/general/reusable/tools/production_guard.py",
                errors,
            )
    return errors


def validate_no_reference_visual_direction_gate(plan, contract, modes, errors):
    """Validate explicit user selection among multiple no-reference visual routes."""
    if not truthy(plan.get("user_approach_established")):
        fail(
            "no-reference production requires user_approach_established=true "
            "before generated production media",
            errors,
        )

    gate = plan.get("visual_direction_gate")
    if not isinstance(gate, dict):
        fail(
            "no-reference production requires MEDIA_PLAN.visual_direction_gate",
            errors,
        )
        return

    if not truthy(gate.get("required")):
        fail("visual_direction_gate.required must be true", errors)
    if not truthy(gate.get("presented_in_chat")):
        fail(
            "visual direction options must be presented to the user in chat "
            "(visual_direction_gate.presented_in_chat=true)",
            errors,
        )
    if not truthy(gate.get("locked")):
        fail("visual_direction_gate must be locked before APPROACH_ESTABLISHED", errors)

    min_options = int(
        contract.get("reference_policy", {}).get(
            "no_visual_reference_min_options", 3
        )
    )
    min_beats = int(
        contract.get("reference_policy", {}).get(
            "no_visual_reference_min_storyboard_beats", 3
        )
    )
    valid_modes = set(modes.get("production_modes", {}).keys())
    options = gate.get("options")
    if not isinstance(options, list) or len(options) < min_options:
        fail(
            f"no-reference visual direction gate requires at least {min_options} "
            "numbered artistic-rendering options",
            errors,
        )
        return

    option_numbers = []
    names = []
    story_routes = []
    render_routes = []

    for index, option in enumerate(options, start=1):
        if not isinstance(option, dict):
            fail(f"visual direction option {index} must be an object", errors)
            continue

        number = option.get("number")
        if not isinstance(number, int) or isinstance(number, bool) or number < 1:
            fail(f"visual direction option {index} requires a positive integer number", errors)
        else:
            option_numbers.append(number)

        name = option.get("name")
        story_approach = option.get("story_approach")
        rendering_route = option.get("rendering_route")
        production_mode = option.get("production_mode")
        if not nonempty_string(name):
            fail(f"visual direction option {index} requires a name", errors)
        else:
            names.append(name.strip().casefold())
        if not nonempty_string(story_approach):
            fail(f"visual direction option {index} requires story_approach", errors)
        else:
            story_routes.append(story_approach.strip().casefold())
        if not nonempty_string(rendering_route):
            fail(f"visual direction option {index} requires rendering_route", errors)
        else:
            render_routes.append(rendering_route.strip().casefold())
        if production_mode not in valid_modes:
            fail(
                f"visual direction option {index} requires valid production_mode "
                f"({', '.join(sorted(valid_modes))})",
                errors,
            )

        storyboard = option.get("storyboard")
        if not isinstance(storyboard, list) or len(storyboard) < min_beats:
            fail(
                f"visual direction option {index} requires a numbered mini-storyboard "
                f"with at least {min_beats} beats/frames",
                errors,
            )
            continue

        beat_numbers = []
        for beat_index, beat in enumerate(storyboard, start=1):
            if not isinstance(beat, dict):
                fail(
                    f"visual direction option {index} storyboard beat {beat_index} "
                    "must be an object",
                    errors,
                )
                continue
            beat_number = beat.get("number")
            description = beat.get("description")
            if (
                not isinstance(beat_number, int)
                or isinstance(beat_number, bool)
                or beat_number < 1
            ):
                fail(
                    f"visual direction option {index} storyboard beat {beat_index} "
                    "requires a positive integer number",
                    errors,
                )
            else:
                beat_numbers.append(beat_number)
            if not nonempty_string(description):
                fail(
                    f"visual direction option {index} storyboard beat {beat_index} "
                    "requires a description",
                    errors,
                )
        if len(beat_numbers) != len(set(beat_numbers)):
            fail(f"visual direction option {index} storyboard numbers must be unique", errors)

    if len(option_numbers) != len(set(option_numbers)):
        fail("visual direction option numbers must be unique", errors)
    if len(names) != len(set(names)):
        fail("visual direction option names must be distinct", errors)
    if len(story_routes) != len(set(story_routes)):
        fail("visual direction story approaches must be distinct", errors)
    if len(render_routes) != len(set(render_routes)):
        fail("visual direction rendering routes must be distinct", errors)

    selection = gate.get("user_selection")
    if not isinstance(selection, dict):
        fail("visual_direction_gate.user_selection is required", errors)
        return

    status = selection.get("status")
    if status not in {"selected", "hybrid"}:
        fail("visual direction user_selection.status must be selected or hybrid", errors)

    selected_numbers = selection.get("selected_option_numbers")
    if not isinstance(selected_numbers, list) or not selected_numbers:
        fail("user selection requires selected_option_numbers", errors)
    else:
        invalid = [
            n for n in selected_numbers
            if not isinstance(n, int)
            or isinstance(n, bool)
            or n not in set(option_numbers)
        ]
        if invalid:
            fail(
                "user selection references unknown visual direction option number(s): "
                + ", ".join(str(n) for n in invalid),
                errors,
            )
        if status == "selected" and len(selected_numbers) != 1:
            fail("selected status must reference exactly one option number", errors)
        if status == "hybrid" and len(selected_numbers) < 2:
            fail("hybrid status must reference at least two option numbers", errors)

    recorded = selection.get("recorded_user_instruction")
    if not nonempty_string(recorded):
        fail(
            "visual direction gate requires recorded_user_instruction from the "
            "current user's explicit selection/modification",
            errors,
        )


def validate_operating_order(project, state, stage, states, modes, errors):
    version = state.get("director_brain_version", 0)
    try:
        version = int(version or 0)
    except (TypeError, ValueError):
        fail("PROJECT_STATE director_brain_version must be an integer", errors)
        return None

    path = project / "OPERATING_ORDER.json"
    if version < 2:
        return load_json(path) if path.is_file() else None

    if not path.is_file():
        fail("Director Brain v3 requires OPERATING_ORDER.json", errors)
        return None

    order = load_json(path)
    if order.get("schema") != "aivideoedit.operating-order.v1":
        fail("OPERATING_ORDER.json has invalid schema", errors)

    valid_authorities = set(modes.get("direction_authorities", []))
    valid_modes = set(modes.get("production_modes", {}).keys())
    authority = order.get("direction_authority")
    mode = order.get("production_mode")

    for key in ("mission", "current_user_direction", "exact_next_action"):
        if not nonempty_string(order.get(key)):
            fail(f"OPERATING_ORDER.{key} must be a non-empty string", errors)

    if authority not in valid_authorities:
        fail(
            "OPERATING_ORDER.direction_authority must be one of: "
            + ", ".join(sorted(valid_authorities)),
            errors,
        )
    if mode not in valid_modes:
        fail(
            "OPERATING_ORDER.production_mode must be one of: "
            + ", ".join(sorted(valid_modes)),
            errors,
        )

    canon = order.get("canon_lock")
    if not isinstance(canon, dict):
        fail("OPERATING_ORDER.canon_lock must be an object", errors)
        canon = {}
    canon_locked = canon.get("locked")
    if not isinstance(canon_locked, bool):
        fail("OPERATING_ORDER.canon_lock.locked must be boolean", errors)
    if canon_locked:
        if not nonempty_string(canon.get("picture_language")):
            fail("locked canon requires canon_lock.picture_language", errors)
        if not isinstance(canon.get("items"), list) or not canon.get("items"):
            fail("locked canon requires at least one canon_lock.items entry", errors)

    baseline = order.get("accepted_baseline")
    if not isinstance(baseline, dict):
        fail("OPERATING_ORDER.accepted_baseline must be an object", errors)
        baseline = {}
    status = baseline.get("status")
    if status not in {"none", "accepted", "retired"}:
        fail("accepted_baseline.status must be none, accepted, or retired", errors)
    if status == "accepted":
        if canon_locked is not True:
            fail("an accepted baseline requires canon_lock.locked=true", errors)
        if not nonempty_string(baseline.get("file_or_locator")):
            fail("accepted baseline requires file_or_locator", errors)
        if not nonempty_string(baseline.get("sha256")):
            fail("accepted baseline requires sha256", errors)
        elif not re.fullmatch(r"[0-9a-fA-F]{64}", baseline.get("sha256").strip()):
            fail("accepted baseline sha256 must contain 64 hexadecimal characters", errors)
        if not nonempty_string(baseline.get("user_acceptance_statement")):
            fail("accepted baseline requires user_acceptance_statement", errors)

        locator = baseline.get("file_or_locator")
        if nonempty_string(locator):
            candidate = Path(locator)
            if not candidate.is_absolute():
                candidate = project / candidate
            if candidate.is_file() and nonempty_string(baseline.get("sha256")):
                if sha256_file(candidate).lower() != baseline.get("sha256").strip().lower():
                    fail("accepted baseline local file hash does not match OPERATING_ORDER", errors)

    refinement = order.get("refinement_scope")
    if not isinstance(refinement, dict):
        fail("OPERATING_ORDER.refinement_scope must be an object", errors)
        refinement = {}
    active = refinement.get("active")
    if not isinstance(active, bool):
        fail("OPERATING_ORDER.refinement_scope.active must be boolean", errors)
    if active:
        if status != "accepted":
            fail("active refinement requires accepted_baseline.status=accepted", errors)
        if not nonempty_string(refinement.get("goal")):
            fail("active refinement requires refinement_scope.goal", errors)
        if not string_list(refinement.get("allowed_changes"), nonempty=True):
            fail("active refinement requires non-empty allowed_changes", errors)
        if not string_list(refinement.get("forbidden_changes"), nonempty=True):
            fail("active refinement requires non-empty forbidden_changes", errors)
        if not isinstance(refinement.get("restart_authorized"), bool):
            fail("refinement_scope.restart_authorized must be boolean", errors)

    idx = states.index(stage)

    def at(name):
        return idx >= states.index(name)

    if at("STORYBOARD_LOCKED") and mode in {"living_scene", "hybrid"}:
        script_path = project / "SCRIPT.json"
        if script_path.is_file():
            script = load_json(script_path)
            entries = script.get("entries")
            if not isinstance(entries, list) or not entries:
                fail("Director Brain v3 SCRIPT.json requires entries", errors)
            else:
                for i, entry in enumerate(entries, start=1):
                    if not isinstance(entry, dict):
                        fail(f"SCRIPT entry {i} must be an object", errors)
                        continue
                    entry_mode = mode
                    if mode == "hybrid":
                        entry_mode = entry.get("production_mode")
                        if entry_mode not in {"living_scene", "cinematic"}:
                            fail(
                                f"hybrid SCRIPT entry {i} requires production_mode "
                                "living_scene or cinematic",
                                errors,
                            )
                            continue
                    if entry_mode == "living_scene":
                        if not string_list(entry.get("motion_regions"), nonempty=True):
                            fail(
                                f"living-scene SCRIPT entry {i} requires semantic motion_regions",
                                errors,
                            )
                        if not string_list(entry.get("protected_regions"), nonempty=True):
                            fail(
                                f"living-scene SCRIPT entry {i} requires protected_regions",
                                errors,
                            )

    supervision=order.get("director_supervision") if isinstance(order,dict) else None
    if version >= 4:
        if not isinstance(supervision,dict) or supervision.get("required") is not True:
            fail("Director Brain v4 requires OPERATING_ORDER.director_supervision.required=true", errors)
        else:
            checkpoints=project/str(supervision.get("checkpoint_file") or "DIRECTOR_CHECKPOINTS.json")
            ledger=project/str(supervision.get("execution_ledger_file") or "PRODUCTION_EXECUTION_LEDGER.json")
            if at("SHOT_PROOFS_ACCEPTED"):
                errors.extend(verify_checkpoints(checkpoints,"representative_proof"))
            if at("ASSEMBLED"):
                errors.extend(verify_checkpoints(checkpoints,"rough_cut"))
            if at("FINAL_QC_PASSED"):
                errors.extend(verify_checkpoints(checkpoints,"final_review"))
                errors.extend(verify_ledger(ledger))

    if at("SHOT_PROOFS_ACCEPTED") and not truthy(state.get("mode_aware_proofs_accepted")):
        fail(
            "Director Brain v3 SHOT_PROOFS_ACCEPTED requires mode_aware_proofs_accepted=true",
            errors,
        )
    if at("FINAL_QC_PASSED") and not truthy(state.get("mode_aware_qc_passed")):
        fail(
            "Director Brain v3 FINAL_QC_PASSED requires mode_aware_qc_passed=true",
            errors,
        )

    return order


def validate_asset_lifecycle(project, state, contract, errors):
    try:
        version = int(state.get("director_brain_version", 0) or 0)
    except (TypeError, ValueError):
        return
    if version < 2:
        return

    manifest = load_json(project / "ASSET_MANIFEST.json")
    allowed = set(contract.get("asset_lifecycle_policy", {}).get("statuses", []))
    entries = manifest.get("assets")
    if entries is None:
        entries = manifest.get("entries")
    if entries is None:
        return
    if not isinstance(entries, list):
        fail("ASSET_MANIFEST assets/entries must be a list", errors)
        return
    for i, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            continue
        status = entry.get("lifecycle_status")
        if status is not None and status not in allowed:
            fail(
                f"ASSET_MANIFEST entry {i} has invalid lifecycle_status: {status}",
                errors,
            )


def validate(branch: str):
    contract = load_json(CONTRACT_PATH)
    media = load_json(MEDIA_PATH)
    modes = load_json(MODES_PATH)
    errors = []

    if branch == "main":
        for p in [
            "AGENTS.md",
            "PRIME_DIRECTIVE.md",
            "SOUL.md",
            "BIBLE.md",
            "SYSTEM_INDEX.md",
            "general/reusable/AIVIDEOEDIT_OS_MANIFEST.json",
            "general/reusable/PRODUCTION_CONTRACT.json",
            "general/reusable/PRODUCTION_MODES.json",
            "general/reusable/PRODUCTION_MODES.md",
            "general/reusable/DOCTRINE_LIVING_SCENE.md",
            "general/reusable/MODE_AWARE_QC.md",
            "general/reusable/PRODUCTION_PIPELINE.md",
            "general/reusable/STYLE_CONTRACT.md",
            "general/reusable/fx_v2/registry.json",
        "general/reusable/fx_v2/promoted_effects.py",
        "general/reusable/STANDARD_WORKFLOW_REGISTRY.json",
        "general/reusable/tools/workflow_resolver.py",
        "general/reusable/tools/workflow_guard.py",
            "projects/OPERATING_ORDER_TEMPLATE.json",
        ]:
            if not (OS_ROOT / p).is_file():
                fail(f"missing system file: {p}", errors)
        return errors

    project, branch_error = resolve_production_project(ROOT, branch)
    if branch_error:
        return [branch_error]
    if project is None:
        return [f"production project could not be resolved for {branch}"]

    for name in contract["required_project_files"]:
        if not (project / name).is_file():
            fail(f"missing required project file: {project.relative_to(ROOT)}/{name}", errors)
    if errors:
        return errors

    state = load_json(project / "PROJECT_STATE.json")
    auth = load_json(project / "SOURCE_AUTHORITY.json")
    refs = load_json(project / "REFERENCE_MANIFEST.json")
    plan = load_json(project / "MEDIA_PLAN.json")
    states = contract["states"]
    stage = state.get("stage")
    if stage not in states:
        return [f"invalid production stage: {stage}"]

    expected_branch = state.get("branch")
    if expected_branch and expected_branch != branch:
        fail(f"PROJECT_STATE branch mismatch: {expected_branch} != {branch}", errors)

    for denied in contract["default_denied_sources"]:
        if (
            auth.get("allow", {}).get(denied) is True
            and denied not in auth.get("explicit_user_authorizations", [])
        ):
            fail(f"historical source enabled without explicit user authorization: {denied}", errors)

    idx = states.index(stage)

    def at(name):
        return idx >= states.index(name)

    order = validate_operating_order(project, state, stage, states, modes, errors)
    validate_asset_lifecycle(project, state, contract, errors)
    validate_recipe_execution(project, state, order or {}, stage, states, errors)

    if at("SOURCE_INGESTED") and not truthy(state.get("source_ingest_complete")):
        fail("SOURCE_INGESTED requires source_ingest_complete=true", errors)

    videos = refs.get("videos", [])
    images = refs.get("images", [])

    if at("REFERENCES_ANALYZED"):
        if not truthy(state.get("reference_analysis_complete")):
            fail("reference analysis not complete", errors)
        for v in videos:
            dur = float(v.get("duration_seconds", 0))
            total = int(v.get("total_frames", 0))
            ext = int(v.get("extracted_frames", 0))
            policy = v.get("extraction_policy")
            short = (
                dur <= contract["reference_policy"]["short_video_max_seconds"]
                and total <= contract["reference_policy"]["short_video_max_frames"]
            )
            if short and (policy != "all_frames" or ext != total):
                fail(
                    f"short reference must extract all frames: "
                    f"{v.get('name', 'video')} {ext}/{total}",
                    errors,
                )
            if not short:
                if policy != "meaningful_sampling":
                    fail(
                        f"long reference requires meaningful_sampling: {v.get('name', 'video')}",
                        errors,
                    )
                if ext <= 0 or not v.get("sampling_description") or not v.get("coverage"):
                    fail(
                        f"long reference sampling evidence incomplete: {v.get('name', 'video')}",
                        errors,
                    )
            if not truthy(v.get("analysis_complete")):
                fail(f"reference video analysis incomplete: {v.get('name', 'video')}", errors)
        for im in images:
            if not truthy(im.get("analysis_complete")):
                fail(f"source image analysis incomplete: {im.get('name', 'image')}", errors)

    if at("APPROACH_ESTABLISHED"):
        selected = plan.get("selected_capabilities", [])
        valid = {x["id"] for x in media["capabilities"]}
        unknown = [x for x in selected if x not in valid]
        if not selected:
            fail("MEDIA_PLAN selected_capabilities is empty", errors)
        if unknown:
            fail("unknown media capabilities: " + ", ".join(unknown), errors)
        if not truthy(state.get("visual_approach_established")):
            fail("visual/media approach not established", errors)
        if not videos and not images:
            validate_no_reference_visual_direction_gate(plan, contract, modes, errors)

    checks = {
        "STORYBOARD_LOCKED": "storyboard_locked",
        "SHOT_PACKAGES_BUILT": "shot_packages_built",
        "SHOT_PROOFS_ACCEPTED": "shot_proofs_accepted",
        "FX_LOCKED": "fx_lock_verified",
        "ASSEMBLED": "assembly_complete",
        "FINAL_QC_PASSED": "final_qc_passed",
        "ARCHIVED": "archive_complete",
    }
    for s, key in checks.items():
        if at(s) and not truthy(state.get(key)):
            fail(f"{s} requires {key}=true", errors)

    if at("FX_LOCKED") and not (project / "fx.lock.json").is_file():
        fail("FX_LOCKED requires fx.lock.json", errors)

    if at("SHOT_PACKAGES_BUILT"):
        sp = project / "shot_packages"
        packages = [p for p in sp.iterdir() if p.is_dir()] if sp.is_dir() else []
        if not packages:
            fail("SHOT_PACKAGES_BUILT requires at least one shot package", errors)

    return errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--branch",
        default=os.environ.get("GITHUB_REF_NAME")
        or os.environ.get("AIVIDEOEDIT_BRANCH")
        or "",
    )
    ap.add_argument(
        "--bootstrap-phase",
        action="store_true",
        help="validate state before the bootstrap session attestation exists",
    )
    args = ap.parse_args()

    if not args.branch:
        raise SystemExit("FAIL: branch required (--branch or GITHUB_REF_NAME)")

    errors = []
    if not args.bootstrap_phase and os.environ.get("AIVIDEOEDIT_BOOTSTRAP_PHASE") != "1":
        errors.extend(verify_bootstrap_session(args.branch))
        if errors:
            print("AIVideoEdit production contract: FAIL", file=sys.stderr)
            for e in errors:
                print("- " + e, file=sys.stderr)
            raise SystemExit(1)

        session = load_json(SESSION_PATH)
        os_root = Path(session.get("os_root") or "")
        if not os_root.is_absolute():
            os_root = (ROOT / os_root).resolve()
        os.environ["AIVIDEOEDIT_OS_ROOT"] = str(os_root)

    errors.extend(validate(args.branch))
    if errors:
        print("AIVideoEdit production contract: FAIL", file=sys.stderr)
        for e in errors:
            print("- " + e, file=sys.stderr)
        raise SystemExit(1)

    print("AIVideoEdit production contract: PASS")


if __name__ == "__main__":
    main()
