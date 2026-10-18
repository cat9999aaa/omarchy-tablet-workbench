#!/usr/bin/python3
"""Prepare private native state from the active legacy node; never take ownership."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
sys.path.insert(0,str(Path(__file__).resolve().parent))
from root_frontend import atomic,safe

def select(nodes,config):
 settings=next(o for o in config['outbounds'] if o.get('tag')=='proxy')['settings']
 found=[n for n in nodes if n['credential']==settings.get('id') and n['server']==settings.get('address') and n['port']==settings.get('port')]
 if len(found)!=1:raise ValueError('active_node_ambiguous')
 return found[0]

def prepare():
 home=Path.home();target=home/'.local/state/omt-proxy';lib=home/'.local/lib/omt-proxy';binary=lib/'omt-proxy'
 if any((target/n).exists() for n in ('owner.json','active.json','catalog.json')):raise ValueError('native_state_already_present')
 source=home/'.local/share/v2rayN/binConfigs/config.json';database=home/'.local/share/v2rayN/guiConfigs/guiNDB.db'
 hashes=[hashlib.sha256(p.read_bytes()).hexdigest() for p in (source,database)]
 spec=importlib.util.spec_from_file_location('prepare_owned',lib/'owned-core.py');owned=importlib.util.module_from_spec(spec);spec.loader.exec_module(owned)
 if not owned.probe():raise ValueError('legacy_not_healthy')
 with socket.socket() as s:s.bind(('127.0.0.1',10818))
 with tempfile.TemporaryDirectory(prefix='omt-prepare-',dir=os.environ['XDG_RUNTIME_DIR']) as temporary:
  store=Path(temporary);store.chmod(0o700)
  def cli(action,payload):
   r=subprocess.run([str(binary),action,str(store)],input=json.dumps(payload).encode(),capture_output=True,timeout=25)
   if r.returncode:raise ValueError('candidate_preparation_failed')
   return json.loads(r.stdout)
  preview=cli('catalog',{'action':'migrate'});cli('catalog',{'action':'commit','preview_id':preview['preview_id'],'confirmed':True})
  catalog=json.loads((store/'catalog.json').read_bytes());config=json.loads(source.read_bytes());node=select(catalog['nodes'],config)
  atomic(store/'template.json',json.dumps(config).encode())
  cli('core-preview',{'mode':'rules','node_id':node['id'],'base_revision':catalog['revision'],'rules':[],'port':10818})
  if not owned.check(store/'candidate.json').get('ok'):raise ValueError('native_check_failed')
  env={'PATH':'/usr/bin','HOME':str(home),'XRAY_LOCATION_ASSET':str(home/'.local/share/v2rayN/bin')}
  child=subprocess.Popen([str(owned.CORE),'run','-c',str(store/'candidate.json')],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  try:
   ready=False
   for _ in range(50):
    if child.poll() is not None:break
    try:
     with socket.create_connection(('127.0.0.1',10818),.1):ready=True;break
    except OSError:time.sleep(.1)
   if not ready:raise ValueError('candidate_not_listening')
   for url in ('https://www.gstatic.com/generate_204','https://www.google.com/generate_204'):
    response=subprocess.run(['curl','--noproxy','','--proxy','socks5h://127.0.0.1:10818','--silent','--fail','--max-time','10','--output','/dev/null','--write-out','%{http_code}',url],capture_output=True,timeout=12)
    if response.returncode or response.stdout.strip()!=b'204':raise ValueError('side_port_probe_failed')
  finally:
   if child.poll() is None:child.terminate()
   try:child.wait(timeout=5)
   except subprocess.TimeoutExpired:child.kill();child.wait()
  if hashes!=[hashlib.sha256(p.read_bytes()).hexdigest() for p in (source,database)] or not owned.probe():raise ValueError('legacy_changed_or_unhealthy')
  active=json.loads((store/'candidate.json').read_bytes());active['inbounds'][0]['port']=10808
  active_bytes=json.dumps(active,separators=(',',':')).encode()
  if target.is_symlink() or target.resolve()!=target:raise ValueError('unsafe_store')
  target.mkdir(parents=True,exist_ok=True,mode=0o700)
  if target.stat().st_mode&0o077:raise ValueError('unsafe_store')
  for name in ('catalog.json','template.json'):
   if (target/name).exists():raise ValueError('native_state_changed')
   atomic(target/name,(store/name).read_bytes())
  atomic(target/'active.json',active_bytes)
  atomic(target/'applied.json',json.dumps({'node_id':node['id'],'mode':'rules','sha256':hashlib.sha256(active_bytes).hexdigest()}).encode())
 return {'prepared':True,'applied':False,'side_port_verified':True,'legacy_unchanged':True}

if __name__=='__main__':
 try:print(json.dumps(prepare()))
 except Exception:print('{"prepared":false,"applied":false,"error_code":"private_preparation_failed"}');sys.exit(1)
