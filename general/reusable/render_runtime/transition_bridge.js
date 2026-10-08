/* AIVideoEdit browser transition bridge.
 *
 * Load order:
 *   1. vendor/aivideoedit-gsap.min.js
 *   2. vendor/aivideoedit-transition-core.js
 *   3. vendor/aivideoedit-transitions.js
 *
 * Production code calls window.AIVideoEditTransitions only. The implementation
 * package behind this bridge is replaceable and is not production identity.
 */
(() => {
  'use strict';

  const EFFECT_MAP = Object.freeze({
    organic_warp: 'domain-warp',
    ember_burn: 'ridged-burn',
    whip_pan: 'whip-pan',
    iris_glow: 'sdf-iris',
    ripple_waves: 'ripple-waves',
    gravity_lens: 'gravitational-lens',
    cinematic_zoom: 'cinematic-zoom',
    chromatic_split: 'chromatic-split',
    digital_glitch: 'glitch',
    vortex_warp: 'swirl-vortex',
    heat_shimmer: 'thermal-distortion',
    white_flash: 'flash-through-white',
    morph_warp: 'cross-warp-morph',
    light_leak: 'light-leak',
  });

  function finiteNumber(value, label) {
    const n = Number(value);
    if (!Number.isFinite(n)) throw new Error(`${label} must be finite`);
    return n;
  }

  function normalizeTransition(item, index) {
    if (!item || typeof item !== 'object') throw new Error(`transition[${index}] must be an object`);
    const effect = String(item.effect || '');
    const shader = EFFECT_MAP[effect];
    if (!shader) throw new Error(`transition[${index}] has unknown AIVideoEdit effect: ${effect}`);
    const time = finiteNumber(item.time, `transition[${index}].time`);
    const duration = item.duration == null ? 0.7 : finiteNumber(item.duration, `transition[${index}].duration`);
    if (time < 0) throw new Error(`transition[${index}].time must be >= 0`);
    if (duration <= 0) throw new Error(`transition[${index}].duration must be > 0`);
    return {
      time,
      duration,
      shader,
      ...(item.ease ? { ease: String(item.ease) } : {}),
    };
  }

  function init(config) {
    if (!config || typeof config !== 'object') throw new Error('transition config is required');
    const core = globalThis.HyperShader;
    if (!core || typeof core.init !== 'function') {
      throw new Error('AIVideoEdit transition core is not loaded');
    }
    const scenes = Array.isArray(config.scenes) ? config.scenes.map(String) : [];
    if (!scenes.length) throw new Error('at least one scene id is required');
    if (new Set(scenes).size !== scenes.length) throw new Error('scene ids must be unique');

    const transitions = (config.transitions || []).map(normalizeTransition);
    transitions.sort((a, b) => a.time - b.time);

    const timeline = core.init({
      bgColor: String(config.bgColor || '#000000'),
      ...(config.accentColor ? { accentColor: String(config.accentColor) } : {}),
      scenes,
      transitions,
      ...(config.timeline ? { timeline: config.timeline } : {}),
      ...(config.compositionId ? { compositionId: String(config.compositionId) } : {}),
      ...(config.previewCaptureFps ? { previewCaptureFps: Number(config.previewCaptureFps) } : {}),
    });

    if (config.compositionId) {
      globalThis.__timelines = globalThis.__timelines || {};
      globalThis.__timelines[String(config.compositionId)] = timeline;
    }
    return timeline;
  }

  globalThis.AIVideoEditTransitions = Object.freeze({
    init,
    names: Object.freeze(Object.keys(EFFECT_MAP)),
    resolve(effect) {
      const resolved = EFFECT_MAP[String(effect || '')];
      if (!resolved) throw new Error(`unknown AIVideoEdit transition effect: ${effect}`);
      return resolved;
    },
  });
})();
