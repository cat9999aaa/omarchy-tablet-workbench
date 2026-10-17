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
    def __init__(self, connection=bus):
        super().__init__(connection, '/omt')
        self.generation = 7
        self.context = 7
        self.focused = True
        self.sensitive = False
        self.commits = []
        self.keys = []
        self.state_calls = 0
        self.state_delay = 0
        self.after_select = None

    def snapshot(self):
        return json.dumps(dict(protocol=2, generation=self.generation, context=self.context, focused=self.focused,
                               sensitive=self.sensitive, noKeyboard=False))

    @dbus.service.method('org.pcadmin.TouchIme1', in_signature='', out_signature='s', async_callbacks=('reply','error'))
    def State(self, reply, error):
        self.state_calls += 1
        snapshot=self.snapshot()
        if self.state_delay:
            def deliver(): reply(snapshot);return False
            GLib.timeout_add(self.state_delay,deliver)
        else: reply(snapshot)

    @dbus.service.signal('org.pcadmin.TouchIme1', signature='s')
    def StateChanged(self, value):
        pass

    def notify(self):
        self.StateChanged(self.snapshot())

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
        if key=="Control+a" and self.after_select:self.after_select()
        return True

bridge = Bridge()
loop = GLib.MainLoop()
threading.Thread(target=loop.run, daemon=True).start()
root = Path(__file__).resolve().parents[1]
states = queue.Queue()
latest_generation = 0
with tempfile.TemporaryDirectory(prefix='omt-backend-test-') as tmp:
    binaries=Path(tmp)/'bin'; binaries.mkdir()
    (binaries/'pw-record').write_text("""#!/usr/bin/python3
import signal,time,os,pathlib
signal.signal(signal.SIGTERM, signal.SIG_IGN if pathlib.Path(os.environ['XDG_RUNTIME_DIR']+'/ignore-term').exists() else lambda *a: exit(0))
while True: time.sleep(.05)
""")
    (binaries/'voxtype').write_text('#!/usr/bin/python3\nimport sys\nprint(\'Loading audio file: "/tmp/speech.wav"\\nAudio format: 16000 Hz, 1 channel(s), Int\\nProcessing 32000 samples (2.00s)...\\n\\n你好测试\')\n')
    for f in binaries.iterdir(): f.chmod(0o700)
    env=dict(os.environ, PATH=str(binaries)+':'+os.environ['PATH'], XDG_RUNTIME_DIR=tmp)
    process = subprocess.Popen([str(root/'build/omt-backend'), str(root/'rime'), tmp],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, text=True, env=env)
    def reader():
        global latest_generation
        for line in process.stdout:
            state=json.loads(line);latest_generation=state['generation'];states.put(state)
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
        process.stdin.write(json.dumps(dict(op=op, generation=latest_generation, **kw))+'\n')
        process.stdin.flush()
    try:
        initial=wait(lambda s: s['focused'] and not s['visible'])
        assert initial['learning'] is True
        assert initial['phrases']==[], 'Do not seed unwanted canned greetings'
        stale_generation=initial['generation']
        calls=bridge.state_calls;time.sleep(.65)
        assert bridge.state_calls==calls, 'Idle backend must not periodically query State'
        assert states.empty(), 'Stable idle must not publish redundant state'
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
        keys_before=list(bridge.keys)
        action('clearField',confirmed=False);wait(lambda s:bool(s['error']))
        assert bridge.keys==keys_before
        action('clearField',confirmed=True);wait(lambda s:not s['error'])
        assert bridge.keys[-2:]==['Control+a','BackSpace']
        for transition in ['generation','sensitive','focus','owner']:
            keys_before=list(bridge.keys)
            def change():
                if transition=='generation':bridge.generation+=1
                elif transition=='sensitive':bridge.sensitive=True
                elif transition=='owner':bus.release_name('org.fcitx.Fcitx5')
                else:bridge.focused=False
            bridge.after_select=change
            action('clearField',confirmed=True);wait(lambda s:bool(s['error']))
            assert bridge.keys==keys_before+['Control+a'],'Field changed after select-all: deletion must be cancelled'
            before_restore=latest_generation
            if transition=='owner':bus.request_name('org.fcitx.Fcitx5')
            bridge.after_select=None;bridge.sensitive=False;bridge.focused=True;bridge.generation+=1;bridge.notify()
            restored=wait(lambda s:s['generation']>before_restore and s['focused'] and not s['sensitive'])
            if not restored['visible']:
                action('show');wait(lambda s:s['visible'])

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
        # Holding delete in a voice draft must never fall through to the application.
        action('voice');wait(lambda s:s['voicePhase']=='recording');time.sleep(.2)
        action('voice');wait(lambda s:s['voiceText']=='你好测试')
        keys_before=list(bridge.keys)
        for _ in range(8):action('key',key='BackSpace',localScope=True)
        time.sleep(.1)
        assert bridge.keys==keys_before,'Local voice deletion leaked to the application'
        wait(lambda s:not s['voiceText'])
        action('clear');wait(lambda s:not s['editingVoice'])
        Path(tmp+'/ignore-term').touch()
        action('voice'); wait(lambda s: s['voicePhase']=='recording')
        time.sleep(.2)
        action('voice'); wait(lambda s: s['voicePhase']=='idle' and bool(s['error']))
        assert not list(Path(tmp).glob('omt-audio-*'))
        action('hide'); wait(lambda s: not s['visible'])
        time.sleep(.3)
        assert states.empty(), 'Manual hide must persist on unchanged focus'
        bridge.generation += 1;bridge.notify()
        wait(lambda s: s['generation']>stale_generation and not s['visible'])
        bridge.context += 1; bridge.generation += 1;bridge.notify()
        wait(lambda s: not s['visible'])
        action('toggle'); wait(lambda s: s['visible'])
        action('toggle'); wait(lambda s: not s['visible'])
        bridge.context += 1; bridge.generation += 1;bridge.notify()
        wait(lambda s: not s['visible'])
        action('toggle'); wait(lambda s: s['visible'])
        process.stdin.write(json.dumps(dict(op='text', generation=stale_generation, text='stale'))+'\n'); process.stdin.flush()
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
        keys_before=list(bridge.keys)
        action('key',key='BackSpace',localScope=True);time.sleep(.1)
        assert bridge.keys==keys_before,'Local handwriting deletion leaked to the application'

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
        bridge.generation += 1;bridge.notify()
        wait(lambda s:not s['preedit'] and s['mode']=='t9')
        action('mode',mode='pinyin');wait(lambda s:s.get('mode')=='pinyin')
        for char in 'nihao':action('key',key=char)
        wait(lambda s:'你好' in s['candidates'])
        action('clear');wait(lambda s:not s['preedit'])
        bridge.generation += 1; bridge.sensitive=True;bridge.notify()
        wait(lambda s: s['sensitive'] and s['mode']=='abc')
        action('mode', mode='t9'); action('mode',mode='handwriting'); action('voice'); action('key', key='a')
        deadline=time.monotonic()+3
        while bridge.commits[-1]!='a' and time.monotonic()<deadline: time.sleep(.01)
        assert bridge.commits[-1]=='a'
        assert bridge.sensitive
        bridge.generation += 1; bridge.focused=False;bridge.notify()
        wait(lambda s: not s['focused'] and not s['visible'])
        action('text', text='unfocused'); wait(lambda s: bool(s['error']))
        assert 'unfocused' not in bridge.commits
        # A restarted bridge may reuse its old counter; UI generations must not.
        before_restart=latest_generation
        bus.release_name('org.fcitx.Fcitx5')
        wait(lambda s: not s['focused'] and bool(s['error']))
        old_bridge=bridge
        new_bus=dbus.SessionBus(private=True)
        bridge=Bridge(new_bus);bridge.focused=False;bridge.state_delay=300
        new_bus.request_name('org.fcitx.Fcitx5')
        deadline=time.monotonic()+3
        while bridge.state_calls==0 and time.monotonic()<deadline:time.sleep(.005)
        assert bridge.state_calls>0, 'Replacement owner must receive startup query'
        bridge.generation=8;bridge.focused=True;bridge.notify()
        restarted=wait(lambda s:s['focused'] and not s['error'])
        assert restarted['generation']>before_restart
        time.sleep(.4)
        assert states.empty(), 'Delayed initial snapshot must not overwrite newer signal'
        old_bridge.generation=999;old_bridge.notify()
        time.sleep(.15)
        assert states.empty(), 'Old unique owner notifications must be ignored'
        process.stdin.write(json.dumps(dict(op='text',generation=stale_generation,text='stale-after-restart'))+'\n');process.stdin.flush()
        wait(lambda s:bool(s['error']))
        assert 'stale-after-restart' not in bridge.commits
        calls=bridge.state_calls;time.sleep(.65)
        assert bridge.state_calls==calls, 'Reconnect must return to event-only idle'
        print('PASS backend: T9 commit, hide, focus change, stale requests, sensitive fields, focus loss')
    finally:
        process.stdin.close()
        process.wait(timeout=5)
        loop.quit()
