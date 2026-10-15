# Godot original music-video experiment

**Branch only:** test/godot-render. Do not treat this as a canonical production.

## Sources
- Approved existing-release media selected *only for this requested experiment*, not reclassified as a locked new song production: `source__04_twilight_inn_beneath_the_flower_crown.png`, SHA-256 `81cfa4e39aa944782978ec921bac45078dfe4ad8adb4372f9ba132168cc3a723`.
- Instrumental WAV `source__El_Viento_trae_tu_nombre_Instrumental.wav`, SHA-256 `8d451360246378db551282c3703add4cd474c9ad3a4c6cf778390ae727820fe0`.
- Both remain unchanged on the original GitHub release. They are downloaded and byte-verified, not embedded in the repo.

## Authored 14-second scene
`scripts/twilight.gd` creates new cinema from one still with music-synced camera keys, local light bloom, independently animated deep/near particles, moving haze, windy foreground silhouettes and a discrete gust sequence. The displayed characters and buildings are drawn from the original image, not AI-regenerated, warped, or reimagined.

The audio analyzer scans source PCM for a high-energy 14-second segment and measures frame-aligned RMS/transient controls at 24 FPS. The segment start is recorded, never invented.

## Two outputs
1. Real Godot Movie Maker PNG frames with the source WAV excerpt, FFmpeg H.264/AAC encoded to `godot.mp4`.
2. The same movie additionally processed by approved original `FX2-ATM-001` plus `FX2-LIGHT-001` through the existing MainV2 FXExecutor, producing `mainv2_fx.mp4`. No FX registry or main workflow modification.

## Proof and limitations
Technical validator checks output dimensions, duration, frame count, audio, cryptographic hashes, frame samples and original source identities. CI artifacts are short-lived. No artistic acceptance without the user's visual review. This is not a true 3D reconstruction, nor is the result a replacement for an approved long-form music film. Stay on the isolated test branch, do not merge `main`.