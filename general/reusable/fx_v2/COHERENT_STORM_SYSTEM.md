# Coherent Storm System

Purpose: make weather read as one physically coupled scene system rather than unrelated overlays.

## Core rule
Rain, wind, cloud mass, lightning, wet reflections, exposed foreground motion, and practical-light response share one authored storm state. A gust or lightning event must propagate consistently through the relevant semantic regions while protected geometry stays stable.

## Required behavior
- Near-locked camera. Internal scene motion carries the effect.
- Exterior rain uses depth-separated planes: near rain travels most, mid rain less, distant rain/clouds slowest.
- Window/glass droplets are separate from exterior rain and never imply rain inside the room.
- Cloud mass advects independently of camera motion.
- Gust events change rain angle/speed and only move foreground elements that are plausibly wind-exposed.
- Lightning originates from a plausible sky region, then produces a brief coherent environmental illumination response. No arbitrary global white flash.
- Wet-road, glass, stone, and reflective surfaces react to rain/light events only where physically plausible.
- Visible practical lights may breathe or fluctuate locally, but must not globally pulse the frame.
- Reflections move like reflections; never deform faces, bodies, hands, phones, architecture, or protected linework.

## Forbidden
- whole-frame rain overlays
- global wobble/shake used as weather
- synchronized motion on unrelated surfaces
- dry-room rain
- random full-frame flashing
- identity/anatomy drift
- endless zoom used in place of internal motion

## Recommended use
Apply the `coherent_storm_system` preset in `presets.json`, then constrain every ROI by semantic masks for exterior, glass, sky, wet surfaces, practical lights, and wind-exposed foreground objects.

This package captures reusable motion/FX principles only. Reference footage is not a runtime dependency and is not redistributed.
