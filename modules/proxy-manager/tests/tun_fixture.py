"""Second network namespace for offline TUN acceptance; fixture data only."""
from pathlib import Path
import http.server
import json
import os
import socket
import subprocess
import sys
import threading
import time
root=Path(sys.argv[1])
(root/'peer-ready').write_text(str(os.getpid()))
while not (root/'peer-go').exists():time.sleep(.02)
subprocess.run(['ip','link','set','lo','up'],check=True)
subprocess.run(['ip','link','set','omt-peer','up'],check=True)
for args in [ ['addr','add','198.19.0.2/24','dev','omt-peer'],['addr','add','203.0.113.2/32','dev','lo'],['-6','addr','add','2001:db8:1::2/64','dev','omt-peer','nodad'],['-6','addr','add','2001:db8:2::2/128','dev','lo','nodad'] ]:
 subprocess.run(['ip']+args,check=True)
class Handler(http.server.BaseHTTPRequestHandler):
 def do_GET(self):self.send_response(200);self.end_headers();self.wfile.write(b'omt-tun-fixture')
 def log_message(self,*args):pass
class V6(http.server.ThreadingHTTPServer):address_family=socket.AF_INET6
for addr,cls in [(('203.0.113.2',28080),http.server.ThreadingHTTPServer),(('198.19.0.2',28081),http.server.ThreadingHTTPServer),(('2001:db8:2::2',28080),V6)]:
 server=cls(addr,Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
cfg=json.loads((root/'server.json').read_text());cfg['inbounds'][0]['listen']='0.0.0.0';cfg['dns']['hosts']['fixture.example']='203.0.113.2'
(root/'peer-server.json').write_text(json.dumps(cfg));(root/'peer-server.json').chmod(0o600)
p=subprocess.Popen(['/cores/xray','run','-c',str(root/'peer-server.json')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
(root/'peer-live').write_text('ready')
try:p.wait()
finally:
 if p.poll() is None:p.terminate();p.wait()
