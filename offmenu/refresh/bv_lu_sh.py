"""BV/LU/SH metadata bindings only. No collector, source-body reader or admission."""
import argparse
import json
import os
from pathlib import Path
import re
import stat

from .core import (RefreshError, atomic_json, canonical, safe_path, sha,
                   strict_json, timestamp)
from .field_provenance import field_origin_errors
from .national_tabular import valid_input_name
from .bv_lu_sh_catalog import BINDINGS

MAX_METADATA = 128 * 1024
COUNTRIES = ('BV', 'LU', 'SH')


def read_pinned_metadata(path, item):
    """One nonblocking descriptor, regular-file identity and bounded pinned bytes."""
    path = safe_path(path)
    identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    before = path.stat(follow_symlinks=False)
    if not stat.S_ISREG(before.st_mode) or before.st_size != item['bytes']:
        raise RefreshError('binding-metadata-file-invalid')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode) or identity(opened) != identity(before):
            raise RefreshError('binding-metadata-file-changed')
        parts, count = [], 0
        while count <= item['bytes']:
            block = os.read(fd, min(65536, item['bytes'] + 1 - count))
            if not block:
                break
            parts.append(block)
            count += len(block)
        after = os.fstat(fd)
        current = path.stat(follow_symlinks=False)
        raw = b''.join(parts)
        if (identity(after) != identity(opened) or identity(current) != identity(after)
                or len(raw) != item['bytes'] or sha(raw) != item['sha256']):
            raise RefreshError('binding-metadata-pin-or-identity-mismatch')
        return raw
    finally:
        os.close(fd)


def pointer(value, selector):
    if not isinstance(selector, str) or not selector.startswith('/'):
        raise RefreshError('binding-selector-invalid')
    for key in selector[1:].split('/'):
        if re.search(r'~(?![01])', key):
            raise RefreshError('binding-selector-invalid')
        key = key.replace('~1', '/').replace('~0', '~')
        if isinstance(value, list):
            if not re.fullmatch('0|[1-9][0-9]*', key):
                raise RefreshError('binding-selector-invalid')
            value = value[int(key)]
        else:
            value = value[key]
    return value


def diagnose(country, spec, evidence_root, *, as_of):
    """Trusted portfolio configuration, deterministic isolated metadata diagnostic.

    Configuration is reviewed code/data, never a source-provided plugin. Only
    declared metadata JSON is read. Body pins and manifests under references are
    declarations, NOT current body-integrity or source-acceptance verification.
    """
    result = dict(country=country, status='malformed', errors=[],
                  metadataBinding=None, bodyReads=0, networkRequests=0,
                  mappings=0, acceptedRecords=0, countryComplete=False)
    errors = set()
    try:
        now = timestamp(as_of)
        if country not in COUNTRIES or not isinstance(spec, dict):
            raise RefreshError('binding-contract-invalid')
        if spec['country'] != country or not isinstance(spec['holds'], list):
            raise RefreshError('binding-contract-invalid')
        result['holds'] = spec['holds']
        result['applicability'] = spec['applicability']
        result['references'] = spec['references']
        result['unknowns'] = spec['unknowns']
        if spec['state'] == 'missing':
            result.update(status='missing', errors=['binding-source-input-missing'])
            return result
        if spec['state'] != 'retained' or not spec['evidence']:
            raise RefreshError('binding-contract-invalid')
        docs, pins = {}, {}
        root = safe_path(evidence_root)
        for item in spec['evidence']:
            name = item['name']
            if (not valid_input_name(name) or name in docs or not name.endswith('.json')
                    or item['role'] != 'metadata' or not valid_input_name(item['path'])
                    or not item['path'].endswith('.json')
                    or type(item['bytes']) is not int or not 0 < item['bytes'] <= MAX_METADATA):
                raise RefreshError('binding-metadata-contract-invalid')
            path = safe_path(root / item['path'])
            if not path.is_relative_to(root):
                raise RefreshError('binding-metadata-contract-invalid')
            try:
                raw = read_pinned_metadata(path, item)
            except FileNotFoundError:
                errors.add('binding-metadata-missing')
                continue
            docs[name] = strict_json(raw)
            pins[name] = item['sha256']
        if errors:
            result.update(status='missing', errors=sorted(errors))
            return result
        release_digest = pointer(docs[spec['releasePin']['input']],
                                 spec['releasePin']['selector'])
        if spec['releaseId'] != 'sha256:' + release_digest:
            raise RefreshError('binding-source-release-mismatch')
        fields, origins = {}, {}
        for field, declaration in spec['fields'].items():
            if not re.fullmatch('[A-Za-z][A-Za-z0-9]*', field):
                raise RefreshError('binding-field-invalid')
            value = pointer(docs[declaration['input']], declaration['selector'])
            if canonical(value) != canonical(declaration['literal']):
                raise RefreshError('binding-field-literal-mismatch')
            fields[field] = value
            origins['/data/' + field] = dict(
                kind='source', sourceId=spec['sourceId'], releaseId=spec['releaseId'],
                inputPath=declaration['input'], inputSha256=pins[declaration['input']],
                sourceRecordId=declaration['selector'], sourceField=declaration['selector'])
        row = dict(data=fields, provenance=dict(
            sourceId=spec['sourceId'], releaseId=spec['releaseId'], fieldOrigins=origins))
        errors.update(field_origin_errors(row, pins))
        acquired = pointer(docs[spec['acquisition']['input']], spec['acquisition']['selector'])
        age = (now - timestamp(acquired)).total_seconds()
        if age < 0:
            raise RefreshError('acquisition-timestamp-in-future')
        # Clock observations only: no shared pure source-neutral planner exists.
        cache = dict(originalAcquiredAt=acquired, metadataValidatedAt=as_of,
                     planningCapability='unsupported-shared-planner-absent',
                     eligibility=None, acquisitionAgeDays=int(age // 86400),
                     mtimeUsedForFreshness=False, validationResetsAcquisitionAge=False,
                     automaticDownloads=0, bodyBytesVerified=False,
                     action='unknown-no-download')
        if spec['holds']:
            errors.add('binding-source-held')
        result['metadataBinding'] = row
        result['cache'] = cache
        # Ages/validation observations are outside the content/no-op identity.
        result['bindingFingerprint'] = sha(canonical(dict(
            sourceId=spec['sourceId'], releaseId=spec['releaseId'],
            fields=fields, evidence=pins, policy=spec)))
        result.update(status='held' if errors else 'metadata-ready', errors=sorted(errors))
        return result
    except (KeyError, IndexError, TypeError, ValueError, OSError, OverflowError, RecursionError):
        # Fixed diagnostics only: never paths, source content or exception text.
        result.update(status='malformed', errors=['binding-metadata-invalid'])
        return result


def diagnose_all(catalog, evidence_root, *, as_of):
    return dict(schemaVersion='offmenu-bv-lu-sh-binding/1',
                scope='metadata-only-not-staging-admission',
                reports=[diagnose(c, catalog.get(c), evidence_root, as_of=as_of)
                         for c in COUNTRIES])


def publish_report(path, report):
    """Metadata output replay: identical diagnostic bytes are an actual no-op.

    Different as-of observations are a new report, even for identical content.
    Source-content identity remains bindingFingerprint; no raw cache is modified.
    """
    path = safe_path(path)
    raw = canonical(report)
    if path.exists() and path.read_bytes() == raw:
        return 'verified-no-op'
    atomic_json(path, report)
    return 'written'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-root', required=True)
    parser.add_argument('--as-of', required=True, help='Explicit UTC clock, never file mtime')
    parser.add_argument('--output')
    args = parser.parse_args(argv)
    report = diagnose_all(BINDINGS, args.evidence_root, as_of=args.as_of)
    if args.output:
        print(publish_report(args.output, report))
    else:
        print(canonical(report).decode(), end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
