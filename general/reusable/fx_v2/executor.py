#!/usr/bin/env python3
"""Canonical FX execution boundary with actual-use receipts."""
from __future__ import annotations
import importlib.util,inspect,json,os
from pathlib import Path
from .runtime import FXRuntime,FXContext
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
REGISTRY=HERE/"registry.json"
def _load_module(path):
    full=(REPO/path).resolve();spec=importlib.util.spec_from_file_location("aive_fx_adapter_"+full.stem,full)
    if spec is None or spec.loader is None:raise RuntimeError(f"cannot load FX adapter: {path}")
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
class FXExecutor:
    def __init__(self,seed=302,ledger_path=None,consumer="fx_executor"):
        self.runtime=FXRuntime(seed=seed);self.registry=json.loads(REGISTRY.read_text(encoding="utf-8"));self.ledger_path=ledger_path or os.environ.get("AIVE_EXECUTION_LEDGER");self.consumer=consumer;self._recorded=set()
    def _rec(self,eid):
        rec=(self.registry.get("effects") or {}).get(eid)
        if not isinstance(rec,dict):raise KeyError(f"unknown canonical FX id: {eid}")
        if rec.get("gate_status")!="approved":raise RuntimeError(f"FX is not production-approved: {eid}")
        return rec
    def _receipt(self,eid,ctx=None,extra=None):
        if not self.ledger_path or eid in self._recorded:return
        from general.reusable.tools.execution_ledger import record
        evidence={}
        if ctx is not None:evidence={"frame_index":int(ctx.frame_index),"time_seconds":float(ctx.t)}
        if extra:evidence.update(extra)
        record(self.ledger_path,component="fx",subject=eid,stage="executed",actor="canonical_fx_executor",consumer=self.consumer,evidence=evidence);self._recorded.add(eid)
    def apply_frame(self,eid,frame,ctx:FXContext,params=None,second_frame=None):
        rec=self._rec(eid);impl=rec.get("implementation") or {};kind=impl.get("kind");params=dict(params or {})
        if kind=="runtime_apply":out=self.runtime.apply(frame,{"id":eid,**params},ctx)
        elif kind=="adapter":
            mod=_load_module(impl.get("path"));fn=getattr(mod,impl.get("symbol") or rec.get("name"))
            if (impl.get("symbol") or "")=="apply_effect":out=fn(impl.get("effect_name") or rec.get("name"),frame,float(ctx.t),float(ctx.duration),float(ctx.energy),float(ctx.transient),second_frame,params=params)
            else:
                kwargs={}
                for name in inspect.signature(fn).parameters:
                    if name in {"bgr","frame","im"}:kwargs[name]=frame
                    elif name=="ctx":kwargs[name]=ctx
                    elif name=="t":kwargs[name]=float(ctx.t)
                    elif name=="duration":kwargs[name]=float(ctx.duration)
                    elif name=="energy":kwargs[name]=float(ctx.energy)
                    elif name=="transient":kwargs[name]=float(ctx.transient)
                    elif name=="second_frame":kwargs[name]=second_frame
                    elif name in params:kwargs[name]=params[name]
                out=fn(**kwargs)
        else:raise RuntimeError(f"{eid} cannot be applied as a frame effect: implementation={kind}")
        self._receipt(eid,ctx);return out
    def apply_transition(self,eid,a,b,p,ctx:FXContext|None=None,params=None):
        rec=self._rec(eid);impl=rec.get("implementation") or {};kind=impl.get("kind");params=dict(params or {})
        if kind=="runtime_transition":
            out=getattr(self.runtime,impl.get("method") or rec.get("name"))(a,b,float(p),**params)
        elif kind=="adapter":
            c=ctx or FXContext(t=float(p),duration=1.0,frame_index=0,fps=1.0);return self.apply_frame(eid,a,c,params=params,second_frame=b)
        else:raise RuntimeError(f"{eid} cannot be applied as a transition: implementation={kind}")
        self._receipt(eid,ctx,{"transition_progress":float(p)});return out
