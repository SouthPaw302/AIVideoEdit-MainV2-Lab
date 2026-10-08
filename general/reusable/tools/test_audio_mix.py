#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from audio_mix import compile_ducking, validate  # noqa: E402


class AudioMixTests(unittest.TestCase):
    def setUp(self):
        self.plan = {
            "schema": "aivideoedit.audio-mix.v1",
            "tracks": [
                {"id": "music", "role": "music", "start": 0, "duration": 20, "volume": 0.8},
                {"id": "vo-1", "role": "voice", "start": 4, "duration": 3},
                {"id": "vo-2", "role": "voice", "start": 10, "duration": 2},
            ],
            "groups": [
                {"id": "voiceover", "members": ["vo-1", "vo-2"], "volume": 1.0}
            ],
            "ducking": [
                {"target": "music", "sources": ["voiceover"], "depth": 0.5, "attack": 0.2, "release": 0.4}
            ],
        }

    def test_valid_plan_compiles_volume_lane(self):
        self.assertEqual(validate(self.plan), [])
        result = compile_ducking(self.plan)
        lane = result["tracks"][0]["automation"]["lanes"][0]
        self.assertEqual(lane["target"], "volume")
        self.assertEqual(lane["generated_by"], "aivideoedit_ducking")
        self.assertTrue(any(point["v"] == 0.5 for point in lane["points"]))
        self.assertEqual(len(result["ducking_compiled"]["relations"][0]["intervals"]), 2)

    def test_ducking_source_must_be_voice(self):
        plan = dict(self.plan)
        plan["tracks"] = [dict(track) for track in self.plan["tracks"]]
        plan["tracks"][1]["role"] = "sfx"
        errors = validate(plan)
        self.assertTrue(any("must have role=voice" in error for error in errors))

    def test_nonautomatable_fx_target_rejected(self):
        plan = dict(self.plan)
        plan["tracks"] = [dict(track) for track in self.plan["tracks"]]
        plan["tracks"][0]["fx_chain"] = {
            "version": 1,
            "nodes": [{"type": "limiter", "id": "n1", "params": {"limit": -1}}],
        }
        plan["tracks"][0]["automation"] = {
            "version": 1,
            "lanes": [{"target": "fx.n1.limit", "points": [{"t": 0, "v": -1}]}],
        }
        errors = validate(plan)
        self.assertTrue(any("non-automatable effect" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
