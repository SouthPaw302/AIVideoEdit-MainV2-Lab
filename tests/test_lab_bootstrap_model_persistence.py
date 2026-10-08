"""Lab regression for MainV2 model persistence across repeated bootstrap."""
from pathlib import Path
import bootstrap

def test_bootstrap_preserves_pinned_onnx_artifact(tmp_path: Path):
    root=tmp_path/".aivideoedit"
    model=root/"models"/"beat_this"/"beat_this.onnx"
    cache=root/"cache"/"main.tar.gz"
    stale=root/"os"/"stale.txt"
    session=root/"session.json"
    for p in (model,cache,stale,session):
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_bytes(b"protected-marker" if p in (model,cache) else b"obsolete-session")
    bootstrap.clear_volatile_session_state(root)
    assert model.read_bytes()==b"protected-marker"
    assert cache.read_bytes()==b"protected-marker"
    assert not stale.exists()
    assert not session.exists()
