import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
spec=importlib.util.spec_from_file_location('client',Path(__file__).parents[1]/'integration/client.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class ClientTests(unittest.TestCase):
 def test_all_entrypoints_use_one_socket_revision(self):
  sent=[]
  def run(argv,**kw):
   v=json.loads(kw['input']);sent.append((argv,v))
   reply={'snapshot':{'revision':88}} if v['action']=='status' else {'outcome':{'verified':True,'stage':'verified'}}
   return subprocess.CompletedProcess(argv,0,json.dumps(reply).encode(),b'')
  result=m.dispatch(Path('/home/fixture'),'enable',True,runner=run)
  self.assertTrue(result['verified']);self.assertEqual(sent[1][1]['expected_revision'],88);self.assertEqual(sent[0][0],sent[1][0])
 def test_disable_needs_confirmation_and_failure_not_success(self):
  result=m.dispatch(Path('/home/fixture'),'disable',False,runner=lambda *a,**k:self.fail('called'))
  self.assertFalse(result['verified']);self.assertEqual(result['stage'],'confirmation')
  result=m.dispatch(Path('/home/fixture'),'enable',True,runner=lambda a,**k:subprocess.CompletedProcess(a,1,b'',b''))
  self.assertFalse(result['verified'])
 def test_owner_flag_rejects_symlinks(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);store=root/'.local/state/omt-proxy';store.mkdir(parents=True);p=store/'owner.json';p.write_text('{"owner":"omt-proxy"}');p.chmod(0o600)
   self.assertTrue(m.native(root));p.unlink();(root/'other').write_text('{"owner":"omt-proxy"}');p.symlink_to(root/'other');self.assertFalse(m.native(root))
if __name__=='__main__':unittest.main()
