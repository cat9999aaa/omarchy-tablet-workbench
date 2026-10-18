"""Failure gates must not report a partial render as complete."""
import importlib.util
import json
from pathlib import Path
import struct
import sys
import zlib
import tempfile
import unittest

class RenderGates(unittest.TestCase):
 def setUp(self):
  path=Path(__file__).with_name('render_support.py')
  self.assertTrue(path.exists(),'render verification support missing')
  spec=importlib.util.spec_from_file_location('render_support',path);self.api=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.api)
  temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.root=Path(temp.name)
 def test_missing_official_parser_rejected(self):
  with self.assertRaises(RuntimeError):self.api.verify_official(self.root)
 def test_failed_process_and_timeout_rejected(self):
  with self.assertRaises(RuntimeError):self.api.run_checked([sys.executable,'-c','raise SystemExit(1)'],timeout=2)
  with self.assertRaises(RuntimeError):self.api.run_checked([sys.executable,'-c','import time;time.sleep(5)'],timeout=.05)
 def test_missing_or_incomplete_receipt_rejected(self):
  with self.assertRaises(RuntimeError):self.api.verify_outputs(self.root,['parsed'],['surface.png'])
  (self.root/'results.json').write_text(json.dumps({'passed':['parsed'],'source_sha256':{'test':'a'*64}}))
  with self.assertRaises(RuntimeError):self.api.verify_outputs(self.root,['parsed'],['surface.png'])
  (self.root/'surface.png').write_bytes(b'not a screenshot')
  with self.assertRaises(RuntimeError):self.api.verify_outputs(self.root,['parsed'],['surface.png'])
 def test_complete_png_and_dimensions(self):
  (self.root/'results.json').write_text(json.dumps({'passed':['parsed'],'failed':[],'source_sha256':{'test':'a'*64}}))
  chunk=lambda kind,data:struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data))
  image=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(b'\0\xff\0\0\xff'))+chunk(b'IEND',b'')
  (self.root/'surface.png').write_bytes(image)
  self.api.verify_outputs(self.root,['parsed'],{'surface.png':(1,1)})
  with self.assertRaises(RuntimeError):self.api.verify_outputs(self.root,['parsed'],{'surface.png':(2,2)})
 def test_truncated_png_with_valid_header_rejected(self):
  (self.root/'results.json').write_text(json.dumps({'passed':['parsed'],'failed':[],'source_sha256':{'test':'a'*64}}))
  chunk=lambda kind,data:struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data))
  header=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',2,2,8,6,0,0,0))
  (self.root/'surface.png').write_bytes(header+b'x'*100)
  with self.assertRaises(RuntimeError):self.api.verify_outputs(self.root,['parsed'],['surface.png'])
 def test_assertion_failure_or_missing_case_rejected(self):
  for value in [{'passed':[],'failed':[]},{'passed':['parsed'],'failed':['state']}]:
   (self.root/'results.json').write_text(json.dumps(value))
   with self.assertRaises(RuntimeError):self.api.verify_outputs(self.root,['parsed'],[])

if __name__=='__main__':unittest.main()
