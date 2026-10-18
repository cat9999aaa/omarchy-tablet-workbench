"""Local read-only contract host. No device writes or authority from payloads."""
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import re
import selectors
import signal
import stat
import subprocess
import time
import uuid

from contracts_loader import ContractsUnavailable, load_contracts

MAX_BYTES = 65536


def finite_nonnegative(value):
    if type(value) not in (int, float) or value < 0:
        return None
    try:
        return value if math.isfinite(value) else None
    except OverflowError:
        return None


def boottime_ms():
    try:
        return finite_nonnegative(time.clock_gettime(time.CLOCK_BOOTTIME) * 1000)
    except (OSError, AttributeError, OverflowError):
        return None


def boot_marker():
    try:
        boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        if re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', boot):
            return hashlib.sha256(('pcadmin-touch-boot-v1:' + boot).encode('ascii')).hexdigest()
    except (OSError, ValueError):
        pass
    return None


def _pairs(pairs):
    data = {}
    for key, value in pairs:
        if key in data:
            raise ValueError('duplicate')
        data[key] = value
    return data


def _bad_constant(value):
    raise ValueError('nonfinite')


def trusted_metadata(info, parents):
    return (stat.S_ISREG(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022
            and bool(parents) and all(stat.S_ISDIR(p.st_mode) and p.st_uid == 0
                                      and not p.st_mode & 0o022 for p in parents))


def read_touch_cache(path):
    """Bounded regular-file read; trust never comes from JSON self-claims."""
    path = Path(path).absolute()
    fd = None
    try:
        parents = [p.lstat() for p in path.parents]
        if any(not stat.S_ISDIR(p.st_mode) for p in parents):
            return {}, False
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_BYTES:
            return {}, False
        raw = os.read(fd, MAX_BYTES + 1)
        after = os.fstat(fd)
        if len(raw) > MAX_BYTES:
            return {}, False
        data = json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs, parse_constant=_bad_constant)
        if type(data) is not dict:
            return {}, False
        stable = all(getattr(before, key) == getattr(after, key)
                     for key in ('st_ino', 'st_dev', 'st_size', 'st_mtime_ns', 'st_ctime_ns'))
        return data, stable and trusted_metadata(after, parents)
    except (OSError, ValueError, UnicodeError, RecursionError):
        return {}, False
    finally:
        if fd is not None:
            os.close(fd)


@dataclass
class Sample:
    legacy: dict
    temperature_started_ms: float | None
    touch_observation: dict | None
    touch_cache_trusted: bool


def _age(now, start):
    now, start = finite_nonnegative(now), finite_nonnegative(start)
    if now is None or start is None or start > now:
        return None
    return finite_nonnegative(now - start)


def failure(code, legacy=None):
    return {'schema_version': 1, 'legacy': legacy if legacy is not None else {'locked': None},
            'contracts': {'version': '0.1.0', 'status': 'unavailable', 'reason_code': code, 'states': []}}


def _bounded(result):
    try:
        if len(json.dumps(result, ensure_ascii=False, allow_nan=False).encode('utf-8')) > MAX_BYTES:
            return failure('output_too_large')
        return result
    except (ValueError, TypeError, UnicodeError, RecursionError):
        return failure('invalid_snapshot')


def response(sample):
    try:
        adapter = load_contracts()
        now = boottime_ms()
        touch_age = None
        obs = sample.touch_observation
        if (sample.touch_cache_trusted is True and type(obs) is dict
                and set(obs) == {'schema', 'boot_marker', 'started_boottime_ms'}
                and type(obs['schema']) is int and obs['schema'] == 1
                and type(obs['boot_marker']) is str
                and re.fullmatch(r'[0-9a-f]{64}', obs['boot_marker'])
                and obs['boot_marker'] == boot_marker()):
            touch_age = _age(now, obs['started_boottime_ms'])
        context = {'device_id': 'local-device', 'session_id': uuid.uuid4().hex,
                   'output_id': 'local', 'owner_generation': uuid.uuid4().hex, 'sequence': 0}
        states = adapter.adapt_control_snapshot(
            {key: sample.legacy.get(key) for key in ('temperature', 'touch')}, context,
            {'temperature': _age(now, sample.temperature_started_ms), 'touch': touch_age})
        result = {'schema_version': 1, 'legacy': sample.legacy,
                  'contracts': {'version': '0.1.0', 'status': 'ok', 'reason_code': None, 'states': states}}
    except ContractsUnavailable as error:
        code = str(error) if str(error) in ('dependency_missing', 'dependency_mismatch', 'dependency_invalid') else 'dependency_invalid'
        result = failure(code, sample.legacy)
    except Exception:
        result = failure('invalid_snapshot', sample.legacy)
    return _bounded(result)


class ReadFailure(RuntimeError):
    pass


class ReadDeadline(ReadFailure):
    pass


class ReadBudget:
    def __init__(self, limit_ms=20000, clock_ms=boottime_ms):
        self.limit_ms = limit_ms
        self.clock_ms = clock_ms
        self.started = finite_nonnegative(clock_ms())
        self.process = None
        self.cancelled = False
        self._old_signal = None

    def remaining_s(self):
        age = _age(self.clock_ms(), self.started)
        if self.cancelled or age is None or age >= self.limit_ms:
            raise ReadDeadline('read_timeout')
        return (self.limit_ms - age) / 1000

    def cancel(self):
        self.cancelled = True
        process = self.process
        if process is not None:
            # Only the private group created by this read is addressed. Existing
            # systemd services/controllers are never members of that group.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                pass
            if process.stdout is not None:
                process.stdout.close()
            self.process = None

    def __enter__(self):
        self._old_signal = signal.getsignal(signal.SIGTERM)
        def stop(signum, frame):
            self.cancel()
            raise ReadDeadline('read_cancelled')
        signal.signal(signal.SIGTERM, stop)
        return self

    def __exit__(self, *args):
        self.cancel()
        signal.signal(signal.SIGTERM, self._old_signal)

    def run_read(self, argv, timeout_s):
        self.remaining_s()
        command_start = finite_nonnegative(self.clock_ms())
        process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                   start_new_session=True)
        self.process = process
        output = bytearray()
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                eof = False
                while not eof or process.poll() is None:
                    remaining = self.remaining_s()
                    age = _age(self.clock_ms(), command_start)
                    if age is None or age >= timeout_s * 1000:
                        raise subprocess.TimeoutExpired(argv, timeout_s)
                    for key, events in selector.select(min(.1, remaining, timeout_s - age / 1000)):
                        chunk = os.read(key.fd, MAX_BYTES + 1 - len(output))
                        if not chunk:
                            selector.unregister(key.fileobj)
                            eof = True
                        else:
                            output.extend(chunk)
                            if len(output) > MAX_BYTES:
                                raise ReadFailure('read_output_too_large')
            self.remaining_s()
            if process.returncode:
                raise subprocess.CalledProcessError(process.returncode, argv)
            return output.decode('utf-8')
        finally:
            # Reap owned descendants too, if a command exited before them.
            was_cancelled = self.cancelled
            self.cancel()
            self.cancelled = was_cancelled
