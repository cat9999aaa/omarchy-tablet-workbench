import unittest
from touch_mode import state_payload

class ExportTests(unittest.TestCase):
 def test_normal_is_temporary_and_has_no_identity(self):
  self.assertEqual(state_payload(0,True,'',100), {'mode':0,'verified':True,'error':'','observed_at':100,'boot_default':1})
 def test_failure_does_not_reuse_previous_mode(self):
  d=state_payload(1,False,'read failed',100)
  self.assertIsNone(d['mode']);self.assertFalse(d['verified'])
 def test_unknown_mode_cannot_claim_verification(self):
  self.assertFalse(state_payload(8,True,'',100)['verified'])
