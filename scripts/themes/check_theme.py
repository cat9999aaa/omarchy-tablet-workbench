"""Read-only validation for the restricted, original Overdrive theme format.

Python 3.11+; no theme contents are executed. This checks the distributed
package, not arbitrary user overrides or final rendered accessibility.
"""
import json
import math
from pathlib import Path
import re
import stat
import sys
import tomllib

FILES = {'colors.toml', 'shell.toml', 'README.md', 'LICENSE', 'source.json'}
PALETTE = set('accent selection muted background dark_background darker_background lighter_background foreground dark_foreground light_foreground bright_foreground red yellow orange green cyan blue magenta brown bright_red bright_yellow bright_green bright_cyan bright_blue bright_magenta'.split())
SURFACE = {'background', 'background-alpha', 'text', 'border', 'border-alpha', 'border-width'}
SHELL = {
    'bar': {'background', 'background-alpha', 'text', 'active', 'size-horizontal', 'icon-slot'},
    'popups': SURFACE,
    'notifications': SURFACE | {'countdown'},
    'menu': SURFACE | {'scrim', 'scrim-alpha', 'selected-background', 'selected-background-alpha', 'selected-text', 'selected-border', 'selected-border-alpha'},
    'controls': {f'{state}-{field}' for state in ['normal', 'hover-cursor', 'focus', 'selected'] for field in ['color', 'fill-alpha', 'border', 'border-width', 'border-alpha']} | {'pressed-fill-alpha', 'selection-fill-alpha'},
}
HEX = re.compile(r'#[0-9A-Fa-f]{6}\Z')
ALIASES = {'hyprland.active-border', 'hyprland.active-border-foreground'}


def _color(value):
    return isinstance(value, str) and HEX.fullmatch(value) is not None


def contrast_ratio(a: str, b: str) -> float:
    def luminance(value):
        if not _color(value):
            raise ValueError('invalid-color')
        channels = [int(value[i:i+2], 16)/255 for i in (1, 3, 5)]
        linear = [v/12.92 if v <= 0.04045 else ((v+0.055)/1.055)**2.4 for v in channels]
        return sum(c*w for c,w in zip(linear, (0.2126, 0.7152, 0.0722)))
    x, y = sorted((luminance(a), luminance(b)))
    return (y+0.05)/(x+0.05)


def validate_theme(path: Path) -> list[str]:
    errors = []
    try:
        if path.is_symlink() or not path.is_dir():
            return ['invalid-directory']
        if {p.name for p in path.iterdir()} != FILES:
            return ['invalid-file-set']
        contents = {}
        total = 0
        for name in sorted(FILES):
            p = path/name
            st = p.lstat()
            if not stat.S_ISREG(st.st_mode) or st.st_mode & 0o111:
                return ['unsafe-file']
            limit = 16384 if name.endswith('.toml') else 131072
            if st.st_size > limit:
                return ['file-too-large']
            with p.open('rb') as stream:
                data = stream.read(limit+1)
            if len(data) > limit:
                return ['file-too-large']
            total += len(data)
            if total > 131072:
                return ['package-too-large']
            contents[name] = data.decode('utf-8')
        palette = tomllib.loads(contents['colors.toml'])
        shell = tomllib.loads(contents['shell.toml'])
        source = json.loads(contents['source.json'])
    except (OSError, UnicodeError, ValueError):
        return ['unreadable-package']
    if set(palette) != PALETTE | {'mode'} or palette.get('mode') != 'dark':
        errors.append('invalid-palette-keys')
    if any(not _color(palette.get(k)) for k in PALETTE):
        errors.append('invalid-palette-color')
    else:
        for role in ['foreground', 'muted', 'red', 'green', 'yellow']:
            if contrast_ratio(palette[role], palette['background']) < 4.5:
                errors.append('text-contrast')
        if contrast_ratio(palette['accent'], palette['background']) < 3:
            errors.append('focus-contrast')
    if set(shell) != set(SHELL):
        errors.append('invalid-shell-sections')
    for section, values in shell.items():
        if section not in SHELL or not isinstance(values, dict):
            errors.append('invalid-shell-section');continue
        for key, value in values.items():
            if key not in SHELL[section]:
                errors.append('unsupported-shell-key');continue
            if key in ('size-horizontal', 'icon-slot'):
                if type(value) is not int or not 16 <= value <= 128:
                    errors.append('invalid-dimension')
            elif key.endswith('-alpha'):
                if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
                    errors.append('invalid-alpha')
            elif key.endswith('-width'):
                if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 4:
                    errors.append('invalid-border-width')
            elif not _color(value) and not (isinstance(value, str) and value in ALIASES):
                errors.append('invalid-shell-color')
    if not isinstance(source, dict) or source.get('license') != 'GPL-3.0-only' or source.get('original') is not True:
        errors.append('invalid-source')
    return sorted(set(errors))


if __name__ == '__main__':
    errors = validate_theme(Path(sys.argv[1])) if len(sys.argv) == 2 else ['usage']
    print(json.dumps({'ok': not errors, 'errors': errors}))
    raise SystemExit(bool(errors))
