"""Bounded on-demand sysfs/udev evidence; never opens input event streams."""
import errno
import math
import os
from pathlib import Path
import re
import stat
import struct

from contract_host import ReadBudget, ReadDeadline, ReadFailure, boottime_ms
from device_classifier import DeviceFacts, aggregate, classify, parse_bitmap

LIMIT = 16384


class EvidenceError(Exception):
    pass


def _inventory(root, budget):
    budget.remaining_s()
    found = {}
    with os.scandir(root / 'class/input') as entries:
        for entry in entries:
            budget.remaining_s()
            if not re.fullmatch(r'event[0-9]+', entry.name):
                continue
            if len(found) >= 128:
                raise EvidenceError('limit_exceeded')
            target = Path(entry.path).resolve(strict=True)
            if not target.is_relative_to(root / 'devices'):
                raise EvidenceError('invalid_data')
            info = target.stat()
            found[entry.name] = (target, info.st_dev, info.st_ino)
    return found


def _read(path, root, budget):
    budget.remaining_s()
    # Legitimate sysfs class/device links are resolved by the caller. Reject
    # final-file links and escapes in intermediate components before opening.
    if not path.parent.resolve(strict=True).is_relative_to(root / 'devices'):
        raise EvidenceError('invalid_data')
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise EvidenceError('invalid_data')
        data = bytearray()
        while True:
            budget.remaining_s()
            chunk = os.read(fd, LIMIT + 1 - len(data))
            if not chunk:
                break
            data.extend(chunk)
            if len(data) > LIMIT:
                raise EvidenceError('limit_exceeded')
        budget.remaining_s()
        return data.decode('ascii', errors='strict')
    finally:
        os.close(fd)


def _parents(device, root, budget):
    kinds = set()
    parent = device
    for _ in range(64):
        budget.remaining_s()
        if parent == root / 'devices':
            return kinds
        if not parent.is_relative_to(root / 'devices'):
            raise EvidenceError('invalid_data')
        link = parent / 'subsystem'
        if link.is_symlink():
            resolved = link.resolve(strict=True)
            for kind in ('usb', 'bluetooth'):
                if resolved == root / 'bus' / kind:
                    kinds.add(kind)
        parent = parent.parent
    raise EvidenceError('limit_exceeded')


def _properties(text):
    if not isinstance(text, str):
        raise EvidenceError('invalid_data')
    if len(text.encode('utf-8', errors='strict')) > LIMIT:
        raise EvidenceError('limit_exceeded')
    result = {}
    for line in text.splitlines():
        key, separator, value = line.partition('=')
        if key not in ('ID_INPUT_KEYBOARD', 'ID_BUS'):
            continue
        if not separator or (key in result and result[key] != value):
            raise EvidenceError('invalid_data')
        result[key] = value
    return result


def collect_device_evidence(*, sysfs_root=Path('/sys'), runner=None, clock_ms=boottime_ms):
    items = []
    start = None
    try:
        root = Path(sysfs_root).resolve(strict=True)
        with ReadBudget(limit_ms=5000, clock_ms=clock_ms, max_bytes=LIMIT) as budget:
            start = budget.started
            inventory = _inventory(root, budget)
            for name, (event, _, _) in sorted(inventory.items()):
                budget.remaining_s()
                device = (event / 'device').resolve(strict=True)
                if not device.is_relative_to(root / 'devices'):
                    raise EvidenceError('invalid_data')
                identity = device.stat()
                word_bits = struct.calcsize('L') * 8
                bitmaps = [parse_bitmap(_read(device / 'capabilities' / field, root, budget), word_bits)
                           for field in ('key', 'abs', 'sw')]
                bus_text = _read(device / 'id/bustype', root, budget).strip()
                if not re.fullmatch(r'[0-9a-fA-F]{1,4}', bus_text):
                    raise EvidenceError('invalid_data')
                kinds = _parents(device, root, budget)
                command = ['/usr/bin/udevadm', 'info', '--query=property', '--path=' + str(event)]
                text = (runner or budget.run_read)(command, budget.remaining_s())
                budget.remaining_s()
                properties = _properties(text)
                after = device.stat()
                if ((event / 'device').resolve(strict=True) != device or
                        (after.st_dev, after.st_ino) != (identity.st_dev, identity.st_ino)):
                    raise EvidenceError('device_changed')
                items.append(classify(DeviceFacts(*bitmaps,
                    device.is_relative_to(root / 'devices/virtual'), 'usb' in kinds,
                    'bluetooth' in kinds, int(bus_text, 16), properties)))
            if _inventory(root, budget) != inventory:
                raise EvidenceError('device_changed')
            budget.remaining_s()
            elapsed = clock_ms() - start
            return aggregate(items, True, 'observed', elapsed)
    except ReadDeadline as exc:
        reason = 'read_cancelled' if str(exc) == 'read_cancelled' else 'read_timeout'
    except EvidenceError as exc:
        reason = str(exc)
    except PermissionError:
        reason = 'read_denied'
    except FileNotFoundError:
        reason = 'device_changed' if start is not None else 'enumeration_failed'
    except (ValueError, UnicodeError):
        reason = 'invalid_data'
    except ReadFailure:
        reason = 'limit_exceeded'
    except OSError as exc:
        reason = 'invalid_data' if exc.errno in (errno.ELOOP, errno.ENOTDIR) else 'read_failed'
    except Exception:
        reason = 'read_failed'
    try:
        duration = clock_ms() - start if start is not None else 0
        if not math.isfinite(duration) or duration < 0:
            duration = 0
    except Exception:
        duration = 0
    return aggregate(items, False, reason, duration)
