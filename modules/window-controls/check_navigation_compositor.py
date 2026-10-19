"""Real matching-version Hyprland gate; no host compositor sockets or inputs.

Fail closed on unavailable renderer or API. No mocked compositor substitute.
"""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts/themes'))

import navigation


@contextmanager
def compositor(root):
 runtime=root/'runtime';runtime.mkdir(mode=0o700)
 env={**os.environ,'XDG_RUNTIME_DIR':str(runtime),'QT_QPA_PLATFORM':'wayland','QT_QUICK_BACKEND':'software',
      'AQ_DRM_DEVICES':'/dev/dri/renderD128','AQ_NO_KMS_REQUIREMENT':'1'}
 for key in ('SWAYSOCK','WAYLAND_DISPLAY','DISPLAY','DBUS_SESSION_BUS_ADDRESS','HYPRLAND_INSTANCE_SIGNATURE'):env.pop(key,None)
 yield env

def main():
 if os.environ.get('C1_ISOLATED_TEST')!='1':raise RuntimeError('isolated namespace required')
 version=subprocess.check_output(['Hyprland','--version'],text=True)
 if not version.startswith('Hyprland 0.56.2 '):raise RuntimeError('matching compositor required')
 with tempfile.TemporaryDirectory(prefix='c2h-') as temp:
  root=Path(temp);cfg=root/'hyprland.lua'
  cfg.write_text('hl.monitor({output="",mode="640x480",position="auto",scale=1})\n')
  with compositor(root) as env:
   env.update(HYPRLAND_NO_CRASHREPORTER='1',HYPRLAND_NO_RT='1')
   with (root/'hypr.log').open('w+') as log:
    child=subprocess.Popen(['Hyprland','--config',str(cfg)],env=env,stdout=log,stderr=subprocess.STDOUT)
    try:
     end=time.monotonic()+10
     while time.monotonic()<end:
      sockets=list((root/'runtime/hypr').glob('*/.socket.sock'))
      if sockets:break
      if child.poll() is not None:raise RuntimeError('matching compositor unavailable')
      time.sleep(.05)
     else:raise RuntimeError('matching compositor startup timeout')
     env['HYPRLAND_INSTANCE_SIGNATURE']=sockets[0].parent.name
     def ctl(*args):
      return subprocess.check_output(['hyprctl',*args],env=env,text=True,timeout=3).strip()
     print('C2_COMPOSITOR_VERSION:0.56.2')
     def wait_for(test,label):
      end=time.monotonic()+5
      while time.monotonic()<end:
       if test():return
       time.sleep(.05)
      raise AssertionError(label)
     displays=[p.name for p in (root/'runtime').glob('wayland-*') if not p.name.endswith('.lock')]
     assert len(displays)==1;env['WAYLAND_DISPLAY']=displays[0]
     def value(name):return json.loads(ctl(name,'-j'))
     quoted='C2-"quoted'
     ctl('output','create','headless',quoted)
     wait_for(lambda:len(value('monitors'))>=2,'two outputs')
     output=value('monitors')[0]['name']
     clients=[]
     try:
      for title in ['C2-A','C2-B']:
       fixture=root/(title+'.qml')
       fixture.write_text('import QtQuick\nimport Quickshell\nShellRoot { FloatingWindow { visible:true; width:200; height:160; title:'+json.dumps(title)+'; color:"#223344" } }')
       clients.append(subprocess.Popen(['qs','-p',str(fixture)],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
      wait_for(lambda:len(value('clients'))==2,'two real windows')
      a,b=value('clients')
      def focus(window):
       assert ctl('dispatch','hl.dsp.focus({window='+json.dumps('address:'+window['address'])+'})')=='ok'
       wait_for(lambda:value('activewindow').get('address')==window['address'],'focus window')
      focus(a)
      output=next(m['name'] for m in value('monitors') if m['focused'])
      target={k:a[k] for k in ('address','pid')}
      def unchanged():assert {w['address'] for w in value('clients')}=={a['address'],b['address']}
      for bad in [dict(target,pid=target['pid']+99999),{'address':b['address'],'pid':target['pid']}]:
       assert ctl('eval',navigation.window_script('close',bad,output=output))!='ok';unchanged()
      assert ctl('eval',navigation.window_script('close',target,output='missing-output'))!='ok';unchanged()
      focus(b);assert ctl('eval',navigation.window_script('close',target,output=output))!='ok';unchanged()
      focus(a);before=value('activewindow')['floating']
      assert ctl('eval',navigation.window_script('float',target,output=output))=='ok'
      wait_for(lambda:value('activewindow')['floating']!=before,'one normal toggle')
      assert ctl('dispatch','hl.dsp.focus({monitor='+json.dumps(quoted)+'})')=='ok'
      wait_for(lambda:any(m['name']==quoted and m['focused'] for m in value('monitors')),'quoted output focused')
      assert ctl('eval',navigation.output_guard(quoted)+'hl.dispatch(hl.dsp.focus({workspace="8"}))')=='ok'
      assert ctl('eval',navigation.output_guard('missing-output')+'hl.dispatch(hl.dsp.focus({workspace="9"}))')!='ok'
      assert value('activeworkspace')['id']==8
      print('C2_COMPOSITOR_PASS:two-outputs-two-windows-stale-identity-quoted-name-single-dispatch')
     finally:
      for client in clients:
       if client.poll() is None:client.terminate()
       try:client.wait(timeout=3)
       except subprocess.TimeoutExpired:client.kill();client.wait()
    finally:
     if child.poll() is None:child.terminate()
     try:child.wait(timeout=3)
     except subprocess.TimeoutExpired:child.kill();child.wait()
     log.seek(0);print(log.read()[-2500:])
     for path in (root/'runtime/hypr').glob('*/hyprland.log'):print(path.read_text()[-6000:])
if __name__=='__main__':main()
