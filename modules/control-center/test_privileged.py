import unittest
from privileged_control import dispatch_guarded

class PrivilegeTests(unittest.TestCase):
 def test_lock_after_auth_denies_mutation(self):
  calls=[]
  with self.assertRaises(PermissionError):dispatch_guarded('tun-stop',1000,lambda uid:False,lambda cmd:calls.append(cmd),request_valid=lambda:True)
  self.assertEqual(calls,[])
 def test_request_is_bound_to_live_process_action_and_lifetime(self):
  import os,json,time,uuid
  from pathlib import Path
  from privileged_control import request_active,process_start
  uid=os.getuid();token=str(uuid.uuid4());p=Path(f'/run/user/{uid}/pcadmin-control-center/request-{token}.json');p.parent.mkdir(mode=0o700,exist_ok=True)
  try:
   p.write_text(json.dumps({'active':True,'privileged_actions':['tun-stop'],'expires_at':time.time()+60,'pid':os.getpid(),'process_start':process_start(os.getpid())}));p.chmod(0o600)
   self.assertTrue(request_active(uid,token,'tun-stop'));self.assertFalse(request_active(uid,token,'tun-start'))
   p.unlink();self.assertFalse(request_active(uid,token,'tun-stop'))
  finally:p.unlink(missing_ok=True)
 def test_unknown_action_cannot_become_root_command(self):
  with self.assertRaises(ValueError):dispatch_guarded('sh -c reboot',1000,lambda uid:True,lambda cmd:0)
 def test_root_caller_not_accepted(self):
  with self.assertRaises(PermissionError):dispatch_guarded('tun-stop',0,lambda uid:True,lambda cmd:0)
 def test_cancelled_request_stays_denied_after_unlock(self):
  calls=[]
  with self.assertRaises(PermissionError):dispatch_guarded('tun-stop',1000,lambda uid:True,lambda cmd:calls.append(cmd),request_valid=lambda:False)
  self.assertEqual(calls,[])
