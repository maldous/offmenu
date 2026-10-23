#!/usr/bin/env python3
"""Prepare source dispositions from pinned metadata; never acquire source bodies.

This is a fixed runner adapter. The existing collect-source-access.py and
offmenu.refresh.acquisition remain the only collection implementation. An owner
snapshot is evidence, not a live claim, licence grant, or reservation release.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import types

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from offmenu.refresh.core import RefreshError, canonical, safe_path, strict_json

SCHEMA = 'offmenu-collection-preparation-summary/1'
DETAIL_SCHEMA = 'offmenu-collection-preparation/1'
OUTPUT = Path('/srv/offmenu-refresh/outputs')
ADOPTED_COMMIT = 'b15de9593d242d36a63d2b00dd6078d57b4d82a3'
ADOPTED_REGISTRY_SHA256 = 'c24dbcb802d1f0d8fe617f08de42c28a60c216a1f136614509b990d7d1d63bab'
SUMMARY_COMMIT = '769df4a95465aa9396c3f5a7b5f3de390f6b075d'
SUMMARY_PIN = ('docs/registry-candidate/2026-10-18/country-lookup-handover/adopted-country-index-summary-20261018.json',
               '554b66c8ab159ce01de6b9042ec624ebe31e8beb570b0395d0be6a4f83235880')
CORE_COMMIT = '37903ac616e6b3c1a5228f0acbcfc67acf4df08b'
CORE_PINS = {
    'scripts/collect-source-access.py': '7bc6cc34dc833e907a60239fe3d3b2f0b21d24f3fc7b9ff1c39e1189b614bb8d',
    'offmenu/refresh/acquisition.py': '9a4ffa93b82c10d5971a61e2ce00277ad8e8e5dd58d9fec7d6bf9dfcf826105b',
    'offmenu/refresh/core.py': '795fd06586c446c91be3bb592855e69dc42feb931e9a8044738c5dca94361e52',
}
# Exact reviewed owner export, rebound by code only. No request/env overrides.
SNAPSHOT_COMMIT = '4aa0976b9dc509b91f76874717f9de5e5e5529df'
SNAPSHOT_PIN = ('docs/handover/2026-10-18/foo-owner-custody/snapshots/20261018T133622Z-408b58302fc3a4fd.json',
                '408b58302fc3a4fd498497e8b769d374261b9002b04f368249bb6d088e8b294c')
EXPORTER_COMMIT = '976a6566ffd9b9790e48533eddc2b23e90aac51c'
EXPORTER_PIN = ('scripts/foo-owner-handover.py',
                'a628602ad83299f0e24f746cd36cf85df7ffc6e510200f7023f9c44f54bf1916')
LICENSED_SOURCE_ALLOWLIST = ()
MINIMUM_CACHE_SECONDS = 30 * 86400
MAX_METADATA = 8 * 1024 * 1024
MAX_RECORDS = 100000
MAX_DETAIL = 16 * 1024 * 1024
DISPOSITIONS = {'held', 'partial', 'owned-observation', 'retained-reported', 'unresolved'}
ERRORS = {'corrected-custody-snapshot-not-pinned', 'custody-validator-not-pinned',
          'fixed-input-pin-mismatch', 'fixed-input-invalid', 'custody-import-invalid',
          'adopted-index-invalid', 'metadata-record-limit', 'unexpected-arguments',
          'output-unavailable', 'output-collision', 'detail-size-limit'}
SAFETY = {'networkAcquisitionEnabled': False, 'sourceBodiesRead': False,
          'sourceContentsUploaded': False, 'sourceClaimsChanged': False,
          'reservationsReleased': False, 'safeToAcquireEstablished': False,
          'countryCoverageComplete': False, 'corpusAcceptanceEstablished': False}


def pinned_bytes(root, pin):
    relative, expected = pin
    if (not isinstance(relative, str) or Path(relative).is_absolute()
            or '..' in Path(relative).parts or not re.fullmatch(r'[a-f0-9]{64}', expected)):
        raise RefreshError('fixed-input-invalid')
    path = safe_path(root / relative)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_METADATA:
            raise RefreshError('fixed-input-invalid')
        raw = stream.read(MAX_METADATA + 1)
        after = os.fstat(stream.fileno())
    current = path.stat()
    identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    if len(raw) > MAX_METADATA or identity(before) != identity(after) or identity(after) != identity(current):
        raise RefreshError('fixed-input-invalid')
    if hashlib.sha256(raw).hexdigest() != expected:
        raise RefreshError('fixed-input-pin-mismatch')
    return raw


def imported_snapshot(root):
    if SNAPSHOT_PIN is None:
        raise RefreshError('corrected-custody-snapshot-not-pinned')
    if EXPORTER_PIN is None:
        raise RefreshError('custody-validator-not-pinned')
    for path, digest in CORE_PINS.items():
        pinned_bytes(root, (path, digest))
    validator_bytes = pinned_bytes(root, EXPORTER_PIN)
    validator = types.ModuleType('fixed_owner_custody_validator')
    validator.__file__ = str(root / EXPORTER_PIN[0])
    # Execute the exact reviewed bytes just hashed; never reopen the code path.
    exec(compile(validator_bytes, validator.__file__, 'exec'), validator.__dict__)
    value = strict_json(pinned_bytes(root, SNAPSHOT_PIN))
    try:
        return validator.validate_imported_snapshot(value)
    except Exception:
        raise RefreshError('custody-import-invalid') from None


def _adopted_index(summary):
    if (summary.get('schemaVersion') != 'offmenu-adopted-country-lookup-summary/1'
            or summary.get('commit') != ADOPTED_COMMIT
            or summary.get('registrySHA256') != ADOPTED_REGISTRY_SHA256
            or summary.get('adoptedStatus') != 'REVIEWED_AND_ADOPTED_METADATA_ONLY'
            or not isinstance(summary.get('sourceDescriptorLookup'), dict)):
        raise RefreshError('adopted-index-invalid')
    return summary['sourceDescriptorLookup']


def record_identity(record, target_id, ordinal):
    """Deduplicate only exact, sufficiently identified representations.

    No country expansion or stripped-query URL is a representation identity.
    Unidentified observations remain separate; counts never claim unique files.
    """
    asset = record.get('assetId')
    if asset:
        return 'asset:' + asset
    if record.get('sha256') and record.get('bytes') is not None and record.get('release'):
        source = record.get('sourceId') or record.get('sourceKey') or record.get('sourceUrl')
        if source:
            return 'representation:' + hashlib.sha256(canonical({
                'source': source, 'release': record['release'],
                'sha256': record['sha256'], 'bytes': record['bytes']})).hexdigest()
    return 'observation:' + hashlib.sha256(canonical([target_id, ordinal, record])).hexdigest()


def prepare(summary, snapshot):
    """Pure projection after the exporter has validated the complete snapshot."""
    adopted = _adopted_index(summary)
    if snapshot.get('schemaVersion') != 'offmenu-owner-custody-snapshot/2':
        raise RefreshError('custody-import-invalid')
    for key in ('snapshotIsLiveOwnershipClearance', 'sourceBodiesRead', 'sourceBodiesUploaded',
                'sourceClaimsChanged', 'reservationsReleased', 'networkAcquisitionEnabled'):
        if snapshot.get(key) is not False:
            raise RefreshError('custody-import-invalid')
    details = summary.get('recipeIngredientAndArchiveDetails', [])
    detail_matches = {}
    for item in details:
        if item.get('sourceUrl') and item.get('recordedSHA256') and type(item.get('recordedBytes')) is int:
            key = (item['sourceUrl'], item['recordedSHA256'], item['recordedBytes'])
            detail_matches.setdefault(key, []).append(item)
    groups, packets, unbound, observed = {}, [], [], 0
    reservation_observations = []
    for observation in snapshot['metadata'] + snapshot['discoveredMetadata']:
        projection = observation.get('reconciliation')
        records = projection['records'] if projection else []
        packets.append({'targetId': observation['targetId'], 'access': observation['access'],
                        'pinStatus': observation.get('pinStatus'),
                        'heldBodyRead': observation.get('heldBodyRead'),
                        'bodyWithheldBySourceHold': observation.get('pinStatus') == 'withheld-source-hold',
                        'observedOwner': observation.get('owner'),
                        'recordCount': len(records),
                        'recordsTruncated': bool(projection and projection['recordsTruncated']),
                        'metadataReferences': projection['metadataReferences'] if projection else [],
                        'unavailableFields': projection['unavailableFields'] if projection else []})
        for ordinal, record in enumerate(records):
            observed += 1
            if observed > MAX_RECORDS:
                raise RefreshError('metadata-record-limit')
            source_bound = any(record.get(k) for k in ('assetId', 'sourceId', 'sourceKey', 'sourceUrl'))
            if any(type(record.get(k)) is int for k in ('reservedBytes', 'reservationBytes')):
                reservation_observations.append({'targetId': observation['targetId'], 'recordIndex': ordinal,
                    'sourceBound': source_bound, 'record': record})
            if not source_bound:
                unbound.append({'targetId': observation['targetId'], 'recordIndex': ordinal,
                                'metadataSHA256': observation.get('metadataSHA256'), 'record': record})
                continue
            key = record_identity(record, observation['targetId'], ordinal)
            groups.setdefault(key, []).append((observation, record))
    results = []
    for key, evidence in sorted(groups.items()):
        asset_ids = sorted({r['assetId'] for _, r in evidence if r.get('assetId')})
        matches = [adopted[a] for a in asset_ids if a in adopted]
        match_evidence = [{'assetId': a, 'basis': 'exact-asset-id'} for a in asset_ids if a in adopted]
        adopted_constraints = [item for item in details if item.get('assetId') in asset_ids]
        for _, record in evidence:
            candidate = (record.get('sourceUrl'), record.get('sha256'), record.get('bytes'))
            for item in detail_matches.get(candidate, []):
                if item not in adopted_constraints:
                    adopted_constraints.append(item)
                match = {'assetId': item['assetId'], 'basis': 'same-row-exact-url-sha256-bytes',
                         'observedRelease': record.get('release'), 'adoptedRelease': item.get('release'),
                         'releaseLabelDiffers': bool(record.get('release') and item.get('release')
                                                    and record['release'] != item['release'])}
                if match not in match_evidence:
                    match_evidence.append(match)
                    matches.append({'recordedExistenceState': 'held-locally-with-evidence'
                                    if item.get('heldExistence') is True else 'not-stated',
                                    'reportedPhysicalStatus': item.get('reportedPhysicalStatus')})
        retained = any(m.get('recordedExistenceState') == 'held-locally-with-evidence'
                       or m.get('reportedPhysicalStatus') is True for m in matches)
        holds = any(item.get('holds') for item in adopted_constraints)
        partial, owned, reserved = False, False, False
        for observation, row in evidence:
            states = {str(row.get(k) or '').lower() for k in
                      ('state', 'status', 'claimStatus', 'transferStatus', 'collectionStatus', 'outcome', 'existenceState')}
            # This exact code describes possession, not a source-use hold.
            tokens = {token for state in states - {'held-locally-with-evidence'}
                      for token in re.split('[-_]', state) if token}
            holds |= (bool(row.get('holdCodes')) or row.get('holdsPresent') is True
                      or row.get('held') is True
                      or bool(tokens & {'held', 'blocked', 'quarantined', 'denied', 'stop', 'stopped'})
                      or any(re.search(r'(?:^|[-_])no[-_]retry(?:$|[-_])', state) for state in states))
            partial |= bool(tokens & {'partial', 'interrupted', 'downloading'})
            partial |= any(type(row.get(k)) is int and row[k] > 0
                           for k in ('partialBytes', 'downloadedBytes'))
            owned |= bool(states & {'running', 'active', 'claimed', 'queued', 'pending'}) or row.get('active') is True
            owned |= observation.get('category') == 'claims' and type(row.get('owner')) is int
            reserved |= any(type(row.get(k)) is int and row[k] > 0
                            for k in ('reservedBytes', 'reservationBytes'))
            retained |= (row.get('heldExistence') is True or row.get('reportedPhysicalStatus') is True
                         or row.get('existenceState') == 'held-locally-with-evidence')
            positive = bool(tokens & {'present', 'acquired', 'fetched', 'retained', 'complete', 'completed', 'verified', 'received'})
            negative = bool(tokens & {'missing', 'failed', 'failure', 'denied', 'error'}) or any(
                re.search(r'(?:^|[-_])no[-_](?:body|transfer)(?:$|[-_])', state) for state in states)
            retained |= positive and not negative
            retained |= row.get('complete') is True and bool(row.get('sha256')) and type(row.get('bytes')) is int
        disposition = ('held' if holds else 'partial' if partial else 'owned-observation' if owned
                       else 'retained-reported' if retained else 'unresolved')
        blockers = ['exact-source-selection-not-approved', 'current-ownership-not-cleared',
                    'source-specific-rights-and-budget-not-admitted']
        observed_blockers = sorted({code for _, r in evidence for field in ('blockers', 'unresolved', 'holdCodes')
                                    for code in r.get(field, [])})
        if holds:
            blockers.append('source-hold-retained')
        if partial:
            blockers.append('partial-transfer-reconciliation-required')
        if reserved:
            blockers.append('reservation-reconciliation-required')
        if not matches:
            blockers.append('adopted-id-unmatched-not-absence')
        representations = {(r.get('release'), r.get('sha256'), r.get('bytes'))
                           for _, r in evidence if r.get('sha256')}
        if len(representations) > 1:
            blockers.append('asset-identity-conflict-requires-reconciliation')
        if any(o.get('reconciliation', {}).get('recordsTruncated') for o, _ in evidence):
            blockers.append('metadata-projection-truncated')
        results.append({'identity': key, 'assetIds': asset_ids,
                        'adoptedIdMatch': bool(matches), 'adoptedMatchEvidence': match_evidence,
                        'adoptedConstraints': [{'assetId': item['assetId'], 'holds': item.get('holds', []),
                            'unresolved': item.get('unresolved', [])} for item in adopted_constraints],
                        'retainedEvidenceObserved': retained,
                        'disposition': disposition, 'blockers': blockers, 'observedBlockerCodes': observed_blockers,
                        'acquisitionEnabled': False, 'observations': [
                            {'targetId': o['targetId'], 'metadataSHA256': o.get('metadataSHA256'),
                             'record': r} for o, r in evidence]})
    counts = {name: sum(r['disposition'] == name for r in results) for name in sorted(DISPOSITIONS)}
    return {'schemaVersion': DETAIL_SCHEMA, 'status': 'prepared',
            'adoptedCommit': ADOPTED_COMMIT, 'adoptedRegistrySHA256': ADOPTED_REGISTRY_SHA256,
            'inputPins': {'adoptedLookupCommit': SUMMARY_COMMIT, 'adoptedLookup': SUMMARY_PIN,
                          'snapshotCommit': SNAPSHOT_COMMIT, 'snapshot': SNAPSHOT_PIN, 'validatorCommit': EXPORTER_COMMIT, 'validator': EXPORTER_PIN,
                          'acquisitionCoreCommit': CORE_COMMIT, 'acquisitionCoreFiles': CORE_PINS},
            'snapshotObservedAt': snapshot['observedAt'], 'cutoverSHA256': snapshot.get('cutoverSHA256'),
            'preservedCutoverConstraints': {k: snapshot.get('baseline', {}).get(k) for k in
                ('hold_propagation', 'ph20', 'active_or_uncertain', 'transport_uncertainty', 'global_holds')},
            'packets': packets, 'sources': results, 'unboundObservations': unbound,
            'snapshotDiagnostics': {k: snapshot.get('discovery', {}).get(k) for k in
                ('claimsCatalogIdentified', 'reservationsCatalogIdentified', 'scopeExhaustive', 'unidentifiedIsEmpty')},
            'capacityEvidence': {'observations': snapshot.get('capacity', []),
                'planningBaseline': snapshot.get('baseline', {}).get('capacity'),
                'reservationObservations': reservation_observations,
                'reservationTotalsAuthoritative': False, 'admissionBudgetEstablished': False,
                'unknownCommitmentsAssumedZero': False},
            'reservationObservationCount': len(reservation_observations),
            'unboundReservationObservationCount': sum(not row['sourceBound'] for row in reservation_observations),
            'withheldPacketCount': sum(row['bodyWithheldBySourceHold'] for row in packets),
            'counts': counts, 'observations': observed, 'sourceDispositions': len(results),
            'unboundObservationCount': len(unbound),
            'sourceBoundObservations': observed - len(unbound),
            'scopeExhaustive': False, 'unmatchedMeansMissing': False,
            'minimumCacheSeconds': MINIMUM_CACHE_SECONDS, 'licensedSourcesSelected': 0,
            'networkRequests': 0, 'networkBytesRead': 0, **SAFETY}


def summary_report(detail=None, error=None):
    value = {'schemaVersion': SCHEMA, 'status': 'blocked' if error else 'prepared',
             'errorCode': error, 'detailSHA256': None if detail is None else hashlib.sha256(canonical(detail)).hexdigest(),
             'snapshotSHA256': None if SNAPSHOT_PIN is None else SNAPSHOT_PIN[1],
             'counts': {} if detail is None else detail['counts'],
             'observations': 0 if detail is None else detail['observations'],
             'sourceDispositions': 0 if detail is None else detail['sourceDispositions'],
             'packetCount': 0 if detail is None else len(detail['packets']),
             'unboundObservationCount': 0 if detail is None else detail['unboundObservationCount'],
             'sourceBoundObservations': 0 if detail is None else detail['sourceBoundObservations'],
             'reservationObservationCount': 0 if detail is None else detail['reservationObservationCount'],
             'unboundReservationObservationCount': 0 if detail is None else detail['unboundReservationObservationCount'],
             'withheldPacketCount': 0 if detail is None else detail['withheldPacketCount'],
             'networkRequests': 0, 'networkBytesRead': 0, 'licensedSourcesSelected': 0,
             'minimumCacheSeconds': MINIMUM_CACHE_SECONDS, **SAFETY}
    return sanitize_report(value)


def sanitize_report(value):
    keys = {'schemaVersion', 'status', 'errorCode', 'detailSHA256', 'snapshotSHA256', 'counts',
            'observations', 'sourceDispositions', 'packetCount', 'unboundObservationCount',
            'sourceBoundObservations', 'reservationObservationCount', 'unboundReservationObservationCount',
            'withheldPacketCount', 'networkRequests', 'networkBytesRead',
            'licensedSourcesSelected', 'minimumCacheSeconds'} | set(SAFETY)
    if not isinstance(value, dict) or set(value) != keys or value['schemaVersion'] != SCHEMA:
        raise ValueError('invalid-summary')
    if value['status'] not in {'prepared', 'blocked'} or value['errorCode'] not in ERRORS | {None}:
        raise ValueError('invalid-summary')
    if (value['status'] == 'blocked') != (value['errorCode'] is not None):
        raise ValueError('invalid-summary')
    for key in ('detailSHA256', 'snapshotSHA256'):
        if value[key] is not None and not re.fullmatch(r'[a-f0-9]{64}', value[key]):
            raise ValueError('invalid-summary')
    if value['status'] == 'prepared' and (value['detailSHA256'] is None or value['snapshotSHA256'] is None):
        raise ValueError('invalid-summary')
    for key in ('observations', 'sourceDispositions', 'packetCount', 'unboundObservationCount',
                'sourceBoundObservations', 'reservationObservationCount', 'unboundReservationObservationCount',
                'withheldPacketCount'):
        if type(value[key]) is not int or not 0 <= value[key] <= MAX_RECORDS:
            raise ValueError('invalid-summary')
    if (value['sourceBoundObservations'] + value['unboundObservationCount'] != value['observations']
            or value['sourceDispositions'] > value['sourceBoundObservations']
            or value['unboundReservationObservationCount'] > value['reservationObservationCount']
            or value['reservationObservationCount'] > value['observations']
            or value['withheldPacketCount'] > value['packetCount']):
        raise ValueError('invalid-summary')
    if not isinstance(value['counts'], dict) or not set(value['counts']) <= DISPOSITIONS:
        raise ValueError('invalid-summary')
    if any(type(n) is not int or not 0 <= n <= MAX_RECORDS for n in value['counts'].values()):
        raise ValueError('invalid-summary')
    if sum(value['counts'].values()) != value['sourceDispositions']:
        raise ValueError('invalid-summary')
    for key, expected in SAFETY.items():
        if value[key] is not expected:
            raise ValueError('invalid-summary')
    for key in ('networkRequests', 'networkBytesRead', 'licensedSourcesSelected'):
        if type(value[key]) is not int or value[key] != 0:
            raise ValueError('invalid-summary')
    if type(value['minimumCacheSeconds']) is not int or value['minimumCacheSeconds'] != MINIMUM_CACHE_SECONDS:
        raise ValueError('invalid-summary')
    return dict(value)


def save_detail(detail):
    """Write one immutable metadata receipt inside the existing output root."""
    raw = canonical(detail)
    if len(raw) > MAX_DETAIL:
        raise RefreshError('detail-size-limit')
    root = safe_path(OUTPUT)
    if not root.is_dir() or root.stat().st_uid != os.getuid():
        raise RefreshError('output-unavailable')
    path = safe_path(root / ('collection-preparation-' + hashlib.sha256(raw).hexdigest() + '.json'))
    # Publish atomically with no replacement: an interrupted write cannot leave
    # a partial final receipt that turns an otherwise safe retry into a collision.
    with tempfile.NamedTemporaryFile(dir=root, prefix='.collection-preparation-', delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
            try:
                os.link(temporary, path)
            except FileExistsError:
                info = path.stat()
                if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size != len(raw)
                        or path.read_bytes() != raw):
                    raise RefreshError('output-collision') from None
        finally:
            temporary.unlink(missing_ok=True)



def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    try:
        if argv:
            raise RefreshError('unexpected-arguments')
        snapshot = imported_snapshot(ROOT)
        adopted = strict_json(pinned_bytes(ROOT, SUMMARY_PIN))
        detail = prepare(adopted, snapshot)
        save_detail(detail)
        report = summary_report(detail)
    except (RefreshError, OSError, ValueError, TypeError, KeyError) as error:
        code = str(error) if isinstance(error, RefreshError) and str(error) in ERRORS else 'fixed-input-invalid'
        report = summary_report(error=code)
    print(canonical(report).decode())
    return 0 if report['status'] == 'prepared' else 2


if __name__ == '__main__':
    raise SystemExit(main())
