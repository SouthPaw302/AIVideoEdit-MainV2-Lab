from __future__ import annotations

import importlib.util
from pathlib import Path


def load_core_adapter():
    path=Path("prototype/backend_gui/core_adapter.py")
    spec=importlib.util.spec_from_file_location("core_adapter_validation_test",path)
    mod=importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_core_ref_defaults_to_main(monkeypatch):
    monkeypatch.delenv("AIVE_CORE_REF",raising=False)
    mod=load_core_adapter()
    assert mod._core_ref()=="main"


def test_core_ref_can_be_overridden_for_validation(monkeypatch):
    monkeypatch.setenv("AIVE_CORE_REF","MainV2-clean")
    mod=load_core_adapter()
    assert mod._core_ref()=="MainV2-clean"


def test_validation_ref_keeps_core_boot_branch_main(monkeypatch, tmp_path):
    monkeypatch.setenv("AIVE_CORE_REF","MainV2-clean")
    mod=load_core_adapter()
    calls=[]
    class P:
        returncode=0
        stdout=""
        stderr=""
    monkeypatch.setattr(mod, "CORE_REPO", tmp_path/"repo")
    mod.CORE_REPO.mkdir(parents=True)
    mod.CORE_REPO.joinpath("bootstrap.py").write_text("pass\n", encoding="utf-8")
    monkeypatch.setattr(mod, "OS_ROOT", tmp_path/"repo"/".aivideoedit"/"os")
    monkeypatch.setattr(mod, "SESSION_FILE", tmp_path/"repo"/".aivideoedit"/"session.json")
    adapter=mod.CoreAdapter()
    monkeypatch.setattr(adapter, "_install_core", lambda offline: P())
    def fake_run(cmd,cwd,timeout=300,env=None):
        calls.append((cmd,env))
        return P()
    monkeypatch.setattr(mod, "_run", fake_run)
    adapter.bootstrap(offline=True)
    cmd,env=calls[-1]
    assert cmd[cmd.index("--branch")+1]=="main"
    assert env["AIVIDEOEDIT_AUTHORITY_REF"]=="MainV2-clean"
    assert env["AIVIDEOEDIT_VALIDATION_MODE"]=="1"
