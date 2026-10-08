from __future__ import annotations

import os
from pathlib import Path
import pytest
import bootstrap


def test_validation_authority_requires_explicit_mode(monkeypatch):
    monkeypatch.setenv("AIVIDEOEDIT_AUTHORITY_REF","MainV2-clean")
    monkeypatch.delenv("AIVIDEOEDIT_VALIDATION_MODE",raising=False)
    with pytest.raises(SystemExit, match="explicit validation mode"):
        bootstrap.authority_ref()


def test_validation_authority_resolves_head_offline(tmp_path: Path, monkeypatch):
    import subprocess
    subprocess.run(["git","init","-b","MainV2-clean",str(tmp_path)],check=True,capture_output=True)
    subprocess.run(["git","-C",str(tmp_path),"config","user.email","test@example.com"],check=True)
    subprocess.run(["git","-C",str(tmp_path),"config","user.name","Test"],check=True)
    (tmp_path/"x").write_text("x")
    subprocess.run(["git","-C",str(tmp_path),"add","x"],check=True)
    subprocess.run(["git","-C",str(tmp_path),"commit","-m","x"],check=True,capture_output=True)
    expected=subprocess.run(["git","-C",str(tmp_path),"rev-parse","HEAD"],check=True,capture_output=True,text=True).stdout.strip()
    monkeypatch.setenv("AIVIDEOEDIT_AUTHORITY_REF","MainV2-clean")
    monkeypatch.setenv("AIVIDEOEDIT_VALIDATION_MODE","1")
    sha,source=bootstrap.fetch_main_sha(True,tmp_path)
    assert sha==expected
    assert source=="validation-ref:MainV2-clean"
