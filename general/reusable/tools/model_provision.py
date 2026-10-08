#!/usr/bin/env python3
"""Provision approved external model files outside normal git history."""
from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import urllib.request
from pathlib import Path

from general.reusable.tools.model_registry import ModelRegistry


def git_blob_sha1(data: bytes) -> str:
    header=f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header+data).hexdigest()


def provision(model_id:str, *, repo_root:Path|None=None, force:bool=False)->dict:
    root=(repo_root or Path.cwd()).resolve()
    registry=ModelRegistry.load(repo_root=root)
    rec=registry.get(model_id)
    if rec.get("runtime")!="onnxruntime":
        raise ValueError(f"model is not externally provisioned ONNX: {model_id}")
    rel=str(rec.get("artifact_path") or "")
    destination=(root/rel).resolve()
    if root!=destination and root not in destination.parents:
        raise RuntimeError("model destination escaped repository root")
    expected_size=int(rec.get("source_size_bytes") or 0)
    expected_blob=str(rec.get("source_git_blob_sha1") or "")
    url=str(rec.get("download_url") or "")
    if not url.startswith("https://"):
        raise RuntimeError("approved HTTPS model URL missing")

    if destination.is_file() and not force:
        data=destination.read_bytes()
        if len(data)==expected_size and git_blob_sha1(data)==expected_blob:
            return {"status":"READY","model":model_id,"path":str(destination)}
        raise RuntimeError("existing model failed pinned verification; use --force")

    destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=destination.parent,delete=False,suffix=".partial") as tmp:
        tmp_path=Path(tmp.name)
        req=urllib.request.Request(url,headers={"User-Agent":"AIVideoEdit-MainV2-clean"})
        with urllib.request.urlopen(req,timeout=180) as response:
            while True:
                block=response.read(1024*1024)
                if not block:break
                tmp.write(block)
    try:
        data=tmp_path.read_bytes()
        if len(data)!=expected_size:
            raise RuntimeError(f"model size mismatch: {len(data)} != {expected_size}")
        actual=git_blob_sha1(data)
        if actual!=expected_blob:
            raise RuntimeError(f"model git blob mismatch: {actual} != {expected_blob}")
        tmp_path.replace(destination)
    finally:
        tmp_path.unlink(missing_ok=True)

    receipt={
        "schema":"aivideoedit.model-provision.v1",
        "model":model_id,
        "path":str(destination),
        "source_commit":rec.get("source_commit"),
        "source_git_blob_sha1":expected_blob,
        "source_size_bytes":expected_size,
    }
    destination.with_suffix(destination.suffix+".receipt.json").write_text(
        json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8"
    )
    return {"status":"PROVISIONED",**receipt}


def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("model_id")
    ap.add_argument("--force",action="store_true")
    args=ap.parse_args()
    print(json.dumps(provision(args.model_id,force=args.force),indent=2,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
