#!/usr/bin/env python3
"""Finite real-value caller probes; only aggregate results leave the worker.

Whole-index coverage belongs to the separate namespace proof. This exercise
does not rescan every key or claim application-serving/identity acceptance.
"""
import argparse
import collections
import contextlib
import fcntl
import json
import os
import time
import uuid
from pathlib import Path
from derive_north_star_bulk import encoded, fsync_dir, sha_file
from source_scoped_north_star_consumer import SourceScopedConsumer


SQL = '''SELECT i.key_sha,i.source,i.release,i.namespace,i.lexical
FROM identifiers i
WHERE EXISTS(SELECT 1 FROM unique_product_keys k
             WHERE k.subject=i.subject AND k.key_sha=i.key_sha)
AND EXISTS(SELECT 1 FROM resolved_edges e
           WHERE e.subject=i.subject AND e.has_context=1)
ORDER BY i.key_sha,i.subject,i.assertion_id LIMIT ?'''


def exercise(source, bulk, basis, bulk_pin, basis_pin, max_keys=64, seconds=600):
    if type(max_keys) is not int or not 1 <= max_keys <= 128:
        raise ValueError('finite key limit must be an integer between 1 and 128')
    if type(seconds) is not int or not 1 <= seconds <= 1200:
        raise ValueError('bounded whole exercise deadline required')
    deadline = time.monotonic() + seconds
    counts = collections.Counter()
    groups = {}
    seen = set()
    with contextlib.ExitStack() as stack:
        for root in (bulk, basis):
            lock = stack.enter_context((root / '.writer.lock').open('rb'))
            fcntl.flock(lock.fileno(), fcntl.LOCK_SH | fcntl.LOCK_NB)
        reader = SourceScopedConsumer(source, bulk, basis, bulk_pin, basis_pin)
        stack.callback(reader.close)
        reader.index.set_progress_handler(lambda: int(time.monotonic() >= deadline), 10000)
        # The identifiers PK supplies this order; no full-key sorting or new
        # index is requested. Bound duplicate assertion rows separately.
        rows = reader.index.execute(SQL, (max_keys * 16,))
        for key, source_id, release, namespace, lexical in rows:
            if key in seen:
                continue
            if time.monotonic() >= deadline:
                raise TimeoutError('caller exercise deadline reached')
            seen.add(key)
            if reader.lookup(source_id, release, namespace, lexical)['status'] != 'candidates-not-requested':
                raise ValueError('candidate opt-in boundary differs')
            result = reader.lookup(source_id, release, namespace, lexical, include_candidates=True)
            if result['status'] != 'source-scoped-candidate-context' or len(result['products']) != 1:
                raise ValueError('selected connected source key did not return one candidate product')
            if result['acceptedIdentityJoins'] != 0 or any(result[k] is not False for k in (
                    'automaticPlanningEligible', 'nutritionAggregationEligible', 'servedApplicationActivation')):
                raise ValueError('caller admission boundary differs')
            c = groups.setdefault((source_id, release, namespace), collections.Counter())
            c['sourceKeyQueries'] += 1
            product = result['products'][0]
            c['productOccurrences'] += 1
            c['citationOccurrences'] += len(product['citations'])
            for profile in product['profiles']:
                c['profileOccurrences'] += 1
                c['citationOccurrences'] += len(profile['citations'])
                context = profile['nutrientContextCandidates']
                if context is None:
                    c['profilesWithoutNutrientContext'] += 1
                else:
                    for assertion in context['assertions']:
                        fields = assertion['value']['fields']
                        quantity = fields.get('quantity')
                        if quantity is None:
                            continue
                        c['nutrientContextOccurrences'] += 1
                        c['unknownQuantityOccurrences'] += int(quantity.get('value') is None)
                        c['zeroQuantityOccurrences'] += int(quantity.get('value') == 0)
                restored = profile['perNutrientBasisCandidates']
                if restored is None:
                    c['profilesWithoutBasisCandidate'] += 1
                else:
                    c['profilesWithBasisCandidate'] += 1
                    c['restoredBasisTargetOccurrences'] += restored['matchedNutrientAssertions']
                    for group in restored['basisGroups']:
                        c['unknownBasisGroupOccurrences'] += int(group['stateStatus'] == 'unknown')
            if len(seen) == max_keys:
                break
        if time.monotonic() >= deadline:
            raise TimeoutError('caller exercise deadline reached')
        for c in groups.values():
            counts.update(c)
        expected_keys = reader.bulk['consumerIndex']['queries']['identifierProductProfileNutrientContextJoins']['count']
        if expected_keys and not seen:
            raise ValueError('completed connected-key index produced no caller probes')
        pins = dict(reader.pins,
                    bulkConsumerIndexSha256=reader.bulk['consumerIndex']['sqliteSha256'],
                    basisConsumerProofSha256=reader.basis['consumerProof']['sqliteSha256'])
    return {
        'schemaVersion': 'offmenu-north-star-source-consumer-probe/1',
        'status': 'finite-source-scoped-local-caller-exercised' if seen else 'no-connected-source-keys-available',
        'sourcePins': pins,
        'codePins': {name: sha_file(Path(__file__).with_name(name)) for name in (
            'exercise_source_scoped_consumer.py', 'source_scoped_north_star_consumer.py',
            'derive_north_star_bulk.py', 'north_star_derivations.py')},
        'selectionSql': SQL,
        'maxSourceKeys': max_keys,
        'wholeIndexConnectedSourceKeys': expected_keys,
        'groups': [dict(sourceId=s, sourceRelease=r, namespace=n, **dict(c))
                   for (s, r, n), c in sorted(groups.items())],
        'counts': dict(counts),
        'rawRecordValuesExported': False,
        'lexicalIdentifiersExported': False,
        'inputsOpenedReadOnly': True,
        'acceptedIdentityJoins': 0,
        'servedApplicationQueries': 0,
        'fullNorthStarComplete': False,
        'limits': 'Finite source-key value-returning caller probes only; repeated profiles are occurrences, '
                  'not distinct foods. Whole-index namespace SQL reports coverage separately. '
                  'No food identity, nutrient comparability, recipe nutrition, planning or app activation.'}


def publish_report(path, result):
    """Durable create-only publication; never replace a prior/foreign report."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp-' + uuid.uuid4().hex)
    try:
        with temp.open('xb') as handle:
            handle.write(encoded(result));handle.flush();os.fsync(handle.fileno())
        os.link(temp, path)  # Atomic and fails if the final path already exists.
        fsync_dir(path.parent)
    finally:
        if temp.exists():
            temp.unlink();fsync_dir(path.parent)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    for name in ('source', 'bulk', 'basis'):
        p.add_argument(name, type=Path)
    p.add_argument('bulk_pin'); p.add_argument('basis_pin'); p.add_argument('output', type=Path)
    p.add_argument('--max-keys', type=int, default=64); p.add_argument('--seconds', type=int, default=600)
    a = p.parse_args()
    if a.output.exists():
        raise ValueError('immutable caller report already exists')
    result = exercise(a.source, a.bulk, a.basis, a.bulk_pin, a.basis_pin, a.max_keys, a.seconds)
    publish_report(a.output, result)
    print(json.dumps({'status': result['status'], 'counts': result['counts']}))
