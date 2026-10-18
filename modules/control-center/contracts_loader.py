"""Load the packaged contract snapshot, without searching cwd or PYTHONPATH.

The package is trusted developer-installed code. Hash checks detect accidental
changes, not a malicious same-user editor who can also replace this loader.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import sys
import uuid

_REVISION = '969cd18647f59bc3072a877a87ce1c4f054351f0'
_ORDER = ('__init__', 'errors', 'versions', 'manifest', 'state', 'adapters')
_FILES = frozenset(['LICENSE'] + ['dashen_contracts/' + name + '.py'
                               for name in (*_ORDER, '__main__')])
_MAX_FILE = 65536


class ContractsUnavailable(RuntimeError):
    """A fixed, non-sensitive failure code for the local host."""


def _pairs(pairs):
    data = {}
    for key, value in pairs:
        if key in data:
            raise ValueError('duplicate')
        data[key] = value
    return data


def _read(path):
    if path.is_symlink():
        raise ContractsUnavailable('dependency_invalid')
    try:
        info = path.stat()
    except FileNotFoundError:
        raise ContractsUnavailable('dependency_missing') from None
    if not stat.S_ISREG(info.st_mode) or info.st_size > _MAX_FILE:
        raise ContractsUnavailable('dependency_invalid')
    data = path.read_bytes()
    if len(data) > _MAX_FILE:
        raise ContractsUnavailable('dependency_invalid')
    return data


def _verified_sources():
    host = Path(__file__).absolute().parent
    root = host / 'vendor/dashen-contracts-0.1.0'
    # Reject links in the fixed installed package path, including its parents.
    for path in [root, *root.parents]:
        if path.is_symlink():
            raise ContractsUnavailable('dependency_invalid')
    origin = json.loads(_read(root / 'source.json'), object_pairs_hook=_pairs)
    if (type(origin) is not dict or set(origin) != {'repository', 'revision', 'version', 'sha256'}
            or origin['repository'] != 'https://github.com/cat9999aaa/dashen-overdrive'
            or origin['revision'] != _REVISION or origin['version'] != '0.1.0'
            or type(origin['sha256']) is not dict or set(origin['sha256']) != _FILES):
        raise ContractsUnavailable('dependency_mismatch')
    paths = list(root.rglob('*'))
    if any(p.is_symlink() for p in paths):
        raise ContractsUnavailable('dependency_invalid')
    if {p.relative_to(root).as_posix() for p in paths if not p.is_dir()} != _FILES | {'source.json'}:
        raise ContractsUnavailable('dependency_mismatch')
    sources = {}
    for name in sorted(_FILES):
        data = _read(root / name)
        if hashlib.sha256(data).hexdigest() != origin['sha256'][name]:
            raise ContractsUnavailable('dependency_mismatch')
        sources[name] = data
    return root, sources


def load_contracts():
    namespace = '_dashen_contracts_fixed_' + uuid.uuid4().hex
    try:
        root, sources = _verified_sources()
        adapter = None
        # The fixed snapshot's import graph is acyclic in this order. Execute
        # the bytes just verified; do not let a later file read or .pyc win.
        for name in _ORDER:
            is_package = name == '__init__'
            key = namespace if is_package else namespace + '.' + name
            path = root / 'dashen_contracts' / (name + '.py')
            spec = importlib.util.spec_from_file_location(
                key, path, submodule_search_locations=[] if is_package else None)
            module = importlib.util.module_from_spec(spec)
            sys.modules[key] = module
            exec(compile(sources['dashen_contracts/' + name + '.py'], str(path), 'exec'), module.__dict__)
            if name == 'adapters':
                adapter = module
        return adapter
    except ContractsUnavailable:
        raise
    except Exception:
        raise ContractsUnavailable('dependency_invalid') from None
    finally:
        # These fixed modules have no lazy relative imports. Imported globals
        # remain owned by the returned module, without leaking import aliases.
        for name in tuple(sys.modules):
            if name == namespace or name.startswith(namespace + '.'):
                del sys.modules[name]
