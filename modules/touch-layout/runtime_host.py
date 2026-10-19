"""Fixed, bounded official read/reload operations; no arbitrary commands."""
import base64
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import tempfile
import time
import tomllib
from bar_compat import NEW, restored
from layout_probe import measure_layout

def command(args):
    result=subprocess.run(args,capture_output=True,text=True,timeout=4)
    if result.returncode or len(result.stdout)>262144:raise ValueError('host-read-failed')
    return result.stdout.strip()

def sha(data):return hashlib.sha256(data).hexdigest()

class Host:
    def __init__(self,home):self.home=Path(home);self.visible_ids=set()
    def context(self):
        if command(['omarchy-shell','lock','isLocked'])!='false':raise ValueError('locked-or-unknown')
        config=json.loads(command(['omarchy-shell','shell','listShellConfig']))
        bar=config.get('bar',{});bar_id=bar.get('id','')
        if not re.fullmatch(r'[A-Za-z0-9_-]+\.bar',bar_id):raise ValueError('unsupported-bar')
        monitors=json.loads(command(['hyprctl','monitors','-j']))
        # debugBarGeometry has no output identifier in this host release.
        if len(monitors)!=1:raise ValueError('ambiguous-bar-output')
        monitor=monitors[0];scale=monitor.get('scale')
        if type(scale) not in (int,float) or not math.isfinite(scale) or scale<=0:raise ValueError('invalid-output')
        width,height=monitor['width'],monitor['height']
        if monitor.get('transform',0)%2:width,height=height,width
        viewport=[round(width/scale),round(height/scale)]
        theme=(self.home/'.local/state/omarchy/current/theme.name').read_text().strip()
        override=self.home/'.config/omarchy/shell.toml'
        raw=override.read_bytes() if override.exists() else b''
        values=tomllib.loads(raw.decode())
        if values.get('bar') or values.get('font'):raise ValueError('user-dimension-overrides')
        return {'theme':theme,'position':bar.get('position'),'output':monitor['name'],'viewport':viewport,'bar_id':bar_id,'layout_hash':sha(json.dumps(bar,sort_keys=True).encode()),'override_hash':sha(raw),'palette_hash':sha((self.home/'.local/state/omarchy/current/theme/colors.toml').read_bytes())}
    def geometry(self):
        rows=json.loads(command(['omarchy-shell','shell','debugBarGeometry']))
        if not isinstance(rows,list) or not 1<=len(rows)<=64:raise ValueError('invalid-geometry')
        for row in rows:
            if not isinstance(row,dict) or not isinstance(row.get('id'),str):raise ValueError('invalid-geometry')
            for key in ('x','y','width','height'):
                if type(row.get(key)) not in (int,float) or not math.isfinite(row[key]):raise ValueError('invalid-geometry')
        return rows
    def measure(self,profile,theme_text):
        context=self.context();rows=self.geometry()
        visible=[r for r in rows if r.get('visible') is True and r.get('itemVisible') is True]
        self.visible_ids={r['id'] for r in visible}
        if len(self.visible_ids)!=len(visible) or 'pcadmin.control-center' not in self.visible_ids:raise ValueError('missing-or-duplicate-entry')
        config=json.loads(command(['omarchy-shell','shell','listShellConfig']))['bar']
        tokens=tomllib.loads(theme_text);font=tokens.get('font',{}).get('base-size',12)/12
        if tokens.get('bar',{}).get('scale-with-font',True) is not True:raise ValueError('unsupported-bar-scaling')
        layout={k:[] for k in ('left','center','right')}
        # Preserve actual order, with conservative widths for external providers.
        for row in sorted(visible,key=lambda r:r['x']):
            if row.get('section') not in layout:raise ValueError('unknown-region')
            layout[row['section']].append({'id':row['id'],'kind':'fixed','width':max(row['width']/font,48 if profile=='touch' else row['width']/font),'primary':row['id']=='pcadmin.control-center'})
        pins=json.loads(Path(__file__).with_name('host-source.json').read_text())
        with tempfile.TemporaryDirectory(prefix='dashen-bar-probe-') as folder:
            root=Path(folder)
            for rel,expected in pins.items():
                source=self.home/'.config/omarchy/plugins'/context['bar_id']/Path(rel).name if rel.startswith('Touch/') else Path('/usr/share/omarchy/shell')/rel
                data=source.read_bytes()
                if rel=='Touch/Bar.qml':
                    text=data.decode()
                    if NEW not in text:raise ValueError('bar-compat-not-installed')
                    data=restored(text).encode()
                if sha(data)!=expected:raise ValueError('unsupported-host-source:'+rel)
                target=root/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
            (root/'hashes.json').write_text(json.dumps(pins))
            result=measure_layout({'centerAnchor':config.get('centerAnchor',''),'layout':layout},profile,context['viewport'],font,source_root=root,theme_text=theme_text)
        if self.context()!=context:raise ValueError('context-changed')
        return result
    def reload(self):
        theme=self.home/'.local/state/omarchy/current/theme'
        try:
            payloads=[base64.b64encode((theme/name).read_bytes()).decode() for name in ('colors.toml','shell.toml')]
            return command(['omarchy-shell','shell','applyTheme',*payloads])=='ok'
        except (OSError,ValueError,subprocess.SubprocessError):return False
    def verify(self,profile):
        # One bounded settle for the existing event-driven theme refresh.
        time.sleep(.25)
        context=self.context();rows=[r for r in self.geometry() if r.get('visible') is True and r.get('itemVisible') is True]
        if {r['id'] for r in rows}!=self.visible_ids:return False
        rows.sort(key=lambda r:r['x'])
        if any(r['x']<0 or r['x']+r['width']>context['viewport'][0] or r['height']<=0 for r in rows):return False
        if any(a['x']+a['width']>b['x']+1 for a,b in zip(rows,rows[1:])):return False
        if profile=='touch' and any(r['width']<48 or r['height']<48 for r in rows):return False
        return True
