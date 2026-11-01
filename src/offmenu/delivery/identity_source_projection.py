"""Finite identity-only source/target admission; no execution or Git writes.

The protected owner supplies this record after original unit/Journal review.
It transfers a reviewed source delta to an advanced target, never the validation
or review verdict to a different source. The fixed identity input closure does
not import the four delivery namespaces below; all other Git bytes stay equal.
"""
import hashlib
from pathlib import Path, PurePosixPath
import re
import subprocess

from .engine import DeliveryError


PROFILE = 'identity-client-focused'
EXCLUDED = ('docs/development/', 'tools/delivery/', 'tests/delivery/',
            'src/offmenu/delivery/')


def require(value):
    if not value:
        raise DeliveryError('Invalid identity source projection')


def sha(value, size=40):
    return type(value) is str and re.fullmatch('[0-9a-f]{'+str(size)+'}', value)


def validate_projection(value, binding=None):
    """Validate sealed DATA only; this is not owner authority or Git evidence."""
    require(type(value) is dict and set(value) == {
        'version', 'profile', 'source', 'target', 'merge_tree', 'outputs',
        'unit_sha256', 'operation_key', 'receipt', 'review_sha256'})
    require(type(value['version']) is int and value['version'] == 1
            and value['profile'] == PROFILE)
    source, target = value['source'], value['target']
    require(type(source) is dict and set(source) == {'head', 'base', 'tree', 'branch'}
            and type(target) is dict and set(target) == {'base', 'tree'})
    require(all(sha(source[k]) for k in ('head', 'base', 'tree'))
            and all(sha(target[k]) for k in ('base', 'tree')) and sha(value['merge_tree']))
    require(type(source['branch']) is str and re.fullmatch(
        r'(?:feature|bugfix)/[a-z0-9][a-z0-9/-]{0,159}', source['branch'])
        and not source['branch'].endswith('/') and '//' not in source['branch'])
    require(all(sha(value[k], 64) for k in ('unit_sha256', 'operation_key', 'review_sha256')))
    receipt = value['receipt']
    require(type(receipt) is dict and set(receipt) == {'path', 'sha256'}
            and type(receipt['path']) is str and receipt['path'].startswith('/')
            and sha(receipt['sha256'], 64))
    outputs = value['outputs']
    require(type(outputs) is dict and outputs)
    for name, expected in outputs.items():
        require(type(name) is str and name and not name.startswith('/')
                and str(PurePosixPath(name)) == name and '..' not in PurePosixPath(name).parts
                and not name.startswith(EXCLUDED) and sha(expected, 64))
    if binding is not None:
        require(binding.get('version') == 2
                and all(binding[k] == source[v] for k, v in
                        (('head', 'head'), ('tree', 'tree'), ('head_branch', 'branch')))
                and binding['base'] == target['base'] and binding['outputs'] == outputs
                and binding['validation_operation_key'] == value['operation_key'])
    return value


def qualify_projection(repository, value, binding=None):
    """Recompute the trivial clean merge using immutable Git objects only.

    Because source changes ONLY reviewed outputs and target did not touch them,
    replacing those entries in target is the complete conflict-free merge. This
    avoids creating a commit, tree, worktree, claim or another validation job.
    """
    validate_projection(value, binding)
    root = Path(repository)
    require(root.is_absolute() and root == root.resolve())
    def git(*args):
        try:
            return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as error:
            raise DeliveryError('Identity projection Git evidence missing') from error
    def tree(revision):
        entries = {}
        for row in git('ls-tree', '-r', '-z', revision).split(b'\0'):
            if row:
                meta, name = row.split(b'\t', 1)
                entries[name.decode()] = tuple(meta.decode().split())
        return entries
    source, target, outputs = value['source'], value['target'], value['outputs']
    require(git('rev-parse', source['head']+'^{tree}').decode().strip() == source['tree']
            and git('rev-parse', target['base']+'^{tree}').decode().strip() == target['tree'])
    require(git('rev-list', '--parents', '-n', '1', source['head']).decode().split()
            == [source['head'], source['base']])
    git('merge-base', '--is-ancestor', source['base'], target['base'])
    original, head, base, merged = (tree(v) for v in
        (source['base'], source['head'], target['base'], value['merge_tree']))
    changed = {p for p in set(original) | set(head) if original.get(p) != head.get(p)}
    require(changed == set(outputs))
    expected = dict(base)
    for name, expected_sha in outputs.items():
        entry = head.get(name)
        require(entry is not None and entry[:2] in (('100644', 'blob'), ('100755', 'blob'))
                and original.get(name) == base.get(name)
                and hashlib.sha256(git('cat-file', 'blob', entry[2])).hexdigest() == expected_sha)
        expected[name] = entry
    require(merged == expected)
    require(all(head.get(p) == merged.get(p) for p in set(head) | set(merged)
                if not p.startswith(EXCLUDED)))
    return value
