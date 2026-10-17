import json
import sys
import tempfile
import unittest
from pathlib import Path

from run import Check, run_checks, verify_shared_ui, run_python_suite, qml_result


class RunnerTests(unittest.TestCase):
    def test_skipped_or_empty_python_suite_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / 'test_partial.py').write_text('import unittest\nclass T(unittest.TestCase):\n'
                ' @unittest.skip("missing dependency")\n def test_skip(self): pass\n'
                ' def test_pass(self): pass\n')
            result = run_python_suite(p, 'test_partial.py')
            self.assertEqual(result['tests'], 2)
            self.assertEqual(result['skipped'], 1)
            self.assertFalse(result['passed'])
            self.assertFalse(run_python_suite(p, 'test_absent.py')['passed'])

    def test_qml_requires_real_tests_without_skips_or_failures(self):
        for xml in ['<testsuite tests="0"/>', '<testsuite><testcase><skipped/></testcase></testsuite>',
                    '<testsuite><testcase><failure/></testcase></testsuite>', 'broken']:
            self.assertFalse(qml_result(xml)['passed'])
        self.assertTrue(qml_result('<testsuite><testcase name="click"/></testsuite>')['passed'])

    def test_failure_missing_tool_and_timeout_cannot_mask_later_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            checks = [
                Check('failed', '.', [sys.executable, '-c', 'raise SystemExit(7)']),
                Check('missing', '.', ['/nonexistent-workbench-test-tool']),
                Check('timeout', '.', [sys.executable, '-c', 'import time;time.sleep(10)'], .05),
                Check('passed', '.', [sys.executable, '-c', 'print("done")']),
            ]
            report = run_checks(root, root / 'report', checks)
            self.assertFalse(report['passed'])
            self.assertEqual([x['status'] for x in report['checks']],
                             ['failed', 'error', 'timeout', 'passed'])
            self.assertEqual(report['checks'][0]['returncode'], 7)
            self.assertEqual(json.loads((root / 'report/summary.json').read_text()), report)
            self.assertIn('done', (root / 'report/passed.log').read_text())

    def test_old_report_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / 'report').mkdir()
            with self.assertRaises(FileExistsError):
                run_checks(p, p / 'report', [Check('noop', '.', [sys.executable, '-c', 'pass'])])

    def test_empty_suite_is_not_a_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            self.assertFalse(run_checks(p, p / 'report', [])['passed'])

    def test_shared_copy_missing_and_drift_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            src = p / 'modules/workbench-ui'
            src.mkdir(parents=True)
            (src / 'Button.qml').write_text('one')
            destinations = ['modules/control-center/Workbench']
            self.assertTrue(verify_shared_ui(p, destinations))
            dst = p / destinations[0]
            dst.mkdir(parents=True)
            (dst / 'Button.qml').write_text('two')
            self.assertTrue(verify_shared_ui(p, destinations))
            (dst / 'Button.qml').write_text('one')
            self.assertEqual(verify_shared_ui(p, destinations), [])
            (dst / 'Stale.qml').write_text('stale')
            self.assertTrue(verify_shared_ui(p, destinations))


if __name__ == '__main__':
    unittest.main()
