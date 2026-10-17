"""Route-only tests: no real desktop, recording or network changes."""
import subprocess
import unittest
from unittest.mock import patch
import edge_menu

class MenuTests(unittest.TestCase):
    @patch.object(edge_menu.subprocess, 'run')
    @patch.object(edge_menu.subprocess, 'check_output')
    def test_desktops_share_navigation(self, output, run):
        output.side_effect=['false\n','true\n'];run.return_value.returncode=0
        self.assertEqual(edge_menu.dispatch(['desktops']),0)
        run.assert_called_once_with(['omarchy-shell','pcadmin.navigation','open','桌面'],timeout=3)
    @patch.object(edge_menu.subprocess, 'run')
    @patch.object(edge_menu.subprocess, 'check_output')
    def test_missing_plugin_keeps_native_fallback(self, output, run):
        output.side_effect=['false\n',subprocess.CalledProcessError(1,['ipc'])];run.return_value.returncode=0
        self.assertEqual(edge_menu.dispatch(['desktops']),0)
        run.assert_called_once_with(['omarchy','menu','summon','desktops'],timeout=5)
    @patch.object(edge_menu.subprocess, 'run')
    @patch.object(edge_menu.subprocess, 'check_output', return_value='true\n')
    def test_lock_never_opens_menu(self, output, run):
        self.assertEqual(edge_menu.dispatch(['desktops']),0);run.assert_not_called()
    @patch.object(edge_menu.subprocess, 'run')
    @patch.object(edge_menu.subprocess, 'check_output', return_value='unknown\n')
    def test_unknown_lock_fails_closed(self, output, run):
        self.assertEqual(edge_menu.dispatch(['desktops']),0);run.assert_not_called()
if __name__=='__main__':unittest.main()
