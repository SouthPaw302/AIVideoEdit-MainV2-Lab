# Director Candidate 04 — source-led proof (review only)

Candidate 04 is a local 1080p reconstruction from all 30 SHA-verified original Drive stills, all three approved archived FX proof batches, and existing EC-03/EC-04 Gemini true-motion continuations. Original 48kHz stereo WAV SHA-256: `6789e6f3ea52501a0d4a151296a6ef7f8abc8516acd1f6cec959213a028ec0d9`.

Output: 6788 decoded frames, 24 fps, 1920x1080, 282.833333s. Review MP4 SHA-256: `7a712c8aa459e4911c7ccb70eab7fea01b6bfe58a203234c4a082df69fb1433c`. The MP4 and Director QC reports are stored privately in the existing Drive production folder **06 QC and Deliveries**.

The renderer is `scripts/director_source_led_render.py`, and the 30 exact file hash identities are in `projects/camion-new/ORIGINAL_SOURCE_SHA256.json`. Point `AIVIDEO_SOURCE_ROOT` to a securely staged source tree including candidate03/shard*/manifest.json, original stills, WAV, three FX archive ZIPs, two Gemini clips, and preserved candidate03 review MP4. It fails closed on missing/altered sources and uses the low-res FX clips as time-dependent optical deltas, not as the finished picture.

**Not a canonical MainV2 runner production, FX v2 equivalence proof, or accepted final release.** Batch03 requires real articulated video for EC-22,24,25,26,28,30. These six shots remain unresolved; no claim that bounded source-still camera motion fulfills true video requirements. Human acceptance remains mandatory. No private Drive file IDs or original source bytes are committed.
