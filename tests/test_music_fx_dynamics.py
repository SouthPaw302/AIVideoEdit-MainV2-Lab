"""Evidence and absolute timeline controls never invent beat positions."""
import json, hashlib, tempfile, unittest, wave, sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from music_fx_dynamics import MusicFXDynamics

class MusicDynamicsTest(unittest.TestCase):
    def test_absolute_window_and_hash_gate(self):
        with tempfile.TemporaryDirectory() as td:
            audio=Path(td)/"a.wav";beats=Path(td)/"beat.json"
            rate=48000;t=np.arange(4*rate)/rate
            pcm=(np.sin(2*np.pi*180*t)*np.where(t<2,.04,.5)*32000).astype("<i2")
            with wave.open(str(audio),"wb") as w:
                w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate);w.writeframes(pcm.tobytes())
            beats.write_text(json.dumps({"engine":"beat_this_onnx","model_resolution":{"used_fallback":False},"beat_positions_seconds":[.5,1.5,2.5,3.5]}))
            sha=hashlib.sha256(beats.read_bytes()).hexdigest()
            d=MusicFXDynamics(audio,beats,sha,24)
            x=d.window(0,96)
            self.assertEqual(x.shape,(96,2))
            np.testing.assert_allclose(x[24:48],d.window(1,24))
            self.assertGreater(float(x[72,0]),float(x[12,0])+.2)
            self.assertGreater(float(x[12,1]),float(x[8,1]))
            self.assertTrue(np.all((x[:,0]>=.22)&(x[:,0]<=.68)))
            with self.assertRaises(ValueError):d.window(3,30)
            with self.assertRaises(ValueError):MusicFXDynamics(audio,beats,"0"*64,24)
if __name__=="__main__":unittest.main()
