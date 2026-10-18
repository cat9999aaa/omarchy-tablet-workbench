import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
spec=importlib.util.spec_from_file_location('guarded',Path(__file__).parents[1]/'integration/guarded_apply.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class GuardedTests(unittest.TestCase):
 def test_watchdog_must_arm_before_switch(self):
  calls=[]
  class Adapter:
   def arm(self,*a):calls.append('arm');return False
   def apply(self,*a):calls.append('apply');return {'verified':True}
   def cancel(self,*a):calls.append('cancel')
  with tempfile.TemporaryDirectory() as d:
   r=m.execute(Path(d),'a'*64,0,Adapter());self.assertFalse(r['verified']);self.assertEqual(calls,['arm'])
 def test_failed_apply_leaves_watchdog_for_recovery(self):
  calls=[]
  class Adapter:
   def arm(self,*a):calls.append('arm');return True
   def apply(self,*a):calls.append('apply');return {'verified':False,'restored':False}
   def cancel(self,*a):calls.append('cancel')
  with tempfile.TemporaryDirectory() as d:
   r=m.execute(Path(d),'a'*64,0,Adapter());self.assertFalse(r['verified']);self.assertEqual(calls,['arm','apply'])
 def test_verified_apply_cancels_only_its_timer(self):
  calls=[]
  class Adapter:
   def arm(self,token,*a):calls.append(('arm',token));return True
   def apply(self,*a):return {'verified':True}
   def cancel(self,token):calls.append(('cancel',token))
  with tempfile.TemporaryDirectory() as d:
   r=m.execute(Path(d),'a'*64,0,Adapter());self.assertTrue(r['verified']);self.assertEqual(calls[0][1],calls[1][1])
if __name__=='__main__':unittest.main()
