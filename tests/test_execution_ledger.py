from general.reusable.tools.execution_ledger import record,verify_ledger
from general.reusable.tools.director_checkpoint import init,decide,verify_checkpoints
def test_ledger_fails_selected_but_unused(tmp_path):
    p=tmp_path/"ledger.json";record(p,component="fx",subject="FX2-TEST",stage="selected",required_execution=True,project="x")
    assert any("never executed" in x for x in verify_ledger(p))
    record(p,component="fx",subject="FX2-TEST",stage="executed",consumer="fixture");assert verify_ledger(p)==[]
def test_ledger_allows_reasoned_waiver(tmp_path):
    p=tmp_path/"ledger.json";record(p,component="fx",subject="FX2-TEST",stage="selected",required_execution=True,project="x");record(p,component="fx",subject="FX2-TEST",stage="waived",reason="scene removed by Director");assert verify_ledger(p)==[]
def test_director_checkpoints_fail_closed(tmp_path):
    p=tmp_path/"director.json";init(p,"x");assert verify_checkpoints(p,"representative_proof")
    decide(p,"media_selection","approved","sandbox_director");decide(p,"representative_proof","approved","sandbox_director");assert verify_checkpoints(p,"representative_proof")==[];assert verify_checkpoints(p,"final_review")
