import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name('proxy-build.py')

class BuildBoundaryTests(unittest.TestCase):
    def run_builder(self, root, job='test-job', phase='test'):
        return subprocess.run([sys.executable, str(SCRIPT), str(root), job, phase], capture_output=True, text=True)

    def test_missing_scope_marker_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            r = self.run_builder(d)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn('scope', r.stdout)

    def test_parent_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, 'build-scope.json').write_text('{}')
            r = self.run_builder(d, '../other')
            self.assertNotEqual(r.returncode, 0)
            self.assertIn('job', r.stdout)

    def test_symlink_root_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            real = Path(d, 'real'); real.mkdir(); (real/'build-scope.json').write_text('{}')
            link = Path(d, 'link'); link.symlink_to(real, target_is_directory=True)
            r = self.run_builder(link)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn('scope', r.stdout)

    def test_arbitrary_command_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, 'build-scope.json').write_text('{}')
            r = self.run_builder(d, phase='sh')
            self.assertNotEqual(r.returncode, 0)
            self.assertIn('phase', r.stdout)

if __name__ == '__main__': unittest.main()
