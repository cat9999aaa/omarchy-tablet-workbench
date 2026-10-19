import json,tempfile,unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
import importlib
ID='00000000-0000-4000-8000-000000000001'
class ModelTests(unittest.TestCase):
 def setUp(self):
  self.assertTrue(Path(__file__).with_name('task_model.py').exists(),'task model missing')
  self.m=importlib.import_module('task_model');self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.home=Path(self.tmp.name);self.project=self.home/'app';self.project.mkdir();(self.home/'application').mkdir()
 def row(self,**kw):return dict(id=ID,status='running',cwd=str(self.project),name='PRIVATE',provider='SECRET',**kw)
 def test_truthful_states(self):
  for v in ['idle','closed','initializing','running','error']:self.assertEqual(self.m.state_kind(v,None),v)
  self.assertEqual(self.m.state_kind('running',2),'needs_permission');self.assertEqual(self.m.state_kind('new',None),'unknown')
  self.assertEqual(self.m.state_kind('running',True),'unknown')
 def test_scope_and_projection(self):
  rows=[self.row(),dict(self.row(),id='00000000-0000-4000-8000-000000000002',cwd=str(self.home/'application'))]
  before=json.dumps(rows);result=self.m.project_rows(rows,self.project,self.home)
  self.assertEqual(result,[{'agent_id':ID,'status':'running'}]);self.assertEqual(json.dumps(rows),before)
  self.assertEqual(self.m.project_rows([dict(self.row(),cwd='~/app')],self.project,self.home),result)
  (self.project/'escape').symlink_to(self.home/'application',target_is_directory=True)
  self.assertEqual(self.m.project_rows([dict(self.row(),cwd=str(self.project/'escape'))],self.project,self.home),[])
 def test_duplicates_and_shapes_rejected(self):
  for raw in [{},[None],[dict(self.row(),id='--host')],[self.row(),dict(self.row(),status='idle')]]:
   with self.assertRaises(self.m.TaskDataError):self.m.project_rows(raw,self.project,self.home)
  self.assertEqual(len(self.m.project_rows([self.row(),self.row()],self.project,self.home)),1)
 def test_detail_identity_privacy_and_unknown(self):
  raw={'Id':ID,'Cwd':str(self.project),'Status':'idle','Name':'PRIVATE','PendingPermissions':[{'id':'p','tool':'SECRET'}],'UpdatedAt':'2020-01-01T00:00:00Z'}
  d=self.m.project_detail(raw,ID,self.project,self.home)
  self.assertEqual(d,{'status':'idle','pending_permission_count':1,'source_updated_at':'2020-01-01T00:00:00Z'})
  for change in [{'Id':'wrong'},{'Cwd':str(self.home/'application')},{'PendingPermissions':True}]:
   with self.assertRaises(self.m.TaskDataError):self.m.project_detail(dict(raw,**change),ID,self.project,self.home)
  raw.pop('PendingPermissions');self.assertIsNone(self.m.project_detail(raw,ID,self.project,self.home)['pending_permission_count'])
 def test_invalid_and_future_time_not_trusted(self):
  for value in ['bad','2020-01-01T00:00:00',(datetime.now(timezone.utc)+timedelta(days=1)).isoformat(),None]:
   d=self.m.project_detail({'Id':ID,'Cwd':str(self.project),'Status':'closed','UpdatedAt':value},ID,self.project,self.home)
   self.assertIsNone(d['source_updated_at'])
 def test_missing_project_fails(self):
  self.project.rmdir()
  with self.assertRaises(self.m.TaskDataError):self.m.project_rows([],self.project,self.home)
if __name__=='__main__':unittest.main()
