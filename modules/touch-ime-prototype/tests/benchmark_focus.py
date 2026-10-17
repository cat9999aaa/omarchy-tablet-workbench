"""Synthetic focus transport benchmark, run only under a PRIVATE dbus-run-session.

Usage: dbus-run-session -- python benchmark_focus.py /path/to/omt-backend /path/to/rime
Measures notification-to-backend JSON, not touch latency, power or real apps.
"""
import json, os, queue, subprocess, sys, tempfile, threading, time
from pathlib import Path
import dbus, dbus.service
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib
DBusGMainLoop(set_as_default=True)
bus=dbus.SessionBus();name=dbus.service.BusName('org.fcitx.Fcitx5',bus)
class Bridge(dbus.service.Object):
    generation=1;calls=0
    @dbus.service.method('org.pcadmin.TouchIme1',out_signature='s')
    def State(self):
        self.calls+=1;return self.snapshot()
    def snapshot(self):
        return json.dumps(dict(protocol=2,generation=self.generation,context=self.generation,focused=True,sensitive=False,noKeyboard=False))
    @dbus.service.signal('org.pcadmin.TouchIme1',signature='s')
    def StateChanged(self,value):pass
bridge=Bridge(bus,'/omt');loop=GLib.MainLoop()
threading.Thread(target=loop.run,daemon=True).start()
with tempfile.TemporaryDirectory(prefix='omt-bench-') as tmp:
    p=subprocess.Popen([sys.argv[1],sys.argv[2],tmp],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True)
    q=queue.Queue()
    def read():
        for line in p.stdout:q.put((time.perf_counter(),json.loads(line)))
    threading.Thread(target=read,daemon=True).start()
    def focused(timeout=10):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            event=q.get(timeout=max(.01,end-time.monotonic()))
            if event[1]['focused']:return event
        raise RuntimeError('No focused state')
    def proc():
        stat=Path(f'/proc/{p.pid}/stat').read_text().split(') ',1)[1].split()
        status=dict(line.split(':',1) for line in Path(f'/proc/{p.pid}/status').read_text().splitlines() if ':' in line)
        return dict(ticks=int(stat[11])+int(stat[12]),voluntary=int(status['voluntary_ctxt_switches']),rss_kib=int(status['VmRSS'].split()[0]))
    try:
        focused();time.sleep(.2)
        calls=bridge.calls;start=proc();t=time.perf_counter();time.sleep(3);elapsed=time.perf_counter()-t;end=proc()
        idle=dict(seconds=elapsed,state_calls=bridge.calls-calls,cpu_seconds=(end['ticks']-start['ticks'])/os.sysconf('SC_CLK_TCK'),main_thread_voluntary_switches=end['voluntary']-start['voluntary'],rss_kib=end['rss_kib'])
        samples=[]
        for i in range(40):
            time.sleep(.013+(i*37%101)/1000)
            while not q.empty():q.get_nowait()
            bridge.generation+=1;sent=time.perf_counter();bridge.StateChanged(bridge.snapshot())
            received,_=focused();samples.append((received-sent)*1000)
        ordered=sorted(samples)
        print(json.dumps(dict(kind='synthetic_private_bus_focus',idle=idle,samples=40,latency_ms=dict(p50=(ordered[19]+ordered[20])/2,p95=ordered[37],maximum=ordered[-1]),limitations='No physical touch, battery, candidate or real-app latency measurement'),indent=2))
    finally:
        p.stdin.close();p.wait(timeout=5);loop.quit()
