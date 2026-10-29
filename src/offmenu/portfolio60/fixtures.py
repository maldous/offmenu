"""Small code-owned authored evidence, never publisher data or source admission."""
from dataclasses import replace

from offmenu.refresh.core import canonical, sha
from .bindings import Binding, Evidence, Field


def authored(case='valid'):
    document = {'country': 'GG', 'release': 'authored-v1', 'url': 'https://example.invalid/authored',
                'original': {'sha256': 'a' * 64, 'bytes': 1,
                             'at': '2026-10-01T00:00:00Z', 'status': 200, 'complete': True},
                'unit': 'mg', 'basis': 'per100g', 'rowSelector': 'authored-only:row1'}
    raw = canonical(document)
    asset = Evidence('metadata/authored-receipt.json', '/authored/receipt.json', len(raw), sha(raw))
    fields = tuple(Field(name, asset.name, selector) for name, selector in (
        ('originalSha256', '/original/sha256'), ('originalBytes', '/original/bytes'),
        ('originalAcquiredAt', '/original/at'), ('nativeUnit', '/unit'),
        ('nativeBasis', '/basis'), ('recordInputSelector', '/rowSelector'), ('sourceUrl', '/url')))
    spec = Binding('authored-portfolio60', 'GG', 'synthetic60', 'authored-v1',
                   'code-owned-authored-fixture-not-a-publisher-release',
                   'https://example.invalid/authored', 'authored-metadata', ('nutrition',),
                   (asset,), fields, asset.name, '/country', asset.name, '/release', (),
                   ('nativeUnit', 'nativeBasis', 'recordInputSelector'),
                   (asset.name, '/original/at', '/original/sha256', '/original/bytes',
                    '/original/status', '/original/complete', True), True)
    if case == 'held':
        spec = replace(spec, holds=('authored-source-use-hold',))
    if case == 'malformed':
        raw = b'{"country":"GG","country":"GG"}'
        spec = replace(spec, inputs=(replace(asset, bytes=len(raw), sha256=sha(raw)),))

    def loader(_):
        if case == 'missing':
            raise FileNotFoundError
        return raw + b' ' if case == 'stale-input' else raw

    return spec, loader
