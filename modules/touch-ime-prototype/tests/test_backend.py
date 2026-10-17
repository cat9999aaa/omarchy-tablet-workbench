"""Private session bus integration; never writes to a real application."""
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import time
import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

DBusGMainLoop(set_as_default=True)
bus = dbus.SessionBus()
name = dbus.service.BusName('org.fcitx.Fcitx5', bus)

class Bridge(dbus.service.Object):
    def __init__(self):
        super().__init__(bus, '/omt')
        self.generation = 7
        self.context = 7
        self.focused = True
        self.sensitive = False
        self.commits = []
        self.keys = []

    @dbus.service.method('org.pcadmin.TouchIme1', in_signature='', out_signature='s')
    def State(self):
        return json.dumps(dict(generation=self.generation, context=self.context, focused=self.focused,
                               sensitive=self.sensitive, noKeyboard=False))

    @dbus.service.method('org.pcadmin.TouchIme1', in_signature='us', out_signature='b')
    def Commit(self, generation, text):
        if not self.focused or generation != self.generation:
            return False
        self.commits.append(str(text))
        return True

    @dbus.service.method('org.pcadmin.TouchIme1', in_signature='us', out_signature='b')
    def Key(self, generation, key):
        if not self.focused or generation != self.generation:
            return False
        self.keys.append(str(key))
        return True

bridge = Bridge()
loop = GLib.MainLoop()
threading.Thread(target=loop.run, daemon=True).start()
root = Path(__file__).resolve().parents[1]
states = queue.Queue()
with tempfile.TemporaryDirectory(prefix='omt-backend-test-') as tmp:
    binaries=Path(tmp)/'bin'; binaries.mkdir()
    (binaries/'pw-record').write_text("""#!/usr/bin/python3
import signal,time,os,pathlib
signal.signal(signal.SIGTERM, signal.SIG_IGN if pathlib.Path(os.environ['XDG_RUNTIME_DIR']+'/ignore-term').exists() else lambda *a: exit(0))
while True: time.sleep(.05)
""")
    (binaries/'voxtype').write_text('#!/bin/sh\nprintf "你好测试\\n"\n')
    for f in binaries.iterdir(): f.chmod(0o700)
    env=dict(os.environ, PATH=str(binaries)+':'+os.environ['PATH'], XDG_RUNTIME_DIR=tmp)
    process = subprocess.Popen([str(root/'build/omt-backend'), str(root/'rime'), tmp],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, text=True, env=env)
    def reader():
        for line in process.stdout:
            states.put(json.loads(line))
    threading.Thread(target=reader, daemon=True).start()
    def wait(predicate):
        end = time.monotonic()+20
        while time.monotonic()<end:
            state = states.get(timeout=max(.01, end-time.monotonic()))
            if os.getenv('OMT_TEST_TRACE'): print(state, flush=True)
            if predicate(state):
                return state
        raise AssertionError('Expected state not received')
    def action(op, **kw):
        process.stdin.write(json.dumps(dict(op=op, generation=bridge.generation, **kw))+'\n')
        process.stdin.flush()
    try:
        initial=wait(lambda s: s['focused'] and not s['visible'])
        assert initial['learning'] is True
        action('learning',enabled=False);wait(lambda s:s['learning'] is False)
        action('learning',enabled=True);wait(lambda s:s['learning'] is True)
        action('toggle'); wait(lambda s: s['visible'])
        for digit in '64426': action('key', key=digit)
        state = wait(lambda s: '你好' in s['candidates'] and len(s['preedit'].replace(' ', '')) == 5)
        action('choose', index=state['candidates'].index('你好'), preedit='stale', page=state['page'])
        wait(lambda s: bool(s['error']))
        assert not bridge.commits, 'Stale candidate list must not commit'
        action('choose', index=state['candidates'].index('你好'), preedit=state['preedit'], page=state['page'])
        wait(lambda s: not s['preedit'])
        assert bridge.commits == ['你好'], repr(bridge.commits)
        action('key',key='Control+c')
        time.sleep(.1);assert bridge.keys[-1:] == ['Control+c'], 'Copy must reach focused application'
        action('voice'); wait(lambda s: s['voicePhase']=='recording')
        time.sleep(.2)
        action('voice'); wait(lambda s: s['voiceText']=='你好测试')
        assert bridge.commits == ['你好'], 'Voice must wait for explicit commit'
        action('voiceEdit'); wait(lambda s: s.get('editingVoice'))
        action('key', key='BackSpace'); wait(lambda s: s['voiceText']=='你好测')
        action('mode', mode='abc'); action('key', key='a')
        wait(lambda s: s['voiceText']=='你好测a')
        action('voiceCommit'); wait(lambda s: not s['voiceText'])
        assert bridge.commits == ['你好', '你好测a']
        Path(tmp+'/ignore-term').touch()
        action('voice'); wait(lambda s: s['voicePhase']=='recording')
        time.sleep(.2)
        action('voice'); wait(lambda s: s['voicePhase']=='idle' and bool(s['error']))
        assert not list(Path(tmp).glob('omt-audio-*'))
        action('hide'); wait(lambda s: not s['visible'])
        time.sleep(.3)
        assert states.empty(), 'Manual hide must persist on unchanged focus'
        bridge.generation += 1
        wait(lambda s: s['generation']==8 and not s['visible'])
        bridge.context += 1; bridge.generation += 1
        wait(lambda s: s['generation']==9 and not s['visible'])
        action('toggle'); wait(lambda s: s['visible'])
        action('toggle'); wait(lambda s: not s['visible'])
        bridge.context += 1; bridge.generation += 1
        wait(lambda s: s['generation']==10 and not s['visible'])
        action('toggle'); wait(lambda s: s['visible'])
        process.stdin.write(json.dumps(dict(op='text', generation=7, text='stale'))+'\n'); process.stdin.flush()
        wait(lambda s: bool(s['error']))
        assert bridge.commits == ['你好', '你好测a'], repr(bridge.commits)
        # A phrase draft must not type into the actual application.
        before=list(bridge.commits)
        action('phraseStart');wait(lambda s:s['editingPhrase'])
        action('mode',mode='abc')
        for char in 'demo123':action('key',key=char)
        wait(lambda s:s['phraseDraft']=='demo123')
        assert bridge.commits==before
        action('phraseSave');wait(lambda s:not s['editingPhrase'] and 'demo123' in s['phrases'])
        assert bridge.commits==before
        action('phraseDelete',text='demo123');wait(lambda s:'demo123' not in s['phrases'])
        # Real offline handwriting, revision guard, and clear while a request is pending.
        action('mode',mode='handwriting');wait(lambda s:s['mode']=='handwriting')
        strokes=[[{'x':35,'y':40},{'x':35,'y':105}],[{'x':35,'y':40},{'x':125,'y':40},{'x':125,'y':105}],[{'x':35,'y':105},{'x':125,'y':105}],[{'x':80,'y':15},{'x':80,'y':140}]]
        action('handwriting',strokes=strokes,width=160,height=155,revision=100)
        hw=wait(lambda s:'中' in s['candidates'])
        before=list(bridge.commits)
        action('choose',index=0,revision=99);wait(lambda s:bool(s['error']))
        assert bridge.commits==before
        action('choose',index=hw['candidates'].index('中'),revision=100)
        wait(lambda s:not s['candidates']);assert bridge.commits[-1]=='中'
        action('handwriting',strokes=strokes,width=160,height=155,revision=101)
        action('handwritingClear',revision=102)
        wait(lambda s:s['handwritingRevision']==102 and not s['candidates'])
        time.sleep(.1)
        action('choose',index=0,revision=101);wait(lambda s:bool(s['error']))
        assert bridge.commits==before+['中']
        action('toggle');wait(lambda s:not s['visible'])
        assert subprocess.run(['pgrep','-P',str(process.pid),'-x','omt-handwriting'],stdout=subprocess.DEVNULL).returncode!=0,'P1 hide must release handwriting worker'
        action('toggle');wait(lambda s:s['visible'])
        action('mode',mode='abc');wait(lambda s:s['mode']=='abc')
        before=list(bridge.commits)
        for char in 'abc123@x.com':action('text',text=char)
        action('dictionaryBackup');wait(lambda s:'词库已备份' in s['notice'] or '词库备份未完成' in s['notice'])
        assert ''.join(bridge.commits[len(before):])=='abc123@x.com'
        bridge.generation += 1
        wait(lambda s:s.get('generation')==bridge.generation)
        action('mode',mode='pinyin');wait(lambda s:s.get('mode')=='pinyin')
        for char in 'nihao':action('key',key=char)
        wait(lambda s:'你好' in s['candidates'])
        action('clear');wait(lambda s:not s['preedit'])
        bridge.generation += 1; bridge.sensitive=True
        wait(lambda s: s['sensitive'] and s['mode']=='abc')
        action('mode', mode='t9'); action('mode',mode='handwriting'); action('voice'); action('key', key='a')
        deadline=time.monotonic()+3
        while bridge.commits[-1]!='a' and time.monotonic()<deadline: time.sleep(.01)
        assert bridge.commits[-1]=='a'
        assert bridge.sensitive
        bridge.generation += 1; bridge.focused=False
        wait(lambda s: not s['focused'] and not s['visible'])
        action('text', text='unfocused'); wait(lambda s: bool(s['error']))
        assert 'unfocused' not in bridge.commits
        print('PASS backend: T9 commit, hide, focus change, stale requests, sensitive fields, focus loss')
    finally:
        process.stdin.close()
        process.wait(timeout=5)
        loop.quit()
