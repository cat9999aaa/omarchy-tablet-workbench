"""Panel-owned, bounded mode reads and per-output choices; no device mutations."""
# SPDX-License-Identifier: GPL-3.0-only
from contextlib import contextmanager
import fcntl
import json
import math
import os
from pathlib import Path
import re
import secrets
import select
import stat
import sys
import time
from contract_host import boottime_ms
from device_classifier import aggregate
from device_evidence import collect_device_evidence
from device_mode import reduce_mode

CHOICES = ('auto', 'tablet', 'desktop')
LIMIT = 4096


def _key(key):
    return isinstance(key, str) and re.fullmatch(r'[A-Za-z0-9_.-]{1,128}', key) is not None


def _pairs(items):
    value = {}
    for key, item in items:
        if key in value:
            raise ValueError('invalid_request')
        value[key] = item
    return value


def _json(raw):
    if len(raw) > LIMIT:
        raise ValueError('invalid_request')
    def invalid(_):
        raise ValueError('invalid_request')
    def finite(text):
        value = float(text)
        if not math.isfinite(value):
            raise ValueError('invalid_request')
        return value
    return json.loads(raw, object_pairs_hook=_pairs, parse_constant=invalid, parse_float=finite)


def parse_request(op, raw):
    try:
        value = _json(raw)
        fields = {'choice', 'last_effective', 'pending'} if op == 'mode-step' else (
            {'output_key', 'choice'} if op == 'mode-preference-write' else {'output_key'})
        if not isinstance(value, dict) or set(value) != fields:
            raise ValueError()
        if op == 'mode-step':
            if value['choice'] not in CHOICES or value['last_effective'] not in (None, 'tablet', 'desktop'):
                raise ValueError()
            pending = value['pending']
            if pending is not None and (not isinstance(pending, dict) or
                    set(pending) != {'target', 'since_ms', 'last_seen_ms'} or
                    pending['target'] not in ('tablet', 'desktop') or
                    any(type(pending[k]) not in (int, float) for k in ('since_ms', 'last_seen_ms'))):
                raise ValueError()
        elif not _key(value['output_key']) or ('choice' in value and value['choice'] not in CHOICES):
            raise ValueError()
        return value
    except (ValueError, TypeError, RecursionError, OverflowError, UnicodeError):
        raise ValueError('invalid_request') from None


def mode_step(request, *, collect=collect_device_evidence, clock_ms=boottime_ms):
    request = parse_request('mode-step', json.dumps(request, allow_nan=False).encode())
    choice, last, pending = (request[k] for k in ('choice', 'last_effective', 'pending'))
    unknown = aggregate([], False, 'read_failed', 0)
    if choice != 'auto':
        return {'schema_version': 1, 'evidence': unknown,
                'mode': reduce_mode(choice, last, unknown, 0, None), 'confirm_after_ms': None}
    start = clock_ms()
    data = collect()
    end = clock_ms()
    if not (math.isfinite(start) and math.isfinite(end) and 0 <= end - start <= 2000):
        mode = {'effective': last, 'health': 'unknown', 'reason_code': 'observation_gap', 'pending': None}
        return {'schema_version': 1, 'evidence': unknown, 'mode': mode, 'confirm_after_ms': None}
    mode = reduce_mode(choice, last, data, start, pending)
    delay = None
    if mode['reason_code'] == 'debouncing':
        p = mode['pending']
        threshold = 500 if p['target'] == 'desktop' else 1000
        delay = max(0, min(1000, math.ceil(p['since_ms'] + threshold - end)))
    return {'schema_version': 1, 'evidence': data, 'mode': mode, 'confirm_after_ms': delay}


def _state_dir():
    base = os.environ.get('XDG_STATE_HOME') or str(Path.home() / '.local/state')
    path = Path(base)
    if not path.is_absolute() or '..' in path.parts:
        raise ValueError('unsafe_state')
    return path / 'pcadmin-control-center'


def _directory(path):
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        for part in path.parts[1:]:
            try:
                os.mkdir(part, 0o700, dir_fd=fd)
            except FileExistsError:
                pass
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
            os.close(fd)
            fd = child
            info = os.fstat(fd)
            if info.st_uid not in (0, os.getuid()) or (info.st_mode & 0o022 and not info.st_mode & stat.S_ISVTX):
                raise ValueError('unsafe_state')
        if os.fstat(fd).st_uid != os.getuid():
            raise ValueError('unsafe_state')
        return fd
    except BaseException:
        os.close(fd)
        raise


def _regular(fd):
    info = os.fstat(fd)
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or
            stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1):
        raise ValueError('unsafe_state')


@contextmanager
def _store():
    path = _state_dir()
    directory = _directory(path)
    lock = None
    try:
        lock = os.open('.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK,
                       0o600, dir_fd=directory)
        _regular(lock)
        deadline = time.monotonic() + 1
        while True:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise ValueError('state_busy')
                time.sleep(.01)
        # Re-open without following any ancestor link after acquiring the lock.
        current = _directory(path)
        try:
            a, b = os.fstat(current), os.fstat(directory)
            if (a.st_dev, a.st_ino) != (b.st_dev, b.st_ino):
                raise ValueError('state_changed')
        finally:
            os.close(current)
        yield directory
    finally:
        if lock is not None:
            os.close(lock)
        os.close(directory)


def _read_doc(directory):
    try:
        fd = os.open('modes.json', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=directory)
    except FileNotFoundError:
        return {'schema_version': 1, 'outputs': {}}
    try:
        _regular(fd)
        data = _json(os.read(fd, LIMIT + 1))
    finally:
        os.close(fd)
    if (not isinstance(data, dict) or set(data) != {'schema_version', 'outputs'} or
            type(data['schema_version']) is not int or data['schema_version'] != 1 or
            not isinstance(data['outputs'], dict) or len(data['outputs']) > 16 or
            any(not _key(k) or v not in CHOICES for k, v in data['outputs'].items())):
        raise ValueError('invalid_state')
    return data


def read_preference(output_key):
    try:
        if not _key(output_key):
            raise ValueError()
        with _store() as directory:
            data = _read_doc(directory)
        return {'schema_version': 1, 'choice': data['outputs'].get(output_key, 'auto'), 'reason_code': 'ok'}
    except (OSError, ValueError, TypeError, RecursionError):
        return {'schema_version': 1, 'choice': 'auto', 'reason_code': 'state_unavailable'}


def write_preference(output_key, choice):
    try:
        if not _key(output_key) or choice not in CHOICES:
            raise ValueError()
        with _store() as directory:
            data = _read_doc(directory)
            if output_key not in data['outputs'] and len(data['outputs']) >= 16:
                raise ValueError()
            data['outputs'][output_key] = choice
            raw = json.dumps(data, separators=(',', ':'), allow_nan=False).encode()
            if len(raw) > LIMIT:
                raise ValueError()
            temporary = '.modes-' + secrets.token_hex(12)
            backup = temporary + '-old'
            had_old = False
            replaced = False
            keep_backup = False
            fd = None
            try:
                try:
                    old_fd = os.open('modes.json', os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC,
                                     dir_fd=directory)
                    try:
                        _regular(old_fd)
                        old_raw = os.read(old_fd, LIMIT + 1)
                        if len(old_raw) > LIMIT:
                            raise ValueError('invalid_state')
                    finally:
                        os.close(old_fd)
                    backup_fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC,
                                        0o600, dir_fd=directory)
                    try:
                        old_view = memoryview(old_raw)
                        while old_view:
                            count = os.write(backup_fd, old_view)
                            if count <= 0:
                                raise OSError('write_failed')
                            old_view = old_view[count:]
                        os.fsync(backup_fd)
                    finally:
                        os.close(backup_fd)
                    had_old = True
                except FileNotFoundError:
                    pass
                fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                             0o600, dir_fd=directory)
                view = memoryview(raw)
                while view:
                    count = os.write(fd, view)
                    if count <= 0:
                        raise OSError('write_failed')
                    view = view[count:]
                os.fsync(fd)
                os.replace(temporary, 'modes.json', src_dir_fd=directory, dst_dir_fd=directory)
                replaced = True
                os.fsync(directory)
            except OSError:
                if replaced:
                    try:
                        if had_old:
                            os.replace(backup, 'modes.json', src_dir_fd=directory, dst_dir_fd=directory)
                        else:
                            os.unlink('modes.json', dir_fd=directory)
                        os.fsync(directory)
                    except OSError:
                        # Preserve the recovery copy if the filesystem also rejects rollback.
                        keep_backup = True
                raise
            finally:
                if fd is not None:
                    os.close(fd)
                for name in [temporary] + ([] if keep_backup else [backup]):
                    try:
                        os.unlink(name, dir_fd=directory)
                    except FileNotFoundError:
                        pass
        return {'schema_version': 1, 'saved': True, 'reason_code': 'ok'}
    except (OSError, ValueError, TypeError, RecursionError):
        return {'schema_version': 1, 'saved': False, 'reason_code': 'state_unavailable'}


def output_policy(output_key, *, sysfs_root=Path('/sys'), clock=time.monotonic):
    fail = {'schema_version': 1, 'eligible': False, 'reason_code': 'output_unavailable'}
    try:
        if not _key(output_key):
            return fail
        deadline = clock() + 1
        root = Path(sysfs_root).resolve(strict=True)
        matches = []
        count = 0
        with os.scandir(root / 'class/drm') as entries:
            for entry in entries:
                count += 1
                if count > 128 or clock() > deadline:
                    return fail
                if not re.fullmatch(r'card[0-9]+-' + re.escape(output_key), entry.name):
                    continue
                target = Path(entry.path).resolve(strict=True)
                if not target.is_relative_to(root / 'devices') or target.is_relative_to(root / 'devices/virtual'):
                    return fail
                fd = os.open(target / 'status', os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC)
                try:
                    if not stat.S_ISREG(os.fstat(fd).st_mode):
                        return fail
                    raw = os.read(fd, 16385)
                    if len(raw) > 16384 or clock() > deadline:
                        return fail
                    matches.append(raw.strip() == b'connected')
                finally:
                    os.close(fd)
        if matches == [True]:
            return {'schema_version': 1, 'eligible': True, 'reason_code': 'local_output'}
    except (OSError, ValueError):
        pass
    return fail


def command(op):
    try:
        raw = bytearray()
        deadline = time.monotonic() + 2
        while True:
            left = deadline - time.monotonic()
            if left <= 0 or not select.select([sys.stdin.fileno()], [], [], left)[0]:
                raise ValueError('invalid_request')
            part = os.read(sys.stdin.fileno(), LIMIT + 1 - len(raw))
            if not part:
                break
            raw.extend(part)
            if len(raw) > LIMIT:
                raise ValueError('invalid_request')
        value = parse_request(op, raw)
        if op == 'mode-step':
            return mode_step(value)
        if op == 'mode-preference-read':
            return read_preference(value['output_key'])
        if op == 'mode-preference-write':
            return write_preference(value['output_key'], value['choice'])
        return output_policy(value['output_key'])
    except Exception:
        raise ValueError('invalid_request') from None
