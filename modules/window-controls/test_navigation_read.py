import importlib.util
import json
from pathlib import Path
import sys
import os
import signal
import tempfile
import time
import unittest
from unittest.mock import patch

class ReadTests(unittest.TestCase):
 def api(self):
  p=Path(__file__).with_name('navigation_read.py')
  self.assertTrue(p.is_file(),'bounded navigation reader missing')
  spec=importlib.util.spec_from_file_location('navigation_read_test',p)
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
 def test_shared_budget_shrinks_and_expires(self):
  a=self.api();clock=[0.0];b=a.ReadBudget(clock=lambda:clock[0])
  self.assertEqual(b.timeout(),1.0)
  clock[0]=4.6;self.assertAlmostEqual(b.timeout(),.4)
  clock[0]=5
  with self.assertRaises(a.ReadError) as e:b.timeout()
  self.assertEqual(e.exception.code,'timeout')
 def test_exact_limit_and_one_extra_byte(self):
  a=self.api()
  for size,success in [(1048576,True),(1048577,False)]:
   code="import sys;sys.stdout.write('\\\"'+'a'*"+str(size-2)+"+'\\\"')"
   if success:self.assertEqual(len(a.read_json([sys.executable,'-c',code],a.ReadBudget())),size-2)
   else:
    with self.assertRaises(a.ReadError) as e:a.read_json([sys.executable,'-c',code],a.ReadBudget())
    self.assertEqual(e.exception.code,'invalid-data')
 def test_single_read_cap_and_process_reaped(self):
  a=self.api();started=[];original=a.subprocess.Popen
  def launch(*args,**kwargs):
   proc=original(*args,**kwargs);started.append(proc);return proc
  start=time.monotonic()
  with patch.object(a.subprocess,'Popen',side_effect=launch):
   with self.assertRaises(a.ReadError) as e:
    a.read_json([sys.executable,'-c','import time;time.sleep(3)'],a.ReadBudget())
  self.assertEqual(e.exception.code,'timeout')
  self.assertLess(time.monotonic()-start,2)
  self.assertIsNotNone(started[0].returncode)
  self.assertTrue(started[0].stdout.closed)
 def test_timeout_cleans_child_after_parent_exit(self):
  a=self.api()
  with tempfile.TemporaryDirectory() as directory:
   receipt=Path(directory)/'pid'
   code="import subprocess,sys;from pathlib import Path;p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(10)']);Path(sys.argv[1]).write_text(str(p.pid))"
   pid=None
   try:
    with self.assertRaises(a.ReadError) as e:a.read_json([sys.executable,'-c',code,str(receipt)],a.ReadBudget(.4))
    self.assertEqual(e.exception.code,'timeout');pid=int(receipt.read_text())
    def alive():
     try:return Path('/proc/'+str(pid)+'/stat').read_text().rsplit(')',1)[1].split()[0]!='Z'
     except FileNotFoundError:return False
    deadline=time.monotonic()+.5
    while alive() and time.monotonic()<deadline:time.sleep(.01)
    self.assertFalse(alive(),'timed-out descendant still running')
   finally:
    if pid:
     try:os.kill(pid,signal.SIGKILL)
     except ProcessLookupError:pass
 def test_timeout_and_invalid_output(self):
  a=self.api()
  for code,want in [("import time;time.sleep(2)",'timeout'),("print('{bad')",'invalid-data'),("print('NaN')",'invalid-data'),("raise SystemExit(2)",'read-failed')]:
   start=time.monotonic()
   with self.assertRaises(a.ReadError) as e:a.read_json([sys.executable,'-c',code],a.ReadBudget(.15))
   self.assertEqual(e.exception.code,want);self.assertLess(time.monotonic()-start,1.5)

class SnapshotTests(unittest.TestCase):
 def setUp(self):
  import navigation
  self.n=navigation
  self.active={'address':'0xab','pid':12,'class':'Synthetic'}
  self.monitors=[{'name':'TEST-1','focused':True,'disabled':False}]
 def values(self):return [False,self.monitors,self.active,{'id':1},[{'workspace':{'id':1}}],self.active,self.monitors,False]
 def snapshot(self,values):
  self.assertTrue(hasattr(self.n,'read_json'),'snapshot must use bounded reader')
  budgets=[]
  def read(argv,budget,**kwargs):
   budgets.append(budget)
   if not values:raise self.n.ReadError('read-failed')
   return values.pop(0)
  with patch.object(self.n,'read_json',side_effect=read),patch.object(self.n,'load_bindings',return_value=self.n.DEFAULTS),patch.object(self.n,'save_bindings') as save:
   result=self.n.snapshot();save.assert_not_called()
  self.assertTrue(all(b is budgets[0] for b in budgets));return result
 def test_valid_and_empty_window(self):
  r=self.snapshot(self.values());self.assertTrue(r['ok']);self.assertEqual(r['output'],'TEST-1');self.assertEqual(r['target'],{'address':'0xab','pid':12});self.assertEqual(r['workspaces'][0]['count'],1)
  v=self.values();v[2]={};v[5]={};r=self.snapshot(v);self.assertTrue(r['ok']);self.assertIsNone(r['target'])
 def test_changed_context_and_lock(self):
  for index,value,reason in [(5,{'address':'0xab','pid':13},'context-changed'),(6,[{'name':'TEST-2','focused':True}],'context-changed'),(7,True,'locked'),(0,None,'lock-unknown')]:
   with self.subTest(index=index):
    v=self.values();v[index]=value;r=self.snapshot(v);self.assertFalse(r['ok']);self.assertEqual(r['reason_code'],reason)
 def test_invalid_data(self):
  for index,value in [(1,{}),(1,[{'name':'bad\nname','focused':True}]),(2,{'address':'0xab','pid':True}),(2,[]),(3,{'id':True}),(4,[None]),(4,[{'workspace':{'id':True}}])]:
   with self.subTest(index=index,value=value):
    v=self.values();v[index]=value;r=self.snapshot(v);self.assertFalse(r['ok']);self.assertEqual(r['reason_code'],'invalid-data')
 def test_failure_only_returns_safe_output_after_fresh_checks(self):
  for final,expected in [(False,'TEST-1'),(True,None),(None,None)]:
   values=[False,self.monitors,self.n.ReadError('timeout'),self.monitors,final]
   def read(argv,budget):
    value=values.pop(0)
    if isinstance(value,Exception):raise value
    return value
   with patch.object(self.n,'read_json',side_effect=read):result=self.n.snapshot()
   self.assertFalse(result['ok']);self.assertEqual(result.get('output'),expected)
   self.assertNotIn('target',result);self.assertNotIn('windowLabel',result)
 def test_failure_feedback_cannot_extend_expired_budget(self):
  clock=[0.0];budget=self.n.ReadBudget(clock=lambda:clock[0]);calls=[]
  def read(argv,current):
   calls.append(argv);current.timeout()
   if len(calls)==1:return False
   if len(calls)==2:return self.monitors
   clock[0]=5.0;raise self.n.ReadError('timeout')
  with patch.object(self.n,'ReadBudget',return_value=budget),patch.object(self.n,'read_json',side_effect=read):result=self.n.snapshot()
  self.assertNotIn('output',result);self.assertEqual(result['reason_code'],'timeout')
  self.assertEqual(len(calls),4)
 def test_failure_does_not_migrate_to_new_output(self):
  values=[False,self.monitors,self.n.ReadError('timeout'),[{'name':'TEST-2','focused':True}]]
  def read(argv,budget):
   value=values.pop(0)
   if isinstance(value,Exception):raise value
   return value
  with patch.object(self.n,'read_json',side_effect=read):result=self.n.snapshot()
  self.assertNotIn('output',result)
 def test_ambiguous_output(self):
  v=self.values();v[1]=self.monitors+[{'name':'TEST-2','focused':True}];r=self.snapshot(v);self.assertFalse(r['ok']);self.assertEqual(r['reason_code'],'output-unavailable')

if __name__=='__main__':unittest.main()
