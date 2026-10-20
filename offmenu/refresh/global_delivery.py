"""Owned metadata adapter over the reviewed global coverage/run harness.

No source callbacks, plugins, raw/derivative reads or staging writer are loaded.
The six-type projection is routing evidence, never canonical domain acceptance.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

from . import coverage, global_run
from .core import RefreshError, canonical, sha, strict_json
from .portfolio05 import _read_bounded_regular
from .retained_policy import plan_retained_input

TYPES = ('ingredients', 'recipes', 'nutrition', 'retailers/providers',
         'prices/baskets', 'dietary references')
SCHEMA = 'offmenu-global-delivery-plan/1'
MAX_METADATA = 16 * 1024 * 1024


def read_metadata(pin, *, reader=_read_bounded_regular):
    """Only explicitly selected metadata pins; never follow embedded pointers."""
    if not isinstance(pin, dict) or not isinstance(pin.get('path'), str):
        raise RefreshError('metadata-pin-required')
    raw = reader(pin['path'], MAX_METADATA, 'delivery-metadata')
    if sha(raw) != pin.get('sha256') or ('bytes' in pin and pin['bytes'] != len(raw)):
        raise RefreshError('delivery-metadata-pin-mismatch')
    return strict_json(raw)


def projection_row(document, required_type):
    """Reconcile observed row containers and one explicit spelling alias only."""
    if not isinstance(document, dict):
        raise RefreshError('projection-document-object-required')
    found = []
    for container in ('categories', 'sixCategoryRows', 'rows'):
        rows = document.get(container)
        if isinstance(rows, dict):
            pairs = [(key, value, '/' + container + '/' + key.replace('~', '~0').replace('/', '~1'))
                     for key, value in rows.items()]
        elif isinstance(rows, list):
            if any(not isinstance(row, dict) for row in rows):
                raise RefreshError('projection-row-object-required')
            pairs = [(row.get('category', row.get('requiredType', row.get('type'))), row,
                      '/' + container + '/' + str(index))
                     for index, row in enumerate(rows)]
        else:
            continue
        for name, row, selector in pairs:
            alias = name == 'ingredients/composition' and required_type == 'ingredients'
            if name == required_type or alias:
                if not isinstance(row, dict):
                    raise RefreshError('projection-row-object-required')
                found.append({'selector': selector, 'row': row,
                              'fieldAlias': 'ingredients/composition -> ingredients' if alias else None,
                              'semanticEquivalenceInferred': False})
    if len(found) != 1:
        raise RefreshError('projection-row-missing-or-ambiguous')
    return found[0]


def validate_registry(partition, seed, crosswalk):
    owners = partition['countryToOwner']
    countries = set(coverage.COUNTRIES)
    if set(owners) != countries or any(type(v) is not int or not 1 <= v <= 64 for v in owners.values()):
        raise RefreshError('delivery-owner-registry-mismatch')
    actual = [(r['country'], r['requiredType']) for r in seed['cells']]
    expected = {(country, category) for country in countries for category in TYPES}
    if len(actual) != 1494 or set(actual) != expected:
        raise RefreshError('projection-denominator-mismatch')
    if any(r['deliveryOwner'] != owners[r['country']] for r in seed['cells']):
        raise RefreshError('projection-owner-mismatch')
    cells = crosswalk['cells']
    actual = [(r['country'], r['canonicalDomain']) for r in cells]
    expected = {(country, domain) for country in countries for domain in coverage.DOMAINS}
    if (len(actual) != 3237 or set(actual) != expected
            or set(crosswalk['canonicalDomains']) != set(coverage.DOMAINS)
            or any(r['owner'] != owners[r['country']] for r in cells)):
        raise RefreshError('canonical-denominator-or-owner-mismatch')
    routes = crosswalk['projection']
    if (len(routes) != 13 or {r['canonicalDomain'] for r in routes} != set(coverage.DOMAINS)
            or any(not set(r['relatedSixTypes']) <= set(TYPES) or r.get('acceptanceInferred') is not False
                   for r in routes)):
        raise RefreshError('canonical-route-mismatch')
    return owners


def adapt59(document, owners):
    """Consume the owned immutable metadata plan; no binding/body pointers opened."""
    if document.get('schemaVersion') != 'offmenu-worker59-retained-runplan/1' or document.get('owner') != 59:
        raise RefreshError('retained-adapter-schema')
    countries = {country for country, owner in owners.items() if owner == 59}
    result = {}
    for key, names in (('cells', coverage.DOMAINS), ('projectionCells', TYPES)):
        rows = document[key]
        expected = {(country, category) for country in countries for category in names}
        actual = [(r['country'], r['requiredType']) for r in rows]
        if (len(actual) != len(expected) or set(actual) != expected
                or any(r['deliveryOwner'] != 59 for r in rows)):
            raise RefreshError('retained-adapter-owner-or-denominator')
        result[key] = {(r['country'], r['requiredType']): r for r in rows}
    batches = document['candidateBatches']
    if len({b['batchId'] for b in batches}) != len(batches) or any(
            b['country'] not in countries or b['deliveryOwner'] != 59 for b in batches):
        raise RefreshError('retained-adapter-batch-owner')
    result['batches'] = batches
    result['highestReadySubsets'] = document.get('highestReadySubsets', [])
    return result


def closed_gate(*, has_holds=False):
    # This adapter never accepts authority declarations or output-identity claims
    # as executable capabilities. Those belong to reviewed trusted source code.
    return {'eligibility': 'BLOCKED_STAGING_AUTHORITY', 'sourceExecutionSucceeded': False,
            'successfulDatasetNoop': False, 'acceptedStagingCells': 0,
            'acceptedStagingRecords': 0, 'sourceHoldPresent': has_holds,
            'replayRefreshResult': 'NOT_EXECUTED_AUTHORITY_UNBOUND'}


def join_selected_scope(config, plan, batches, custody):
    """Refuse cross-source config/evidence before resolving any batch blocker."""
    try:
        scope, inputs, selected = config['selectedScope'], plan['input'], plan['selection']
        matches = [batch for batch in batches if batch['batchId'] == scope['batchId']]
        if len(matches) != 1:
            raise RefreshError('selected-batch-not-unique')
        batch = matches[0]
        identity = inputs['sourceIdentity']
        pin_identity = lambda pin: (pin['path'], pin['sha256'])
        if (plan['schemaVersion'] != 'offmenu-wfp-selected-normalization-plan/1'
                or plan['owner'] != 59 or selected['writer'] != 59
                or selected['executionOwner'] != selected['writer']
                or selected['managementOperationResolved'] is not True
                or selected['managementWriterResolved'] is not True
                or scope['executionWriter'] != selected['writer']
                or batch['deliveryOwner'] != selected['executionOwner']
                or scope['operation'] != selected['operation']
                or not isinstance(scope['operation'], str) or not scope['operation'].strip()
                or scope['country'] != inputs['country'] or batch['country'] != inputs['country']
                or inputs['country'] != 'LY'
                or type(inputs['records']) is not int or inputs['records'] != 69273
                or type(scope['records']) is not int or scope['records'] != inputs['records']
                or type(batch['candidateRecords']) is not int or batch['candidateRecords'] != inputs['records']
                or any(not isinstance(identity[key], str) or not identity[key].strip()
                       for key in ('sourceId', 'releaseId', 'sourceBodySha256', 'useScope'))
                or scope['sourceIdentity'] != identity or batch['sourceIdentity'] != identity
                or pin_identity(scope['derivative']) != pin_identity(inputs['derivative'])
                or pin_identity(batch['derivative']) != pin_identity(inputs['derivative'])
                or pin_identity(inputs['priorPlan']) != pin_identity(config['owner59'])
                or pin_identity(scope['sourceSelection']) != pin_identity(selected['source'])
                or scope['sourceSelectionLedgerSequence'] != selected['ledgerSequence']
                or batch['originalAcquiredAt'] != inputs['originalAcquiredAt']):
            raise RefreshError('selected-execution-scope-mismatch')
        source, acquisition = custody['source'], custody['custody']
        claim = acquisition['claimFields']
        if (custody['owner'] != 27 or acquisition['historicalAcquisitionCustodian'] != 27
                or claim['owner'] != 27 or claim['country'] != inputs['country']
                or source['recordedSha256'] != identity['sourceBodySha256']
                or source['release'] != identity['releaseId'] or claim['release'] != identity['releaseId']
                or source['originalAcquiredAt'] != inputs['originalAcquiredAt']
                or custody['sourceUseEvidence']['denialClause'] is not None):
            raise RefreshError('custody-use-evidence-mismatch')
    except (KeyError, TypeError, AttributeError):
        raise RefreshError('selected-scope-required-fields-invalid') from None


def batch_plan(batch, *, now, policy_pin, selection, metadata_pin, custody_evidence=None):
    selected = batch['batchId'] == selection.get('batchId')
    identity = batch.get('sourceIdentity', {})
    # The verified input is metadata, not a secretly reopened derivative body.
    # This policy identity cannot prove a body identity/no-op. Preserve the
    # source acquisition clock while naming the actual input being planned.
    age_plan = plan_retained_input(
        source_id=identity['sourceId'], release_id=identity['releaseId'],
        input_pins={'owner59-runplan-metadata': {'sha256': metadata_pin['sha256'],
                                               'bytes': metadata_pin['bytes']}},
        policy_sha256=policy_pin,
        scope_sha256=sha(canonical({'batchId': batch['batchId'],
                                    'scope': selection if selected else identity})),
        original_acquired_at=batch.get('originalAcquiredAt'), now=now,
        validated_at=batch.get('validatedAt'))
    original_age = age_plan['acquisitionAgeSeconds']
    resolved = {'STAGING_SCOPE_AND_WRITER_NOT_SELECTED'} if selected else set()
    custody_bound = selected and custody_evidence is not None
    if custody_bound:
        resolved.add('ORIGINAL_CUSTODIAN_NOT_QUALIFIED')
    blockers = [v for v in batch.get('blockedFields', []) if v not in resolved]
    blockers += ['EXACT_EXISTING_STAGING_DESTINATION_UNBOUND', 'REVIEWED_TRUSTED_BINDING_UNBOUND']
    if not custody_bound:
        blockers.append('EXACT_SNAPSHOT_USE_CUSTODY_UNQUALIFIED')
    return {**batch, **closed_gate(), 'historicalOwnerEligibility': batch.get('eligibility'),
            'managementSelection': selection if selected else None,
            'executionWriter': selection['executionWriter'] if selected else None,
            'operationSelected': selection['operation'] if selected else None,
            'sourceCustodian': 27 if custody_bound else batch.get('sourceCustodian'),
            'custodyUseEvidence': custody_evidence if custody_bound else None,
            'custodyUseExtent': 'ACTUAL_HISTORICAL_ACQUIRER_AND_RETAINED_SOURCE_DECLARED_USE; '
                               'NOT_FULL_LEGAL_TEXT_AUDIT_OR_FRESH_BODY_IDENTITY' if custody_bound else None,
            'originalAcquisitionAgeSeconds': original_age,
            'cacheAgeObservation': ('original-acquisition-time-missing' if original_age is None else
                                   'reuse-window-under-30-days' if original_age < 30 * 86400 else
                                   'revalidation-required'),
            'retainedPolicyPlan': age_plan,
            'retainedPolicyIdentityScope': 'VERIFIED_METADATA_INPUT_ONLY_NOT_DATASET_BODY',
            'blockedFields': sorted(set(blockers)),
            'currentBodyIdentityVerified': False,
            'priorReuseKeyDeclaration': batch.get('reuseKey'),
            'nextAction': '00 pins existing destination/volume and native-engine lookup; if no suitable handler, '
                          '59 implements narrow authored-fixture normalizer,45 reviews code; '
                          '59 executes only after binding review; independent output review27 unless handlerauthor then45.'
                          if selected else batch.get('requiredDecision')}


def build(config, *, reader=read_metadata):
    partition, seed, crosswalk = (reader(config[key]) for key in ('partition', 'seed', 'crosswalk'))
    owners = validate_registry(partition, seed, crosswalk)
    retained = adapt59(reader(config['owner59']), owners)
    selected_plan = reader(config['selectedExecutionPlan'])
    custody = reader(config['custodyUseEvidence'])
    join_selected_scope(config, selected_plan, retained['batches'], custody)
    evidence = reader(config['ledgerEvidence'])
    diagnostics, packet_refs, labels = [], {}, {}
    workers = partition['workers']
    if len(workers) != 64 or {w['owner'] for w in workers} != set(range(1, 65)):
        raise RefreshError('owner-packet-registry-mismatch')
    for worker in workers:
        owner, pin = worker['owner'], worker['packet']
        packet_refs[owner] = pin
        try:
            packet = reader(pin)
            if packet['owner'] != owner or set(packet['countryCodes']) != set(worker['countries']):
                raise RefreshError('owner-packet-country-mismatch')
            for country in packet['countries']:
                if owners[country['country']] != owner:
                    raise RefreshError('owner-packet-owner-mismatch')
                labels[country['country']] = country.get('sourceCustodianLabelsRetained', [])
        except (OSError, ValueError, KeyError, TypeError) as error:
            diagnostics.append({'owner': owner, 'kind': 'OWNER_PACKET_METADATA_INVALID',
                                'errorType': type(error).__name__, 'pin': pin})
    projection, documents, fixes = [], {}, Counter()
    for row in sorted(seed['cells'], key=lambda r: (r['country'], r['requiredType'])):
        country, category, owner = row['country'], row['requiredType'], row['deliveryOwner']
        pin = row['categoryEvidence']
        parsed, issue = None, None
        try:
            key = (pin['path'], pin['sha256'], 'bytes' in pin, canonical(pin.get('bytes')))
            if key not in documents:
                try:
                    document = reader(pin)
                    if not isinstance(document, dict):
                        raise RefreshError('projection-document-object-required')
                    documents[key] = (document, None)
                except (OSError, ValueError, KeyError, TypeError) as error:
                    documents[key] = (None, 'projection-document-object-required'
                                      if isinstance(error, RefreshError)
                                      and str(error) == 'projection-document-object-required'
                                      else type(error).__name__)
            document, issue = documents[key]
            if document is not None:
                parsed = projection_row(document, category)
                if row.get('retainedCategory') is None:
                    fixes['seedGapResolved'] += 1
                    fixes['fieldAlias' if parsed['fieldAlias'] else 'alternateContainer'] += 1
        except (ValueError, KeyError, TypeError) as error:
            issue = str(error) if isinstance(error, RefreshError) and str(error) in (
                'projection-document-object-required', 'projection-row-object-required',
                'projection-row-missing-or-ambiguous') else type(error).__name__
        adapted = retained['projectionCells'].get((country, category), {})
        projection.append({'country': country, 'requiredType': category, 'deliveryOwner': owner,
                           'sourceCustodian': adapted.get('sourceCustodian'),
                           'sourceCustodianLabels': labels.get(country, []),
                           'source': adapted.get('source', [pin]), 'review': adapted.get('review', []),
                           'handler': adapted.get('handler'), 'ownerPacket': packet_refs[owner],
                           'originalAcquiredAt': adapted.get('originalAcquiredAt'),
                           'validatedAt': adapted.get('validatedAt'), 'categoryEvidence': pin,
                           'retainedCategory': parsed, 'metadataIssue': issue,
                           'reasons': adapted.get('reasons', ['EXACT_SOURCE_DOMAIN_EXECUTION_CONTRACT_UNBOUND']),
                           'provenanceCoverage': adapted.get('provenanceCoverage', 'CONTROL_METADATA_ONLY'),
                           'candidateBatchIds': adapted.get('candidateBatchIds', []),
                           **closed_gate()})
        if issue:
            diagnostics.append({'country': country, 'requiredType': category,
                                'kind': 'COVERAGE_METADATA_INVALID', 'errorType': issue, 'pin': pin})
    assessed = coverage.assess(config['matrixPath'], config['sourceLedgerPath'])
    report = global_run.run(assessed, bindings={}, limits=global_run.Limits(workers=4, max_sources=4096),
                            fetch_policy='reuse')
    canonical_cells = []
    routes = {r['canonicalDomain']: r['relatedSixTypes'] for r in crosswalk['projection']}
    for country in sorted(owners):
        for domain in coverage.DOMAINS:
            source_rows = [r for r in assessed['sources'] if country in r['countries'] and domain in r['domains']]
            adapted = retained['cells'].get((country, domain), {})
            holds = [{'sourceId': r['sourceId'], 'holds': r['holds']} for r in source_rows if r.get('holds')]
            canonical_cells.append({
                'country': country, 'requiredType': domain, 'deliveryOwner': owners[country],
                'sourceCustodian': adapted.get('sourceCustodian'),
                'sourceCustodianLabels': labels.get(country, []),
                'source': adapted.get('source', []), 'review': adapted.get('review', []),
                'handler': adapted.get('handler'), 'originalAcquiredAt': adapted.get('originalAcquiredAt'),
                'validatedAt': adapted.get('validatedAt'), 'sourceHolds': holds,
                'inventorySourceIds': [r['sourceId'] for r in source_rows],
                'sourceInventoryPins': assessed.get('inventoryPins', {}),
                'historicalHandlersAreExecutionAuthority': False,
                'relatedSixTypes': routes[domain], 'routingIsSemanticAcceptance': False,
                'notApplicable': None, 'ownerPacket': packet_refs[owners[country]],
                'reasons': adapted.get('reasons', ['EXACT_SOURCE_DOMAIN_EXECUTION_CONTRACT_UNBOUND']),
                'candidateBatchIds': adapted.get('candidateBatchIds', []),
                'provenanceCoverage': adapted.get('provenanceCoverage', 'HISTORICAL_DISCOVERY_METADATA_ONLY'),
                **closed_gate(has_holds=bool(holds))})
    batches = [batch_plan(b, now=config['now'], policy_pin=config['retainedPolicySha256'],
                          selection=config['selectedScope'], metadata_pin=config['owner59'],
                          custody_evidence=config['custodyUseEvidence'])
               for b in retained['batches']]
    result = {'schemaVersion': SCHEMA, 'mode': 'BOUNDED_METADATA_ASSESSMENT_ONLY',
              'observedAt': config['now'], 'retainedPolicySha256': config['retainedPolicySha256'],
              'pins': {k: config[k] for k in
                  ('partition', 'seed', 'crosswalk', 'owner59', 'ledgerEvidence', 'selectedExecutionPlan', 'custodyUseEvidence')},
              'canonicalAction': {'key': None, 'generation': None, 'declaration': None, 'eligible': False},
              'denominators': {'countries': 249, 'canonicalDomains': 13, 'canonicalCells': 3237,
                               'sixTypeProjectionCells': 1494, 'historicalDiscoveredSources': 1303},
              'canonicalCells': canonical_cells, 'projectionCells': projection,
              'schemaReconciliation': dict(fixes), 'diagnostics': diagnostics,
              'candidateBatches': batches, 'dependencyReadySubsets': retained['highestReadySubsets'],
              'selectedExecutionScope': selected_plan,
              'currentSelectedScopeUpdates': {
                  'writer': 59, 'operation': config['selectedScope']['operation'],
                  'custodyAndDeclaredUseEvidence': custody,
                  'supersedesHistoricalMissingFields': ['management operation/writer', 'actual historical acquisition custodian',
                                                        'retained declared use/attribution'],
                  'unresolved': ['reviewed immutable retained-only normalizer/schema/isolation/limits',
                                 'exact existing approved host/path/volume/writer limits/commit-resume contract',
                                 'current derivative identity and independently reviewed actual output'],
                  'noFreshBodyOrFullLegalTextAuditInferred': True},
              'ledgerEvidence': evidence,
              'existingHarnessResult': global_run.compact(report),
              'nativeSourceBindingsLoaded': 0, 'sourceBodiesRead': 0, 'derivativeBodiesRead': 0,
              'networkRequests': 0, 'acceptedStagingRecords': 0, 'acceptedStagingCells': 0,
              'goldAdmittedRecords': 0, 'countriesComplete': 0,
              'status': 'BLOCKED_STAGING_AUTHORITY', 'successfulDatasetNoop': False,
              'holds': ['source-use/privacy/custody/denial', 'FI/Frida/native-NO-FR',
                        'production/CIX paused', 'DEV7645/UI', 'mandatory auto_review'],
              'nextAction': 'Morgan consumes exact pending source/handler/destination scope; '
                            'SAME45 reviews owned immutable adapter; 00 integrates. Original country owners execute.'}
    result['planIdentitySha256'] = sha(canonical({'pins': result['pins'],
                                               'retainedPolicySha256': result['retainedPolicySha256'],
                                               'selectedScope': config['selectedScope'],
                                               'schemaVersion': SCHEMA}))
    return result, report


def preflight_publication(report, path):
    """Check existing output conflicts without publishing any artifact."""
    path = Path(path)
    expected = global_run.stream_report(report)
    if path.exists() or path.is_symlink():
        raw = _read_bounded_regular(path, 64 * 1024 * 1024, 'delivery-output')
        if (sha(raw), len(raw)) != expected:
            raise RefreshError('delivery-existing-output-identity-mismatch')
        return expected, True
    return expected, False


def publish(report, path):
    """Own metadata artifact replay only; never a dataset successful no-op."""
    expected, replay = preflight_publication(report, path)
    if replay:
        return {'sha256': expected[0], 'bytes': expected[1], 'artifactReplay': True,
                'artifactBytesWritten': 0, 'successfulDatasetNoop': False}
    digest, size = global_run.write_report(report, path)
    return {'sha256': digest, 'bytes': size, 'artifactReplay': False,
            'artifactBytesWritten': size, 'successfulDatasetNoop': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--output-root', required=True)
    args = parser.parse_args(argv)
    config = strict_json(_read_bounded_regular(args.config, MAX_METADATA, 'delivery-config'))
    result, harness = build(config)
    root = Path(args.output_root)
    preflight_publication(result, root / 'manifest.json')
    preflight_publication(harness, root / 'global-run.json')
    outputs = {'manifest': publish(result, root / 'manifest.json'),
               'harness': publish(harness, root / 'global-run.json')}
    print(json.dumps({'status': result['status'], 'denominators': result['denominators'],
                      'schemaReconciliation': result['schemaReconciliation'],
                      'diagnosticCount': len(result['diagnostics']), 'outputs': outputs,
                      'acceptedStagingCells': 0, 'acceptedStagingRecords': 0}, sort_keys=True))
    return 3


if __name__ == '__main__':
    raise SystemExit(main())
