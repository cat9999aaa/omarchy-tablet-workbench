"""Native layer lifecycle gate. Requires isolated Quickshell/Sway; no device actions."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts/themes'))
from render_support import compositor

def main():
    if os.environ.get('C1_ISOLATED_TEST')!='1':raise RuntimeError('isolated namespace required')
    source=Path(__file__).parent
    with tempfile.TemporaryDirectory(prefix='edge-layers-') as temp:
        root=Path(temp);home=root/'home';config=home/'.config/omarchy/shell.json'
        config.parent.mkdir(parents=True)
        def write(position):config.write_text(json.dumps({'bar':{'id':'test.bar','position':position}}))
        write('bottom')
        for name in ('EdgeInput.qml','EdgePolicy.js','Gesture.js'):shutil.copy2(source/name,root/name)
        # Test-only observation hooks, actual PanelWindow and FileView retained.
        text=(source/'EdgeGestures.qml').read_text().replace('id: root','id: root\n    property var probes: []',1)
        text=text.replace('id: strip','id: strip\n        Component.onCompleted: root.probes.push(strip)\n        Component.onDestruction: root.probes = root.probes.filter(p => p !== strip)\n        readonly property bool inputEnabled: input.enabled',1)
        (root/'EdgeGestures.qml').write_text(text)
        (root/'Test.qml').write_text('''import QtQuick
import Quickshell
import Quickshell.Io
ShellRoot {
 EdgeGestures {id:edges;hostPosition:"bottom"}
 IpcHandler {
  target:"testEdges"
  function position(value:string):void {edges.hostPosition=value}
  function state():string {return JSON.stringify(edges.probes.map(p=>({edge:p.edge,screen:p.screen?p.screen.name:null,visible:p.visible,enabled:p.inputEnabled,width:p.width,height:p.height})))}
 }
}
''')
        with compositor(root) as env:
            env['HOME']=str(home);env['SWAYSOCK']=str(next((root/'runtime').glob('sway-ipc.*.sock')))
            def sway(*args):subprocess.run(['swaymsg',*args],env=env,check=True,stdout=subprocess.PIPE,timeout=3)
            with (root/'shell.log').open('w+') as log:
                shell=subprocess.Popen(['qs','-p',str(root/'Test.qml')],env=env,stdout=log,stderr=subprocess.STDOUT)
                def set_position(value):
                    subprocess.run(['qs','ipc','--pid',str(shell.pid),'call','testEdges','position',value],env=env,check=True,capture_output=True,timeout=3)
                def state():
                    p=subprocess.run(['qs','ipc','--pid',str(shell.pid),'call','testEdges','state'],env=env,capture_output=True,text=True,timeout=3)
                    try:return json.loads(p.stdout) if p.returncode==0 else []
                    except ValueError:return []
                def expect(active,count=2):
                    end=time.monotonic()+5
                    while time.monotonic()<end:
                        rows=state()
                        if len(rows)==count and all(r['visible']==(r['edge'] in active) and r['enabled']==(r['edge'] in active) for r in rows) and all(r['height']==12 and r['width']>0 for r in rows if r['visible']):
                            return rows
                        time.sleep(.05)
                    raise AssertionError((active,count,rows))
                try:
                    expect({'top'});print('EDGE_PASS:bottom-bar-no-bottom-layer')
                    write('top');expect({'top'});print('EDGE_PASS:actual-owner-position-wins');set_position('top');expect({'bottom'});print('EDGE_PASS:top-bar-no-top-layer')
                    for position in ('left','right'):
                        write(position);set_position(position);expect({'top','bottom'})
                    config.write_text('{');expect(set());print('EDGE_PASS:invalid-config-no-layers')
                    write('bottom');set_position('bottom');expect({'top'})
                    sway('create_output');expect({'top'},4)
                    sway('output','HEADLESS-2','disable');rows=expect({'top'},2)
                    assert all(r['screen']=='HEADLESS-1' for r in rows)
                    print('EDGE_PASS:output-removal-cleans-layers')
                finally:
                    shell.terminate()
                    try:shell.wait(timeout=3)
                    except subprocess.TimeoutExpired:shell.kill();shell.wait()
                    log.seek(0);logs=log.read();print(logs)
                if any(s in logs for s in ('ReferenceError:','TypeError:','Unable to assign','Binding loop','Failed to load')):raise RuntimeError('edge runtime warning')
    print('native edge layer gate passed')
if __name__=='__main__':main()
