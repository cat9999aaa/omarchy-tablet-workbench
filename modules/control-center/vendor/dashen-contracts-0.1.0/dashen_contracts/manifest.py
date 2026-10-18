"""Bounded, non-executing manifest validation (RFC 0001)."""
import json
import math
from pathlib import Path
import re
import stat

from .errors import ContractError
from .versions import parse_version, version_range

MAX_BYTES = 65536
_NAME = re.compile(r'[a-z][a-z0-9-]*(?:\.[a-z][a-z0-9-]*)+')
PERMISSIONS = frozenset({'device.temperature.read', 'device.touch-mode.read', 'device.input.read'})


def invalid():
    raise ContractError('invalid_request')


def json_value(value, depth=0):
    """Reject Python-only values, lone surrogates and unreasonable nesting."""
    if depth > 64:
        invalid()
    if value is None or type(value) in (bool, int):
        return
    if type(value) is float:
        if not math.isfinite(value):
            invalid()
    elif type(value) is str:
        try:
            value.encode('utf-8')
        except UnicodeError:
            invalid()
    elif type(value) is list:
        for item in value:
            json_value(item, depth + 1)
    elif type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                invalid()
            json_value(key, depth + 1)
            json_value(item, depth + 1)
    else:
        invalid()


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            invalid()
        result[key] = value
    return result


def parse_json(raw: bytes) -> dict:
    if type(raw) is not bytes or len(raw) > MAX_BYTES:
        invalid()
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs,
                           parse_constant=lambda _: invalid())
        json_value(value)
    except (UnicodeError, ValueError, RecursionError, OverflowError):
        invalid()
    if type(value) is not dict:
        invalid()
    return value


def valid_name(value):
    return type(value) is str and len(value) <= 256 and _NAME.fullmatch(value) is not None


def _names(value):
    if type(value) is not list or len(value) > 64:
        invalid()
    if any(not valid_name(item) for item in value) or len(set(value)) != len(value):
        invalid()


def _entry(entry, root):
    if type(entry) is not dict or set(entry) != {'kind', 'path'} or entry['kind'] != 'declarative':
        invalid()
    path = entry['path']
    if type(path) is not str or not path or len(path) > 4096 or '\\' in path or '\x00' in path:
        invalid()
    parts = path.split('/')
    if any(p in ('', '.', '..') for p in parts):
        invalid()
    try:
        base = Path(root).resolve(strict=True)
        current = base
        for part in parts:
            current = current / part
            if stat.S_ISLNK(current.lstat().st_mode):
                invalid()
        if not stat.S_ISREG(current.stat().st_mode) or not current.resolve().is_relative_to(base):
            invalid()
    except (OSError, ValueError, RuntimeError):
        invalid()
    # Metadata check only; the caller must revalidate if the package changes.


def validate_manifest(raw: bytes, root: Path) -> dict:
    value = parse_json(raw)
    required = {'schema_version', 'id', 'version', 'contracts', 'provides', 'requires', 'permissions', 'entry'}
    if set(value) != required or type(value['schema_version']) is not int:
        invalid()
    if value['schema_version'] != 1:
        raise ContractError('unsupported_version')
    if not valid_name(value['id']) or type(value['version']) is not str:
        invalid()
    for key in ('provides', 'requires', 'permissions'):
        _names(value[key])
    if any(p not in PERMISSIONS for p in value['permissions']):
        raise ContractError('permission_denied')
    ranges = value['contracts']
    if type(ranges) is not dict or set(ranges) != {'min', 'max_exclusive'} or any(type(v) is not str for v in ranges.values()):
        invalid()
    parse_version(value['version'])
    version_range(ranges)
    _entry(value['entry'], root)
    return value
