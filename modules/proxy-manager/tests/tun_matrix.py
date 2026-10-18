"""Exercise sing-box TUN and protected route ownership in an isolated namespace."""
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import time

def exercise(root,stack,run,start,private):
 baseline_rules=run(['ip','-j','rule']).stdout
 baseline_rules6=run(['ip','-6','-j','rule']).stdout
 baseline_links={v['ifname'] for v in json.loads(run(['ip','-j','link']).stdout)}
 # Owned peer lives in a nested net namespace; no external endpoints.
 log=open(root/'peer.log','wb');stack.callback(log.close)
 peer=subprocess.Popen(['unshare','--net','python',str(Path(__file__).with_name('tun_fixture.py')),str(root)],stdout=log,stderr=log,start_new_session=True)
 def stop_peer():
  if peer.poll() is None:os.killpg(peer.pid,signal.SIGTERM)
  try:peer.wait(timeout=3)
  except subprocess.TimeoutExpired:os.killpg(peer.pid,signal.SIGKILL);peer.wait()
 stack.callback(stop_peer)
 def wait_file(name):
  for _ in range(100):
   if (root/name).exists():return
   if peer.poll() is not None:raise AssertionError('peer fixture exited: '+(root/'peer.log').read_text()[-2000:])
   time.sleep(.05)
  raise AssertionError('peer namespace timeout')
 wait_file('peer-ready')
 run(['ip','link','add','omt-uplink','type','veth','peer','name','omt-peer'])
 run(['ip','link','set','omt-peer','netns',str(peer.pid)])
 run(['ip','link','set','omt-uplink','up'])
 run(['ip','addr','add','198.19.0.1/24','dev','omt-uplink'])
 run(['ip','-6','addr','add','2001:db8:1::1/64','dev','omt-uplink','nodad'])
 run(['ip','route','add','default','via','198.19.0.2','dev','omt-uplink'])
 run(['ip','-6','route','add','default','via','2001:db8:1::2','dev','omt-uplink'])
 (root/'peer-go').write_text('go');wait_file('peer-live')
 client=json.loads((root/'candidate.json').read_text());client['outbounds'][0]['settings']['address']='198.19.0.2'
 client['dns']={'hosts':{'fixture.example':'203.0.113.2'}}
 private(root/'tun-client.json',client)
 core=start('/cores/xray','tun-client')
 for _ in range(80):
  try:
   with socket.create_connection(('127.0.0.1',10818),.1):break
  except OSError:time.sleep(.05)
 tunconfig={'log':{'level':'warn'},'inbounds':[{'type':'tun','tag':'tun-in','interface_name':'omt-test','address':['172.31.254.1/30','fdfe:dcba:9876::1/126'],'auto_route':True,'strict_route':True,'stack':'gvisor','route_exclude_address':['198.19.0.2/32','127.0.0.0/8','10.0.0.0/8','172.16.0.0/12','192.168.0.0/16','2001:db8:1::2/128']}],'outbounds':[{'type':'socks','tag':'proxy','server':'127.0.0.1','server_port':10818},{'type':'direct','tag':'direct'}],'route':{'auto_detect_interface':True,'rules':[{'process_path':['/cores/xray','/cores/sing-box'],'outbound':'direct'},{'ip_is_private':True,'outbound':'direct'}],'final':'proxy'}}
 private(root/'tun.json',tunconfig);run(['/cores/sing-box','check','-c',str(root/'tun.json')])
 tun=start('/cores/sing-box','tun')
 for _ in range(80):
  if tun.poll() is not None:raise AssertionError('TUN exited: '+(root/'tun.log').read_text()[-3000:])
  if 'omt-test' in {v['ifname'] for v in json.loads(run(['ip','-j','link']).stdout)}:break
  time.sleep(.05)
 def fetch(url):return run(['curl','--noproxy','*','--connect-timeout','3','--max-time','6','--fail','--silent',url]).stdout
 assert fetch('http://203.0.113.2:28080')==b'omt-tun-fixture'
 assert fetch('http://[2001:db8:2::2]:28080')==b'omt-tun-fixture'
 # Test the ZeroTier UID-rule structure with the only mapped namespace UID (0).
 # This proves policy routing, not a real ZeroTier peer connection.
 for family in [[],['-6']]:run(['ip']+family+['rule','add','priority','8990','uidrange','0-0','lookup','main'])
 for family,target in [([], '203.0.113.2'),(['-6'],'2001:db8:2::2')]:
  route=json.loads(run(['ip']+family+['-j','route','get',target,'uid','0']).stdout)
  assert route[0]['dev']=='omt-uplink'
  run(['ip']+family+['rule','del','priority','8990','uidrange','0-0','lookup','main'])
 # Kill proxy transport: direct exception remains; normal TUN traffic must fail.
 core.terminate();core.wait(timeout=4)
 assert fetch('http://198.19.0.2:28081')==b'omt-tun-fixture'
 try:fetch('http://203.0.113.2:28080')
 except subprocess.CalledProcessError:pass
 else:raise AssertionError('TUN leaked through default direct route')
 tun.terminate();tun.wait(timeout=4)
 run(['ip','link','del','omt-uplink']);stop_peer()
 assert baseline_rules==run(['ip','-j','rule']).stdout
 assert baseline_rules6==run(['ip','-6','-j','rule']).stdout
 assert baseline_links=={v['ifname'] for v in json.loads(run(['ip','-j','link']).stdout)}
 return ['tun-ipv4','tun-ipv6','tun-no-direct-leak','zerotier-uid-route-v4-v6','owned-route-cleanup']
