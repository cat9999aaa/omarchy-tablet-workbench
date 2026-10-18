"""Deterministic selection from actual finite supported-version lists."""
import re
from .errors import ContractError

_VERSION = re.compile(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)')


def unsupported():
    raise ContractError('unsupported_version')


def parse_version(value: str) -> tuple[int, int, int]:
    if type(value) is not str or len(value) > 256 or not _VERSION.fullmatch(value):
        unsupported()
    return tuple(int(part) for part in value.split('.'))


def version_range(value: dict):
    if type(value) is not dict or set(value) != {'min', 'max_exclusive'}:
        unsupported()
    low, high = parse_version(value['min']), parse_version(value['max_exclusive'])
    if low >= high:
        unsupported()
    return low, high


def _supported(values):
    if type(values) is not list or not 1 <= len(values) <= 16:
        unsupported()
    parsed = [parse_version(v) for v in values]
    if len(set(parsed)) != len(parsed):
        unsupported()
    return set(parsed)


def _family(version):
    return version[:2] if version[0] == 0 else version[:1]


def negotiate(local_versions: list[str], remote_versions: list[str],
              local_range: dict, remote_range: dict) -> str:
    local, remote = _supported(local_versions), _supported(remote_versions)
    lo, hi = version_range(local_range)
    rlo, rhi = version_range(remote_range)
    candidates = [v for v in local & remote if lo <= v < hi and rlo <= v < rhi
                  and _family(v) == _family(lo) == _family(rlo)]
    if not candidates:
        unsupported()
    return '.'.join(map(str, max(candidates)))
