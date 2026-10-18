#!/usr/bin/python3
"""Offline core fixture. Must run in the build runner's isolated network namespace."""
import contextlib
import hashlib
import http.server
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import threading
import time

XRAY='/cores/xray'
SING='/cores/sing-box'
CLI='/work/modules/proxy-manager/target/debug/omt-proxy'
UUID='11111111-2222-3333-4444-555555555555'

def run(argv, **kw):
 return subprocess.run(argv,check=True,capture_output=True,timeout=20,**kw)
def private(path,value):
 path.write_text(json.dumps(value));path.chmod(0o600);return str(path)
def wait_port(port, process):
 for _ in range(80):
  if process.poll() is not None:raise AssertionError('fixture process exited')
  try:
   with socket.create_connection(('127.0.0.1',port),.1):return
  except OSError:time.sleep(.05)
 raise AssertionError('fixture listen timeout')
class Handler(http.server.BaseHTTPRequestHandler):
 def do_GET(self):
  self.send_response(200);self.end_headers();self.wfile.write(b'omt-isolated-fixture')
 def log_message(self,*args):pass
class IPv6Server(http.server.ThreadingHTTPServer):address_family=socket.AF_INET6

def main():
 # Never execute against a real host namespace, even if invoked manually.
 assert os.environ.get('OMT_ISOLATED_NETWORK')=='1'
 assert {x['ifname'] for x in json.loads(run(['ip','-j','link']).stdout)}=={'lo'},'unexpected host interfaces'
 assert hashlib.sha256(Path(XRAY).read_bytes()).hexdigest()=='4cca4de3ab8c16b3803a70e9ebe0570d2a72480c716d89aa91603ec568bf0f44'
 assert hashlib.sha256(Path(SING).read_bytes()).hexdigest()=='768d31fa7f68debc067bb4626539498a1e8751d36a7b99e1a54bee6a23815f93'
 run(['ip','link','set','lo','up'])
 run(['ip','addr','add','198.18.0.2/32','dev','lo'])
 run(['ip','-6','addr','add','2001:db8::2/128','dev','lo','nodad'])
 before=run(['ip','-j','rule']).stdout
 with tempfile.TemporaryDirectory() as temp,contextlib.ExitStack() as stack:
  root=Path(temp);root.chmod(0o700)
  for address,cls in [(('198.18.0.2',28080),http.server.ThreadingHTTPServer),(('127.0.0.1',28081),http.server.ThreadingHTTPServer),(('2001:db8::2',28080),IPv6Server)]:
   server=cls(address,Handler);threading.Thread(target=server.serve_forever,daemon=True).start();stack.callback(server.server_close);stack.callback(server.shutdown)
  run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(root/'key.pem'),'-out',str(root/'cert.pem'),'-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost'])
  uri=f'vless://{UUID}@127.0.0.1:24443?security=tls&type=ws&sni=localhost&path=%2Fws#Offline-fixture'
  def cli(payload,op='catalog'):
   return json.loads(run([CLI,op,str(root)],input=json.dumps(payload).encode()).stdout)
  preview=cli({'action':'preview-uri','text':uri})
  # Use the same import/commit flow as the UI; no private fixtures on stdout.
  if 'preview_id' not in preview:raise AssertionError('fixture import shape')
  catalog=cli({'action':'commit','preview_id':preview['preview_id'],'confirmed':True})
  stored=json.loads((root/'catalog.json').read_text());node=stored['nodes'][0]
  private(root/'template.json',{'dns':{'hosts':{'fixture.example':'198.18.0.2'}},'routing':{'domainStrategy':'IPIfNonMatch','rules':[]}})
  cli({'mode':'rules','node_id':node['id'],'base_revision':stored['revision'],'rules':[],'port':10818},'core-preview')
  client=json.loads((root/'candidate.json').read_text());client['log']['loglevel']='debug'
  # Fixture CA only: the core defaults to its embedded trust store, not SSL_CERT_FILE.
  client['outbounds'][0]['streamSettings']['tlsSettings']['certificates']=[{'certificateFile':str(root/'cert.pem'),'usage':'verify'}]
  private(root/'candidate.json',client)
  server_config={'log':{'loglevel':'debug'},'dns':{'hosts':{'fixture.example':'198.18.0.2'}},'inbounds':[{'listen':'127.0.0.1','port':24443,'protocol':'vless','settings':{'clients':[{'id':UUID}],'decryption':'none'},'streamSettings':{'network':'ws','security':'tls','wsSettings':{'path':'/ws'},'tlsSettings':{'certificates':[{'certificateFile':str(root/'cert.pem'),'keyFile':str(root/'key.pem')}]}}}],'outbounds':[{'protocol':'freedom','settings':{'targetStrategy':'UseIP','finalRules':[{'action':'allow','ip':['198.18.0.2/32','203.0.113.2/32','2001:db8::/32']}]}}]}
  private(root/'server.json',server_config)
  env=dict(os.environ,SSL_CERT_FILE=str(root/'cert.pem'))
  for name in ['candidate','server']:run([XRAY,'run','-test','-c',str(root/(name+'.json'))],env=env)
  def start(binary,config):
   log=open(root/(config+'.log'),'wb');stack.callback(log.close)
   p=subprocess.Popen([binary,'run','-c',str(root/(config+'.json'))],stdout=log,stderr=log,env=env)
   def stop():
    if p.poll() is None:p.terminate()
    try:p.wait(timeout=4)
    except subprocess.TimeoutExpired:p.kill();p.wait()
   stack.callback(stop);return p
  upstream=start(XRAY,'server');wait_port(24443,upstream)
  clientp=start(XRAY,'candidate');wait_port(10818,clientp)
  def fetch(url,expected_failure=False):
   try:return run(['curl','--noproxy','','--socks5-hostname','127.0.0.1:10818','--connect-timeout','3','--max-time','5','--fail','--silent',url]).stdout
   except subprocess.CalledProcessError:
    if not expected_failure:
     for name in ['candidate','server']:print(name,(root/(name+'.log')).read_text()[-6000:])
    raise
  assert run(['curl','--noproxy','*','--max-time','3','--silent','http://198.18.0.2:28080']).stdout==b'omt-isolated-fixture'
  assert fetch('http://198.18.0.2:28080')==b'omt-isolated-fixture'
  assert fetch('http://[2001:db8::2]:28080')==b'omt-isolated-fixture'
  assert fetch('http://fixture.example:28080')==b'omt-isolated-fixture'
  upstream.terminate();upstream.wait(timeout=4)
  assert fetch('http://127.0.0.1:28081')==b'omt-isolated-fixture'
  try:fetch('http://198.18.0.2:28080',True)
  except subprocess.CalledProcessError:pass
  else:raise AssertionError('proxy request incorrectly bypassed failed upstream')
  assert before==run(['ip','-j','rule']).stdout
  clientp.terminate();clientp.wait(timeout=4)
  from tun_matrix import exercise
  tun_results=exercise(root,stack,run,start,private)
 print(json.dumps({'passed':['xray-native-validation','vless-ws-tls','proxy-ipv4','proxy-ipv6','dns-host-routing','lan-direct-with-upstream-down','no-residual-policy-rules'],'tun':tun_results,'zerotier':'UID policy routing verified; real peer reachability not simulated'}))
if __name__=='__main__':main()
