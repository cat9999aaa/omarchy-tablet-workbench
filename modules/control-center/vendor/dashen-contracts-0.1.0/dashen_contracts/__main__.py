"""Low-frequency offline CLI. No extension activation or device actions."""
import json
import os
from pathlib import Path
import stat
import sys

from .adapters import adapt_control_snapshot
from .errors import ContractError
from .manifest import MAX_BYTES, invalid, parse_json, validate_manifest
from .versions import negotiate


def read_input(path: Path) -> bytes:
    # Nonblocking open plus fstat prevents a named pipe from hanging the CLI.
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as handle:
        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
            invalid()
        raw = handle.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        invalid()
    return raw


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else argv
    try:
        if len(args) != 2:
            invalid()
        command, filename = args
        if command not in ('validate', 'negotiate', 'example'):
            raise ContractError('permission_denied')
        path = Path(filename)
        raw = read_input(path)
        if command == 'validate':
            value = validate_manifest(raw, path.parent)
            result = {'valid': True, 'id': value['id'], 'schema_version': value['schema_version']}
        elif command == 'negotiate':
            value = parse_json(raw)
            if set(value) != {'local_versions', 'remote_versions', 'local_range', 'remote_range'}:
                invalid()
            result = {'version': negotiate(**value)}
        else:
            context = {'device_id': 'simulation-device', 'session_id': 'simulation-session',
                       'output_id': 'simulation-output', 'owner_generation': 'simulation-generation', 'sequence': 0}
            result = {'simulation': True, 'cards': adapt_control_snapshot(parse_json(raw), context, {})}
        print(json.dumps(result, ensure_ascii=True, allow_nan=False))
        return 0
    except ContractError as error:
        print(error.code, file=sys.stderr)
        return 3 if error.code in ('permission_denied', 'unsupported_version') else 2
    except (OSError, ValueError, RecursionError, OverflowError):
        print('invalid_request', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
