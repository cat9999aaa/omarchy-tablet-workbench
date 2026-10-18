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

class ObservationTests(unittest.TestCase):
 def setUp(self):
  import touch_mode
  self.tool=touch_mode
  self.assertTrue(callable(getattr(touch_mode,'cache_payload',None)), 'trusted cache payload is not implemented')
  self.observation={'schema':1,'boot_marker':'a'*64,'started_boottime_ms':1000}

 def test_legacy_payload_has_no_boot_marker(self):
  self.assertEqual(self.tool.state_payload(0,True,'',100),{'mode':0,'verified':True,'error':'','observed_at':100,'boot_default':1})
  cached=self.tool.cache_payload(0,True,'',100,self.observation)
  self.assertEqual(cached['observation'],self.observation)
  self.assertEqual(cached['mode'],0);self.assertEqual(cached['boot_default'],1)
  self.assertNotIn('boot_marker',self.tool.state_payload(0,True,'',100))

 def test_cache_observation_precedes_device_query(self):
  from unittest.mock import patch
  import io,json,tempfile
  from contextlib import redirect_stdout
  from pathlib import Path
  order=[]
  def start():order.append('start');return dict(self.observation)
  def query(mode):order.append('query');return {'actual':0,'verified':True}
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'cache'
   with patch.object(self.tool,'observation_start',side_effect=start),patch.object(self.tool,'read_apply',side_effect=query),patch.object(self.tool.os,'geteuid',return_value=0),patch.object(self.tool,'Path',return_value=path),patch('sys.argv',['touch_mode.py','export']),patch.object(self.tool.time,'time',return_value=999):
    output=io.StringIO()
    with redirect_stdout(output):self.tool.main()
   self.assertEqual(order,['start','query'])
   cached=json.loads((path/'state.json').read_text())
   self.assertEqual(cached['observation']['started_boottime_ms'],1000)
   self.assertEqual(cached['observed_at'],999)
   public=json.loads(output.getvalue());self.assertNotIn('observation',public)
   self.assertNotIn('a'*64,output.getvalue())
   self.assertEqual(list(path.iterdir()),[path/'state.json'])

 def test_missing_clock_or_boot_marker_keeps_legacy_cache(self):
  from unittest.mock import patch
  for missing in ('clock','boot'):
   with self.subTest(missing=missing),patch.object(self.tool.Path,'read_text',side_effect=OSError('unavailable') if missing=='boot' else None,return_value='00000000-0000-4000-8000-000000000000\n'),patch.object(self.tool.time,'clock_gettime',side_effect=OSError('unavailable') if missing=='clock' else None,return_value=1.0):
    observation=self.tool.observation_start()
    self.assertIsNone(observation)
    value=self.tool.cache_payload(1,True,'',100,observation)
    self.assertNotIn('observation',value);self.assertEqual(value['mode'],1)
  self.assertNotIn('observation',self.tool.cache_payload(1,True,'',100))

 def test_clock_values_reject_bool_nonfinite_negative(self):
  for value in (True,False,-1,float('nan'),float('inf'),-float('inf'),10**1000,'100',None):
   with self.subTest(value=repr(value)[:30]):
    observation={**self.observation,'started_boottime_ms':value}
    self.assertNotIn('observation',self.tool.cache_payload(1,True,'',100,observation))
  for change in ({'schema':True},{'schema':2},{'boot_marker':'x'},{'boot_marker':None},{'extra':'no'}):
   self.assertNotIn('observation',self.tool.cache_payload(1,True,'',100,{**self.observation,**change}))

 def test_failed_read_never_reuses_success(self):
  from unittest.mock import patch
  import tempfile,json
  from pathlib import Path
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'cache'
   with patch.object(self.tool,'Path',return_value=path):
    self.tool.export_state(1,True,observation=self.observation)
    self.tool.export_state(None,False,'failed',observation=self.observation)
   value=json.loads((path/'state.json').read_text())
   self.assertIsNone(value['mode']);self.assertFalse(value['verified'])
   self.assertNotIn('observation',value)

 def test_boot_marker_is_opaque_and_clock_converted_to_ms(self):
  from unittest.mock import patch
  boot='00000000-0000-4000-8000-000000000000'
  with patch.object(self.tool.Path,'read_text',return_value=boot+'\n'),patch.object(self.tool.time,'clock_gettime',return_value=1.25):
   observation=self.tool.observation_start()
  self.assertEqual(observation['started_boottime_ms'],1250)
  self.assertEqual(observation['schema'],1)
  self.assertRegex(observation['boot_marker'],'^[a-f0-9]{64}$')
  self.assertNotIn(boot,str(observation))
  for bad in ('', 'not-a-boot-id', boot+'extra'):
   with patch.object(self.tool.Path,'read_text',return_value=bad):self.assertIsNone(self.tool.observation_start())
