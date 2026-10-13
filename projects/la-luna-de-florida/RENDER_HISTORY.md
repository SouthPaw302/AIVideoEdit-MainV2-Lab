# Render history

- Candidate 01: 321.16s, H.264 960x540 24fps + AAC stereo, SHA256 `a351b923d8d20189f102ea6275b118f51f706e398e30adc36c1bda3d023f2967`. **Superseded** after discovering embedded generated-layout artefacts in two extracted images.
- Candidate 02: 321.16s, same technical format, SHA256 `bf2485631c0388ec304f13ef97eaafa4048ccdcf490259fb37a78b09d061727b`. Current review-only workprint uploaded to Drive.

The render was executed in a local sandbox with Python/OpenCV/FFmpeg and verified by ffprobe. It was not executed by the canonical MainV2 GitHub Actions pipeline. Do not describe it as a canonical render, video-generation-model inference, or an artistically approved film.
