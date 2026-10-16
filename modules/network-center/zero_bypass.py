#!/usr/bin/python3
"""Keep only the dedicated ZeroTier daemon's outer transport outside TUN.

No peer addresses, tokens, or proxy configuration are read or persisted.
"""
import json
import pwd
import subprocess
import sys


def rule_change(uid, rules, family, remove=False):
    if not isinstance(uid, int) or uid <= 0 or family not in ('-4', '-6'):
        raise ValueError('Dedicated non-root UID and IP family required')
    at_priority = [r for r in rules if r.get('priority') == 8990]
    owned = [r for r in at_priority if r.get('table') in ('main', 254)
             and (r.get('uidrange') == {'start': uid, 'end': uid}
                  or (r.get('uid_start') == uid and r.get('uid_end') == uid))]
    if remove:
        if not owned:
            return None
    elif at_priority:
        if len(at_priority) == len(owned) == 1:
            return None
        raise ValueError('Priority 8990 already used by a different rule')
    return ['ip', family, 'rule', 'del' if remove else 'add', 'priority', '8990',
            'uidrange', f'{uid}-{uid}', 'lookup', 'main']


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ('start', 'stop'):
        raise ValueError('Use start or stop')
    uid = pwd.getpwnam('zerotier-one').pw_uid
    changes = []
    # Validate both families before altering either.
    for family in ('-4', '-6'):
        rules = json.loads(subprocess.check_output(['/usr/bin/ip', family, '-j', 'rule', 'show']))
        command = rule_change(uid, rules, family, remove=sys.argv[1] == 'stop')
        if command:
            command[0] = '/usr/bin/ip'
            changes.append(command)
    applied = []
    try:
        for command in changes:
            subprocess.run(command, check=True, timeout=5)
            applied.append(command)
    except Exception:
        if sys.argv[1] == 'start':
            for command in reversed(applied):
                undo = command.copy()
                undo[3] = 'del'
                subprocess.run(undo, check=False, timeout=5)
        raise
    print(json.dumps({'operation': sys.argv[1], 'changed_families': len(changes)}))


if __name__ == '__main__':
    main()
