"""Pinned code must be loaded from its package, never cwd/PYTHONPATH."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid

ROOT = Path(__file__).resolve().parent
REVISION = '969cd18647f59bc3072a877a87ce1c4f054351f0'
LICENSE_SHA256 = '8b1ba204bb69a0ade2bfcf65ef294a920f6bb361b317dba43c7ef29d96332b9b'


class LoaderTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT / 'contracts_loader.py').is_file(), 'fixed-source loader is not implemented')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.host = self.root / 'host'
        self.host.mkdir()
        shutil.copy2(ROOT / 'contracts_loader.py', self.host / 'contracts_loader.py')
        shutil.copytree(ROOT / 'vendor', self.host / 'vendor')
        self.vendor = self.host / 'vendor/dashen-contracts-0.1.0'
        spec = importlib.util.spec_from_file_location('loader_test_' + uuid.uuid4().hex, self.host / 'contracts_loader.py')
        self.loader = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.loader)

    def assert_rejected(self):
        with self.assertRaises(self.loader.ContractsUnavailable) as error:
            self.loader.load_contracts()
        self.assertIn(str(error.exception), ('dependency_missing', 'dependency_mismatch', 'dependency_invalid'))
        self.assertNotIn(str(self.root), str(error.exception))

    def test_fixed_source_ignores_cwd_and_pythonpath(self):
        fake = self.root / 'fake'
        package = fake / 'dashen_contracts'
        package.mkdir(parents=True)
        marker = self.root / 'wrong-source-imported'
        (package / '__init__.py').write_text('from pathlib import Path\nPath(' + repr(str(marker)) + ').touch()\n')
        script = '''import importlib.util,json
from pathlib import Path
spec=importlib.util.spec_from_file_location('fixed_loader', PATH)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
a=m.load_contracts()
f=lambda actual:{'available':True,'actual':actual,'health':'observed','observed_at':100,'stale_after':15,'source':'synthetic'}
r=a.adapt_control_snapshot({'temperature':f(0),'touch':dict(f(0),boot_default=1)}, {'device_id':'d','session_id':'s','output_id':'local','owner_generation':'g','sequence':0}, {'temperature':0,'touch':0})
print(json.dumps({'values':[x['state']['actual'] for x in r],'health':[x['state']['health'] for x in r],'origin':str(Path(a.__file__).resolve())}))
'''.replace('PATH', repr(str(self.host / 'contracts_loader.py')))
        env = {**os.environ, 'PYTHONPATH': str(fake), 'PYTHONDONTWRITEBYTECODE': '1'}
        result = subprocess.run([sys.executable, '-c', script], cwd=fake, env=env, capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data['values'], [0, 0])
        self.assertEqual(data['health'], ['observed', 'observed'])
        self.assertTrue(Path(data['origin']).is_relative_to(self.vendor))
        self.assertFalse(marker.exists())

    def test_missing_changed_or_symlinked_dependency(self):
        names = ['LICENSE', 'source.json'] + ['dashen_contracts/' + name for name in ('__init__.py', '__main__.py', 'adapters.py', 'errors.py', 'manifest.py', 'state.py', 'versions.py')]
        for name in names:
            path = self.vendor / name
            original = path.read_bytes()
            for kind in ('missing', 'changed', 'symlink'):
                with self.subTest(file=name, kind=kind):
                    path.unlink()
                    if kind == 'changed':
                        path.write_bytes(original + b'\n# unexpected change\n')
                    elif kind == 'symlink':
                        outside = self.root / 'outside'
                        outside.write_bytes(original)
                        path.symlink_to(outside)
                    self.assert_rejected()
                    if path.is_symlink() or path.exists():
                        path.unlink()
                    path.write_bytes(original)

    def test_wrong_revision_or_file_set_rejected(self):
        path = self.vendor / 'source.json'
        original = json.loads(path.read_text())
        for change in ('revision', 'files'):
            data = json.loads(json.dumps(original))
            if change == 'revision':
                data['revision'] = '0' * 40
            else:
                data['sha256'].pop('dashen_contracts/adapters.py')
            path.write_text(json.dumps(data))
            self.assert_rejected()
        path.write_text(json.dumps(original))
        (self.vendor / 'dashen_contracts/extra.py').write_text('raise RuntimeError("unexpected code")')
        self.assert_rejected()

    def test_symlinked_package_directory_rejected(self):
        package = self.vendor / 'dashen_contracts'
        outside = self.root / 'outside-package'
        package.rename(outside)
        package.symlink_to(outside, target_is_directory=True)
        self.assert_rejected()

    def test_packaged_license_and_origin(self):
        data = json.loads((self.vendor / 'source.json').read_text())
        self.assertEqual(data['revision'], REVISION)
        self.assertEqual(hashlib.sha256((self.vendor / 'LICENSE').read_bytes()).hexdigest(), LICENSE_SHA256)
        adapter = self.loader.load_contracts()
        self.assertTrue(callable(adapter.adapt_control_snapshot))

    def test_import_failure_cleans_private_namespace(self):
        from unittest.mock import patch
        before = set(sys.modules)
        real = importlib.util.module_from_spec
        calls = 0
        def fail_partway(spec):
            nonlocal calls
            calls += 1
            if calls == 3:
                raise RuntimeError('private path must not escape')
            return real(spec)
        with patch('importlib.util.module_from_spec', side_effect=fail_partway):
            self.assert_rejected()
        self.assertEqual(set(sys.modules) - before, set())


if __name__ == '__main__':
    unittest.main()
