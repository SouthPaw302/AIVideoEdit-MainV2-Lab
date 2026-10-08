#!/usr/bin/env python3
"""Fail closed when selected/locked canonical FX have no execution receipt."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import sys
from pathlib import Path
REPO=Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0,str(REPO))
from general.reusable.tools.execution_ledger import verify_ledger
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--requirements",required=True);ap.add_argument("--ledger",required=True);a=ap.parse_args()
    req=json.loads(Path(a.requirements).read_text(encoding="utf-8"));expected=[x.get("id") for x in (req.get("effects",[])+req.get("transitions",[])) if isinstance(x,dict) and x.get("id")]
    ledger=json.loads(Path(a.ledger).read_text(encoding="utf-8"));events=ledger.get("events",[])
    executed={e.get("subject") for e in events if e.get("component")=="fx" and e.get("stage")=="executed"}
    waived={e.get("subject") for e in events if e.get("component")=="fx" and e.get("stage")=="waived" and str(e.get("reason") or "").strip()}
    missing=[eid for eid in expected if eid not in executed and eid not in waived];errs=verify_ledger(a.ledger,"fx")+[f"selected canonical FX never executed: {x}" for x in missing];errs=list(dict.fromkeys(errs))
    print(json.dumps({"result":"PASS" if not errs else "FAIL","expected":expected,"executed":sorted(x for x in executed if x),"waived":sorted(x for x in waived if x),"errors":errs},indent=2));return 0 if not errs else 2
if __name__=="__main__":raise SystemExit(main())
