import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
FX = ROOT / 'general/reusable/fx_v2'
sys.path.insert(0, str(FX))
from promoted_effects import EFFECT_NAMES, LEGACY_ALIASES
from verify_promoted_effects import verify


def test_promoted_effect_verification_passes():
    result = verify()
    assert result['result'] == 'PASS'
    assert result['effect_count'] == len(EFFECT_NAMES) == 52
    assert result['legacy_alias_count'] == len(LEGACY_ALIASES) == 71
    assert all(v['status'] == 'PASS' for v in result['effects'].values())


def test_every_legacy_alias_resolves_to_live_effect_name():
    registry = json.loads((FX / 'effect_name_registry.json').read_text())['effects']
    aliases = json.loads((FX / 'effect_aliases.json').read_text())['aliases']
    assert set(registry) == set(EFFECT_NAMES)
    for label, name in aliases.items():
        assert name in registry, label
        assert registry[name]['status'] == 'approved'
        assert registry[name]['call'] == 'apply_effect'
        assert LEGACY_ALIASES[label] == name
