#!/usr/bin/python3
"""Dell 7220 eGalax P80H84: apply verified TouchMode command, no firmware writes."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import select
import time


def find_device():
    for p in Path('/sys/class/hidraw').glob('hidraw*'):
        device = (p / 'device').resolve()
        if '0EEF:C003' not in device.name.upper():
            continue
        if 'eGalaxTouch P80H84 0710 vA1_N k47_45' not in (device / 'uevent').read_text():
            continue
        return '/dev/' + p.name
    return None


def query(fd, selector, value=0):
    end = time.monotonic() + 3
    while select.select([fd], [], [], 0)[0]:
        os.read(fd, 4096)
        if time.monotonic() >= end:
            raise TimeoutError('Input queue did not drain')
    os.write(fd, bytes([3, 4, 0x3f, 0x65, selector, value]) + bytes(58))
    end = time.monotonic() + 3
    while time.monotonic() < end:
        if not select.select([fd], [], [], max(0, end - time.monotonic()))[0]:
            break
        data = os.read(fd, 4096)
        if len(data) >= 6 and data[:5] == bytes([3, 4, 0x3f, 0x65, selector]):
            return data[5]
    raise TimeoutError('No matching TouchMode response')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['status', 'glove', 'normal'])
    args = parser.parse_args()
    with open('/run/lock/pcadmin-touch-mode.lock', 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        device = None
        for _ in range(20):
            device = find_device()
            if device:
                break
            time.sleep(.5)
        if not device:
            raise RuntimeError('Exact verified Dell touchscreen not found; no writes')
        fd = os.open(device, os.O_RDWR | os.O_NONBLOCK)
        try:
            before = query(fd, 0)
            if before not in (0, 1, 2):
                raise RuntimeError('Unknown current mode; no writes')
            desired = {'normal': 0, 'glove': 1}.get(args.mode, before)
            if desired != before:
                try:
                    query(fd, 1, desired)
                    if query(fd, 0) != desired:
                        raise RuntimeError('Mode readback mismatch')
                except BaseException:
                    query(fd, 1, before)
                    raise
            actual = query(fd, 0)
            if actual != desired:
                raise RuntimeError('Final mode readback mismatch')
            print(json.dumps({'device': device, 'before': before, 'actual': actual,
                              'mode': args.mode, 'verified': True}), flush=True)
        finally:
            os.close(fd)


if __name__ == '__main__':
    main()
