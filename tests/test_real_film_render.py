"""Real render preflight invariants; no fake frames or bypassed user authority."""
import pytest
from scripts.render_real_music_film import validate_manifest

def test_requires_real_authority_audio_and_shots():
    base={"schema":"aivideoedit.real-render.v1","render_authorization":"explicit_user_render_request",
          "audio":{"path":"sound.wav","sha256":"0"*64},
          "shots":[{"id":"s1","source":{"path":"shot.png","sha256":"1"*64},"duration_seconds":2}],
          "output":{"fps":24,"width":1280,"height":720}}
    assert validate_manifest(base)[-1] == [48]
    base["render_authorization"]="automatic"
    with pytest.raises(ValueError,match="explicit user authorization"):
        validate_manifest(base)

def test_fail_closed_for_placeholder_and_invalid_duration():
    base={"schema":"aivideoedit.real-render.v1","render_authorization":"explicit_user_render_request",
          "audio":{"path":"song.wav","sha256":"0"*64},
          "shots":[{"id":"source","source":None,"duration_seconds":1}],
          "output":{"fps":24,"width":1280,"height":720}}
    with pytest.raises(ValueError,match="real source"):
        validate_manifest(base)
    base["shots"][0]["source"]={"path":"clip.mp4","sha256":"1"*64}
    base["shots"][0]["duration_seconds"]=0
    with pytest.raises(ValueError,match="duration"):
        validate_manifest(base)
