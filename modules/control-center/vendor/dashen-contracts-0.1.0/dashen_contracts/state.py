"""Pure freshness and ordered snapshot/event rules; no clocks or I/O."""
from copy import deepcopy
import math

from .errors import ContractError
from .manifest import invalid, json_value, valid_name


def nonnegative(value):
    if type(value) not in (int, float):
        return None
    try:
        return value if math.isfinite(value) and value >= 0 else None
    except OverflowError:
        return None


def normalize_state(state: dict, age_upper_bound_ms: float | None, elapsed_ms: float) -> dict:
    if type(state) is not dict:
        invalid()
    # Invalid time evidence is representable as unknown; invalid data is not.
    result = dict(state)
    for key in ('observed_at', 'stale_after'):
        result[key] = nonnegative(result.get(key))
    json_value(result)
    result = deepcopy(result)
    age, elapsed = nonnegative(age_upper_bound_ms), nonnegative(elapsed_ms)
    health = result.get('health')
    if result.get('available') is False:
        health = 'unavailable'
    elif health in ('error', 'unavailable', 'stale'):
        pass  # Failure/expiry cannot be cured by wrapping the same observation.
    elif (result.get('available') is not True or result.get('actual') is None
          or any(v is None for v in (age, elapsed, result['observed_at'], result['stale_after']))):
        health = 'unknown'
    elif nonnegative(age + elapsed) is None or nonnegative(result['stale_after'] * 1000) is None:
        health = 'unknown'
    elif age + elapsed > result['stale_after'] * 1000:
        health = 'stale'
    elif health != 'observed':
        health = 'unknown'
    result['health'] = health
    return result


def identifier(value):
    if type(value) is not str or not 1 <= len(value) <= 256:
        return False
    return all(32 < ord(char) < 127 for char in value)


def sequence_number(value):
    return type(value) is int and 0 <= value < 2**53


def _state_valid(value):
    try:
        if type(value) is not dict:
            return False
        json_value(value)
        return True
    except ContractError:
        return False


class StateCursor:
    """One authenticated subscription instance. Caller routes only its key.

    Events carry complete per-capability state values, not JSON merge patches.
    A cursor does not authenticate packets or infer their device/session identity.
    """
    def __init__(self, instance_key: tuple[str, str, str, str, str]):
        if (type(instance_key) is not tuple or len(instance_key) != 5
                or not all(identifier(x) for x in instance_key) or not valid_name(instance_key[3])):
            invalid()
        self._instance_key = instance_key
        self._epoch = self._nonce = self._generation = None
        self._sequence = None
        self._state = None
        self._needs_snapshot = True

    @property
    def state(self) -> dict | None:
        return deepcopy(self._state)

    @property
    def needs_snapshot(self) -> bool:
        return self._needs_snapshot

    def begin(self, epoch: str, nonce: str) -> None:
        if not identifier(epoch) or not identifier(nonce):
            invalid()
        self._epoch, self._nonce = epoch, nonce
        self._needs_snapshot = True

    def accept_snapshot(self, epoch: str, nonce: str, generation: str, sequence: int, state: dict) -> bool:
        if (self._nonce is None or epoch != self._epoch or nonce != self._nonce
                or not identifier(generation) or not sequence_number(sequence) or not _state_valid(state)):
            return False
        if generation == self._generation and (sequence < self._sequence
                or (sequence == self._sequence and state != self._state)):
            return False
        self._generation, self._sequence = generation, sequence
        self._state = deepcopy(state)
        self._nonce = None  # One response consumes the outstanding request.
        self._needs_snapshot = False
        return True

    def accept_event(self, epoch: str, generation: str, sequence: int, state: dict) -> bool:
        if (epoch != self._epoch or self._needs_snapshot or not identifier(generation)
                or not sequence_number(sequence) or not _state_valid(state)):
            return False
        if generation != self._generation:
            self._needs_snapshot = True
            return False
        if sequence <= self._sequence:
            return False
        if sequence != self._sequence + 1:
            self._needs_snapshot = True
            return False
        self._sequence, self._state = sequence, deepcopy(state)
        return True
