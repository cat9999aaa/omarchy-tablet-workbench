import importlib.util
import json
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('upstream',Path(__file__).with_name('proxy-upstream.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class UpstreamTests(unittest.TestCase):
 def release(self):return {'tag_name':'v26.10.10','prerelease':False,'draft':False,'html_url':'https://github.com/XTLS/Xray-core/releases/tag/v26.10.10','assets':[{'name':'Xray-linux-64.zip','digest':'sha256:'+'a'*64,'browser_download_url':'https://github.com/XTLS/Xray-core/releases/download/v26.10.10/Xray-linux-64.zip'}]}
 def test_public_metadata_only(self):
  r=self.release();r['body']='untrusted body';v=m.normalize('XTLS/Xray-core',r,1000)
  self.assertEqual(v['version'],'v26.10.10');self.assertEqual(v['digest'],'a'*64);self.assertIsNone(v['observed_digest']);self.assertNotIn('untrusted body',json.dumps(v));self.assertEqual(v['compatibility'],'unverified')
 def test_prerelease_and_injected_source_rejected(self):
  r=self.release();r['prerelease']=True
  with self.assertRaises(ValueError):m.normalize('XTLS/Xray-core',r,1000)
  r=self.release();r['assets'][0]['browser_download_url']='https://evil.example/x'
  with self.assertRaises(ValueError):m.normalize('XTLS/Xray-core',r,1000)
 def test_manifest_never_claims_artifact_signature(self):
  r=self.release();r['assets'][0].pop('digest');v=m.normalize('XTLS/Xray-core',r,1000)
  self.assertIsNone(v['digest']);self.assertIsNone(v['observed_digest'])
if __name__=='__main__':unittest.main()
