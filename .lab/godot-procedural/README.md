# New procedural 3D Godot scene, not a reused video

This isolated `test/godot-render` experiment builds terrain, boulders, stone ruins, altar, orbiting emissive rings, stars, mist and floating particles from **new GDScript-generated 3D geometry**. A physically moving 3D camera creates real geometric parallax. Zero input images or videos are used.

The real El Viento instrumental WAV is downloaded from the project's media release, SHA-256 checked, then analyzed for per-frame audio energy and transients. Godot renders 336 frames (14 seconds, 960x540, 24 fps) with Xvfb/Mesa software OpenGL on GitHub Actions.

Variants: pure Godot MP4 and the Godot frames additionally processed by the repo's existing approved `FX2-ATM-001` and `FX2-LIGHT-001` via the actual FXExecutor. Technical QC records hashes, frames, streams, runtime identity; creative approval remains human-only. Separate read-only authoritative main checkout/bootstrap, no production promotion, no other branch modifications. Technical and aesthetic quality are distinct.
