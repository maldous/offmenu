"""Trusted static fixture admission and adapter contract. No caller-defined plugins.

Only exact authored fixture bytes are admitted. A source/scope label, a new hash,
or an access grant cannot authorize historical bodies. Additions require code,
input-lock, rights and semantic review. The legacy Wikibooks v1 loader is separate.
"""
import base64
from dataclasses import dataclass
from .core import ROOT, RefreshError, canonical, digest, sha, strict_json, verify
from . import fixture_resources, serialization

NORWAY_LOCK_PIN = {'bytes': 1066, 'sha256': '0e39e65eb38e0353abbf54514c8e163a347f5945f2357420f13a233ddf1e3d28'}
OUTPUT_FILES = ('build-manifest.json', 'content-manifest.json',
                'normalized.jsonl.gz', 'source-metadata.json')
MAX_OUTPUT = 256 * 1024 * 1024
FIXTURES = ('norway',)


@dataclass(frozen=True)
class Fixture:
    name: str
    lock: dict
    blobs: dict
    repinned: bool

    @property
    def source_id(self):
        return self.lock['sourceId']

    @property
    def output_files(self):
        return OUTPUT_FILES

    @property
    def dependencies(self):
        return tuple(item['path'] for item in self.lock['dependencies'])

    def pins(self):
        return {'schemaVersion': 'offmenu-refresh-bundle/2',
                'sourceId': self.source_id, 'releaseId': self.lock['releaseId'],
                'scope': self.lock['scope'], 'fixtureId': self.name,
                'admission': 'reviewed-immutable-authored-fixture',
                'inputLock': self.lock, 'serializationPolicy': serialization.POLICY,
                'outputFiles': list(self.output_files),
                'resources': {'maximumInputBytes': 64 * 1024 * 1024,
                              'maximumOutputBytes': MAX_OUTPUT,
                              'memoryBytes': 1024 * 1024 * 1024,
                              'cpuSeconds': 110, 'wallSeconds': 120}}

    def bundle_key(self):
        # Compatible with the source library's retained provenance identity.
        return sha(canonical({'sourceId': self.source_id,
                              'releaseId': self.lock['releaseId'],
                              'inputs': sorted(self.lock['inputs'], key=lambda x: x['path'])}))


def fixture(name, *, repin_runtime=False, with_blobs=True):
    """Resolve only one fixed trusted fixture, before any source or cache read."""
    if name != 'norway':
        raise RefreshError('fixture-not-registered')
    raw = fixture_resources.NORWAY_LOCK
    if serialization.asset(raw) != NORWAY_LOCK_PIN:
        raise RefreshError('fixture-lock-pin-mismatch')
    lock = strict_json(raw)
    # Fixed lock hash pins scope, release, rights/interpretation contract, exact
    # inputs and implementation. Never accept equivalent caller-provided locks.
    for item in lock['dependencies']:
        verify(ROOT / item['path'], item)
    from offmenu_norway import adapter
    changed = lock['runtime'] != adapter.runtime()
    if repin_runtime:
        lock['runtime'] = adapter.runtime()
    try:
        adapter.validate_lock(lock)
    except adapter.AdapterError as error:
        raise RefreshError(str(error)) from None
    if not with_blobs:
        return Fixture(name, lock, {}, changed and repin_runtime)
    if set(fixture_resources.NORWAY_BLOBS) != {i['path'] for i in lock['inputs']}:
        raise RefreshError('fixture-bundle-set-mismatch')
    blobs = {name: base64.b64decode(raw, validate=True)
             for name, raw in fixture_resources.NORWAY_BLOBS.items()}
    for item in lock['inputs']:
        if serialization.asset(blobs[item['path']]) != {k: item[k] for k in ('bytes', 'sha256')}:
            raise RefreshError('fixture-input-pin-mismatch')
    return Fixture(name, lock, blobs, changed and repin_runtime)


def render(entry, bundle, build_key):
    """Pure transform of the verified bundle; shared core owns all publication."""
    from offmenu_norway import adapter
    try:
        documents, contract = adapter.verify_bundle(entry.lock, bundle)
        rows, metadata = adapter.normalize(documents, contract, entry.bundle_key())
    except adapter.AdapterError as error:
        raise RefreshError(str(error)) from None
    records = serialization.encode_records(rows)
    native_metadata = canonical(metadata)
    counts = {'raw': len(rows), 'normalized': len(rows), 'duplicates': 0,
              'quarantined': 0, 'excluded': 0, 'accepted': None,
              'nutrientDefinitions': len(metadata['nutrients']['nutrients']),
              'sourceReferences': len(metadata['sources']['sources']),
              'unresolvedSourceReferences': len(metadata['unresolvedSourceIds'])}
    content = {'schemaVersion': 'offmenu-normalized-content/2',
               'sourceId': entry.source_id, 'releaseId': entry.lock['releaseId'],
               'scope': entry.lock['scope'], 'inputBundleSha256': entry.bundle_key(),
               'serializationPolicy': serialization.CONTENT_POLICY,
               'canonicalArtifacts': {'normalized.jsonl': serialization.asset(records),
                                      'source-metadata.json': serialization.asset(native_metadata)},
               'counts': counts, 'acceptance': 'not-performed',
               'completeness': {'selectedInputSetComplete': True,
                                'selectedScopeComplete': False, 'registryComplete': False,
                                'countryCoverageComplete': False, 'countryCoverage': 'unassessed'},
               'publicExport': 'not-enabled', 'holds': contract['holds']}
    assets = {'normalized.jsonl.gz': serialization.compress(records),
              'source-metadata.json': native_metadata, 'content-manifest.json': canonical(content)}
    build = {'schemaVersion': 'offmenu-qualified-build/2', 'buildKey': build_key,
             'buildPins': entry.pins(),
             'canonicalContentSha256': sha(assets['content-manifest.json']),
             'transportArtifacts': {name: serialization.asset(body) for name, body in sorted(assets.items())}}
    assets['build-manifest.json'] = canonical(build)
    return assets


def validate_candidate(directory, entry, build_key):
    """Check content and transport independently without accepting a candidate."""
    import gzip
    content_raw = (directory / 'content-manifest.json').read_bytes()
    content = strict_json(content_raw)
    build = strict_json((directory / 'build-manifest.json').read_bytes())
    if (build.get('buildKey') != build_key or build.get('buildPins') != entry.pins()
            or build.get('canonicalContentSha256') != sha(content_raw)):
        raise RefreshError('candidate-build-identity-mismatch')
    for name in ('content-manifest.json', 'normalized.jsonl.gz', 'source-metadata.json'):
        if digest(directory / name) != build['transportArtifacts'].get(name):
            raise RefreshError('candidate-transport-identity-mismatch')
    # A bounded decode is required even after transport validation, so corrupt
    # ledger data cannot turn a small gzip into an unbounded decompression.
    with gzip.open(directory / 'normalized.jsonl.gz', 'rb') as stream:
        records = stream.read(MAX_OUTPUT + 1)
    if len(records) > MAX_OUTPUT:
        raise RefreshError('canonical-output-size-limit-exceeded')
    metadata = (directory / 'source-metadata.json').read_bytes()
    if content.get('canonicalArtifacts') != {
            'normalized.jsonl': serialization.asset(records),
            'source-metadata.json': serialization.asset(metadata)}:
        raise RefreshError('candidate-canonical-identity-mismatch')
    if (content.get('sourceId') != entry.source_id or content.get('releaseId') != entry.lock['releaseId']
            or content.get('scope') != entry.lock['scope'] or content.get('inputBundleSha256') != entry.bundle_key()
            or content.get('serializationPolicy') != serialization.CONTENT_POLICY
            or content.get('acceptance') != 'not-performed' or content.get('publicExport') != 'not-enabled'
            or content.get('counts', {}).get('accepted') is not None):
        raise RefreshError('candidate-scope-or-acceptance-mismatch')
    return content, sha(content_raw)
