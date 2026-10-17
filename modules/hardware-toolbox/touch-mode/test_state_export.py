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
 def test_guard_blocks_mode_write_after_query(self):
  from unittest.mock import patch,mock_open
  from touch_mode import read_apply
  queries=[]
  def query(fd,selector,value=0):queries.append(selector);return 1
  def denied():raise PermissionError('locked after authorization')
  with patch('builtins.open',mock_open()),patch('touch_mode.fcntl.flock'),patch('touch_mode.find_device',return_value='/dev/test'),patch('touch_mode.os.open',return_value=123),patch('touch_mode.os.close'),patch('touch_mode.query',side_effect=query):
   with self.assertRaises(PermissionError):read_apply('normal',guard=denied)
  self.assertNotIn(1,queries)
