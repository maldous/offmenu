"""Explicit Foo-only metadata evidence check; never reads source/candidate bodies.

The pure selector check is also exercised with committed authored fixtures.
Private evidence availability is not a dependency of default test discovery.
"""
import argparse
from pathlib import Path

from .core import RefreshError, canonical, sha, strict_json
from .worker24_bindings import CONFIG


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
                        help='Explicitly read private pinned metadata evidence on Foo')
    parser.parse_args(argv)
    document = strict_json(CONFIG.read_bytes())
    documents, results = {}, []
    for profile in document['profiles']:
        for asset in profile['inputs']:
            try:
                evidence = asset['selectorEvidence']
                if evidence not in profile['evidence']:
                    raise RefreshError('metadata-evidence-not-bound')
                if evidence['path'] not in documents:
                    # Only metadata evidence path; node.source.path is never opened.
                    with open(evidence['path'], 'rb') as stream:
                        raw = stream.read(256 * 1024 + 1)
                    if len(raw) > 256 * 1024:
                        raise RefreshError('metadata-evidence-too-large')
                    documents[evidence['path']] = raw
                check_selector(asset, documents[evidence['path']])
                code = 'metadata-selector-matched'
            except OSError:
                code = 'metadata-evidence-unavailable'
            except (RefreshError, ValueError):
                code = 'metadata-selector-check-failed'
            results.append({'country': profile['country'], 'input': asset['path'], 'code': code})
    print(canonical({'results': results, 'sourceBodiesRead': 0,
                     'candidateBodiesRead': 0, 'networkRequests': 0,
                     'payloadBytesVerified': False, 'countryAcceptance': False}).decode(), end='')
    return 0 if all(x['code'] == 'metadata-selector-matched' for x in results) else 2


if __name__ == '__main__':
    raise SystemExit(main())
