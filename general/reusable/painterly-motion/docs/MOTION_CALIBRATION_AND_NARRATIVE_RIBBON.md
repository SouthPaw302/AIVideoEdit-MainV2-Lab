# Reference-Motion Calibration & Narrative-Ribbon Reframing

Two reusable methods were developed during Silver Coin V5/V5.1.

## 1. Reference-motion calibration

### Problem

A textual style label describes appearance but often fails to describe **how much the image should move**. Applying the same pan/zoom/warp to every scene creates either a slideshow or unstable painterly boiling.

### Method

Use `tools/video_fx/analyze_motion_signature.py` on one or more user-approved motion references. Measure:

- dense optical-flow magnitude
- P90/P99 motion per frame
- frame-difference energy
- phase-correlation camera drift
- mean saturation/luminance

Treat the measured low/high references as a permissible motion envelope.

Then map the music and scene role into that envelope:

- quiet verse / portrait → low-reference motion
- ordinary narrative → interpolated mid-range
- chorus / dance → high-reference neighborhood
- transient accents → short P90/P99 excursions only

Do **not** copy subjects or exact camera paths from the reference. The reference defines motion density and cadence.

### Silver Coin measured envelope

At 280×280 analysis scale:

- restrained reference mean flow: ~0.428 px/frame
- active reference mean flow: ~1.566 px/frame
- active-reference median P90: ~2.214 px/frame
- active-reference median P99: ~3.235 px/frame

Silver Coin V5 uses these values to cap audio-driven camera and micro-motion.

## 2. Narrative-ribbon reframing

### Problem

Recovered storyboard sheets may contain many narrow adjacent panels with caption/lyric bands. Enlarging each small panel independently can create bad crops—hands, torsos, or object fragments with no readable composition. Generative inpainting can introduce unstable pixels that shimmer once animated.

### Method

1. Identify a contiguous horizontal/vertical run of related panels.
2. Crop a clean **ribbon** that excludes caption/title bands before animation.
3. Define semantic centers for each narrative beat inside the ribbon.
4. Extract overlapping 16:9 windows around those centers.
5. Optionally animate a continuous camera pan through the ribbon rather than hard-cutting between every small panel.
6. Keep provenance: source rectangle, centers, window widths, output names.

Implementation: `tools/video_fx/narrative_ribbon.py`.

### Silver Coin V5.1 bridge use

The bridge originally produced over-cropped fragments for farmer, smith, carter, maid, lovers, tomorrow-work, and wine-table beats. V5.1 rebuilt those images from one clean storyboard ribbon above the lyric band, producing readable character compositions without generative repair.

## Production principle

When recovering visual assets, prefer:

**real pixels + deterministic reframing + stable motion**

over
**large generative repairs + uncertain temporal texture**.

These methods are project-independent and should be considered for every future AIVideoEdit production with user-supplied visual references or storyboard/contact-sheet sources.
