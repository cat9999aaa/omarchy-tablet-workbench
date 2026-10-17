import unittest
from privileged_control import dispatch_guarded

class PrivilegeTests(unittest.TestCase):
 def test_lock_after_auth_denies_mutation(self):
  calls=[]
  with self.assertRaises(PermissionError):dispatch_guarded('tun-stop',1000,lambda uid:False,lambda cmd:calls.append(cmd))
  self.assertEqual(calls,[])
 def test_unknown_action_cannot_become_root_command(self):
  with self.assertRaises(ValueError):dispatch_guarded('sh -c reboot',1000,lambda uid:True,lambda cmd:0)
 def test_root_caller_not_accepted(self):
  with self.assertRaises(PermissionError):dispatch_guarded('tun-stop',0,lambda uid:True,lambda cmd:0)
