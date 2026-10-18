"""Exercise pinned official theme commands and QML parser in an isolated HOME."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from check_theme import validate_theme
from render_support import compositor, run_checked, verify_official, verify_outputs

ROOT=Path(__file__).resolve().parents[2]
CASES=['theme-command','background-preserved','command-restored','user-color-override','user-font-override','palette-loaded','override-removal','theme-surface','old-theme-fallback','theme-restored','window-survived','capture-requested','screenshot-saved']


def main(output, official):
    if os.environ.get('C1_ISOLATED_TEST')!='1':raise RuntimeError('isolated-namespace-required')
    hashes=verify_official(official)
    theme=ROOT/'themes/dashen-overdrive'
    errors=validate_theme(theme)
    if errors:raise RuntimeError('invalid-theme:'+','.join(errors))
    output.mkdir(parents=True,exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='c1-theme-') as temp:
        work=Path(temp);home=work/'home';home.mkdir()
        themes=home/'.config/omarchy/themes';themes.mkdir(parents=True)
        shutil.copytree(theme,themes/'dashen-overdrive')
        old=themes/'c1-previous';old.mkdir();(old/'colors.toml').write_text('mode="dark"\nbackground="#000000"\nforeground="#ffffff"\naccent="#00ffff"\n')
        old_background=home/'previous-background';old_background.write_bytes(b'synthetic-background-marker')
        current=home/'.local/state/omarchy/current';current.mkdir(parents=True)
        (current/'background').symlink_to(old_background)
        user=home/'.config/omarchy/shell.toml';user.write_text('[font]\nbase-size=18\n[popups]\nbackground="#182028"\n')
        module=work/'Official';module.mkdir()
        for name in ['Color.qml','Style.qml','Util.qml','BorderGeometry.js']:shutil.copy2(official/'Commons'/name,module/name)
        (module/'qmldir').write_text('module qs.Commons\nsingleton Color 1.0 Color.qml\nsingleton Style 1.0 Style.qml\nsingleton Util 1.0 Util.qml\n')
        fixture=work/'ShellTheme.qml';shutil.copy2(Path(__file__).parent/'fixtures/ShellTheme.qml',fixture)
        with compositor(work) as env:
            env.update(HOME=str(home),OMARCHY_PATH=str(official),OMARCHY_THEME_HEADLESS='1',OMARCHY_THEME_SKIP_BACKGROUND='1',PATH=str(official/'bin')+':'+env['PATH'],C1_OUTPUT=str(output),C1_PALETTE=str(theme/'colors.toml'),C1_SHELL=str(theme/'shell.toml'))
            for name in ['dashen-overdrive','c1-previous','dashen-overdrive']:
                run_checked([str(official/'bin/omarchy-theme-set'),name],env,30)
                if (current/'theme.name').read_text().strip()!=name:raise RuntimeError('theme-command-did-not-switch')
            if (current/'theme/colors.toml').read_bytes()!=(theme/'colors.toml').read_bytes():raise RuntimeError('theme-restore-mismatch')
            if (current/'background').resolve()!=old_background:raise RuntimeError('background-changed')
            log=run_checked(['qs','-p',str(fixture)],env,20)
            (output/'shell.log').write_text(log)
            lines=[line.split('C1_RESULT:',1)[1] for line in log.splitlines() if 'C1_RESULT:' in line]
            if len(lines)!=1 or 'C1_FAIL:' in log:raise RuntimeError('parser-result-missing')
            receipt=json.loads(lines[0]);receipt['passed']+=['theme-command','background-preserved','command-restored']
            receipt['source_sha256']={**hashes,**{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in theme.iterdir() if p.is_file()}}
            receipt['kind']='isolated-official-theme-parser';receipt['physical_acceptance']='not-run'
            (output/'results.json').write_text(json.dumps(receipt,indent=2)+'\n')
            verify_outputs(output,CASES,{'shell.png':(640,480)})
    print('official theme parser and restore passed')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--official-root',type=Path,default=Path('/official'));args=parser.parse_args()
    main(args.output.absolute(),args.official_root)
