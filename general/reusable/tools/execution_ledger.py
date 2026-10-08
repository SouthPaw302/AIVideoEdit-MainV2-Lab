#!/usr/bin/env python3
"""Execution ledger: proves selected systems were actually executed and consumed."""
from __future__ import annotations
import argparse, hashlib, json, os, tempfile
from datetime import datetime, timezone
from pathlib import Path
SCHEMA="aivideoedit.production-execution-ledger.v1"
VALID_STAGES={"selected","verified","executed","consumed","waived"}
def _now(): return datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
def sha256_file(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for c in iter(lambda:f.read(1024*1024),b""): h.update(c)
    return h.hexdigest()
def load(path, project=None):
    p=Path(path)
    if p.is_file():
        data=json.loads(p.read_text(encoding="utf-8"))
        if data.get("schema")!=SCHEMA: raise ValueError("invalid execution ledger schema")
        return data
    return {"schema":SCHEMA,"project":project,"created_at":_now(),"updated_at":_now(),"events":[]}
def save(path,data):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);data["updated_at"]=_now()
    fd,tmp=tempfile.mkstemp(prefix=p.name+".",dir=str(p.parent))
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as f:
            json.dump(data,f,indent=2,sort_keys=True);f.write("\n")
        os.replace(tmp,p)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
def record(path,*,component,subject,stage,actor=None,consumer=None,evidence=None,metadata=None,required_execution=False,required_consumption=False,reason=None,project=None):
    if stage not in VALID_STAGES: raise ValueError(f"invalid ledger stage: {stage}")
    data=load(path,project)
    ev={"component":str(component),"subject":str(subject),"stage":stage,"at":_now(),"actor":actor,"consumer":consumer,"evidence":dict(evidence or {}),"metadata":dict(metadata or {}),"required_execution":bool(required_execution),"required_consumption":bool(required_consumption),"reason":reason}
    data["events"].append(ev);save(path,data);return ev
def _groups(data,component=None):
    groups={}
    for ev in data.get("events",[]):
        if component and ev.get("component")!=component: continue
        groups.setdefault((ev.get("component"),ev.get("subject")),[]).append(ev)
    return groups
def verify_ledger(path,component=None):
    p=Path(path)
    if not p.is_file(): return ["execution ledger missing"]
    try:data=load(p)
    except Exception as e:return [f"execution ledger invalid: {e}"]
    errors=[]
    for (comp,subject),events in _groups(data,component).items():
        stages={e.get("stage") for e in events}
        waived=any(e.get("stage")=="waived" and str(e.get("reason") or "").strip() for e in events)
        if any(e.get("required_execution") for e in events) and "executed" not in stages and not waived: errors.append(f"{comp}:{subject} selected/verified but never executed")
        if any(e.get("required_consumption") for e in events) and "consumed" not in stages and not waived: errors.append(f"{comp}:{subject} output was never consumed downstream")
    return errors
def summary(path):
    data=load(path);out={}
    for (comp,subject),events in _groups(data).items():out[f"{comp}:{subject}"]=[e.get("stage") for e in events]
    return {"schema":data.get("schema"),"project":data.get("project"),"subjects":out,"verification_errors":verify_ledger(path)}
def main():
    ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest="cmd",required=True)
    p=sub.add_parser("init");p.add_argument("--ledger",required=True);p.add_argument("--project")
    p=sub.add_parser("record");p.add_argument("--ledger",required=True);p.add_argument("--project");p.add_argument("--component",required=True);p.add_argument("--subject",required=True);p.add_argument("--stage",choices=sorted(VALID_STAGES),required=True);p.add_argument("--actor");p.add_argument("--consumer");p.add_argument("--reason");p.add_argument("--evidence-file");p.add_argument("--required-execution",action="store_true");p.add_argument("--required-consumption",action="store_true")
    p=sub.add_parser("verify");p.add_argument("--ledger",required=True);p.add_argument("--component")
    p=sub.add_parser("summary");p.add_argument("--ledger",required=True)
    a=ap.parse_args()
    if a.cmd=="init":
        d=load(a.ledger,a.project);save(a.ledger,d);print(json.dumps(d,indent=2));return 0
    if a.cmd=="record":
        evidence={"path":str(a.evidence_file),"sha256":sha256_file(a.evidence_file)} if a.evidence_file else {}
        print(json.dumps(record(a.ledger,project=a.project,component=a.component,subject=a.subject,stage=a.stage,actor=a.actor,consumer=a.consumer,evidence=evidence,required_execution=a.required_execution,required_consumption=a.required_consumption,reason=a.reason),indent=2));return 0
    if a.cmd=="verify":
        errs=verify_ledger(a.ledger,a.component);print(json.dumps({"result":"PASS" if not errs else "FAIL","errors":errs},indent=2));return 0 if not errs else 2
    print(json.dumps(summary(a.ledger),indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
