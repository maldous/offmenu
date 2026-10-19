"""Combined fetch-only accounting and publication, entirely synthetic and offline.

The real 4,753-row manifest, 988-row verification plan, 93 metadata targets,
closed validators, shared meters, evidence custody and publisher are exercised.
No retained original, owner metadata, HTTP endpoint or GitHub service is read.
Acquisition/verification results below are synthetic observations, not custody
claims about the user's source bodies. Activation is injected for this test only.
"""
from contextlib import ExitStack, contextmanager
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import builtins
import hashlib
import io
import json
import os
import socket
import tempfile
import threading
import time
import unittest

import test_actual988_stages as full
import test_taiwan_fetch_acceptance as tw
from offmenu.refresh import fetch_evidence as evidence
from offmenu.refresh import fetch_metadata_reconciliation as metadata
from offmenu.refresh import fetch_reconciliation_runtime as runtime
from offmenu.refresh import owner_head_diagnostic as heads
from offmenu.refresh import reviewed_fetch_intake as reviewed

ROOT = Path(__file__).resolve().parents[1]
g = full.g


def synthetic_active_config():
    value = json.loads((ROOT / runtime.CONFIG_PATH).read_bytes())
    value['status'] = 'parent-reviewed-owner-manual'
    value['metadataSelection']['readerSHA256'] = g.a.sha(Path(metadata.__file__).read_bytes())
    return value


def metadata_report(config, *, near_limit=False):
    """Real sanitizer output joined to synthetic complete finite target accounting."""
    proposal = runtime.proposal()
    inventory = runtime.inventory()
    targets = metadata.inspect_proposal(proposal)
    report = metadata._base(targets)
    report.update(parentSelectionSHA256=g.a.sha(g.a.canonical(config['metadataSelection'])),
                  status='metadata-proposals-only')
    selected = {row['targetId'] for row in config['metadataSelection']['targets']}
    withheld = set(config['metadataSelection']['withheldTargetIds'])
    for target, outcome in zip(targets, report['outcomes']):
        if target.target_id in selected:
            outcome.update(code='reconciled', bytesRead=target.extent,
                           readBytesUpperBound=target.extent)
        elif target.target_id in withheld:
            outcome['code'] = 'withheld'
        else:
            outcome['code'] = 'unselected'
    target = max((target for target in targets if target.target_id in selected), key=lambda t: t.extent)
    asset_id = min(inventory.asset_ids - inventory.held_asset_ids)
    value = {'assetId': asset_id, 'title': 'SECRET-SYNTHETIC-TITLE',
             'headers': {'Authorization': 'Bearer SECRET-SYNTHETIC-HEADER'},
             'body': 'SECRET-SYNTHETIC-BODY'}
    count = 1
    if near_limit:
        sample = metadata._sanitize(g.a.canonical({'records': [value]}), target,
            inventory, time.monotonic() + 30, metadata.MAX_OUTPUT, metadata.MAX_OBJECTS)['rows'][0]
        # Reserve pointer digit growth, JSON punctuation and the report envelope.
        count = min(metadata.MAX_OBJECTS - 1,
                    (metadata.MAX_OUTPUT - metadata.REPORT_RESERVE - 32768) //
                    (len(g.a.canonical(sample)) + 6))
    clean = metadata._sanitize(g.a.canonical({'records': [value] * count}), target,
        inventory, time.monotonic() + 30, metadata.MAX_OUTPUT - metadata.REPORT_RESERVE,
        metadata.MAX_OBJECTS)
    outcome = next(row for row in report['outcomes'] if row['targetId'] == target.target_id)
    outcome.update(recoveredObjects=len(clean['rows']), visitedNodes=clean['visitedNodes'],
                   sanitizedObjectsProduced=clean['sanitizedObjectsProduced'],
                   sanitizedRowBytesProduced=clean['sanitizedRowBytesProduced'])
    report.update(rows=clean['rows'], recoveredObjectCount=len(clean['rows']),
                  metadataBytesRead=sum(row['bytesRead'] for row in report['outcomes']))
    for key in ('visitedNodes', 'sanitizedObjectsProduced', 'sanitizedRowBytesProduced'):
        report[key] = sum(row[key] for row in report['outcomes'])
    runtime.metadata_validator(report, config)
    return report


def maximum_head_report():
    """Five maximal sanitized header observations; all input is in-memory."""
    contracts = {row['sourceKey']: row for row in g.prepared_comprehensive_configs()[0]['sources']}
    sources = [{**deepcopy(row), 'contract': contracts[row['entry']['sourceKey']]}
               for row in heads.SOURCE_IDENTITIES]
    report = heads.report_template()
    report.update(sourceAttemptsConsumed=5, requestAttemptedCount=5,
                  sourceMetadataUnchanged=True, ledgerResultSHA256='d' * 64)
    for source in sources:
        # 100 distinct unknown names maximize the bounded safe facts. Values
        # contain a marker that must not survive the pure sanitizer.
        header_rows = [('X-Synthetic-%03d' % i, 'SECRET-SYNTHETIC-HEADER') for i in range(100)]
        for count in range(100, 0, -1):
            try:
                observation = heads.sanitize_response(source, 200, header_rows[:count], 65536)
            except ValueError as error:
                if str(error) != 'header-envelope-exceeded':
                    raise
            else:
                break
        else:
            raise AssertionError('no valid synthetic HEAD projection')
        report['items'].append({'sourceKey': source['entry']['sourceKey'],
            'requestAttempted': True, 'sourceMetadataUnchanged': True,
            'observation': observation})
    heads.validate_report(report)
    return report


class WholeInventoryFetchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        full.Actual988Tests.setUpClass.__func__(cls)
        cls.config = synthetic_active_config()
        cls.new_sources = reviewed.prepared_sources()
        cls.new_by_key = {row['sourceKey']: row for row in cls.new_sources}
        cls.big_metadata = metadata_report(cls.config, near_limit=True)
        cls.small_metadata = metadata_report(cls.config)
        cls.head_report = maximum_head_report()
        cls.acceptance_report = tw.report()
        cls.blocked_acceptance_report = tw.report(blocked=True)
        cls.tw_keys = {row['sourceKey'] for row in tw.MANIFEST['items']}

    @contextmanager
    def execution(self, *, maximum=True, metadata_failure=False, taiwan_blocked=False):
        selected, manifest = deepcopy(self.selected), deepcopy(self.manifest)
        config = deepcopy(self.config)
        calls = {'old': [], 'new': [], 'verify': [], 'prepare': [],
                 'meters': [], 'coordinators': [], 'fooOpens': 0, 'begin': 0,
                 'accept': 0, 'guard': 0}
        report_metadata = deepcopy(self.big_metadata if maximum else self.small_metadata)
        head_report = deepcopy(self.head_report)
        source_order = {row['sourceKey']: index for index, row in enumerate(self.new_sources)}
        lock = threading.Lock()
        def detail(child, *, successful=False, code='private-original-conflict', count=0):
            return {'status': 'verified-private-original' if successful else
                        ('failed' if child.snapshot()['requests'] else 'blocked'),
                    'errorCode': None if successful else code,
                    'network': child.snapshot(),
                    'validation': {'sha256': 'b' * 64, 'bytes': count,
                        'originalAcquiredAt': '2026-10-19T00:00:00Z'} if successful else None,
                    'responseMetadata': None, 'responsePolicy': None,
                    'cacheStatus': 'downloaded-200' if successful else None,
                    'originalDisposition': 'saved-original' if successful else None,
                    'privateSaveState': 'saved-original' if successful else 'none',
                    'localBodyBytes': count if successful else 0,
                    'receiptPersistence': 'written'}
        def acquire_old(source, **kwargs):
            child = kwargs['batch_meter']
            self.assertIs(kwargs.get('reuse_only'), True)
            self.assertEqual((child.maximumRequests, child.maximumBytes), (0, 0))
            with self.assertRaises(g.a.RefreshError):
                child.start_request()
            with lock:
                calls['old'].append(source['sourceKey'])
                calls['meters'].append(child.parent)
                calls['coordinators'].append(kwargs['coordinator'])
            return detail(child)
        def acquire_new(source, **kwargs):
            child = kwargs['batch_meter']
            self.assertFalse(kwargs.get('reuse_only', False))
            self.assertIs(type(child), g.SourceBudget)
            self.assertEqual((child.maximumRequests, child.maximumBytes), (1, source['hardTransferBytes']))
            self.assertLessEqual(kwargs['deadline'], deadline)
            with lock:
                calls['new'].append(source['sourceKey'])
                calls['meters'].append(child.parent)
                calls['coordinators'].append(kwargs['coordinator'])
            child.start_request()
            count = source['hardTransferBytes'] if maximum else 17
            child.record_bytes(count)
            index = source_order[source['sourceKey']]
            # One unknown worker exception, explicit validation failures,
            # and successes all must receive separate complete final outcomes.
            if index == 0:
                raise TimeoutError('SECRET-SYNTHETIC-WORKER-ERROR')
            if index % 3 == 0:
                return detail(child, code='fetch-extension-identity-changed')
            if index % 3 == 1:
                return detail(child, code='fetch-extension-media-mismatch')
            return detail(child, successful=True, count=count)
        def verify(contract, path, worker_deadline, slot=None):
            self.assertEqual(contract['permissions'], {'read': True, 'copy': False, 'extract': False})
            self.assertEqual(contract['maximumOutputBytes'], 0)
            g.retained_verification.validate_contract(contract)
            calls['verify'].append(contract['assetId'])
            return {'schemaVersion': g.retained_verification.RESULT_SCHEMA,
                'assetId': contract['assetId'], 'contractSHA256': g.a.sha(g.a.canonical(contract)),
                'status': 'verified-retained', 'errorCode': 'verification-media-unverified',
                'bytesRead': contract['expectedBytes'], 'maximumReadBytes': contract['expectedBytes'],
                'originalSHA256': contract['expectedSHA256'], 'originalBytes': contract['expectedBytes'],
                'actualMediaType': None, 'integrityVerified': True, 'mediaObserved': False,
                'nextStageReady': False, 'sourceCopied': False, 'extractionPerformed': False,
                'networkRequests': 0, 'payloadBytesWritten': 0}
        def begin(candidate, **kwargs):
            calls['begin'] += 1
            self.assertIs(threading.current_thread(), threading.main_thread())
            self.assertIsInstance(kwargs['lease_fd'], int)
            self.assertTrue(callable(kwargs['current_adverse_evidence']))
            if metadata_failure:
                raise g.a.RefreshError('fetch-evidence-invalid')
            reference = evidence.save('metadata-reconciliation', report_metadata,
                output_root=root, adapter=g.a,
                validator=lambda v: runtime.metadata_validator(v, config),
                private_directory=g.save.private_directory)
            return report_metadata, reference
        def extension(candidate, result, **kwargs):
            if metadata_failure:
                self.assertIsNone(result)
                raise g.a.RefreshError('fetch-extension-custody-unresolved')
            self.assertEqual(result, report_metadata)
            return {'authority': object(), 'owner_runtime': object(),
                'sources': deepcopy(self.new_sources),
                'mode': {'predecessors': [], 'diagnosticReportPin': None,
                         'freshSources': list(self.new_by_key)}}
        def guard(*args, **kwargs):
            calls['guard'] += 1
        def accept(*args, **kwargs):
            calls['accept'] += 1
            self.assertIs(threading.current_thread(), threading.main_thread())
            self.assertIsInstance(kwargs['lease_fd'], int)
            return deepcopy(self.blocked_acceptance_report if taiwan_blocked else self.acceptance_report)
        def prepare(*args, **kwargs):
            calls['prepare'].append(args)
            raise AssertionError('fetch must never parse')
        def no_foo_open(real):
            def checked(path, *args, **kwargs):
                if isinstance(path, (str, bytes, os.PathLike)):
                    resolved = os.path.realpath(os.fsdecode(path))
                    private_roots = ('/home/user/src/offmenu-data/', '/srv/offmenu-refresh/')
                    if resolved.startswith(private_roots):
                        calls['fooOpens'] += 1
                        raise AssertionError('Foo private-root access forbidden')
                return real(path, *args, **kwargs)
            return checked
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory)
            (root / 'collection/intents').mkdir(parents=True)
            owner = SimpleNamespace(root=root)
            deadline = time.monotonic() + 180
            for key, value in (('OUTPUT', root), ('GUARD', 0)):
                stack.enter_context(patch.object(g.a, key, value))
            for key, value in (('selection_config', selected), ('manifest_config', manifest),
                               ('effective_resources', full.RES), ('stat_original', 'stat-observed')):
                stack.enter_context(patch.object(g, key, return_value=value))
            stack.enter_context(patch.object(runtime, 'configuration', return_value=config))
            stack.enter_context(patch.object(runtime, 'begin', side_effect=begin))
            stack.enter_context(patch.object(runtime, 'extension', side_effect=extension))
            # Real missing-meter/deadline/coordinator/capability cases live in
            # test_fetch_reconciliation_runtime.py, with no guard patch there.
            stack.enter_context(patch.object(g, 'validate_fetch_execution', side_effect=guard))
            stack.enter_context(patch.object(g.save, 'run_selected', side_effect=acquire_old))
            stack.enter_context(patch.object(g.media_save, 'run_selected', side_effect=acquire_old))
            stack.enter_context(patch.object(reviewed, 'run_selected', side_effect=acquire_new))
            stack.enter_context(patch.object(g.twaccept, 'perform', side_effect=accept))
            stack.enter_context(patch.object(g.retained_collection, 'verify_worker', side_effect=verify))
            stack.enter_context(patch.object(g.a, 'capacity', return_value=10**15))
            stack.enter_context(patch.object(g.a, 'reserve', side_effect=lambda *a, **k: (os.open('/dev/null', os.O_RDONLY), None)))
            stack.enter_context(patch.object(g.a, 'release_own_reservation', side_effect=lambda path, fd, identity: os.close(fd)))
            # Real host-spacing behavior has its own scheduler tests. Synthetic
            # host labels avoid sleeping against real publication source names.
            stack.enter_context(patch.object(g.intake, 'source_hosts', side_effect=lambda s: [s['sourceKey'] + '.invalid']))
            stack.enter_context(patch.object(g.media, 'capabilities', return_value=g.runtime_capabilities('fetch')))
            for obj, name in ((g.taiwan, 'run_diagnostics'), (g.prepdiag, 'run_diagnostics'),
                              (g.twrecovery, 'validate_selected')):
                stack.enter_context(patch.object(obj, name, side_effect=AssertionError('unstaged diagnostic forbidden')))
            for name in ('socket', 'create_connection', 'getaddrinfo'):
                stack.enter_context(patch.object(socket, name, side_effect=AssertionError('live network forbidden')))
            for obj in (os, builtins, io):
                stack.enter_context(patch.object(obj, 'open', side_effect=no_foo_open(obj.open)))
            report = g.run_global(manifest, selected, prepare=prepare, owner_runtime=owner,
                stage='fetch', retained_acceptance_selection=config['taiwanAcceptance'],
                current_adverse_evidence=lambda: [], reconciliation_config=config,
                head_observation=head_report, invocation_deadline=deadline)
            g.sanitize_report(report)
            yield report, calls, root, config, report_metadata
            self.assertEqual(calls['fooOpens'], 0)
            self.assertEqual(self.pins, {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                                         for path in self.paths})

    def assert_cardinality(self, report, calls):
        self.assertEqual(report['assetCount'], 4753)
        self.assertEqual((report['countryCount'], report['typeCount']), (249, 13))
        self.assertEqual(len(self.manifest['cells']), 3237)
        self.assertEqual(len(g.expand_outcomes(report['assetOutcomeGroups'], 4753)), 4753)
        self.assertEqual(set(calls['verify']) & self.ids, self.ids)
        self.assertEqual(len([key for key in calls['verify'] if key in self.ids]), 988)
        self.assertFalse(set(calls['verify']) & set(self.plan['excludedAssetIds']))
        self.assertEqual(report['retainedOriginalVerification']['reservedOriginalReadBytes'], 28437596435)
        self.assertEqual(report['retainedOriginalVerification']['verifiedOriginalPayloadBytes'], 28437595507)
        self.assertEqual(calls['prepare'], [])
        self.assertEqual(report['preparedBytes'], 0)
        self.assertTrue(all(change['preparation'] is None for change in report['changes']))
        self.assertEqual(set(calls['old']) | self.tw_keys, {s['sourceKey'] for s in self.selected['sources']})
        self.assertEqual(len(calls['old']), 12)
        self.assertFalse(set(calls['old']) & self.tw_keys)
        self.assertEqual(calls['accept'], 1)
        self.assertFalse(report['fetchCoverageAcceptance']['coverageComplete'])
        self.assertEqual(report['fetchCoverageAcceptance']['satisfiedRequirements'], 0)

    def publish_and_reload(self, report, root, config, report_metadata):
        with g.owner_successor_profile(['--mode', 'user']):
            publisher = g.publisher_module()
        envelope = {'schemaVersion': 'offmenu-owner-manual-global-result/1',
            'executionContext': 'owner-manual-foo', 'invokingUID': 1000,
            'outputRoot': '/home/test/src/offmenu-data/owner-collection-runtime',
            'handover': {'handoffId': publisher.HANDOFF, 'runtimeConfigSHA256': publisher.RUNTIME_SHA256,
                'dispatchHoldSHA256': publisher.HOLD_SHA256, 'executionContext': 'owner-manual-foo',
                'runnerResumeRequiresOutcomeImport': True},
            'historicalRunnerRootAccess': {'/srv/offmenu-refresh/outputs/collection': 'inaccessible',
                '/srv/offmenu-refresh/cache': 'absent'}, 'nativeClaimsRoot': publisher.NATIVE_CLAIMS,
            'nativeCoverageExhaustive': False, 'globalReportSHA256': g.a.sha(g.a.canonical(report)),
            'globalReport': report}
        owner = SimpleNamespace(root=root)
        saved = g.saved_manual_result(owner, envelope, stage='fetch')
        self.assertEqual(g.saved_manual_result(owner, stage='fetch'), saved)
        actual_uid = os.getuid()
        def load(reference, output_root):
            self.assertEqual(output_root, envelope['outputRoot'])
            # Envelope identity uses a synthetic non-root user, local private
            # evidence remains owned by this test process's real account.
            with patch.object(evidence.os, 'getuid', return_value=actual_uid):
                return evidence.load(reference, output_root=root,
                    validator=runtime.evidence_validator(reference['kind']))
        with patch.object(publisher.os, 'getuid', return_value=1000), \
             patch.object(publisher.os, 'geteuid', return_value=1000), \
             patch.object(publisher.pwd, 'getpwuid', return_value=SimpleNamespace(pw_dir='/home/test')), \
             patch.object(runtime, 'load_evidence', side_effect=load):
            receipt, files, raw = publisher.build_payload(envelope, g)
            self.assertEqual(receipt['expandedCounts'], {'assets': 4753, 'countryTypeCells': 3237, 'statPaths': 1937})
            self.assertLessEqual(len(files) + 1, 96)  # Include the separate receipt.
            self.assertLessEqual(sum(len(data) for _, data in files) + len(raw), 8 * 1024**2)
            self.assertLessEqual(len(raw), 128 * 1024)
            self.assertTrue(all(len(data) <= 128 * 1024 for _, data in files))
            self.assertFalse(receipt['rawSourceBodiesPublished'])
            self.assertFalse(receipt['checkpointBodiesPublished'])
            rows = [row for name, data in files if '/assets-' in name for row in json.loads(data)['rows']]
            cells = [row for name, data in files if '/country-types-' in name for row in json.loads(data)['rows']]
            self.assertEqual(len(rows), 4753)
            self.assertEqual(len(cells), 3237)
            self.assertTrue(all(row['countryTypeComplete'] is False for row in cells))
            self.assertEqual(sum('retainedVerification' in row for row in rows), 988)
            self.assertEqual(sum('retainedReferenceAcceptance' in row for row in rows), 3)
            self.assertEqual({row['sourceKey'] for row in rows if (row.get('change') or {}).get('acquisition')
                              and row['sourceKey'] in self.new_by_key}, set(self.new_by_key))
            control = next(json.loads(data) for name, data in files if name.endswith('/fetch-metadata-control.json'))
            expected_digest = control.pop('reconstructedReportSHA256')
            control['rows'] = [row for name, data in files if '/fetch-metadata-rows-' in name for row in json.loads(data)['rows']]
            self.assertEqual(control, report_metadata)
            self.assertEqual(g.a.sha(g.a.canonical(control)), expected_digest)
            self.assertEqual(len(control['outcomes']), 93)
            heads.validate_report(next(json.loads(data) for name, data in files if name.endswith('/fetch-response-diagnostics.json')))
            self.assertFalse(any(b'SECRET-SYNTHETIC' in data for _, data in files))
            api = full.pub_fixture.FakeAPI()
            first = publisher.publish_result(envelope, g, api)
            self.assertTrue(first['verified'], first)
            self.assertEqual(sum(call[0] == 'PATCH' for call in api.calls), 1)
            api.calls = []
            second = publisher.publish_result(envelope, g, api)
            self.assertEqual(second['status'], 'verified-existing')
            self.assertEqual(first['receiptPath'], second['receiptPath'])
            self.assertTrue(all(call[0] == 'GET' for call in api.calls))
        print('WHOLE_INVENTORY_FETCH', json.dumps({'summaryBytes': len(g.a.canonical(report)),
            'metadataBytes': len(g.a.canonical(report_metadata)), 'headBytes': len(g.a.canonical(self.head_report)),
            'files': len(files), 'publicationBytes': sum(len(data) for _, data in files),
            'gets': report['networkRequests'], 'bodyBytes': report['networkBytesRead']}))

    def test_full_combined_mixed_outcomes_exact_budgets_and_idempotent_publication(self):
        with self.execution() as (report, calls, root, config, metadata_result):
            self.assert_cardinality(report, calls)
            self.assertEqual(len(calls['new']), 26)
            self.assertEqual(calls['guard'], 26)
            self.assertEqual(set(calls['new']), set(self.new_by_key))
            self.assertEqual(len({id(meter) for meter in calls['meters']}), 1)
            self.assertEqual(len({id(coordinator) for coordinator in calls['coordinators']}), 1)
            meter = calls['meters'][0]
            self.assertEqual(meter.snapshot(), {'requests': 26, 'bodyBytesRead': 644874240,
                'maximumRequests': 26, 'maximumBytes': 644874240})
            self.assertEqual((report['networkRequests'], report['networkBytesRead']), (26, 644874240))
            with self.assertRaises(g.a.RefreshError):
                meter.child('unselected', 1, 1).start_request()
            self.assertEqual(report['fetchNetworkAccounting'], {'bodyGETRequests': 26,
                'diagnosticHEADRequests': 5, 'diagnosticUncertainRequests': 0,
                'maximumTotalRequests': 31, 'totalAttemptedOrUncertainRequests': 31})
            acquired = [row['acquisition'] for row in report['changes'] if row['acquisition'] is not None]
            added = [row for row in acquired if row['sourceKey'] in self.new_by_key]
            self.assertEqual(len(added), 26)
            self.assertEqual(len({row['sourceKey'] for row in added}), 26)
            self.assertEqual({row['status'] for row in added}, {'failed', 'verified-private-original'})
            self.assertEqual(sum(row['errorCode'] == 'collector-rejected' for row in added), 1)
            self.assertEqual(sum(row['status'] == 'verified-private-original' for row in added), 8)
            self.assertTrue(all(row['networkRequests'] == 0 for row in acquired if row['sourceKey'] not in self.new_by_key))
            self.assertEqual(len(metadata_result['outcomes']), 93)
            self.assertEqual(sum(row['code'] == 'reconciled' for row in metadata_result['outcomes']), 92)
            self.assertGreater(len(g.a.canonical(metadata_result)), 3.75 * 1024**2)
            self.assertLessEqual(len(g.a.canonical(metadata_result)), 4 * 1024**2)
            self.assertLessEqual(len(g.a.canonical(self.head_report)), 65536)
            self.assertEqual(report['retainedReferenceAcceptance']['verifiedOriginalPayloadBytes'], 6490476)
            self.assertEqual(report['retainedReferenceAcceptance']['localOriginalReadBytes'], 12980952)
            self.publish_and_reload(report, root, config, metadata_result)
            for field, excess in (('networkRequests', 27), ('networkBytesRead', 644874241)):
                changed = deepcopy(report)
                changed[field] = excess
                with self.subTest(field=field), self.assertRaises(ValueError):
                    g.sanitize_report(changed)
            missing = deepcopy(report)
            missing['changes'] = [change for change in missing['changes']
                if not (change['acquisition'] and change['acquisition']['sourceKey'] == self.new_sources[-1]['sourceKey'])]
            with self.assertRaises(ValueError):
                g.sanitize_report(missing)

    def test_failed_metadata_keeps_all26_terminal_and_independent_old_and_retained_work(self):
        with self.execution(maximum=False, metadata_failure=True, taiwan_blocked=True) as (report, calls, root, config, _):
            self.assert_cardinality(report, calls)
            self.assertEqual(calls['new'], [])
            self.assertEqual((report['networkRequests'], report['networkBytesRead']), (0, 0))
            self.assertEqual(report['retainedReferenceAcceptance']['status'], 'blocked')
            self.assertEqual(report['retainedReferenceAcceptance']['items'], [])
            added = [row['acquisition'] for row in report['changes']
                     if row['acquisition'] and row['acquisition']['sourceKey'] in self.new_by_key]
            self.assertEqual(len(added), 26)
            self.assertTrue(all(row['status'] == 'blocked' and row['errorCode'] == 'fetch-extension-custody-unresolved' for row in added))
            self.assertIn('fetch-evidence-unavailable', report['globalErrors'])
            self.assertEqual([row['kind'] for row in report['fetchEvidence']], ['response-diagnostics'])
            self.assertEqual(calls['fooOpens'], 0)

    def test_final_configuration_binds_parent_adopted_authority(self):
        self.assertEqual(runtime.configuration()['additionalAuthorityPin']['sha256'],'29eb7e4ded0bd28e0064ac854bc3e5e9c6b1d58b019d10f8d81c468c26096add')
        candidate = runtime.configuration(allow_inactive=True)
        self.assertEqual(candidate['status'], 'parent-reviewed-owner-manual')
        self.assertEqual(candidate['oldSourceGETs'], 0)
        self.assertEqual((candidate['maximumGETs'], candidate['maximumHEADs']), (26, 5))
        self.assertFalse(candidate['globalCoverageComplete'])


if __name__ == '__main__':
    unittest.main()
