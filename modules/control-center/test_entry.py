import unittest
import importlib.util
from pathlib import Path
from unittest.mock import patch
import subprocess

p=Path(__file__).resolve().parents[1]/'edge-gestures/edge_menu.py'
spec=importlib.util.spec_from_file_location('entry',p);entry=importlib.util.module_from_spec(spec);spec.loader.exec_module(entry)

class EntryTests(unittest.TestCase):
 def test_ready_control_center_receives_quickstatus(self):
  calls=[]
  def run(cmd,**kw):calls.append(cmd);return subprocess.CompletedProcess(cmd,0)
  with patch.object(entry.subprocess,'check_output',side_effect=['false','true']),patch.object(entry.subprocess,'run',side_effect=run):
   self.assertEqual(entry.dispatch(['quickstatus']),0)
  self.assertIn(['omarchy-shell','pcadmin.controlCenter','toggle'],calls)
 def test_missing_control_center_falls_back(self):
  calls=[]
  with patch.object(entry.subprocess,'check_output',side_effect=['false','']),patch.object(entry.subprocess,'run',side_effect=lambda cmd,**kw:(calls.append(cmd) or subprocess.CompletedProcess(cmd,0))):entry.dispatch(['quickstatus'])
  self.assertEqual(calls,[['omarchy','menu','summon','quickstatus']])
 def test_lock_unknown_blocks_all_entries(self):
  with patch.object(entry.subprocess,'check_output',return_value=''),patch.object(entry.subprocess,'run') as run:entry.dispatch(['quickstatus']);run.assert_not_called()
 def test_toggle_failure_falls_back_without_shell_restart(self):
  calls=[]
  def run(cmd,**kw):calls.append(cmd);return subprocess.CompletedProcess(cmd,1 if cmd[0]=='omarchy-shell' else 0)
  with patch.object(entry.subprocess,'check_output',side_effect=['false','true']),patch.object(entry.subprocess,'run',side_effect=run):entry.dispatch(['quickstatus'])
  self.assertEqual(calls[-1],['omarchy','menu','summon','quickstatus'])
 def test_desktop_menu_stays_unchanged(self):
  with patch.object(entry.subprocess,'check_output',return_value='false'),patch.object(entry.subprocess,'run',return_value=subprocess.CompletedProcess([],0)) as run:entry.dispatch(['desktops'])
  self.assertEqual(run.call_args.args[0],['omarchy','menu','summon','desktops'])
