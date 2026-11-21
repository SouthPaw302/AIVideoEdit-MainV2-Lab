"""Fast, offline tests of the exact runner protocol."""
import json
import tempfile
import unittest
from pathlib import Path

from prototype.neural_mesh import mesh


class NeuralMeshTests(unittest.TestCase):
    def test_real_two_round_message_exchange_and_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            mesh.prepare(84, folder)
            obs = mesh.load(folder / "observation.json")
            truth = mesh.load(folder / "truth.json")
            weights = mesh.load(folder / "weights.json")
            self.assertNotIn("future_position", json.dumps(obs))
            outputs = folder / "r1"
            outputs.mkdir()
            for node in mesh.NODES:
                receipt = mesh.run_node(node, 1, obs, weights)
                mesh.save(outputs / f"node-{node}.json", receipt)
            packet1 = mesh.integrate(1, weights, outputs)
            self.assertAlmostEqual(sum(packet1["attention"].values()), 1.0)
            self.assertEqual(len(packet1["routing"]), 6)
            outputs2 = folder / "r2"
            outputs2.mkdir()
            for node in mesh.NODES:
                receipt = mesh.run_node(node, 2, obs, weights, packet1)
                mesh.save(outputs2 / f"node-{node}.json", receipt)
            packet2 = mesh.integrate(2, weights, outputs2)
            self.assertNotEqual(packet1["predictions"], packet2["predictions"])
            scores, checkpoint = mesh.evaluate(packet1, packet2, truth, weights)
            self.assertEqual(scores["status"], "MEASURED_SYNTHETIC_EXPERIMENT_NOT_VIDEO_OR_ARTISTIC_QC")
            self.assertGreaterEqual(scores["round2_consensus_mse"], 0)
            self.assertIn("learned_routing", checkpoint)
            self.assertNotEqual(weights, checkpoint)

    def test_missing_node_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            mesh.prepare(33, folder)
            with self.assertRaisesRegex(ValueError, "expected 6 worker receipts"):
                mesh.integrate(1, mesh.load(folder / "weights.json"), folder)

    def test_unauthorized_feedback_or_wrong_seed_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            mesh.prepare(33, folder)
            obs = mesh.load(folder / "observation.json")
            weights = mesh.load(folder / "weights.json")
            with self.assertRaisesRegex(ValueError, "requires stage 1"):
                mesh.run_node("position", 2, obs, weights)
            obs["seed"] = 34
            with self.assertRaisesRegex(ValueError, "seed mismatch"):
                mesh.run_node("position", 1, obs, weights)

    def test_repeatable_training_and_sensing(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            mesh.prepare(900, a)
            mesh.prepare(900, b)
            for item in ("observation.json", "truth.json", "weights.json"):
                self.assertEqual((Path(a)/item).read_bytes(), (Path(b)/item).read_bytes())


if __name__ == "__main__":
    unittest.main()
