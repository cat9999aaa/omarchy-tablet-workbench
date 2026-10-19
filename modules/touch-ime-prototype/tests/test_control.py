import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('ime_entry',Path(__file__).resolve().parents[1]/'control.py')
control=importlib.util.module_from_spec(spec);spec.loader.exec_module(control)

class ControlTest(unittest.TestCase):
    def test_locked_or_unknown_never_attempts_toggle(self):
        for state in ('true', '', 'unexpected'):
            with self.subTest(state=state), patch.object(control,'output',side_effect=[state,'true','{}']), patch.object(control,'execute') as execute:
                control.main();execute.assert_not_called()
    def test_ready_native_has_only_one_action(self):
        with patch.object(control,'output',side_effect=['false','true','{}']) as output, patch.object(control,'execute',return_value=True) as execute:
            control.main()
            self.assertEqual(output.call_count,2)
            self.assertEqual([c.args[0] for c in execute.call_args_list],[['omarchy-shell','omtInput','toggle']])
    def test_not_ready_notifies_without_fallback(self):
        with patch.object(control,'output',side_effect=['false','false']), patch.object(control,'execute',return_value=True) as execute:
            control.main()
            self.assertEqual(execute.call_count,1)
            self.assertEqual(execute.call_args.args[0][0],'notify-send')

if __name__=='__main__':unittest.main()
