import importlib,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ID='00000000-0000-4000-8000-000000000001'
class SourceTests(unittest.TestCase):
 def setUp(self):
  self.assertTrue(Path(__file__).with_name('task_source.py').exists(),'task source missing')
  self.m=importlib.import_module('task_source');self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.p=Path(self.tmp.name);self.project=self.p/'app';self.project.mkdir()
 def reader(self,argv,budget,**kw):
  if argv==['omarchy-shell','lock','isLocked']:return False
  if argv==['hyprctl','monitors','-j']:return [{'name':'TEST','focused':True}]
  if argv==['paseo','ls','--global','--json']:return [{'id':ID,'status':'idle','cwd':str(self.project),'name':'PRIVATE'}]
  if argv==['paseo','inspect',ID,'--json']:return {'Id':ID,'Cwd':str(self.project),'Status':'idle','PendingPermissions':[],'Name':'PRIVATE'}
  raise AssertionError(argv)
 def test_snapshot_scoped_and_dnd_partial(self):
  with patch.object(self.m,'read_json',side_effect=self.reader),patch.object(self.m,'read_text',return_value='off'):
   r=self.m.collect_snapshot(self.project,self.m.ReadBudget(max_read_seconds=2))
  self.assertTrue(r['ok']);self.assertEqual(r['rows'],[{'agent_id':ID,'status':'idle'}]);self.assertEqual(r['output'],'TEST');self.assertFalse(r['dnd']);self.assertNotIn('PRIVATE',json.dumps(r))
 def test_detail_checks_requested_output_and_membership(self):
  with patch.object(self.m,'read_json',side_effect=self.reader):
   r=self.m.collect_detail(self.project,ID,self.m.ReadBudget(max_read_seconds=2),expected_output='TEST')
   self.assertEqual(r['detail']['pending_permission_count'],0)
   with self.assertRaises(self.m.ReadError):self.m.collect_detail(self.project,ID,self.m.ReadBudget(max_read_seconds=2),expected_output='OTHER')
 def test_locked_does_not_query_paseo(self):
  calls=[]
  def locked(argv,budget,**kw):calls.append(argv);return True
  with patch.object(self.m,'read_json',side_effect=locked):
   with self.assertRaises(self.m.ReadError):self.m.collect_snapshot(self.project,self.m.ReadBudget())
  self.assertEqual(calls,[['omarchy-shell','lock','isLocked']])
 def test_source_failure_not_empty_success(self):
  def fail(argv,budget,**kw):
   if argv[0]=='paseo':raise self.m.ReadError('read-failed')
   return self.reader(argv,budget,**kw)
  with patch.object(self.m,'read_json',side_effect=fail),patch.object(self.m,'read_text',return_value='on'):
   r=self.m.collect_snapshot(self.project,self.m.ReadBudget())
  self.assertIsNone(r['rows']);self.assertEqual(r['source_reason'],'read-failed');self.assertTrue(r['dnd'])
 def test_project_replaced_during_read_is_rejected(self):
  def replaced(argv,budget,**kw):
   value=self.reader(argv,budget,**kw)
   if argv[0]=='paseo':
    self.project.rename(self.p/'previous');self.project.mkdir()
   return value
  with patch.object(self.m,'read_json',side_effect=replaced),patch.object(self.m,'read_text',return_value='off'):
   r=self.m.collect_snapshot(self.project,self.m.ReadBudget())
  self.assertIsNone(r['rows']);self.assertEqual(r['source_reason'],'invalid-project')
if __name__=='__main__':unittest.main()
