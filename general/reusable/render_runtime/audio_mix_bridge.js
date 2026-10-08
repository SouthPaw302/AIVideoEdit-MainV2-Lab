/* AIVideoEdit browser audio mix bridge.
 *
 * Applies a validated aivideoedit.audio-mix.v1 plan to composition media.
 * The render engine consumes the resulting attributes. Production code talks
 * only to AIVideoEditAudioMix.
 */
(() => {
  'use strict';

  function jsonAttr(value) {
    return JSON.stringify(value);
  }

  function cleanAutomation(automation) {
    if (!automation) return null;
    return {
      version: 1,
      lanes: (automation.lanes || []).map((lane) => ({
        target: lane.target,
        points: (lane.points || []).map((point) => {
          const out = { t: Number(point.t), v: Number(point.v) };
          if (point.curve != null) out.curve = Number(point.curve);
          if (point.viaX != null) out.viaX = Number(point.viaX);
          if (point.viaY != null) out.viaY = Number(point.viaY);
          return out;
        }),
      })),
    };
  }

  function applyFxAndAutomation(element, record) {
    if (record.volume != null) element.setAttribute('data-volume', String(record.volume));
    if (record.fx_chain) element.setAttribute('data-fx-chain', jsonAttr(record.fx_chain));
    const automation = cleanAutomation(record.automation);
    if (automation) element.setAttribute('data-automation', jsonAttr(automation));
  }

  function ensureGroup(group, strict) {
    let element = document.getElementById(group.id);
    if (element && element.tagName.toLowerCase() !== 'hf-audio-group') {
      if (strict) throw new Error(`audio group id collides with non-group element: ${group.id}`);
      return null;
    }
    if (!element) {
      element = document.createElement('hf-audio-group');
      element.id = group.id;
      element.hidden = true;
      document.body.appendChild(element);
    }
    if (group.label) element.setAttribute('data-label', String(group.label));
    applyFxAndAutomation(element, group);
    return element;
  }

  function apply(plan, options = {}) {
    if (!plan || plan.schema !== 'aivideoedit.audio-mix.v1') {
      throw new Error('AIVideoEdit audio mix requires aivideoedit.audio-mix.v1');
    }
    const strict = options.strict !== false;
    const tracks = new Map((plan.tracks || []).map((track) => [String(track.id), track]));
    const groupMembership = new Map();

    for (const group of plan.groups || []) {
      ensureGroup(group, strict);
      for (const member of group.members || []) {
        const id = String(member);
        if (groupMembership.has(id)) throw new Error(`track belongs to multiple audio groups: ${id}`);
        groupMembership.set(id, String(group.id));
      }
    }

    const applied = [];
    const missing = [];
    for (const [id, track] of tracks) {
      const element = document.getElementById(id);
      if (!element) {
        missing.push(id);
        if (strict) throw new Error(`audio mix track element not found: ${id}`);
        continue;
      }
      applyFxAndAutomation(element, track);
      const groupId = groupMembership.get(id);
      if (groupId) element.setAttribute('data-audio-group', groupId);
      applied.push(id);
    }

    return Object.freeze({ applied, missing, groups: [...new Set(groupMembership.values())] });
  }

  globalThis.AIVideoEditAudioMix = Object.freeze({ apply });
})();
