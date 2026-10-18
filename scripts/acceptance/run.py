#!/usr/bin/env python3
"""Software-only acceptance. Run on a disposable CI runner or isolated build host."""
import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
import xml.etree.ElementTree as ET


@dataclass(frozen=True)
class Check:
    name: str
    directory: str
    command: list[str]
    timeout: float = 90


DESTINATIONS = ['modules/control-center/Workbench', 'modules/network-center/Workbench',
                'modules/battery-manager/panel/Workbench', 'modules/window-controls/Workbench']


def run_python_suite(directory, pattern):
    suite = unittest.TestLoader().discover(str(directory), pattern=pattern)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return {'tests': result.testsRun, 'skipped': len(result.skipped),
            'passed': result.testsRun > 0 and not result.skipped and result.wasSuccessful()}


def qml_result(xml):
    try:
        root = ET.fromstring(xml)
        cases = list(root.iter('testcase'))
        skipped = len(list(root.iter('skipped')))
        failures = len(list(root.iter('failure'))) + len(list(root.iter('error')))
        real = [c for c in cases if c.get('name') not in ('initTestCase', 'cleanupTestCase')]
        return {'tests': len(cases), 'skipped': skipped,
                'passed': bool(real) and not skipped and not failures}
    except ET.ParseError:
        return {'tests': 0, 'skipped': 0, 'passed': False}


def run_qml_suite(runner, directory):
    with tempfile.TemporaryDirectory(prefix='workbench-qml-') as tmp:
        xml = Path(tmp) / 'results.xml'
        proc = subprocess.run([runner, '-input', directory, '-o', str(xml) + ',junitxml',
                               '-o', '-,txt'])
        result = qml_result(xml.read_text()) if xml.exists() else qml_result('')
        result['passed'] = result['passed'] and proc.returncode == 0
        return result


def verify_shared_ui(root, destinations=DESTINATIONS):
    source = root / 'modules/workbench-ui'
    files = {p.name: p.read_bytes() for p in source.iterdir()
             if p.is_file() and p.suffix in ('.qml', '.js')}
    if not files:
        return ['Shared UI source is empty']
    errors = []
    for directory in destinations:
        target = root / directory
        if not target.is_dir():
            errors.append(directory + ': missing')
            continue
        actual = {p.name: p.read_bytes() for p in target.iterdir() if p.is_file()}
        if files != actual:
            errors.append(directory + ': missing, stale or changed generated files')
    return errors


def source_digest(root):
    """Identify source bytes; no machine paths, environment or runtime data in reports."""
    digest = hashlib.sha256()
    source_roots = {
        'modules': None, 'scripts/acceptance': None, 'themes': None,
        'scripts/themes': {'.py', '.js', '.cjs', '.qml'},
        'scripts/workbench-ui': {'.py', '.md'},
    }
    for directory, suffixes in source_roots.items():
        for p in sorted((root / directory).rglob('*')):
            if not p.is_file() or p.is_symlink():
                continue
            rel = p.relative_to(root)
            if any(part in ('build', 'target', '__pycache__', '.venv') for part in rel.parts):
                continue
            if suffixes is not None and p.suffix not in suffixes:
                continue
            digest.update(str(rel).encode() + b'\0' + p.read_bytes() + b'\0')
    return digest.hexdigest()


def run_checks(root, output, checks):
    output.mkdir(parents=True, exist_ok=False)
    report = {'schema': 1, 'kind': 'software-acceptance',
              'observed_at': datetime.now(timezone.utc).isoformat(),
              'source_sha256': source_digest(root), 'checks': [], 'passed': False,
              'hardware_acceptance': 'not-run'}
    env = {**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software',
           'PYTHONDONTWRITEBYTECODE': '1'}
    for check in checks:
        started = time.monotonic()
        entry = {'name': check.name, 'status': 'error', 'returncode': None}
        with (output / (check.name + '.log')).open('w') as log:
            try:
                child = subprocess.Popen(check.command, cwd=root / check.directory, env=env,
                                         stdout=log, stderr=subprocess.STDOUT,
                                         start_new_session=True)
                try:
                    entry['returncode'] = child.wait(timeout=check.timeout)
                    entry['status'] = 'passed' if entry['returncode'] == 0 else 'failed'
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait()
                    entry['status'] = 'timeout'
                    log.write('\nCHECK TIMED OUT\n')
            except OSError as error:
                log.write(type(error).__name__ + ': ' + str(error) + '\n')
        entry['seconds'] = round(time.monotonic() - started, 3)
        for line in (output / (check.name + '.log')).read_text(errors='replace').splitlines():
            if line.startswith('ACCEPTANCE_COUNTS='):
                entry['test_result'] = json.loads(line.removeprefix('ACCEPTANCE_COUNTS='))
        report['checks'].append(entry)
        print(check.name + ': ' + entry['status'], flush=True)
        if entry['status'] != 'passed':
            print((output / (check.name + '.log')).read_text(errors='replace')[-3000:])
    report['passed'] = bool(checks) and all(x['status'] == 'passed' for x in report['checks'])
    (output / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def checks_for(suite):
    checks = []
    if suite in ('all', 'models'):
        checks += [Check('shared-copies', '.', [sys.executable, __file__, '--verify-copies']),
                   Check('device-observer', 'modules/control-center/device-observer',
                         ['cargo', 'test', '--locked', '--offline'])]
        python_suites = [
            ('acceptance-runner', 'scripts/acceptance', 'test_runner.py'),
            ('theme-validation', 'scripts/themes', 'test_*.py'),
            ('theme-sync', 'scripts/workbench-ui', 'test_sync.py'),
            ('network', 'modules/network-center', 'test_*.py'),
            ('control', 'modules/control-center', 'test_*.py'),
            ('battery', 'modules/battery-manager/recorder', 'tests/test_*.py'),
            ('remote-build', 'modules/remote-build', 'test_*.py'),
            ('plugin-release', 'modules/plugin-release', 'test_*.py'),
            ('pen-metrics', 'modules/hardware-toolbox/pen-test', 'test_*.py'),
            ('touch-mode', 'modules/hardware-toolbox/touch-mode', 'test_*.py'),
            ('arcade-catalog', 'modules/offline-arcade/catalog', 'test_*.py'),
            ('ime-control', 'modules/touch-ime-prototype', 'tests/test_control.py'),
            ('navigation', 'modules/window-controls', 'test_navigation.py'),
            ('edge-menu', 'modules/edge-gestures', 'test_menu.py'),
        ]
        for name, directory, pattern in python_suites:
            p = Path(pattern)
            checks.append(Check(name, directory, [sys.executable, __file__, '--python-suite',
                                str(p.parent), p.name]))
        for name, directory, file in [
            ('control-model', 'control-center', 'test-model.cjs'),
            ('contract-model', 'control-center', 'test-contract-model.cjs'),
            ('output-route', 'control-center', 'test-output-route.cjs'),
            ('mode-protocol', 'control-center', 'test-mode-protocol.cjs'),
            ('control-actions', 'control-center', 'test-control-actions.cjs'),
            ('battery-history', 'battery-manager/panel', 'test_history.js'),
            ('battery-icon', 'battery-manager/panel', 'test_icon.js'),
            ('shared-model', 'workbench-ui', 'test-model.cjs'),
            ('theme-tokens', 'workbench-ui', 'test-theme.cjs'),
            ('edge-gesture', 'edge-gestures', 'test-gesture.cjs'),
        ]:
            checks.append(Check(name, 'modules/' + directory, ['node', file]))
        checks.append(Check('theme-contrast', 'scripts/themes', ['node', 'test-contrast.cjs']))
    if suite in ('all', 'qml'):
        runner = shutil.which('qmltestrunner') or next(
            (p for p in ('/usr/lib/qt6/bin/qmltestrunner', '/usr/lib/qt6/qmltestrunner')
             if Path(p).is_file()), 'qmltestrunner')
        checks.append(Check('control-layout', 'modules/control-center',
                            [sys.executable, 'check_panel_layout.py']))
        checks.append(Check('contract-qml', 'modules/control-center',
                            [sys.executable, __file__, '--qml-suite', runner, 'tests']))
        checks.append(Check('shared-qml', 'modules/workbench-ui',
                            [sys.executable, __file__, '--qml-suite', runner, 'tests']))
        checks.append(Check('navigation-layout', 'modules/window-controls',
                            [sys.executable, 'test_navigation_layout.py']))
        checks.append(Check('ime-layout', 'modules/touch-ime-prototype',
                            [sys.executable, 'tests/test_layout.py']))
        checks.append(Check('theme-surfaces', '.',
                            [sys.executable, 'scripts/themes/check_status_surfaces.py']))
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite', choices=('models', 'qml', 'all'), default='all')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--verify-copies', action='store_true')
    parser.add_argument('--python-suite', nargs=2, help=argparse.SUPPRESS)
    parser.add_argument('--qml-suite', nargs=2, help=argparse.SUPPRESS)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.python_suite or args.qml_suite:
        result = (run_python_suite(*args.python_suite) if args.python_suite
                  else run_qml_suite(*args.qml_suite))
        print('ACCEPTANCE_COUNTS=' + json.dumps(result))
        return int(not result['passed'])
    if args.verify_copies:
        errors = verify_shared_ui(root)
        print('\n'.join(errors) if errors else 'Shared UI copies match')
        return int(bool(errors))
    if args.output is None:
        parser.error('--output must name a new report directory')
    return int(not run_checks(root, args.output.resolve(), checks_for(args.suite))['passed'])


if __name__ == '__main__':
    raise SystemExit(main())
