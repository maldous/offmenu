"""Authored fixtures only: no private inventory, body, worker, or helper audit."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh import global_delivery as d
from offmenu.refresh import coverage
from offmenu.refresh.core import RefreshError

H = 'a' * 64
PIN = {'path': '/authored/metadata.json', 'sha256': H, 'bytes': 123}


def registries():
    owners = {country: 1 + i % 64 for i, country in enumerate(coverage.COUNTRIES)}
    # Four authored countries for owner59, including MA rather than MK.
    owners = {country: (58 if owner == 59 else owner) for country, owner in owners.items()}
    owners.update({country: 59 for country in ('LV', 'LY', 'MA', 'MC')})
    seed = {'cells': [{'country': c, 'requiredType': t, 'deliveryOwner': owner,
                       'categoryEvidence': dict(PIN), 'retainedCategory': None}
                      for c, owner in owners.items() for t in d.TYPES]}
    cross = {'canonicalDomains': list(coverage.DOMAINS),
             'cells': [{'country': c, 'canonicalDomain': t, 'owner': owner}
                       for c, owner in owners.items() for t in coverage.DOMAINS],
             'projection': [{'canonicalDomain': t, 'relatedSixTypes': [], 'acceptanceInferred': False}
                            for t in coverage.DOMAINS]}
    return {'countryToOwner': owners}, seed, cross


def retained(owners):
    countries = [c for c, owner in owners.items() if owner == 59]
    return {'schemaVersion': 'offmenu-worker59-retained-runplan/1', 'owner': 59,
            'cells': [{'country': c, 'requiredType': t, 'deliveryOwner': 59}
                      for c in countries for t in coverage.DOMAINS],
            'projectionCells': [{'country': c, 'requiredType': t, 'deliveryOwner': 59}
                                for c in countries for t in d.TYPES], 'candidateBatches': []}


def batch():
    return {'batchId': 'wfp-LY-69273-retained', 'country': 'LY', 'deliveryOwner': 59,
            'sourceIdentity': {'sourceId': 'fixture-wfp', 'releaseId': 'fixture-v1',
                               'sourceBodySha256': 'b' * 64, 'useScope': 'fixture-literal-only'},
            'candidateRecords': 69273, 'derivative': {'path': '/authored/not-opened.jsonl', 'sha256': H},
            'originalAcquiredAt': '2026-10-01T00:00:00Z',
            'validatedAt': '2026-10-02T00:00:00Z',
            'blockedFields': ['STAGING_SCOPE_AND_WRITER_NOT_SELECTED'],
            'stagingAuthority': {'unverifiedDeclaration': 'must not enable execution'},
            'reuseKey': H}


def selected_fixture():
    b = batch()
    selection_pin = {'path': '/authored/selection.json', 'sha256': H}
    operation = 'authored bounded literal normalization'
    scope = {'batchId': b['batchId'], 'country': 'LY', 'sourceIdentity': copy.deepcopy(b['sourceIdentity']),
             'derivative': copy.deepcopy(b['derivative']), 'records': 69273, 'executionWriter': 59,
             'operation': operation, 'sourceSelection': selection_pin, 'sourceSelectionLedgerSequence': 7}
    plan = {'schemaVersion': 'offmenu-wfp-selected-normalization-plan/1', 'owner': 59,
            'input': {'country': 'LY', 'records': 69273, 'priorPlan': {'path': 'owner59', 'sha256': H},
                      'sourceIdentity': copy.deepcopy(b['sourceIdentity']), 'derivative': copy.deepcopy(b['derivative']),
                      'originalAcquiredAt': b['originalAcquiredAt']},
            'selection': {'writer': 59, 'executionOwner': 59, 'operation': operation,
                          'source': selection_pin, 'ledgerSequence': 7,
                          'managementOperationResolved': True, 'managementWriterResolved': True}}
    custody = {'owner': 27, 'source': {'recordedSha256': 'b' * 64, 'release': 'fixture-v1',
                                      'originalAcquiredAt': b['originalAcquiredAt']},
               'custody': {'historicalAcquisitionCustodian': 27,
                           'claimFields': {'owner': 27, 'country': 'LY', 'release': 'fixture-v1'}},
               'sourceUseEvidence': {'denialClause': None}}
    return b, scope, plan, custody


def authored_build_fixture():
    p, seed, cross = registries()
    p['workers'] = [{'owner': n, 'countries': [c for c, owner in p['countryToOwner'].items() if owner == n],
                     'packet': {'path': 'packet-' + str(n)}} for n in range(1, 65)]
    owner59 = retained(p['countryToOwner'])
    b, scope, plan, custody = selected_fixture()
    owner59['candidateBatches'] = [b]
    controls = {'partition': p, 'seed': seed, 'crosswalk': cross, 'owner59': owner59,
                'ledgerEvidence': {}, 'selectedExecutionPlan': plan, 'custodyUseEvidence': custody}
    config = {key: {'path': key, 'sha256': H, 'bytes': 123} for key in controls}
    config.update({'now': '2026-10-18T00:00:00Z', 'matrixPath': '/authored/matrix',
                   'sourceLedgerPath': '/authored/ledger', 'retainedPolicySha256': H, 'selectedScope': scope})
    def read(pin):
        if pin['path'].startswith('packet-'):
            n = int(pin['path'].split('-')[1])
            return {'owner': n, 'countryCodes': p['workers'][n-1]['countries'], 'countries': []}
        if pin['path'] == PIN['path']:
            raise RefreshError('authored-peer-malformed')
        return controls[pin['path']]
    return config, controls, read


class GlobalDeliveryTests(unittest.TestCase):
    def test_denominators_are_distinct_and_exhaustive(self):
        p, s, c = registries()
        self.assertEqual(len(d.validate_registry(p, s, c)), 249)
        c['cells'].pop()
        with self.assertRaises(RefreshError):
            d.validate_registry(p, s, c)

    def test_projection_owner_is_checked(self):
        p, s, c = registries()
        s['cells'][0]['deliveryOwner'] = 64
        with self.assertRaises(RefreshError):
            d.validate_registry(p, s, c)

    def test_container_alias_is_explicit_not_semantics(self):
        for container in ('categories', 'sixCategoryRows', 'rows'):
            r = d.projection_row({container: [{'category': 'ingredients/composition', 'status': 'old-PASS'}]},
                                 'ingredients')
            self.assertIsNotNone(r['fieldAlias'])
            self.assertFalse(r['semanticEquivalenceInferred'])
        self.assertEqual(d.projection_row({'categories': {'recipes': {'status': 'old-PASS'}}},
                                         'recipes')['selector'], '/categories/recipes')
        with self.assertRaises(RefreshError):
            d.projection_row({'rows': [{'category': 'recipes'}, {'category': 'recipes'}]}, 'recipes')

    def test_adapter_rejects_duplicate_or_wrong_owner(self):
        p, _, _ = registries()
        r = retained(p['countryToOwner'])
        out = d.adapt59(r, p['countryToOwner'])
        self.assertEqual((len(out['cells']), len(out['projectionCells'])), (52, 24))
        r['cells'][0]['country'] = 'MK'
        with self.assertRaises(RefreshError):
            d.adapt59(r, p['countryToOwner'])

    def test_metadata_reader_never_follows_embedded_body_pointer(self):
        raw = json.dumps({'source': {'path': '/forbidden/body.csv'}}).encode()
        calls = []
        def read(path, maximum, label):
            calls.append(path)
            return raw
        d.read_metadata({'path': '/selected/control.json', 'sha256': d.sha(raw), 'bytes': len(raw)}, reader=read)
        self.assertEqual(calls, ['/selected/control.json'])
        with self.assertRaises(RefreshError):
            d.read_metadata({'path': '/selected/control.json', 'sha256': H}, reader=read)

    def test_selected_writer_does_not_grant_staging_or_noop(self):
        selection = {'batchId': 'wfp-LY-69273-retained', 'executionWriter': 59,
                     'operation': 'authored bounded literal normalization'}
        r = d.batch_plan(batch(), now='2026-10-18T00:00:00Z', policy_pin=H,
                         selection=selection, metadata_pin=PIN)
        self.assertEqual(r['executionWriter'], 59)
        self.assertNotIn('STAGING_SCOPE_AND_WRITER_NOT_SELECTED', r['blockedFields'])
        self.assertEqual(r['eligibility'], 'BLOCKED_STAGING_AUTHORITY')
        self.assertFalse(r['successfulDatasetNoop'])
        self.assertEqual(r['acceptedStagingRecords'], 0)
        self.assertFalse(r['currentBodyIdentityVerified'])

    def test_validation_clock_never_resets_source_age(self):
        b = batch()
        b['validatedAt'] = '2026-10-31T00:00:00Z'
        kwargs = {'now': '2026-10-31T00:00:00Z', 'policy_pin': H, 'selection': {}, 'metadata_pin': PIN}
        r = d.batch_plan(b, **kwargs)
        self.assertEqual(r['cacheAgeObservation'], 'revalidation-required')
        self.assertEqual(r['retainedPolicyPlan']['acquisitionAgeSeconds'], 30 * 86400)
        b['originalAcquiredAt'] = None
        r = d.batch_plan(b, **kwargs)
        self.assertEqual(r['cacheAgeObservation'], 'original-acquisition-time-missing')
        self.assertEqual(r['eligibility'], 'BLOCKED_STAGING_AUTHORITY')

    def test_artifact_replay_is_not_dataset_noop(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'report.json'
            first = d.publish({'scope': 'fixture'}, path)
            replay = d.publish({'scope': 'fixture'}, path)
            self.assertGreater(first['artifactBytesWritten'], 0)
            self.assertEqual(replay['artifactBytesWritten'], 0)
            self.assertTrue(replay['artifactReplay'])
            self.assertFalse(replay['successfulDatasetNoop'])
            with self.assertRaises(RefreshError):
                d.publish({'scope': 'changed'}, path)

    def test_malformed_peer_metadata_does_not_drop_cells(self):
        config, _, read = authored_build_fixture()
        with patch.object(d.coverage, 'assess', return_value={'sources': []}), \
                patch.object(d.global_run, 'run', return_value={}) as run, \
                patch.object(d.global_run, 'compact', return_value={}):
            manifest, _ = d.build(config, reader=read)
        self.assertEqual(len(manifest['canonicalCells']), 3237)
        self.assertEqual(len(manifest['projectionCells']), 1494)
        self.assertEqual(len(manifest['diagnostics']), 1494)
        self.assertEqual(run.call_args.kwargs['bindings'], {})
        self.assertTrue(all(r['eligibility'] == 'BLOCKED_STAGING_AUTHORITY'
                            for r in manifest['canonicalCells']))

    def test_exact_selection_join_resolves_only_matching_batch(self):
        config, controls, _ = authored_build_fixture()
        batches = controls['owner59']['candidateBatches']
        d.join_selected_scope(config, controls['selectedExecutionPlan'], batches, controls['custodyUseEvidence'])
        selected = d.batch_plan(batches[0], now=config['now'], policy_pin=H,
                                selection=config['selectedScope'], metadata_pin=config['owner59'],
                                custody_evidence=config['custodyUseEvidence'])
        self.assertEqual(selected['sourceCustodian'], 27)
        self.assertNotIn('EXACT_SNAPSHOT_USE_CUSTODY_UNQUALIFIED', selected['blockedFields'])
        other = copy.deepcopy(batches[0])
        other.update({'batchId': 'fixture-LV', 'country': 'LV'})
        other['blockedFields'].append('ORIGINAL_CUSTODIAN_NOT_QUALIFIED')
        unselected = d.batch_plan(other, now=config['now'], policy_pin=H,
                                  selection=config['selectedScope'], metadata_pin=config['owner59'],
                                  custody_evidence=config['custodyUseEvidence'])
        self.assertIsNone(unselected['sourceCustodian'])
        self.assertIn('ORIGINAL_CUSTODIAN_NOT_QUALIFIED', unselected['blockedFields'])
        self.assertIn('EXACT_SNAPSHOT_USE_CUSTODY_UNQUALIFIED', unselected['blockedFields'])
        self.assertEqual(selected['eligibility'], 'BLOCKED_STAGING_AUTHORITY')

    def test_selection_conflicts_missing_fields_and_duplicate_batches_refused(self):
        # Every mutation independently conflicts with one immutable join input.
        paths = [('config', 'selectedScope', 'batchId'), ('config', 'selectedScope', 'country'),
                 ('config', 'selectedScope', 'executionWriter'), ('config', 'selectedScope', 'operation'),
                 ('config', 'selectedScope', 'records'), ('config', 'selectedScope', 'sourceSelectionLedgerSequence'),
                 ('config', 'selectedScope', 'sourceIdentity', 'sourceId'),
                 ('config', 'selectedScope', 'sourceIdentity', 'releaseId'),
                 ('config', 'selectedScope', 'sourceIdentity', 'sourceBodySha256'),
                 ('config', 'selectedScope', 'derivative', 'sha256'),
                 ('config', 'selectedScope', 'derivative', 'path'),
                 ('plan', 'input', 'sourceIdentity', 'sourceBodySha256'),
                 ('plan', 'input', 'derivative', 'sha256'), ('plan', 'input', 'records'),
                 ('batch', 'candidateRecords'), ('batch', 'sourceIdentity', 'releaseId'),
                 ('custody', 'source', 'release'), ('custody', 'source', 'recordedSha256'),
                 ('custody', 'custody', 'claimFields', 'country')]
        for path in paths:
            for missing in (False, True):
                with self.subTest(path=path, missing=missing):
                    b, scope, plan, custody = selected_fixture()
                    config = {'selectedScope': scope, 'owner59': {'path': 'owner59', 'sha256': H}}
                    roots = {'config': config, 'plan': plan, 'batch': b, 'custody': custody}
                    parent = roots[path[0]]
                    for key in path[1:-1]:
                        parent = parent[key]
                    key = path[-1]
                    if missing:
                        del parent[key]
                    else:
                        parent[key] = 45 if isinstance(parent[key], int) else 'conflicting-fixture'
                    with self.assertRaises(RefreshError):
                        d.join_selected_scope(config, plan, [b], custody)
        b, scope, plan, custody = selected_fixture()
        config = {'selectedScope': scope, 'owner59': {'path': 'owner59', 'sha256': H}}
        for batches in ([], [b, copy.deepcopy(b)]):
            with self.assertRaises(RefreshError):
                d.join_selected_scope(config, plan, batches, custody)

    def test_cross_country_config_refused_before_metadata_harness(self):
        config, controls, read = authored_build_fixture()
        lv = copy.deepcopy(controls['owner59']['candidateBatches'][0])
        lv.update({'batchId': 'fixture-LV', 'country': 'LV'})
        lv['sourceIdentity']['sourceBodySha256'] = 'c' * 64
        controls['owner59']['candidateBatches'].append(lv)
        config['selectedScope'].update({'batchId': lv['batchId'], 'country': 'LV', 'executionWriter': 45,
                                         'sourceIdentity': copy.deepcopy(lv['sourceIdentity'])})
        with patch.object(d.coverage, 'assess') as assess, patch.object(d.global_run, 'run') as run:
            with self.assertRaises(RefreshError):
                d.build(config, reader=read)
            assess.assert_not_called()
            run.assert_not_called()

    def test_mixed_decoded_peer_shapes_keep_valid_peers_and_denominators(self):
        bad_documents = [None, [], 'decoded-string', 17, True,
                         {'categories': ['bad-row']}, {'categories': {t: None for t in d.TYPES}}]
        for bad in bad_documents:
            with self.subTest(document=bad):
                config, controls, base_read = authored_build_fixture()
                for row in controls['seed']['cells']:
                    row['categoryEvidence'] = {'path': 'peer-' + row['country'], 'sha256': H}
                bad_country = 'LV'
                valid = {'categories': {t: {'status': 'AUTHORED_METADATA_ONLY'} for t in d.TYPES}}
                def read(pin):
                    if pin['path'].startswith('peer-'):
                        return bad if pin['path'] == 'peer-' + bad_country else valid
                    return base_read(pin)
                with patch.object(d.coverage, 'assess', return_value={'sources': []}), \
                        patch.object(d.global_run, 'run', return_value={}) as run, \
                        patch.object(d.global_run, 'compact', return_value={}):
                    manifest, _ = d.build(config, reader=read)
                self.assertEqual((len(manifest['canonicalCells']), len(manifest['projectionCells'])), (3237, 1494))
                self.assertEqual(len(manifest['diagnostics']), 6)
                self.assertEqual({x['country'] for x in manifest['diagnostics']}, {bad_country})
                peers = [row for row in manifest['projectionCells'] if row['country'] != bad_country]
                self.assertTrue(all(row['retainedCategory'] and row['metadataIssue'] is None for row in peers))
                broken = [row for row in manifest['projectionCells'] if row['country'] == bad_country]
                self.assertTrue(all(row['retainedCategory'] is None and row['metadataIssue'] for row in broken))
                self.assertEqual(run.call_args.kwargs['limits'].max_sources, 4096)

    def test_invalid_matched_row_diagnoses_only_affected_category(self):
        document = {'categories': {t: {'status': 'fixture'} for t in d.TYPES}}
        document['categories']['recipes'] = None
        with self.assertRaisesRegex(RefreshError, 'projection-row-object-required'):
            d.projection_row(document, 'recipes')
        self.assertIsNotNone(d.projection_row(document, 'nutrition')['row'])

    def test_cached_projection_checks_each_byte_length_pin_in_either_order(self):
        raw = d.canonical({'categories': {t: {'status': 'synthetic'} for t in d.TYPES}})
        for bad_index, omit_valid_length in ((0, False), (1, False), (1, True)):
            with self.subTest(bad_index=bad_index, omit_valid_length=omit_valid_length):
                config, controls, base_read = authored_build_fixture()
                for row in controls['seed']['cells']:
                    row['categoryEvidence'] = {'path': PIN['path'], 'sha256': d.sha(raw)}
                    if not omit_valid_length:
                        row['categoryEvidence']['bytes'] = len(raw)
                rows = sorted(controls['seed']['cells'], key=lambda r: (r['country'], r['requiredType']))
                bad = rows[bad_index]
                bad['categoryEvidence']['bytes'] = None if omit_valid_length else len(raw) + 1
                def read(pin):
                    if pin['path'] == PIN['path']:
                        return d.read_metadata(pin, reader=lambda *args: raw)
                    return base_read(pin)
                with patch.object(d.coverage, 'assess', return_value={'sources': []}), \
                        patch.object(d.global_run, 'run', return_value={}), \
                        patch.object(d.global_run, 'compact', return_value={}):
                    manifest, _ = d.build(config, reader=read)
                self.assertEqual(len(manifest['diagnostics']), 1)
                broken = [r for r in manifest['projectionCells'] if r['metadataIssue']]
                self.assertEqual([(r['country'], r['requiredType']) for r in broken],
                                 [(bad['country'], bad['requiredType'])])
                self.assertIsNone(broken[0]['retainedCategory'])
                self.assertEqual(sum(r['retainedCategory'] is not None for r in manifest['projectionCells']), 1493)

    def test_plan_identity_binds_retained_policy_and_is_stable_for_same_policy(self):
        config, _, read = authored_build_fixture()
        with patch.object(d.coverage, 'assess', return_value={'sources': []}), \
                patch.object(d.global_run, 'run', return_value={}), \
                patch.object(d.global_run, 'compact', return_value={}):
            first, _ = d.build(config, reader=read)
            replay, _ = d.build(config, reader=read)
            config['retainedPolicySha256'] = 'b' * 64
            changed, _ = d.build(config, reader=read)
        self.assertEqual(first['planIdentitySha256'], replay['planIdentitySha256'])
        self.assertNotEqual(first['planIdentitySha256'], changed['planIdentitySha256'])
        self.assertEqual(first['retainedPolicySha256'], H)
        self.assertEqual(changed['retainedPolicySha256'], 'b' * 64)

    @staticmethod
    def cli_reports():
        return ({'status': 'BLOCKED_STAGING_AUTHORITY', 'denominators': {'countries': 249},
                 'schemaReconciliation': {}, 'diagnostics': []}, {'syntheticHarness': True})

    def test_cli_conflicting_output_never_publishes_the_other_file(self):
        for conflict in ('manifest.json', 'global-run.json'):
            with self.subTest(conflict=conflict), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                config = root / 'config.json'
                config.write_text('{}')
                d.publish({'stale': True}, root / conflict)
                before = {p.name: p.read_bytes() for p in root.iterdir()}
                with patch.object(d, 'build', return_value=self.cli_reports()), patch('builtins.print'):
                    with self.assertRaises(RefreshError):
                        d.main(['--config', str(config), '--output-root', str(root)])
                self.assertEqual({p.name: p.read_bytes() for p in root.iterdir()}, before)

    def test_cli_dangling_second_output_never_publishes_manifest(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            config = root / 'config.json'
            config.write_text('{}')
            target = root / 'missing-synthetic-target'
            (root / 'global-run.json').symlink_to(target)
            with patch.object(d, 'build', return_value=self.cli_reports()), patch('builtins.print'):
                with self.assertRaises((RefreshError, d.global_run.GlobalRunError, OSError)):
                    d.main(['--config', str(config), '--output-root', str(root)])
            self.assertFalse((root / 'manifest.json').exists())
            self.assertTrue((root / 'global-run.json').is_symlink())
            self.assertFalse(target.exists())

    def test_cli_new_outputs_and_exact_replay_remain_blocked_dataset_operations(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            config = root / 'config.json'
            config.write_text('{}')
            with patch.object(d, 'build', return_value=self.cli_reports()), patch('builtins.print') as output:
                args = ['--config', str(config), '--output-root', str(root)]
                self.assertEqual(d.main(args), 3)
                before = {p.name: p.read_bytes() for p in root.iterdir()}
                self.assertEqual(d.main(args), 3)
                receipt = json.loads(output.call_args.args[0])
            self.assertEqual({p.name: p.read_bytes() for p in root.iterdir()}, before)
            self.assertEqual(receipt['acceptedStagingRecords'], 0)
            self.assertTrue(all(v['artifactReplay'] and v['artifactBytesWritten'] == 0
                                and not v['successfulDatasetNoop'] for v in receipt['outputs'].values()))


if __name__ == '__main__':
    unittest.main()
