#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from scene_timeline import audio_anchors, snap_timeline, validate  # noqa: E402


class SceneTimelineTests(unittest.TestCase):
    def setUp(self):
        self.plan = {
            "schema": "aivideoedit.scene-timeline.v1",
            "duration_sec": 20.0,
            "scenes": [
                {"id": "scene-01", "start": 0.0, "end": 8.1},
                {"id": "scene-02", "start": 8.1, "end": 20.0},
            ],
            "transitions": [
                {"at": 8.1, "effect": "light_leak", "duration": 0.7},
            ],
        }
        self.audiomap = {
            "schema": "aivideoedit.audiomap.v1",
            "source": {"sha256": "abc123"},
            "rhythm": {"beats_sec": [8.0], "downbeats_sec": [8.0]},
            "energy": {"key_moments": [{"t": 8.0, "kind": "surge"}]},
            "silences": [],
            "phrase_candidates": [{"start": 0.0, "end": 8.0}, {"start": 8.0, "end": 20.0}],
        }

    def test_anchor_priority_and_snap(self):
        anchors = audio_anchors(self.audiomap)
        self.assertIn((8.0, "energy_surge", 0), anchors)
        result = snap_timeline(self.plan, self.audiomap, window=0.2)
        self.assertEqual(result["transitions"][0]["at"], 8.0)
        self.assertEqual(result["scenes"][0]["end"], 8.0)
        self.assertEqual(result["scenes"][1]["start"], 8.0)
        self.assertEqual(result["audio_timing"]["source_sha256"], "abc123")

    def test_unknown_effect_fails_validation(self):
        broken = dict(self.plan)
        broken["transitions"] = [{"at": 8.1, "effect": "not_real", "duration": 0.7}]
        errors = validate(broken, {"light_leak"})
        self.assertTrue(any("unknown effect" in error for error in errors))

    def test_no_snap_outside_window(self):
        result = snap_timeline(self.plan, self.audiomap, window=0.01)
        self.assertEqual(result["transitions"][0]["at"], 8.1)


if __name__ == "__main__":
    unittest.main()
