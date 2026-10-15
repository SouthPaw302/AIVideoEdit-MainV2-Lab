#!/usr/bin/env python3
"""Download only the exact SHA-pinned real source from the repository's fixture."""
import hashlib
import json
import sys
import urllib.request
from pathlib import Path
manifest=json.loads(Path(sys.argv[1]).read_text())
source=manifest["audio"] if len(sys.argv)>3 and sys.argv[3]=="audio" else manifest["shots"][0]["source"]
target=Path(sys.argv[2])
target.parent.mkdir(parents=True,exist_ok=True)
request=urllib.request.Request(source["url"],headers={"User-Agent":"AIVideoEdit-Godot-Lab-Proof"})
with urllib.request.urlopen(request,timeout=45) as response,open(target,"wb") as out:
    while True:
        chunk=response.read(1<<20)
        if not chunk:break
        out.write(chunk)
h=hashlib.sha256(target.read_bytes()).hexdigest()
if h!=source["sha256"]:
    target.unlink(missing_ok=True)
    sys.exit(f"Source hash mismatch; not proceeding: {h}")
print("Pinned source SHA-256 PASS: "+h)