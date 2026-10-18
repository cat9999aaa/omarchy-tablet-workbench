"""Pure conversion of existing control-center snapshots. No device access."""
import math

from .manifest import invalid, json_value
from .state import identifier, nonnegative, normalize_state, sequence_number

_MAPPING = (
    ('temperature', 'dashen.device.temperature', 'thermal-summary', 'device.temperature.read'),
    ('touch', 'dashen.device.touch-mode', 'touch-mode', 'device.touch-mode.read'),
)
_CONTEXT = {'device_id', 'session_id', 'output_id', 'owner_generation', 'sequence'}
_FIELDS = {'capability', 'available', 'desired', 'actual', 'health', 'observed_at',
           'stale_after', 'source', 'reason', 'boot_default'}
_AUTHORITY = {'admin', 'confirmed', 'permissions', 'principal', 'argv', 'action', 'authorization', 'ticket'}


def _reject_authority(value):
    if type(value) is dict:
        if _AUTHORITY.intersection(value):
            invalid()
        for item in value.values():
            _reject_authority(item)
    elif type(value) is list:
        for item in value:
            _reject_authority(item)


def adapt_control_snapshot(snapshot: dict, context: dict, ages_ms: dict[str, float | None]) -> list[dict]:
    if type(snapshot) is not dict or type(context) is not dict or type(ages_ms) is not dict:
        invalid()
    if set(context) != _CONTEXT or not sequence_number(context['sequence']):
        invalid()
    if not all(identifier(context[k]) for k in _CONTEXT - {'sequence'}):
        invalid()
    json_value(snapshot)
    _reject_authority(snapshot)
    result = []
    for field, capability, resource, permission in _MAPPING:
        old = snapshot.get(field)
        if type(old) is not dict:
            state = {'available': False, 'actual': None, 'health': 'unavailable',
                     'source': 'missing-control-field', 'observed_at': None, 'stale_after': None}
        else:
            state = {key: value for key, value in old.items() if key in _FIELDS}
        actual = state.get('actual')
        if field == 'temperature':
            valid = type(actual) in (int, float) and -20 <= actual <= 150 and math.isfinite(actual)
        else:
            valid = type(actual) is int and actual in (0, 1, 2)
        if actual is not None and not valid:
            state['actual'] = None
            if state.get('health') not in ('error', 'stale', 'unavailable'):
                state['health'] = 'unknown'
        if field == 'touch' and 'boot_default' in state:
            default = state['boot_default']
            if type(default) is not int or default not in (0, 1, 2):
                state['boot_default'] = None
                if state.get('health') not in ('error', 'stale', 'unavailable'):
                    state['health'] = 'unknown'
        age = nonnegative(ages_ms.get(field))
        state = normalize_state(state, age, 0)
        result.append({**context, 'contract_version': '0.1.0', 'capability_id': capability,
                       'resource_id': resource, 'read_permission': permission,
                       'observation_context': {'age_upper_bound_ms': age}, 'state': state})
    return result
