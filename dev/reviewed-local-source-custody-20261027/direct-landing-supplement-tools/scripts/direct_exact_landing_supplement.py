#!/usr/bin/env python3
"""Exact two authored landing literals plus one pinned DOM source; no Actions.
No JavaScript evaluation, recursive lookup, body-table upload or host mutation.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import types

PUBLISHER_SHA = '013e7e2bdc1246e257f6f7724fcc127a9d3fae0989a734738ef6e0373bc389b2'
HELPER_SHA = 'd6e348a926043ece29e4c9fcbd5e6dfafd30dabaf2d529ef1dc944a9aa14d4e2'
PARSER_SHA = '876841e43b8abd8958f219ce4be957aa27aadb44408496ab60f64dfc2c69a089'
DOM_PATH = '/home/user/src/offmenu-data/runtime/layout-migration/worker05/local-own-data-root14-successor-20261027/cover-r2-source-r1/root-dom-assets.mjs'
DOM_SHA = '17105266ad9defbe04dc659f38a9e18584ae228b1ee34ce151c7c4d26401abfb'
PREFIX = 'dev/reviewed-local-source-custody-20261027/direct-landing-supplement/'

class Refused(Exception):
    pass

def need(value, code):
    if not value: raise Refused(code)

def sha256(raw): return hashlib.sha256(raw).hexdigest()

SOURCE_PATH = '/home/user/src/offmenu-data/runtime/layout-migration/worker05/local-own-data-root14-successor-20261027/all15-ready-source-r1/root-static-assets.mjs'
SOURCE_SHA = '1d16ed224861874bc1bcc51221eb04554308139e4a86048d20f177f70934dab6'
TARGETS = [{'route': '/landing-world-actions/current183-all15-r2-assets/native15-first-sequence-20261026/full15-master-r1/scene12-compact-world-adapter-r3/reach-alpha-samples.json', 'bytes': 13887, 'mime': 'application/json', 'sha256': '21e6aadc33f397c4e0da69b071c336e15ee64f329b8c7d7eb1891fc7f3479c69'}, {'route': '/landing-world-actions/current183-all15-r2-assets/native15-helper-world-registration-20261027/scene-12/owner-12/r2/shelf-wood-source-crop.png', 'bytes': 846, 'mime': 'image/png', 'sha256': 'bc893ba64eb6f05169c1c68a76f8b5a7f5c7b7d23e33dd796195070c6ec2a80f'}]

def safe_local_read(path, limit):
    path = str(Path(path).absolute())
    parts = Path(path).parts[1:]
    need(parts and all(x not in ("", ".", "..") for x in parts), "invalid-input-path")
    parent = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in parts[:-1]:
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            os.close(parent); parent = nxt
        fd = os.open(parts[-1], os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW, dir_fd=parent)
    finally:
        os.close(parent)
    try:
        import stat
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_size <= limit,
             "input-not-bounded-regular-file")
        def read():
            result = bytearray()
            while True:
                chunk = os.read(fd, min(65536, limit + 1 - len(result)))
                if not chunk: break
                result.extend(chunk)
                need(len(result) <= limit, "input-too-large")
            return bytes(result)
        raw = read(); os.lseek(fd, 0, os.SEEK_SET); second = read()
        after = os.fstat(fd)
        identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        need(identity(before) == identity(after) and len(raw) == before.st_size and raw == second,
             "input-changed-during-read")
        return raw
    finally:
        os.close(fd)



def load_publisher(path):
    raw = safe_local_read(path, 1024 * 1024)
    need(sha256(raw) == PUBLISHER_SHA, 'publisher-pin-mismatch')
    module = types.ModuleType('pinned_direct_publisher')
    module.__file__ = str(Path(path).absolute())
    exec(compile(raw, module.__file__, 'exec'), module.__dict__)
    return module


def exact_literals(raw, parser, helper):
    need(sha256(raw) == SOURCE_SHA, 'static-parent-pin-mismatch')
    text = raw.decode('utf-8', errors='strict')
    routes = parser.literal_table(text, 'ROOT14_ROUTES')
    bodies = parser.literal_table(text, 'ROOT14_BODIES')
    result = []
    for target in TARGETS:
        descriptor = {key: target[key] for key in ('sha256', 'bytes', 'mime')}
        need(routes.get(target['route']) == descriptor, 'exact-route-descriptor-mismatch')
        encoded = bodies.get(target['sha256'])
        need(type(encoded) is str and len(encoded) == 4 * ((target['bytes'] + 2) // 3),
             'exact-body-encoding-mismatch')
        body = base64.b64decode(encoded, validate=True)
        need(len(body) == target['bytes'] and sha256(body) == target['sha256'], 'exact-body-pin-mismatch')
        helper.check_body(body, 'artwork' if target['mime'] == 'image/png' else 'source')
        if target['mime'] == 'image/png': need(body.startswith(b'\x89PNG\r\n\x1a\n'), 'exact-png-signature-mismatch')
        else: helper.decode(body)
        result.append(dict(target, contentBase64=base64.b64encode(body).decode(),
                           provenance={'parentSourcePath': SOURCE_PATH, 'parentSourceSha256': SOURCE_SHA,
                                       'routeTable': 'ROOT14_ROUTES', 'bodyTable': 'ROOT14_BODIES',
                                       'bodyKey': target['sha256']}))
    return result


def prepare(helper, parser):
    helper.source_path(SOURCE_PATH); helper.source_path(DOM_PATH)
    parent, _ = helper.read_regular(SOURCE_PATH, helper.MAX_FILE)
    projected = exact_literals(parent, parser, helper)
    dom, _ = helper.read_regular(DOM_PATH, helper.MAX_FILE)
    need(sha256(dom) == DOM_SHA, 'dom-source-pin-mismatch')
    helper.check_body(dom, 'source')
    return {'schemaVersion': 'offmenu-exact-landing-supplement/1',
            'sourceParent': {'sourcePath': SOURCE_PATH, 'sha256': SOURCE_SHA, 'bytes': len(parent)},
            'literalParserSha256': PARSER_SHA, 'sourceHelperSha256': HELPER_SHA,
            'publisherSha256': PUBLISHER_SHA, 'projectedBodies': projected,
            'selectedSources': [{'sourcePath': DOM_PATH, 'sha256': DOM_SHA, 'bytes': len(dom),
                                 'kind': 'source', 'contentBase64': base64.b64encode(dom).decode()}],
            'exclusions': 'Only the two exact reviewed sceneJSON/PNG literals and pinned DOM source; no other table bodies, full static parent, launch bundle, JavaScript execution or runtime adoption'}


def publish(projection, output_directory, base, helper, api):
    raw = helper.canonical(projection); digest = sha256(raw)
    os.mkdir(output_directory, 0o700)
    path = str(Path(output_directory) / 'landing-supplement.json')
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as out: out.write(raw); out.flush(); os.fsync(out.fileno())
    blob_sha = base.git_blob(raw)
    parent = base.current_ref(api); tree_sha = base.verify_safe_parent(api, parent)
    destination = PREFIX + digest
    expected = {'landing-supplement.json': (blob_sha, len(raw))}
    existing = base.tree_at(api, tree_sha, destination)
    if existing is not None:
        need(all(x.get('type') == 'blob' and x.get('mode') == '100644' for x in existing)
             and {x['path']: (x['sha'], x['size']) for x in existing} == expected,
             'existing-projection-conflict-no-overwrite')
        return {'status': 'already-preserved', 'commit': parent, 'path': destination, 'projectionSha256': digest,
                'actionsDispatched': 0, 'runtimeAdopted': False}
    reread, _ = helper.read_regular(path, len(raw))
    need(reread == raw, 'projection-changed-before-upload')
    root = 'repos/' + base.REPOSITORY
    blob = api(root + '/git/blobs', 'POST', {'encoding': 'base64', 'content': base64.b64encode(raw).decode()})
    need(blob.get('sha') == blob_sha, 'uploaded-blob-identity-mismatch')
    tree = api(root + '/git/trees', 'POST', {'base_tree': tree_sha, 'tree': [
        {'path': destination + '/landing-supplement.json', 'mode': '100644', 'type': 'blob', 'sha': blob_sha}]})
    commit = api(root + '/git/commits', 'POST', {'message': 'Preserve exact reviewed landing supplement; no Actions\n\nProjection SHA256 ' + digest,
                                               'tree': tree['sha'], 'parents': [parent]})
    new_sha = commit.get('sha', '')
    need(re.fullmatch(r'[0-9a-f]{40}', new_sha), 'created-commit-unverified')
    need(base.current_ref(api) == parent, 'custody-branch-moved-no-ref-update')
    try: api(root + '/git/refs/heads/' + base.BRANCH, 'PATCH', {'sha': new_sha, 'force': False})
    except Exception: need(base.current_ref(api) == new_sha, 'ref-update-unconfirmed-readback-required')
    need(base.current_ref(api) == new_sha, 'published-ref-readback-mismatch')
    remote = api(root + '/git/commits/' + new_sha)
    need(remote.get('tree', {}).get('sha') == tree['sha'] and [x['sha'] for x in remote.get('parents', [])] == [parent],
         'published-ancestry-mismatch')
    final = base.tree_at(api, tree['sha'], destination)
    need(final is not None and {x['path']: (x['sha'], x.get('size')) for x in final} == expected,
         'published-projection-tree-mismatch')
    return {'status': 'preserved', 'commit': new_sha, 'parent': parent, 'path': destination,
            'projectionSha256': digest, 'projectedBodies': 2, 'projectedBytes': sum(x['bytes'] for x in projection['projectedBodies']),
            'selectedSources': 1, 'selectedSourceBytes': projection['selectedSources'][0]['bytes'],
            'actionsDispatched': 0, 'runtimeAdopted': False}


def main():
    argument = argparse.ArgumentParser(description=__doc__)
    for option in ('publisher', 'source-helper', 'literal-parser', 'output-directory'):
        argument.add_argument('--' + option, required=True)
    args = argument.parse_args(); base = None; helper = None; stage = 'load-reviewed-tools'
    try:
        need(os.geteuid() != 0, 'must-run-as-normal-owner'); os.umask(0o077)
        base = load_publisher(args.publisher)
        helper = base.load_helper(args.source_helper, HELPER_SHA)
        parser = base.load_helper(args.literal_parser, PARSER_SHA)
        stage = 'exact-source-projection'
        projection = prepare(helper, parser)
        stage = 'publish-exact-supplement'
        result = publish(projection, args.output_directory, base, helper, base.GitHub())
        print(json.dumps(result, sort_keys=True)); return 0
    except Exception as error:
        safe = isinstance(error, Refused) or base is not None and isinstance(error, base.Refused) or helper is not None and isinstance(error, helper.Rejected)
        print(json.dumps({'status': 'stopped', 'stage': stage,
                          'errorCode': str(error) if safe else 'exact-supplement-failed-no-private-details',
                          'exceptionClass': type(error).__name__, 'actionsDispatched': 0}), file=sys.stderr)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
