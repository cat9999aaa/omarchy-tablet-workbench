import json
import subprocess
import unittest
from unittest.mock import patch
import control_center as c

class PrepareOpenTests(unittest.TestCase):
    def test_single_native_hide_before_layer_verification(self):
        with patch.object(c,'read_lock',return_value=False), patch.object(c.subprocess,'run',return_value=subprocess.CompletedProcess([],0)) as run, patch.object(c.subprocess,'check_output',return_value='{}'):
            self.assertTrue(c.prepare_open())
            self.assertEqual([x.args[0] for x in run.call_args_list],[['omarchy-shell','omtInput','hide']])
    def test_hide_failure_does_not_open(self):
        with patch.object(c,'read_lock',return_value=False), patch.object(c.subprocess,'run',return_value=subprocess.CompletedProcess([],1)), patch.object(c.subprocess,'check_output',return_value='{}'):
            self.assertFalse(c.prepare_open())
    def test_unknown_lock_never_hides(self):
        with patch.object(c,'read_lock',return_value=None), patch.object(c.subprocess,'run') as run:
            self.assertFalse(c.prepare_open());run.assert_not_called()
    def test_lock_changed_during_hide_blocks_open(self):
        with patch.object(c,'read_lock',side_effect=[False,True]), patch.object(c.subprocess,'run',return_value=subprocess.CompletedProcess([],0)), patch.object(c.subprocess,'check_output',return_value='{}'):
            self.assertFalse(c.prepare_open())
    def test_mapped_keyboard_still_blocks(self):
        layers=json.dumps({'screen':{'levels':{'2':[{'namespace':'pcadmin-touch-ime'}]}}})
        with patch.object(c,'read_lock',return_value=False), patch.object(c.subprocess,'run',return_value=subprocess.CompletedProcess([],0)), patch.object(c.subprocess,'check_output',return_value=layers), patch.object(c.time,'sleep'):
            self.assertFalse(c.prepare_open())
