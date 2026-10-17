"""Run only with disposable GTK editor focused; drives real QML handlers/DBus.

Does not emulate a physical fingertip. Production overlay must be disabled.
"""
from pathlib import Path
import json, os, shutil, subprocess, tempfile, time

root=Path(__file__).resolve().parents[1]
active=json.loads(subprocess.check_output(['hyprctl','activewindow','-j']))
assert active['class']=='touch_editor.py', 'Refuse to test against a user application'
# Disposable editor starts empty; no keyboard injection is needed.
with tempfile.TemporaryDirectory(prefix='omt-ui-test-') as tmp:
    tmp=Path(tmp)
    for f in (root/'qml').glob('*.qml'):shutil.copy2(f,tmp/f.name)
    (tmp/'Commons').symlink_to('/usr/share/omarchy/shell/Commons',target_is_directory=True)
    (tmp/'Ui').symlink_to('/usr/share/omarchy/shell/Ui',target_is_directory=True)
    qml=(root/'qml/TouchIme.qml').read_text()
    qml=qml.replace('Quickshell.env("HOME") + "/.local/share/pcadmin-touch-ime/rime"', json.dumps(str(tmp/'rime')))
    qml=qml.replace('target: "omtInput"', '''target: "omtTest"
        function testState(): string { return JSON.stringify(root.state) }
        function drawSample(): bool {
            handPad.strokes=[[{x:35,y:40},{x:35,y:105}],[{x:35,y:40},{x:125,y:40},{x:125,y:105}],[{x:35,y:105},{x:125,y:105}],[{x:80,y:15},{x:80,y:140}]];
            handPad.inkChanged();return true
        }
        function tap(label: string): bool {
            function find(item) {
                if (item.label === label && item.enabled && item.visible && item.triggered) { item.triggered(); return true }
                if (!item.children) return false
                for (var i=0;i<item.children.length;i++) if(find(item.children[i])) return true
                return false
            }
            return find(panel.contentItem)
        }
''')
    (tmp/'TouchIme.qml').write_text(qml)
    file=tmp/'shell.qml';file.write_text('import Quickshell\nShellRoot { TouchIme {} }\n')
    log=open(tmp/'qml.log','w+')
    process=subprocess.Popen(['quickshell','-p',str(file),'--no-color'],stdout=log,stderr=log)
    def ipc(method,*args):
        return subprocess.check_output(['quickshell','ipc','--pid',str(process.pid),'call','omtTest',method,*args],stderr=subprocess.DEVNULL,text=True).strip()
    def wait(predicate):
        end=time.monotonic()+15
        while time.monotonic()<end:
            try:
                state=json.loads(ipc('testState'))
                if predicate(state): return state
            except (subprocess.CalledProcessError,json.JSONDecodeError): pass
            time.sleep(.05)
        log.seek(0);raise AssertionError(log.read())
    def tap(label): assert ipc('tap',label)=='true', 'Button unavailable: '+label
    try:
        wait(lambda s:s['focused'] and not s['visible'])
        ipc('toggle')
        wait(lambda s:s['visible'])
        for label in ['MNO','GHI','GHI','ABC','MNO']: tap(label)
        wait(lambda s:s['preedit'].replace(' ','')=='64426')
        tap('下一页');wait(lambda s:s['page']==1)
        tap('上一页');wait(lambda s:s['page']==0)
        tap('你好');wait(lambda s:not s['preedit'])
        end=time.monotonic()+2
        while time.monotonic()<end and (not Path('/tmp/omt-test-editor-result').exists() or Path('/tmp/omt-test-editor-result').read_text()!='你好'):time.sleep(.02)
        assert Path('/tmp/omt-test-editor-result').read_text()=='你好'
        tap('英文');wait(lambda s:s['mode']=='abc')
        for label in 'abc123@x.com':tap(label)
        end=time.monotonic()+2
        while time.monotonic()<end and Path('/tmp/omt-test-editor-result').read_text()!='你好abc123@x.com':time.sleep(.02)
        assert Path('/tmp/omt-test-editor-result').read_text()=='你好abc123@x.com'
        tap('全选');tap('复制');tap('▶');tap('粘贴')
        end=time.monotonic()+2
        while time.monotonic()<end and Path('/tmp/omt-test-editor-result').read_text()!='你好abc123@x.com你好abc123@x.com':time.sleep(.02)
        assert Path('/tmp/omt-test-editor-result').read_text()=='你好abc123@x.com你好abc123@x.com'
        tap('手写');wait(lambda s:s['mode']=='handwriting')
        assert ipc('drawSample')=='true'
        wait(lambda s:'中' in s['candidates'])
        tap('中');wait(lambda s:not s['candidates'])
        end=time.monotonic()+2
        while time.monotonic()<end and Path('/tmp/omt-test-editor-result').read_text()!='你好abc123@x.com你好abc123@x.com中':time.sleep(.02)
        assert Path('/tmp/omt-test-editor-result').read_text()=='你好abc123@x.com你好abc123@x.com中'
        tap('收起 ↓');wait(lambda s:not s['visible'])
        time.sleep(.2)
        layers=json.loads(subprocess.check_output(['hyprctl','layers','-j']))
        assert 'pcadmin-touch-ime' not in json.dumps(layers)
        print('PASS actual QML handlers → backend → native Fcitx → GTK: T9, pages, candidate commit, hide releases surface')
    finally:
        process.terminate()
        try:process.wait(timeout=4)
        except subprocess.TimeoutExpired:process.kill();process.wait()
