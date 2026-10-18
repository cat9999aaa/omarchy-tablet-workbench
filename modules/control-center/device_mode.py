"""Pure local mode suggestions; does not apply settings or control input."""
import math


def _time(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def reduce_mode(choice: str, last_effective: str | None, evidence: dict,
                now_ms: float, pending: dict | None) -> dict:
    if choice not in ('auto', 'tablet', 'desktop') or last_effective not in (None, 'tablet', 'desktop'):
        raise ValueError('invalid mode')

    def result(effective=last_effective, health='unknown', reason='unknown_evidence', next_pending=None):
        return {'effective': effective, 'health': health, 'reason_code': reason, 'pending': next_pending}

    if choice != 'auto':
        return result(choice, 'observed', 'manual')
    if not _time(now_ms):
        return result(reason='time_invalid')
    if pending is not None:
        if (not isinstance(pending, dict) or pending.get('target') not in ('tablet', 'desktop') or
                not _time(pending.get('since_ms')) or not _time(pending.get('last_seen_ms')) or
                not pending['since_ms'] <= pending['last_seen_ms'] <= now_ms):
            return result(reason='time_invalid')
        if now_ms - pending['last_seen_ms'] > 2000:
            return result(reason='observation_gap')
    if (not isinstance(evidence, dict) or type(evidence.get('schema_version')) is not int or
            evidence['schema_version'] != 1 or evidence.get('complete') is not True or
            evidence.get('health') != 'observed' or
            any(value is not None and type(value) is not bool for value in
                (evidence.get('physical_keyboard_present'), evidence.get('touch_present'),
                 evidence.get('tablet_switch_capability')))):
        return result()
    keyboard = evidence.get('physical_keyboard_present')
    touch = evidence.get('touch_present')
    if keyboard is None or (keyboard is False and touch is None):
        return result()
    if keyboard is True:
        target, threshold = 'desktop', 500
    elif touch is True:
        target, threshold = 'tablet', 1000
    else:
        return result(reason='no_supported_mode')
    since = pending['since_ms'] if pending and pending['target'] == target else now_ms
    next_pending = {'target': target, 'since_ms': since, 'last_seen_ms': now_ms}
    if now_ms - since >= threshold:
        return result(target, 'observed', 'stable', next_pending)
    return result(reason='debouncing', next_pending=next_pending)
