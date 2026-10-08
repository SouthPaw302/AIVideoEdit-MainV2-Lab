#!/usr/bin/env python3
"""Director review checkpoints for sandbox-supervised productions."""
from __future__ import annotations
import argparse,json
from datetime import datetime,timezone
from pathlib import Path
try:
    from .execution_ledger import sha256_file
except ImportError:
    from execution_ledger import sha256_file
SCHEMA="aivideoedit.director-checkpoints.v1"
ORDER=["media_selection","representative_proof","rough_cut","fx_pass","final_review"]
def _now():return datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
def save(path,d):
    d["updated_at"]=_now();p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def init(path,project=None):
    p=Path(path)
    if p.is_file():
        d=json.loads(p.read_text(encoding="utf-8"))
        if d.get("schema")!=SCHEMA:raise ValueError("invalid director checkpoint schema")
        return d
    d={"schema":SCHEMA,"project":project,"created_at":_now(),"updated_at":_now(),"checkpoints":{k:{"status":"pending"} for k in ORDER}};save(path,d);return d
def decide(path,checkpoint,status,reviewer,evidence_file=None,notes=None,project=None):
    if checkpoint not in ORDER:raise ValueError("unknown checkpoint")
    if status not in {"approved","rejected"}:raise ValueError("status must be approved or rejected")
    d=init(path,project);ev={"path":str(evidence_file),"sha256":sha256_file(evidence_file)} if evidence_file else {}
    d["checkpoints"][checkpoint]={"status":status,"reviewer":reviewer,"at":_now(),"evidence":ev,"notes":notes};save(path,d);return d["checkpoints"][checkpoint]
def verify_checkpoints(path,through="final_review"):
    p=Path(path)
    if not p.is_file():return ["director checkpoint file missing"]
    try:d=init(p)
    except Exception as e:return [f"director checkpoint file invalid: {e}"]
    if through not in ORDER:return [f"unknown director checkpoint: {through}"]
    return [f"director checkpoint not approved: {k}" for k in ORDER[:ORDER.index(through)+1] if ((d.get("checkpoints") or {}).get(k) or {}).get("status")!="approved"]
def main():
    ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest="cmd",required=True)
    p=sub.add_parser("init");p.add_argument("--file",required=True);p.add_argument("--project")
    p=sub.add_parser("decide");p.add_argument("--file",required=True);p.add_argument("--project");p.add_argument("--checkpoint",choices=ORDER,required=True);p.add_argument("--status",choices=["approved","rejected"],required=True);p.add_argument("--reviewer",required=True);p.add_argument("--evidence-file");p.add_argument("--notes")
    p=sub.add_parser("verify");p.add_argument("--file",required=True);p.add_argument("--through",choices=ORDER,default="final_review")
    a=ap.parse_args()
    if a.cmd=="init":print(json.dumps(init(a.file,a.project),indent=2));return 0
    if a.cmd=="decide":print(json.dumps(decide(a.file,a.checkpoint,a.status,a.reviewer,a.evidence_file,a.notes,a.project),indent=2));return 0
    errs=verify_checkpoints(a.file,a.through);print(json.dumps({"result":"PASS" if not errs else "FAIL","errors":errs},indent=2));return 0 if not errs else 2
if __name__=="__main__":raise SystemExit(main())
