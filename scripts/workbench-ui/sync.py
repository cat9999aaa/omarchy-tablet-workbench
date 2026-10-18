"""Synchronize the six shared runtime files into four fixed consumers.

Preflight all destinations before writing. Unknown files are conflicts, never
removed. root injection exists for temporary-tree tests, not arbitrary outputs.
"""
import argparse
import os
from pathlib import Path
import tempfile

FILES = ('TouchButton.qml','PanelHeader.qml','PanelBody.qml','Layout.js','State.js','Theme.js')
DESTINATIONS = ('modules/control-center/Workbench','modules/network-center/Workbench',
                'modules/battery-manager/panel/Workbench','modules/window-controls/Workbench')


def safe_path(root, path):
    relative = path.relative_to(root)
    current = root
    if current.is_symlink():
        return False
    for part in relative.parts:
        current = current/part
        if current.is_symlink():
            return False
    return True


def sync(root: Path, write: bool = False) -> list[str]:
    root = Path(root).absolute()
    source = root/'modules/workbench-ui'
    errors = []
    try:
        data = {}
        for name in FILES:
            p = source/name
            if not safe_path(root,p) or not p.is_file():
                errors.append('unsafe-source:'+name)
            else:
                data[name] = p.read_bytes()
        for directory in DESTINATIONS:
            target = root/directory
            if not safe_path(root,target) or not target.is_dir():
                errors.append('unsafe-destination:'+directory);continue
            for p in target.iterdir():
                if p.name not in FILES or not safe_path(root,p) or not p.is_file():
                    errors.append('conflicting-file:'+directory+'/'+p.name)
        if errors:
            return errors
        for directory in DESTINATIONS:
            target = root/directory
            for name, content in data.items():
                p = target/name
                if p.exists() and p.read_bytes() == content:
                    continue
                if not write:
                    errors.append('stale-copy:'+directory+'/'+name);continue
                fd, temporary = tempfile.mkstemp(prefix='.workbench-',dir=target)
                try:
                    with os.fdopen(fd,'wb') as stream:
                        stream.write(content)
                        stream.flush()
                        os.fsync(stream.fileno())
                    os.chmod(temporary,0o644)
                    os.replace(temporary,p)
                finally:
                    Path(temporary).unlink(missing_ok=True)
    except OSError as exc:
        errors.append('io-error:'+type(exc).__name__)
    return errors


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--check',action='store_true')
    group.add_argument('--write',action='store_true')
    args = parser.parse_args()
    errors = sync(Path(__file__).resolve().parents[2],args.write)
    print('\n'.join(errors) if errors else 'shared copies match')
    raise SystemExit(bool(errors))
