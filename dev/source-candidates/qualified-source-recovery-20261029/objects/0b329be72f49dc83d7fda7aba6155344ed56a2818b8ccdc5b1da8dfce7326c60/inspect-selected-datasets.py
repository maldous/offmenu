#!/usr/bin/env python3
"""Read-only, fixed-selection checksum/receipt diagnostic. Never parse source bodies."""
import argparse
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import sys
import time

SCHEMA = 'offmenu-selected-data-inventory/1'
MAX_RAW = 64 * 1024 * 1024
MAX_TOTAL = 256 * 1024 * 1024
MAX_META = 64 * 1024
MAX_REPORT = 12 * 1024
TIME_LIMIT = 210
# Historical metadata pins establish what was inspected, not current upstream freshness.
SELECTION = {
 'NO_EN_FOODS': ('norway/en-foods.json', 'raw', '89b8f5f494a79731bf7d8d98065ee66c55263ccdbb519e7c87941218be6c948d'),
 'NO_NB_FOODS': ('norway/nb-foods.json', 'raw', None),
 'NO_EN_NUTRIENTS': ('norway/en-nutrients.json', 'raw', None),
 'NO_EN_SOURCES': ('norway/en-sources.json', 'raw', None),
 'FR_WORKBOOK': ('ciqual/Table Ciqual 2025_ENG_2025_11_03.xlsx', 'raw', '2c3495c8136d17356c50db410918da2102cb28096cb497c9cdf83c5f8ecb10ba'),
 'FR_IDENTITIES': ('ciqual/alim_2025_11_03.xml', 'raw', None),
 'NATIONAL_ACQUISITION': ('metadata/national-acquisition.json', 'metadata', '654f91bd14d83b7b55a058777a0b8fd836674310e3dc38235638ec9435dc4edc'),
 'NO_PRIOR_MANIFEST': ('metadata/no-prior-manifest.json', 'metadata', '8b6eb6d3adc99c3aab9053bd0fc373d7755ad1638769c72bafaf4f3a510b94a9'),
 'FR_PRIOR_MANIFEST': ('metadata/fr-prior-manifest.json', 'metadata', 'df4df008991e573c1a0f23111611b5fff2f68b62640546d9bb0360fe760cf9ab'),
 'FI_ACQUISITION': ('metadata/fi-acquisition.json', 'metadata', 'd37f68c855ef24ac235bbc9c6903a26a757fc3c5a9ee621dc33e8f8801c5356f'),
 'FI_PRIOR_MANIFEST': ('metadata/fi-prior-manifest.json', 'metadata', 'e5ec80fc5e0276c76985015924d942db48227b8bcb949cd77f53859b5adee269'),
}
SOURCES = {
 'NO': ('matvaretabellen', '2026', ('NO_EN_FOODS','NO_NB_FOODS','NO_EN_NUTRIENTS','NO_EN_SOURCES'), 'NO_PRIOR_MANIFEST', 'mattilsynet-attribution'),
 'FR': ('ciqual', '2025', ('FR_WORKBOOK','FR_IDENTITIES'), 'FR_PRIOR_MANIFEST', 'etalab-open-2.0'),
 'FI': ('fineli', '20.0', (), 'FI_PRIOR_MANIFEST', 'cc-by-4.0'),
}
LICENSES = {
 'NO': 'Mattilsynet API reuse: source attribution required; see https://www.matvaretabellen.no/api/',
 'FR': 'Etalab Licence Ouverte 2.0',
 'FI': 'CC BY 4.0',
}
HEX = re.compile(r'[0-9a-f]{64}\Z')
STATUSES = {'missing','unsafe-path','not-regular','multiple-links','oversized','aggregate-limit','unreadable','changed','deadline','inspected','invalid-json','unsupported-schema','internal-error'}
MATCHES = {'match','mismatch','unknown'}
ACQUISITION_BASES = {'fixed-key','pinned-receipt-content'}
ACQUISITION_REASONS = {'matched','acquisition-receipt-untrusted','prior-manifest-untrusted',
    'rights-profile-unverified','prior-declaration-missing','raw-unverified','raw-receipt-mismatch',
    'no-content-match','duplicate-content-match','reused-file-label','ambiguous-prior-content'}
SCHEMA_REASONS = {'unsupported-schema','malformed-national-declaration','conflicting-digest-size'}


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()


def signature(s):
    return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_mode,s.st_nlink)


class Blocked(Exception):
    pass


def safe_dir(path):
    """Open all directory components without symlink traversal, starting at /."""
    if not isinstance(path, str) or not path.startswith('/') or '\x00' in path:
        raise Blocked('unsafe-path')
    parts = path.split('/')[1:]
    if any(p in ('.','..') for p in parts):
        raise Blocked('unsafe-path')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in parts:
            if part:
                nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = nxt
        return fd
    except BaseException:
        os.close(fd)
        raise


def parent_fd(root_fd, relative):
    fd = os.dup(root_fd)
    try:
        parts = relative.split('/')
        for part in parts[:-1]:
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = nxt
        return fd, parts[-1]
    except BaseException:
        os.close(fd)
        raise


def classify(exc):
    if isinstance(exc, Blocked):
        return str(exc) if str(exc) in STATUSES else 'internal-error'
    if isinstance(exc, FileNotFoundError):
        return 'missing'
    if isinstance(exc, (NotADirectoryError,)) or getattr(exc, 'errno', None) == 40:
        return 'unsafe-path'
    return 'unreadable' if isinstance(exc, OSError) else 'internal-error'


def strict_json(body):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate')
            result[key] = value
        return result
    def constant(_):
        raise ValueError('constant')
    def finite_float(value):
        parsed = float(value)
        if not math.isfinite(parsed):
            raise ValueError('nonfinite')
        return parsed
    return json.loads(body.decode('utf-8'), object_pairs_hook=pairs, parse_constant=constant, parse_float=finite_float)


def read_selected(root_fd, key, before, deadline):
    relative, kind, _ = SELECTION[key]
    parent, name = parent_fd(root_fd, relative)
    fd = None
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        current = os.fstat(fd)
        if signature(current) != signature(before):
            raise Blocked('changed')
        read_only = bool(os.fstatvfs(fd).f_flag & os.ST_RDONLY)
        digest = hashlib.sha256()
        data = bytearray() if kind == 'metadata' else None
        remaining = before.st_size
        read_count = 0
        while remaining:
            if time.monotonic() > deadline:
                raise Blocked('deadline')
            chunk = os.read(fd, min(65536, remaining))
            if not chunk:
                raise Blocked('changed')
            read_count += len(chunk)
            remaining -= len(chunk)
            digest.update(chunk)
            if data is not None:
                data.extend(chunk)
        # fstat plus anchored pathname check detect replacement/growth without an extra payload read.
        if signature(os.fstat(fd)) != signature(before) or signature(os.stat(name, dir_fd=parent, follow_symlinks=False)) != signature(before):
            raise Blocked('changed')
        return digest.hexdigest(), read_count, read_only, data
    finally:
        if fd is not None:
            os.close(fd)
        os.close(parent)


def timestamp(value):
    if not isinstance(value, str) or len(value) > 32:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
        if parsed.tzinfo is None or parsed.utcoffset() != dt.timedelta(0):
            return None
        return parsed.isoformat().replace('+00:00','Z')
    except ValueError:
        return None


def declarations(value, allowed):
    if not isinstance(value, list) or len(value) > 512:
        raise ValueError('schema')
    result = {}
    for item in value:
        if not isinstance(item, dict) or not isinstance(item.get('key'), str):
            raise ValueError('schema')
        key = item['key']
        if key not in allowed:
            continue
        if key in result or type(item.get('bytes')) is not int or not 0 <= item['bytes'] <= MAX_RAW or not isinstance(item.get('sha256'),str) or not HEX.fullmatch(item['sha256']):
            raise ValueError('declaration')
        result[key] = (item['bytes'], item['sha256'])
    return result


def metadata_facts(key, value):
    """Recognize existing collection/1 and acquisition-list shapes; export no free text."""
    if key.endswith('PRIOR_MANIFEST'):
        country = key[:2]
        source, release, assets, _, rights = SOURCES[country]
        if not isinstance(value, dict) or value.get('schemaVersion') != 'offmenu-collection/1' or value.get('sourceId') != source or value.get('releaseId') != release or value.get('status') != 'normalized':
            raise ValueError('schema')
        allowed = {SELECTION[a][0].split('/')[-1]:a for a in assets}
        decl = declarations(value.get('sourceFiles'), allowed)
        return {'declarations': {allowed[k]:v for k,v in decl.items()}, 'rights': rights if value.get('license') == LICENSES[country] else 'unknown', 'acquiredAt': None}
    if key == 'NATIONAL_ACQUISITION' and isinstance(value, list) and any(isinstance(item, dict) and 'file' in item and 'key' not in item for item in value):
        return national_content_facts(value)
    allowed = {v[0]:k for k,v in SELECTION.items() if v[1] == 'raw'}
    # Acquisition keys are accepted only at these exact known relative locations.
    decl = declarations(value, allowed)
    acquired = {}
    for item in value:
        if item['key'] in allowed:
            # Never substitute completedAt or filesystem mtime for acquisition.
            acquired[allowed[item['key']]] = timestamp(item.get('acquiredAt'))
    return {'declarations': {allowed[k]:v for k,v in decl.items()}, 'rights':'unknown', 'acquiredAt':acquired}


def national_content_facts(value):
    """File and URL strings are opaque receipt labels, never paths or asset identities."""
    if len(value) > 512:
        raise ValueError('malformed-national-declaration')
    records, labels, sizes = {}, {}, {}
    for item in value:
        if (not isinstance(item, dict) or not {'file','bytes','sha256','url'} <= set(item) or 'key' in item or
                not isinstance(item['file'], str) or not item['file'] or
                not isinstance(item['url'], str) or type(item['bytes']) is not int or
                not 0 <= item['bytes'] <= 2**63-1 or not isinstance(item['sha256'], str) or
                not HEX.fullmatch(item['sha256'])):
            raise ValueError('malformed-national-declaration')
        size, digest, label = item['bytes'], item['sha256'], item['file']
        if digest in sizes and sizes[digest] != size:
            raise ValueError('conflicting-digest-size')
        sizes[digest] = size
        records.setdefault((size,digest), []).append(label)
        labels[label] = labels.get(label, 0) + 1
    # Additional receipt fields stay inert, including any timestamp-like metadata.
    # This schema carries no recognized acquisition time. Ignore filesystem time.
    return {'contentRecords':records,'labelCounts':labels,'declarations':{},
            'rights':'unknown','acquiredAt':{},'matchMode':'pinned-receipt-content'}


def corroborate_national(report, facts):
    """Bind content to names only through pinned prior source/release/rights receipts."""
    acquisition = facts.get('NATIONAL_ACQUISITION', {})
    if acquisition.get('matchMode') != 'pinned-receipt-content':
        return
    meta = report['assets']['NATIONAL_ACQUISITION']
    acquisition_ok = meta['status'] == 'inspected' and meta['historicalMatch'] == 'match'
    claims = {}
    for country in ('NO','FR'):
        prior = SOURCES[country][3]
        state = report['assets'][prior]
        if state['status'] == 'inspected' and state['historicalMatch'] == 'match':
            for asset_id, pair in facts.get(prior, {}).get('declarations', {}).items():
                claims.setdefault(pair, set()).add(asset_id)
    for country in ('NO','FR'):
        _, _, required, prior, rights = SOURCES[country]
        state, fact = report['assets'][prior], facts.get(prior, {})
        for asset_id in required:
            asset = report['assets'][asset_id]
            pair = fact.get('declarations', {}).get(asset_id)
            labels = acquisition['contentRecords'].get(pair, [])
            if not acquisition_ok:
                reason = 'acquisition-receipt-untrusted'
            elif state['status'] != 'inspected' or state['historicalMatch'] != 'match':
                reason = 'prior-manifest-untrusted'
            elif fact.get('rights') != rights:
                reason = 'rights-profile-unverified'
            elif pair is None:
                reason = 'prior-declaration-missing'
            elif asset['status'] != 'inspected' or asset['historicalMatch'] == 'mismatch':
                reason = 'raw-unverified'
            elif (asset.get('bytes'), asset.get('sha256')) != pair:
                reason = 'raw-receipt-mismatch'
            elif len(claims.get(pair, ())) != 1:
                reason = 'ambiguous-prior-content'
            elif not labels:
                reason = 'no-content-match'
            elif len(labels) != 1:
                reason = 'duplicate-content-match'
            elif acquisition['labelCounts'][labels[0]] != 1:
                reason = 'reused-file-label'
            else:
                reason = 'matched'
                asset['acquisitionMatch'] = 'match'
                asset['acquisitionMatchBasis'] = 'pinned-receipt-content'
            asset['acquisitionReason'] = reason


def inspect(cache_root):
    report = {'schemaVersion':SCHEMA, 'status':'incomplete', 'completeReady':False,
              'inspectorSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'selectionSha256':hashlib.sha256(canonical(SELECTION)).hexdigest(),
              'sourceBodiesParsed':0,'downloads':0,'originalBytesWritten':0,
              'selectedBytesHashed':0,'minimumReuseDays':30,'countryCoverageComplete':False,
              'assets':{}, 'sources':{}}
    observations, facts = {}, {}
    deadline = time.monotonic() + TIME_LIMIT
    root_fd = None
    try:
        try:
            root_fd = safe_dir(cache_root)
            root_error = None
        except Exception as exc:
            root_error = classify(exc)
        raw_total = 0
        for key, (relative, kind, pin) in SELECTION.items():
            asset = {'status':root_error or 'missing','historicalMatch':'unknown','receiptMatch':'unknown','acquisitionMatch':'unknown','readOnlyView':False}
            report['assets'][key] = asset
            if root_error:
                continue
            try:
                parent, name = parent_fd(root_fd, relative)
                try:
                    s = os.stat(name, dir_fd=parent, follow_symlinks=False)
                finally:
                    os.close(parent)
                if stat.S_ISLNK(s.st_mode):
                    raise Blocked('unsafe-path')
                if not stat.S_ISREG(s.st_mode):
                    raise Blocked('not-regular')
                if s.st_nlink != 1:
                    raise Blocked('multiple-links')
                asset['bytes'] = s.st_size
                if s.st_size > (MAX_RAW if kind == 'raw' else MAX_META):
                    raise Blocked('oversized')
                observations[key] = s
                if kind == 'raw':
                    raw_total += s.st_size
            except Exception as exc:
                asset['status'] = classify(exc)
        # All aggregate bounds are checked before any raw payload is opened.
        for key, before in observations.items():
            asset = report['assets'][key]
            kind, pin = SELECTION[key][1:]
            if kind == 'raw' and raw_total > MAX_TOTAL:
                asset['status'] = 'aggregate-limit'
                continue
            try:
                digest, count, readonly, data = read_selected(root_fd, key, before, deadline)
                report['selectedBytesHashed'] += count
                asset.update(status='inspected', sha256=digest, readOnlyView=readonly,
                             historicalMatch=('match' if digest == pin else 'mismatch') if pin else 'unknown')
                if data is not None:
                    try:
                        value = strict_json(data)
                    except (ValueError, UnicodeError, RecursionError):
                        asset['status'] = 'invalid-json'
                        continue
                    try:
                        facts[key] = metadata_facts(key, value)
                    except (ValueError, TypeError, KeyError, RecursionError) as exc:
                        asset['status'] = 'unsupported-schema'
                        if key == 'NATIONAL_ACQUISITION':
                            asset['schemaReason'] = str(exc) if str(exc) in SCHEMA_REASONS else 'unsupported-schema'
            except Exception as exc:
                asset['status'] = classify(exc)
    finally:
        if root_fd is not None:
            os.close(root_fd)
    corroborate_national(report, facts)
    for country, (source, release, required, manifest, rights) in SOURCES.items():
        meta = report['assets'][manifest]
        fact = facts.get(manifest, {})
        trusted = meta['status'] == 'inspected' and meta['historicalMatch'] == 'match'
        for asset_id in required:
            asset = report['assets'][asset_id]
            declaration = fact.get('declarations', {}).get(asset_id) if trusted else None
            if declaration and 'sha256' in asset:
                asset['declaredSha256'] = declaration[1]
                asset['receiptMatch'] = 'match' if (asset.get('bytes'), asset['sha256']) == declaration else 'mismatch'
        bundle = {a:report['assets'][a].get('sha256') for a in required}
        acquisition_id = 'FI_ACQUISITION' if country == 'FI' else 'NATIONAL_ACQUISITION'
        acquisition = report['assets'][acquisition_id]
        acquisition_ok = acquisition['status'] == 'inspected' and acquisition['historicalMatch'] == 'match'
        for asset_id in required:
            asset = report['assets'][asset_id]
            declaration = facts.get(acquisition_id, {}).get('declarations', {}).get(asset_id) if acquisition_ok else None
            if declaration and 'sha256' in asset:
                asset['acquisitionMatch'] = 'match' if (asset.get('bytes'), asset['sha256']) == declaration else 'mismatch'
                if asset['acquisitionMatch'] == 'match':
                    asset['acquisitionMatchBasis'] = 'fixed-key'
        ready = country != 'FI' and trusted and acquisition_ok and fact.get('rights') == rights and all(report['assets'][a]['status'] == 'inspected' and report['assets'][a]['receiptMatch'] == 'match' and report['assets'][a]['acquisitionMatch'] == 'match' and report['assets'][a]['historicalMatch'] != 'mismatch' and report['assets'][a]['readOnlyView'] for a in required) and meta['readOnlyView'] and acquisition['readOnlyView']
        times = facts.get(acquisition_id, {}).get('acquiredAt') or {}
        known_times = {times.get(a) for a in required}
        acquired_at = next(iter(known_times)) if len(known_times) == 1 and None not in known_times else None
        report['sources'][country] = {
            'sourceId':source,'releaseId':release,
            'status':'metadata-only-held' if country == 'FI' else ('ready-for-adapter-design' if ready else 'incomplete'),
            'requiredAssets':list(required), 'bundleSha256':hashlib.sha256(canonical(bundle)).hexdigest() if required and all(bundle.values()) else None,
            'historicalRightsProfile':fact.get('rights','unknown') if trusted else 'unknown',
            'rightsDecision':'not-performed','acceptance':'not-performed',
            'provenanceVerified':bool(required) and trusted and acquisition_ok and all(report['assets'][a]['receiptMatch'] == 'match' and report['assets'][a]['acquisitionMatch'] == 'match' for a in required),
            'acquiredAt':acquired_at if acquisition_ok else None,
            'freshness':'timestamp-known' if acquired_at and acquisition_ok else 'unknown',
            'acquisitionPolicy':'manual-only-held' if country == 'FI' else 'offline-only',
        }
    report['completeReady'] = all(report['sources'][c]['status'] == 'ready-for-adapter-design' for c in ('NO','FR'))
    if report['completeReady']:
        report['status'] = 'ready-for-adapter-design'
    return sanitize_report(report)


def sanitize_report(value):
    """Strict export boundary; rejects malformed evidence, drops every unknown field."""
    if not isinstance(value, dict) or value.get('schemaVersion') != SCHEMA:
        raise ValueError('invalid-dataset-report')
    result = {'schemaVersion':SCHEMA}
    for key in ('status',):
        if value.get(key) not in ('incomplete','ready-for-adapter-design'):
            raise ValueError('invalid-dataset-report')
        result[key] = value[key]
    for key in ('completeReady','countryCoverageComplete'):
        if type(value.get(key)) is not bool or (key == 'countryCoverageComplete' and value[key]):
            raise ValueError('invalid-dataset-report')
        result[key] = value[key]
    for key in ('sourceBodiesParsed','downloads','originalBytesWritten'):
        if type(value.get(key)) is not int or value[key] != 0:
            raise ValueError('invalid-dataset-report')
        result[key] = 0
    if type(value.get('selectedBytesHashed')) is not int or not 0 <= value['selectedBytesHashed'] <= MAX_TOTAL + 5*MAX_META or (type(value.get('minimumReuseDays')) is not int or value['minimumReuseDays'] != 30):
        raise ValueError('invalid-dataset-report')
    result.update(selectedBytesHashed=value['selectedBytesHashed'],minimumReuseDays=30)
    for key in ('inspectorSha256','selectionSha256'):
        if not isinstance(value.get(key),str) or not HEX.fullmatch(value[key]):
            raise ValueError('invalid-dataset-report')
        result[key] = value[key]
    if not isinstance(value.get('assets'),dict) or set(value['assets']) != set(SELECTION):
        raise ValueError('invalid-dataset-report')
    result['assets'] = {}
    for asset_id, item in value['assets'].items():
        if not isinstance(item, dict):
            raise ValueError('invalid-dataset-report')
        clean = {}
        for key, choices in [('status',STATUSES),('historicalMatch',MATCHES),('receiptMatch',MATCHES),('acquisitionMatch',MATCHES)]:
            if item.get(key) not in choices:
                raise ValueError('invalid-dataset-report')
            clean[key] = item[key]
        if type(item.get('readOnlyView')) is not bool:
            raise ValueError('invalid-dataset-report')
        clean['readOnlyView'] = item['readOnlyView']
        if 'bytes' in item:
            if type(item['bytes']) is not int or not 0 <= item['bytes'] <= 2**63-1:
                raise ValueError('invalid-dataset-report')
            clean['bytes'] = item['bytes']
        for key in ('sha256','declaredSha256'):
            if key in item:
                if not isinstance(item[key],str) or not HEX.fullmatch(item[key]):
                    raise ValueError('invalid-dataset-report')
                clean[key] = item[key]
        for key, choices in (('acquisitionMatchBasis',ACQUISITION_BASES),('acquisitionReason',ACQUISITION_REASONS),('schemaReason',SCHEMA_REASONS)):
            if key in item:
                if not isinstance(item[key],str) or item[key] not in choices:
                    raise ValueError('invalid-dataset-report')
                if key == 'schemaReason':
                    if asset_id != 'NATIONAL_ACQUISITION' or item['status'] != 'unsupported-schema':
                        raise ValueError('invalid-dataset-report')
                elif SELECTION[asset_id][1] != 'raw':
                    raise ValueError('invalid-dataset-report')
                clean[key] = item[key]
        result['assets'][asset_id] = clean
    if not isinstance(value.get('sources'),dict) or set(value['sources']) != set(SOURCES):
        raise ValueError('invalid-dataset-report')
    result['sources'] = {}
    for country, (source, release, required, _, rights) in SOURCES.items():
        item = value['sources'][country]
        if not isinstance(item, dict):
            raise ValueError('invalid-dataset-report')
        expected = {'sourceId':source,'releaseId':release,'requiredAssets':list(required),'rightsDecision':'not-performed','acceptance':'not-performed','acquisitionPolicy':'manual-only-held' if country == 'FI' else 'offline-only'}
        if any(item.get(k) != v for k,v in expected.items()):
            raise ValueError('invalid-dataset-report')
        clean = dict(expected)
        choices = {'status':{'metadata-only-held'} if country == 'FI' else {'incomplete','ready-for-adapter-design'},'historicalRightsProfile':{'unknown',rights},'freshness':{'unknown','timestamp-known'}}
        for key, allowed in choices.items():
            if item.get(key) not in allowed:
                raise ValueError('invalid-dataset-report')
            clean[key] = item[key]
        for key in ('bundleSha256',):
            v = item.get(key)
            if v is not None and (not isinstance(v,str) or not HEX.fullmatch(v)):
                raise ValueError('invalid-dataset-report')
            clean[key] = v
        v = item.get('acquiredAt')
        if v is not None and timestamp(v) != v:
            raise ValueError('invalid-dataset-report')
        clean['acquiredAt'] = v
        if type(item.get('provenanceVerified')) is not bool:
            raise ValueError('invalid-dataset-report')
        clean['provenanceVerified'] = item['provenanceVerified']
        result['sources'][country] = clean
    expected_ready = all(result['sources'][c]['status'] == 'ready-for-adapter-design' for c in ('NO','FR'))
    if result['completeReady'] != expected_ready or (result['status'] == 'ready-for-adapter-design') != expected_ready:
        raise ValueError('invalid-dataset-report')
    for country in ('NO','FR'):
        source = result['sources'][country]
        for asset_id in SOURCES[country][2]:
            asset = result['assets'][asset_id]
            basis, reason = asset.get('acquisitionMatchBasis'), asset.get('acquisitionReason')
            if basis and asset['acquisitionMatch'] != 'match':
                raise ValueError('invalid-dataset-report')
            if reason and ((reason == 'matched') != (asset['acquisitionMatch'] == 'match') or
                           (reason == 'matched' and basis != 'pinned-receipt-content')):
                raise ValueError('invalid-dataset-report')
            if basis == 'pinned-receipt-content':
                metadata_ids = ('NATIONAL_ACQUISITION', SOURCES[country][3])
                if (reason != 'matched' or asset['receiptMatch'] != 'match' or
                        asset['status'] != 'inspected' or asset['historicalMatch'] == 'mismatch' or
                        'sha256' not in asset or asset.get('declaredSha256') != asset['sha256'] or
                        source['historicalRightsProfile'] != SOURCES[country][4] or
                        source['freshness'] != 'unknown' or source['acquiredAt'] is not None or
                        any(result['assets'][a]['status'] != 'inspected' or result['assets'][a]['historicalMatch'] != 'match' for a in metadata_ids)):
                    raise ValueError('invalid-dataset-report')
        if source['status'] == 'ready-for-adapter-design':
            metadata_ids = ('NATIONAL_ACQUISITION', SOURCES[country][3])
            raw_ok = all(result['assets'][a]['status'] == 'inspected' and result['assets'][a]['readOnlyView'] and result['assets'][a]['receiptMatch'] == 'match' and result['assets'][a]['acquisitionMatch'] == 'match' and result['assets'][a]['historicalMatch'] != 'mismatch' and 'sha256' in result['assets'][a] and result['assets'][a].get('declaredSha256') == result['assets'][a]['sha256'] for a in SOURCES[country][2])
            meta_ok = all(result['assets'][a]['status'] == 'inspected' and result['assets'][a]['readOnlyView'] and result['assets'][a]['historicalMatch'] == 'match' for a in metadata_ids)
            if not raw_ok or not meta_ok or not source['provenanceVerified'] or source['historicalRightsProfile'] != SOURCES[country][4]:
                raise ValueError('invalid-dataset-report')
    if len(canonical(result)) > MAX_REPORT:
        raise ValueError('invalid-dataset-report')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache-root', required=True)
    args = parser.parse_args()
    try:
        result = inspect(args.cache_root)
        print(canonical(result).decode())
        return 0 if result['completeReady'] else 2
    except Exception:
        # Never stringify exceptions: paths, document fragments and secrets are excluded.
        print(json.dumps({'schemaVersion':SCHEMA,'status':'error','completeReady':False,'errorCode':'inspector-failed'}))
        return 2


if __name__ == '__main__':
    sys.exit(main())
