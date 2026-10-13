"""Independent fail-closed structural tests for the experimental specialist."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from scripts.prototype_ai_specialist import decode_observation, invoke


class PrototypeDirectorTests(unittest.TestCase):
    def test_observation_only_accepts_review_required(self):
        text = json.dumps({
            "observation": "Different lighting in later frame",
            "possible_defects": ["Possible lighting jump"],
            "needs_human_review": True,
        })
        self.assertEqual(decode_observation(text)["needs_human_review"], True)

    def test_unstructured_pass_rejected(self):
        for text in ("COMPLETE", '{"status":"PASS"}',
                     '{"observation":"looks fine","possible_defects":[],"needs_human_review":false}'):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    decode_observation(text)

    def test_missing_model_fails_before_any_inference(self):
        with TemporaryDirectory() as directory:
            p = Path(directory)
            clip = p / "input.mp4"
            clip.write_bytes(b"placeholder")
            with patch("scripts.prototype_ai_specialist.sample_frames") as frames:
                with self.assertRaises(FileNotFoundError):
                    invoke(clip, "Keep visual canon", p / "missing.gguf",
                           p / "missing-mmproj.gguf", p / "missing-cli",
                           p / "out")
                frames.assert_not_called()

    def test_model_does_not_get_to_approve(self):
        text = '{"observation":"Check source","possible_defects":[],"needs_human_review":true}'
        self.assertTrue(decode_observation(text)["needs_human_review"])


if __name__ == "__main__":
    unittest.main()
