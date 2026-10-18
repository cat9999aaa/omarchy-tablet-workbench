"""Actual product UI bodies with pinned official styles and synthetic devices."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from render_support import compositor,run_checked,verify_official,verify_outputs
from surface_sources import write_sources,ROOT


def cases():
    rows=[]
    for surface,mode in [('control','tablet'),('control','desktop'),('navigation','tablet'),('network','tablet'),('power','tablet')]:
        for width in (320,480,640):
            for orientation in ('landscape','portrait'):
                for scale in (1,1.25,1.5):
                    for state in ('unknown','error','stale','unavailable','observed'):
                        for high in (False,True):
                            height=round(width*(.75 if orientation=='landscape' else 1.5))
                            name=f'{surface}-{mode}-{width}-{orientation}-{scale}-{state}-{int(high)}'
                            rows.append(dict(name=name,surface=surface,mode=mode,width=width,height=height,scale=scale,state=state,high=high))
    return rows


def main(output,official,surface=None):
    if os.environ.get('C1_ISOLATED_TEST')!='1':raise RuntimeError('isolated-namespace-required')
    hashes=verify_official(official)
    for name in ['Commons/Border.qml','Ui/Button.qml','Ui/BorderSurface.qml','Ui/BorderOverlay.qml','Ui/PanelSeparator.qml','Ui/PanelSectionHeader.qml']:
        if name not in hashes:raise RuntimeError('missing-official-ui:'+name)
    output.mkdir(parents=True,exist_ok=False);rows=[r for r in cases() if surface is None or r["surface"]==surface]
    with tempfile.TemporaryDirectory(prefix='c1-surfaces-') as temp:
        work=Path(temp);home=work/'home';home.mkdir();write_sources(work)
        for folder in ('Commons','Ui'):shutil.copytree(official/folder,work/folder)
        (work/'Commons/qmldir').write_text('module qs.Commons\n'+''.join('singleton '+n+' 1.0 '+n+'.qml\n' for n in ['Color','Style','Util','Border']))
        (work/'Ui/qmldir').write_text('module qs.Ui\n'+''.join(n+' 1.0 '+n+'.qml\n' for n in ['Button','BorderSurface','BorderOverlay','PanelSeparator','PanelSectionHeader']))
        (work/'Cases.js').write_text('var rows = '+json.dumps(rows)+';\n')
        fixture=work/'WorkbenchMatrix.qml';shutil.copy2(Path(__file__).parent/'fixtures/WorkbenchMatrix.qml',fixture)
        with compositor(work) as env:
            env.update(HOME=str(home),C1_OUTPUT=str(output))
            log=run_checked(['qs','-p',str(fixture)],env,240);(output/'render.log').write_text(log)
        lines=[line.split('C1_RESULT:',1)[1] for line in log.splitlines() if 'C1_RESULT:' in line]
        if len(lines)!=1 or any(marker in log for marker in ['C1_FAIL:','ReferenceError:','TypeError:','Unable to assign','Binding loop detected']):raise RuntimeError('render-result-missing: '+log[-5000:])
        receipt=json.loads(lines[0]);receipt['cases']=rows;receipt['source_sha256']=hashes
        for folder in ['modules/control-center','modules/window-controls','modules/network-center','modules/battery-manager/panel','modules/workbench-ui','scripts/themes']:
            for p in (ROOT/folder).rglob('*'):
                if p.is_file() and p.suffix in ('.qml','.js','.py'):receipt['source_sha256'][str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
        receipt['coverage']='targeted' if surface else 'full';receipt['kind']='actual-content-isolated-render';receipt['host_device_io']='synthetic-boundaries';receipt['physical_acceptance']='not-run'
        (output/'results.json').write_text(json.dumps(receipt,indent=2)+'\n')
        verify_outputs(output,[r['name'] for r in rows],{r['name']+'.png':(r['width'],r['height']) for r in rows})
    print('targeted UI matrix passed:' if surface else 'full actual UI matrix passed:',len(rows))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--official-root',type=Path,default=Path('/official'));parser.add_argument('--surface',choices=['control','navigation','network','power']);args=parser.parse_args();main(args.output.absolute(),args.official_root,args.surface)
