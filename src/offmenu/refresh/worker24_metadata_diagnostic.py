"""Explicit private local metadata evidence check; never reads source/candidate bodies.

The pure selector check is also exercised with committed authored fixtures.
Private evidence availability is not a dependency of default test discovery.
"""
import argparse
import errno
import os
from pathlib import Path
import stat

from .core import RefreshError, canonical, sha, strict_json
from .worker24_bindings import catalogue

MAX_EVIDENCE_BYTES = 256 * 1024


def read_metadata_evidence(path):
    """Read one bounded regular descriptor without waiting for a FIFO writer.

    No output is opened. The path must still name this same unchanged regular
    file after the read; descriptor metadata and length must also stay stable.
    Content authentication remains check_selector's pinned digest check.
    """
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC)
    except OSError as exc:
        code = 'metadata-evidence-not-regular' if exc.errno == errno.ELOOP else 'metadata-evidence-unavailable'
        raise RefreshError(code) from None
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise RefreshError('metadata-evidence-not-regular')
        if before.st_size > MAX_EVIDENCE_BYTES:
            raise RefreshError('metadata-evidence-too-large')
        raw = bytearray()
        while len(raw) <= MAX_EVIDENCE_BYTES:
            chunk = os.read(fd, min(65536, MAX_EVIDENCE_BYTES + 1 - len(raw)))
            if not chunk:
                break
            raw.extend(chunk)
        if len(raw) > MAX_EVIDENCE_BYTES:
            raise RefreshError('metadata-evidence-too-large')
        after = os.fstat(fd)
        try:
            named = os.stat(path, follow_symlinks=False)
        except OSError:
            raise RefreshError('metadata-evidence-changed') from None
        def identity(item):
            return (item.st_dev, item.st_ino, item.st_mode, item.st_size,
                    item.st_mtime_ns, item.st_ctime_ns)
        if (identity(before) != identity(after) or identity(after) != identity(named)
                or len(raw) != before.st_size):
            raise RefreshError('metadata-evidence-changed')
        return bytes(raw)
    except OSError:
        raise RefreshError('metadata-evidence-read-failed') from None
    finally:
        os.close(fd)


def check_selector(asset, raw):
    """Verify a metadata pin and exact declaration from supplied metadata bytes."""
    if sha(raw) != asset['selectorEvidence']['sha256']:
        raise RefreshError('metadata-evidence-hash-mismatch')
    node = strict_json(raw)
    try:
        pointer = asset['selector']
        if not isinstance(pointer, str) or not pointer.startswith('/'):
            raise ValueError
        for part in pointer.split('/')[1:]:
            part = part.replace('~1', '/').replace('~0', '~')
            if isinstance(node, list):
                if not part.isdecimal() or str(int(part)) != part:
                    raise ValueError
                node = node[int(part)]
            else:
                node = node[part]
        actual = (Path(node['source']['path']).name, node['source']['sha256'],
                  node['source']['bytes'], node['header'],
                  node.get('version', node.get('resourceVersion')))
        expected = (asset['path'], asset['sha256'], asset['bytes'],
                    asset['headers'], asset['releaseId'])
    except (KeyError, IndexError, TypeError, ValueError):
        raise RefreshError('metadata-selector-unresolved') from None
    if actual != expected:
        raise RefreshError('metadata-selector-declaration-mismatch')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--foo-metadata', action='store_true', required=True,
                        help='Explicitly read private pinned metadata evidence on the local host')
    parser.parse_args(argv)
    try:
        document = catalogue()
    except (RefreshError, ValueError) as exc:
        code = str(exc) if isinstance(exc, RefreshError) else 'metadata-config-invalid'
        print(canonical({'errorCode': code, 'sourceBodiesRead': 0,
                         'candidateBodiesRead': 0, 'networkRequests': 0}).decode(), end='')
        return 2
    documents, results = {}, []
    for profile in document['profiles']:
        for asset in profile['inputs']:
            try:
                evidence = asset['selectorEvidence']
                if evidence not in profile['evidence']:
                    raise RefreshError('metadata-evidence-not-bound')
                if evidence['path'] not in documents:
                    # Only metadata evidence path; node.source.path is never opened.
                    documents[evidence['path']] = read_metadata_evidence(evidence['path'])
                check_selector(asset, documents[evidence['path']])
                code = 'metadata-selector-matched'
            except RefreshError as exc:
                code = str(exc)
            except ValueError:
                code = 'metadata-selector-check-failed'
            results.append({'country': profile['country'], 'input': asset['path'], 'code': code})
    print(canonical({'results': results, 'sourceBodiesRead': 0,
                     'candidateBodiesRead': 0, 'networkRequests': 0,
                     'payloadBytesVerified': False, 'countryAcceptance': False}).decode(), end='')
    return 0 if all(x['code'] == 'metadata-selector-matched' for x in results) else 2


if __name__ == '__main__':
    raise SystemExit(main())
