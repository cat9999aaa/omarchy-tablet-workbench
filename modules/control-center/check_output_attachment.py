#!/usr/bin/env python3
"""Real Quickshell output attachment gate. Requires isolated sway + headless/pixman.

Run only inside a fresh mount/PID/network namespace, with no host runtime,
Wayland socket, bus, input or DRM nodes mounted. Remote harness supplies signed
sway/wlroots packages in a read-only /usr overlay. Never reuses SWAYSOCK.
"""
# SPDX-License-Identifier: GPL-3.0-only
import os
from pathlib import Path
import selectors
import shutil
import subprocess
import tempfile
import time


def main(fixture_path=None, extra_files=(), extra_required=(), verify_children=False):
    if os.environ.get('B2_ISOLATED_TEST') != '1':
        raise RuntimeError('isolated test namespace required')
    for tool in ('sway', 'swaymsg', 'qs'):
        if not shutil.which(tool):
            raise RuntimeError('missing test dependency: ' + tool)
    with tempfile.TemporaryDirectory(prefix='b2-output-') as folder:
        root = Path(folder)
        runtime = root / 'runtime'
        runtime.mkdir(mode=0o700)
        fixture = root / 'OutputAttachment.qml'
        shutil.copy2(fixture_path or Path(__file__).parent / 'tests/OutputAttachment.qml', fixture)
        for source in extra_files:
            shutil.copy2(source, root / Path(source).name)
        shutil.copy2(Path(__file__).parent / 'OutputRoute.js', root / 'OutputRoute.js')
        config = root / 'sway.conf'
        config.write_text('output HEADLESS-1 resolution 640x480 position 0 0\n'
                          'output HEADLESS-2 resolution 640x480 position 640 0\n')
        env = {**os.environ, 'XDG_RUNTIME_DIR': str(runtime),
               'WLR_BACKENDS': 'headless', 'WLR_HEADLESS_OUTPUTS': '2',
               'WLR_RENDERER': 'pixman', 'QT_QPA_PLATFORM': 'wayland',
               'QT_QUICK_BACKEND': 'software'}
        for key in ('SWAYSOCK', 'WAYLAND_DISPLAY', 'DISPLAY', 'DBUS_SESSION_BUS_ADDRESS'):
            env.pop(key, None)
        compositor = None
        shell = None
        with (root / 'sway.log').open('w+') as log:
            try:
                compositor = subprocess.Popen(['sway', '-c', str(config)], env=env,
                                              stdout=log, stderr=subprocess.STDOUT)
                end = time.monotonic() + 10
                while time.monotonic() < end:
                    sockets = list(runtime.glob('sway-ipc.*.sock'))
                    displays = [p for p in runtime.glob('wayland-*') if not p.name.endswith('.lock')]
                    if sockets and displays:
                        break
                    if compositor.poll() is not None:
                        raise RuntimeError('compositor exited')
                    time.sleep(.05)
                else:
                    raise RuntimeError('compositor startup timeout')
                env.update(SWAYSOCK=str(sockets[0]), WAYLAND_DISPLAY=displays[0].name)
                print(subprocess.check_output(['sway', '--version'], env=env, text=True).strip())
                print(subprocess.check_output(['qs', '--version'], env=env, text=True).strip())
                shell = subprocess.Popen(['qs', '-p', str(fixture)],
                                         env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                selector = selectors.DefaultSelector()
                selector.register(shell.stdout, selectors.EVENT_READ)
                end = time.monotonic() + 20
                data = b''
                removed = False
                while time.monotonic() < end:
                    for key, _ in selector.select(.1):
                        chunk = os.read(key.fd, 4096)
                        if chunk:
                            data += chunk
                            if len(data) > 65536:
                                print(data[:2000].decode(errors='replace') + '\n...\n' + data[-2000:].decode(errors='replace'))
                                raise RuntimeError('oversize test output')
                    if b'B2_FAIL:' in data:
                        break
                    if b'B2_READY_REMOVE' in data and not removed:
                        subprocess.run(['swaymsg','output','HEADLESS-2','disable'], env=env,
                                       check=True, timeout=3, stdout=subprocess.PIPE)
                        removed = True
                    if shell.poll() is not None:
                        break
                text = data.decode(errors='replace')
                print(text)
                required = ['attachment', 'two-outputs', 'destroy', 'ambiguous', 'no-migration'] + list(extra_required)
                if shell.poll() != 0 or 'B2_COMPLETE' not in text or 'B2_FAIL:' in text or not all('B2_PASS:'+s in text for s in required):
                    raise RuntimeError('output attachment gate failed')
                if verify_children:
                    active=set();pids=set()
                    for row in (root/'events').read_text().splitlines():
                        event,pid=row.split();pids.add(int(pid))
                        if event=='start':active.add(pid)
                        else:active.discard(pid)
                        if len(active)>1:raise RuntimeError('observer lifetime overlap')
                    for pid in pids:
                        try:os.kill(pid,0)
                        except ProcessLookupError:continue
                        raise RuntimeError('observer remains after output teardown')
                print('real output attachment gate passed')
            finally:
                for child in (shell, compositor):
                    if child is not None and child.poll() is None:
                        child.terminate()
                        try:
                            child.wait(timeout=3)
                        except subprocess.TimeoutExpired:
                            child.kill()
                            child.wait()
                log.seek(0)
                if compositor is not None and compositor.returncode not in (0, -15):
                    print(log.read()[-5000:])


if __name__ == '__main__':
    main()
