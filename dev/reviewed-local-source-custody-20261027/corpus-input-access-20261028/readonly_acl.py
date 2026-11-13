"""Pure POSIX ACL planner. No filesystem reads or writes.
Input must be numeric getfacl output for ONE inode; installer owns collision,
no-follow traversal, inode pinning, backup, application and rollback.
"""
import re

WORKER = 985
OWNER = 1000
class ACLPlanError(ValueError):
    pass

def bits(s):
    if not re.fullmatch(r'[r-][w-][x-]', s):
        raise ACLPlanError('Unsupported permissions')
    return (4 if s[0] == 'r' else 0) | (2 if s[1] == 'w' else 0) | (1 if s[2] == 'x' else 0)

def perms(n):
    return ''.join(c if n & b else '-' for b, c in ((4, 'r'), (2, 'w'), (1, 'x')))

def validate(a):
    if not all(k in a for k in [('user', ''), ('group', ''), ('other', '')]):
        raise ACLPlanError('Missing base ACL')
    named = any(q for _, q in a)
    if named and ('mask', '') not in a:
        raise ACLPlanError('Named entries require mask')

def parse(text):
    scopes = [{}, {}]
    for line in text.splitlines():
        line = line.split('#', 1)[0].strip()
        if not line:
            continue
        d = line.startswith('default:')
        if d:
            line = line[len('default:'):]
        fields = line.split(':')
        if len(fields) != 3:
            raise ACLPlanError('Unsupported ACL grammar')
        kind, qualifier, rights = fields
        if kind not in ('user', 'group', 'mask', 'other'):
            raise ACLPlanError('Unsupported ACL entry')
        if qualifier and (kind not in ('user', 'group') or not re.fullmatch(r'0|[1-9][0-9]*', qualifier)):
            raise ACLPlanError('Numeric IDs required')
        key = kind, qualifier
        if key in scopes[d]:
            raise ACLPlanError('Duplicate ACL entry')
        scopes[d][key] = bits(rights)
    validate(scopes[0])
    if scopes[1]:
        validate(scopes[1])
    return scopes

def effective(a, key):
    value = a[key]
    if key[0] == 'group' or (key[0] == 'user' and key[1]):
        return value & a.get(('mask', ''), 7)
    return value

def normalize(a):
    return {k: effective(a, k) for k in a if k != ('mask', '')}

def finish(a):
    result = dict(a)
    mask = 0
    for (kind, qualifier), value in a.items():
        if kind == 'group' or (kind == 'user' and qualifier):
            mask |= value
    result['mask', ''] = mask
    return result

def verify_preserved(before, after, exceptions=()):
    """Verify each old entry's effective rights; mask itself isn't a principal."""
    for key in before:
        if key == ('mask', '') or key in exceptions:
            continue
        if key not in after or effective(before, key) != effective(after, key):
            raise ACLPlanError('Existing effective permission changed')
    return True

def render(scopes):
    def order(item):
        (kind, q), _ = item
        return ({'user': 0, 'group': 1, 'mask': 2, 'other': 3}[kind], bool(q), int(q or 0))
    lines = []
    for default, scope in enumerate(scopes):
        for (kind, qualifier), value in sorted(scope.items(), key=order):
            lines.append(('default:' if default else '') + f'{kind}:{qualifier}:{perms(value)}')
    return '\n'.join(lines) + '\n'

def readonly_plan(text, *, owner, group, is_dir):
    access, default = parse(text)
    if owner == WORKER:
        raise ACLPlanError('Worker-owned source inode cannot be confined by named ACL')
    current = effective_for_identity(access, owner=owner, group=group)
    if current & 2:
        raise ACLPlanError('Source inode already writable by worker; not changed')
    wanted = 5 if is_dir else 4
    if current & wanted == wanted:
        return render([access, default]), False
    result = normalize(access)
    worker_key = ('user', str(WORKER))
    result[worker_key] = current | wanted
    result = finish(result)
    verify_preserved(access, result, exceptions=(worker_key,))
    if effective_for_identity(result, owner=owner, group=group) & 2:
        raise ACLPlanError('Write bit would be granted')
    if effective_for_identity(result, owner=owner, group=group) & wanted != wanted:
        raise ACLPlanError('Required readonly rights not achieved')
    return render([result, default]), True

"""Pure POSIX ACL evaluation for preserving externally shared regular inodes.
No filesystem operations; caller verifies inode identity, nlink and ACL stability.
"""

def effective_for_identity(access, *, owner, group, uid=985, gids=(977,)):
    if uid == owner:
        return access['user', '']
    mask=access.get(('mask',''),7)
    named=('user',str(uid))
    if named in access:
        return access[named] & mask
    matching=False
    granted=0
    if group in gids:
        matching=True
        granted |= access['group','']
    for gid in gids:
        key=('group',str(gid))
        if key in access:
            matching=True
            granted |= access[key]
    # A matching group with no permissions does NOT fall through to other.
    return granted & mask if matching else access['other','']

