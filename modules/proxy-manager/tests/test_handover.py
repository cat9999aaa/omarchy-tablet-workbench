import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('handover',Path(__file__).parents[1]/'integration/handover.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Adapter:
 def __init__(self,failed=None):self.failed=failed;self.calls=[]
 def step(self,name):self.calls.append(name);return name!=self.failed
class HandoverTests(unittest.TestCase):
 def test_watchdog_precedes_old_owner_stop(self):
  a=Adapter('arm');r=m.sequence(a)
  self.assertFalse(r['verified']);self.assertNotIn('stop_old',a.calls)
 def test_failure_restores_previous_owner(self):
  a=Adapter('verify');r=m.sequence(a)
  self.assertFalse(r['verified']);self.assertTrue(r['restored']);self.assertEqual(a.calls[-1],'restore')
  self.assertLess(a.calls.index('arm'),a.calls.index('stop_old'))
 def test_only_verified_cutover_commits(self):
  a=Adapter();self.assertTrue(m.sequence(a)['verified']);self.assertEqual(a.calls[-2:],['verify','commit'])
if __name__=='__main__':unittest.main()
