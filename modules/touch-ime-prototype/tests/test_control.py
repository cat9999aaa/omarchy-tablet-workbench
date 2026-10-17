import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

path=Path(__file__).resolve().parents[1]/'control.py'
spec=importlib.util.spec_from_file_location('control',path)
control=importlib.util.module_from_spec(spec);spec.loader.exec_module(control)

class ControlTest(unittest.TestCase):
    def test_locked_session_never_opens_desktop_keyboard(self):
        with patch.object(control,'output',return_value='true'), patch.object(control,'execute') as execute:
            control.main();execute.assert_not_called()
    def test_native_hides_old_panel_first(self):
        with patch.object(control,'output',side_effect=['false','true']), patch.object(control,'old_visible',return_value=True), patch.object(control,'execute',return_value=True) as execute:
            control.main()
            self.assertEqual(execute.call_args_list[0].args[0][-1],'hide')
            self.assertEqual(execute.call_args_list[1].args[0],['omarchy-shell','omtInput','toggle'])
    def test_native_failure_never_launches_old_keyboard(self):
        with patch.object(control,'output',side_effect=['false','false']),patch.object(control,'execute',return_value=True) as execute:
            control.main();self.assertFalse(any(call.args[0][0]==control.OLD and call.args[0][-1]=='toggle' for call in execute.call_args_list))

if __name__=='__main__':unittest.main()
