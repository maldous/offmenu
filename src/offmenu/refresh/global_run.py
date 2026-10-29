"""Exhaustive, deterministic global assessment and bounded trusted stage dispatch.

No production source bindings are implied by the historical discovery ledger.
Callbacks are reviewed application code, never dynamically imported CLI plugins.
They own subprocess isolation, byte/time limits, cache verification and recovery.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
import hashlib
import json
import re
import os
from pathlib import Path
import tempfile
from types import MappingProxyType

STAGES = ('acquire', 'verify', 'parse', 'normalize', 'validate', 'curate',
          'graph', 'qualify', 'accept')
POLICIES = ('reuse', 'refresh', 'revalidate', 'force-download')
SUCCESS = ('succeeded', 'reused')
RESULT_STATES = SUCCESS + ('failed', 'held', 'unsupported', 'quarantined')
CODE = re.compile(r'[a-z][a-z0-9-]{0,95}')
DIGEST = re.compile(r'[0-9a-f]{64}')


class GlobalRunError(ValueError):
    """Fixed, shareable diagnostic code."""


@dataclass(frozen=True)
class Limits:
    workers: int = 4
    max_sources: int = 2048
    memory_bytes: int = 1024 * 1024 * 1024
    job_memory_bytes: int = 256 * 1024 * 1024
    acquire_bytes: int = 64 * 1024 * 1024
    acquire_wall_seconds: int = 180
    input_bytes: int = 64 * 1024 * 1024
    output_bytes: int = 256 * 1024 * 1024
    wall_seconds: int = 120

    def validate(self):
        ranges = {'workers': (1, 4), 'max_sources': (1, 4096),
                  'memory_bytes': (1, 4 * 1024**3),
                  'job_memory_bytes': (1, 1024**3),
                  'acquire_bytes': (1, 1024**4), 'acquire_wall_seconds': (1, 600),
                  'input_bytes': (1, 64 * 1024**2),
                  'output_bytes': (1, 256 * 1024**2), 'wall_seconds': (1, 120)}
        for key, (low, high) in ranges.items():
            value = getattr(self, key)
            if type(value) is not int or not low <= value <= high:
                raise GlobalRunError('invalid-resource-limit')
        if self.job_memory_bytes > self.memory_bytes:
            raise GlobalRunError('insufficient-memory-reservation')
        return min(self.workers, self.memory_bytes // self.job_memory_bytes)


@dataclass(frozen=True)
class StageResult:
    status: str
    code: str = 'none'
    evidence: tuple = ()  # SHA-256 references only; never paths, URLs or logs.
    observed_count: int | None = None

    def receipt(self):
        if self.status not in RESULT_STATES or not CODE.fullmatch(self.code):
            raise GlobalRunError('invalid-stage-result')
        if not isinstance(self.evidence, tuple) or len(self.evidence) > 32 or any(
                not isinstance(x, str) or not DIGEST.fullmatch(x) for x in self.evidence):
            raise GlobalRunError('invalid-stage-evidence')
        if self.observed_count is not None and (type(self.observed_count) is not int or self.observed_count < 0):
            raise GlobalRunError('invalid-stage-count')
        if self.status in SUCCESS and not self.evidence:
            raise GlobalRunError('stage-evidence-required')
        return {'status': self.status, 'code': self.code,
                'evidence': sorted(set(self.evidence)), 'observedCount': self.observed_count}


@dataclass(frozen=True)
class StageContext:
    source_id: str
    stage: str
    limits: Limits
    fetch_policy: str | None
    force_rebuild: bool
    previous: tuple


@dataclass(frozen=True)
class Binding:
    """Trusted per-source binding; callbacks must honor the supplied budgets.

No capability is inferred from a callback existing. A reviewed isolation/resource
boundary is required before dispatch. Production bindings remain absent here.
"""
    handlers: dict = field(default_factory=dict)
    admission: str = 'unassessed'
    resource_boundary_verified: bool = False
    endstate: dict = field(default_factory=dict)


def _blocked(status, code):
    return {'status': status, 'code': code, 'evidence': [], 'observedCount': None}


def _source(source, binding, limits, fetch_policy, force_rebuild):
    rows = {}
    if binding is not None:
        binding.endstate.clear()  # Endstate evidence is per-run, never retained state.
    held = source.get('status') == 'held' or bool(source.get('holds'))
    gate = ('source-held' if held else
            'reviewed-handler-binding-missing' if binding is None else
            'source-admission-not-reviewed' if binding.admission != 'reviewed' else
            'resource-boundary-unverified' if not binding.resource_boundary_verified else None)
    for stage in STAGES:
        if gate:
            rows[stage] = _blocked('held' if held else 'unsupported', gate)
            continue
        if rows and list(rows.values())[-1]['status'] not in SUCCESS:
            rows[stage] = _blocked('blocked', 'upstream-stage-incomplete')
            continue
        handler = binding.handlers.get(stage)
        if handler is None:
            rows[stage] = _blocked('unsupported', 'stage-handler-missing')
            continue
        prior = tuple((name, MappingProxyType({**value, 'evidence': tuple(value['evidence'])}))
                      for name, value in rows.items())
        context = StageContext(source['sourceId'], stage, limits,
                               fetch_policy if stage == 'acquire' else None,
                               force_rebuild if stage != 'acquire' else False, prior)
        try:
            result = handler(context)
            if not isinstance(result, StageResult):
                raise GlobalRunError('invalid-stage-result')
            rows[stage] = result.receipt()
        except GlobalRunError:
            rows[stage] = _blocked('failed', 'stage-contract-invalid')
        except Exception:
            # Exception messages may contain credentials, paths or response data.
            rows[stage] = _blocked('failed', 'stage-execution-failed')
    complete = all(row['status'] in SUCCESS for row in rows.values())
    from .acceptance import _valid_acceptance_receipt, fingerprint
    endstate = binding.endstate if binding is not None else {}
    acceptance = endstate.get('acceptance')
    verified_acceptance = (isinstance(acceptance, dict)
                           and _valid_acceptance_receipt(acceptance) and complete
                           and fingerprint(acceptance) in rows['accept']['evidence'])
    return {'sourceId': source['sourceId'],
            'discoveryStatus': source.get('status', 'unassessed'),
            'holds': list(source.get('holds', [])),
            'countries': sorted(source.get('countries', [])),
            'declaredCountries': sorted(source.get('declaredCountries', [])),
            'globalRoute': bool(source.get('globalRoute', False)),
            'blockers': list(source.get('blockers', [])),
            'errors': list(source.get('errors', [])),
            'domains': sorted(source.get('domains', [])),
            'rightsStatus': source.get('rightsStatus', 'unassessed'),
            'cacheStatus': source.get('cacheStatus', 'unassessed'),
            'historicalLandingEvidence': source.get('historicalLandingEvidence'),
            'historicalCapability': source.get('historicalCapability'),
            'normalizationStatus': source.get('normalizationStatus', 'unassessed'),
            'stages': rows,
            'selectedSourceComplete': complete,
            'normalizedCandidate': rows['normalize']['status'] in SUCCESS,
            'qualificationResults': endstate.get('qualifications', {}),
            'sourceAcceptance': acceptance if verified_acceptance else None,
            'acceptedCount': acceptance['acceptedCount'] if complete and verified_acceptance else None}


def run(coverage, *, bindings=None, limits=None, fetch_policy='reuse', force_rebuild=False,
        cell_requirements=(), acceptance_receipts=None):
    """One job per source, sorted independent results, exhaustive country coverage.

Country evidence requires independent reviewed cell requirements and acceptance
receipts bound to completed source stages; parser success alone cannot promote it.
Threads only coordinate bounded adapters; this is not an OS isolation boundary.
"""
    from .coverage import COUNTRIES, DOMAINS
    limits = limits or Limits()
    workers = limits.validate()
    if fetch_policy not in POLICIES or type(force_rebuild) is not bool:
        raise GlobalRunError('invalid-execution-mode')
    sources = coverage['sources']
    ids = [row['sourceId'] for row in sources]
    countries = coverage['countries']
    if (len(countries) != 249 or {r['iso2'] for r in countries} != set(COUNTRIES)
            or any(set(r['domains']) != set(DOMAINS) for r in countries)
            or set(coverage['domainNames']) != set(DOMAINS)):
        raise GlobalRunError('incomplete-country-domain-registry')
    if len(ids) != len(set(ids)) or not ids or len(ids) > limits.max_sources:
        raise GlobalRunError('invalid-source-registry-size')
    bindings = bindings or {}
    if not set(bindings) <= set(ids) or any(not isinstance(b, Binding) for b in bindings.values()):
        raise GlobalRunError('invalid-source-binding')
    # A fixed cap bounds both queued jobs and memory reservations. Executor.map
    # alone eagerly submits the complete registry on older Python versions.
    source_results = []
    ordered = sorted(sources, key=lambda row: row['sourceId'])
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for start in range(0, len(ordered), workers):
            futures = [pool.submit(_source, row, bindings.get(row['sourceId']), limits,
                                   fetch_policy, force_rebuild)
                       for row in ordered[start:start + workers]]
            source_results.extend(future.result() for future in futures)
    from .acceptance import assess_cells, fingerprint
    # Only receipts bound to successful current accept stages qualify this run.
    accepted_evidence = {evidence for source in source_results
                         if source['selectedSourceComplete']
                         for evidence in source['stages']['accept']['evidence']}
    verified_receipts = [receipt for receipt in (acceptance_receipts or {}).values()
                         if fingerprint(receipt) in accepted_evidence]
    cell_results = assess_cells(cell_requirements,
                                verified_receipts,
                                countries=COUNTRIES, domains=DOMAINS)
    failures = sum(not row['selectedSourceComplete'] for row in source_results)
    report = {
        'schemaVersion': 'offmenu-global-run/1',
        'status': 'complete' if failures == 0 and cell_results['countryCoverageComplete'] else 'incomplete',
        'assessmentComplete': True, 'registryComplete': True,
        'executionComplete': failures == 0, 'selectedScopeComplete': failures == 0,
        'countryCoverageComplete': cell_results['countryCoverageComplete'],
        'countryDomainAcceptance': cell_results['cells'],
        'inventoryPins': coverage.get('inventoryPins', {}),
        'retainedReleases': coverage.get('retainedReleases', []),
        'supportingHandlers': coverage.get('supportingHandlers', []),
        'capabilityEvidence': coverage.get('capabilityEvidence', []),
        'fetchPolicy': fetch_policy, 'forceLocalRebuild': force_rebuild,
        'minimumCacheReuseDays': 30, 'parallelSourceLimit': workers,
        'resourceLimits': dict(vars(limits)),
        'networkRequests': 0 if not bindings else None,
        'countries': sorted(countries, key=lambda row: row['iso2']),
        'sources': source_results,
        'summary': {'countries': 249, 'requiredCountryDomainCells': 249 * len(DOMAINS),
                    'sources': len(source_results), 'sourcesComplete': len(source_results) - failures,
                    'sourcesIncomplete': failures, 'acceptedCountryDomainCells': cell_results['acceptedCountryDomainCells'],
                    'sourcesWithHistoricalHandlers': coverage.get('summary', {}).get('sourcesWithHistoricalHandlers'),
                    'sourcesWithoutHistoricalHandlers': coverage.get('summary', {}).get('sourcesWithoutHistoricalHandlers')},
        'limitations': ([] if cell_results['countryCoverageComplete'] else
                        ['reviewed-country-domain-acceptance-incomplete']) +
                        ['production-and-cix-remain-paused'],
    }
    return report


def compact(report):
    """Closed small report for bounded control logs; full report stays on Foo."""
    fingerprint, size = stream_report(report)
    totals = {state: 0 for state in ('succeeded', 'reused', 'failed', 'held',
                                     'unsupported', 'quarantined', 'blocked')}
    for source in report['sources']:
        for result in source['stages'].values():
            totals[result['status']] += 1
    return {'schemaVersion': 'offmenu-global-run-summary/1',
            'status': report['status'], 'assessmentComplete': report['assessmentComplete'],
            'registryComplete': report['registryComplete'],
            'executionComplete': report['executionComplete'],
            'selectedScopeComplete': report['selectedScopeComplete'],
            'countryCoverageComplete': report['countryCoverageComplete'],
            'summary': report['summary'], 'stageStatusCounts': totals,
            'reportSha256': fingerprint,
            'reportBytes': size, 'networkRequests': report['networkRequests']}


def stream_report(report, stream=None):
    """Incremental canonical serialization; no duplicate giant JSON byte string."""
    digest = hashlib.sha256()
    size = 0
    encoder = json.JSONEncoder(sort_keys=True, separators=(',', ':'), allow_nan=False)
    for part in encoder.iterencode(report):
        raw = part.encode('utf-8')
        digest.update(raw)
        size += len(raw)
        if stream is not None:
            stream.write(raw)
    return digest.hexdigest(), size


def write_report(report, output):
    """Stream an exclusive report to an operator-selected Foo output location.

No overwrite, pointer update, remote upload, or implicit directory creation.
The caller is responsible for selecting its approved Foo-only storage route.
"""
    output = Path(os.path.abspath(output))
    if any(path.is_symlink() for path in (output, *output.parents)):
        raise GlobalRunError('report-symlink-rejected')
    if not output.parent.is_dir() or output.exists():
        raise GlobalRunError('report-output-unavailable')
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=output.parent, prefix='.global-report-', delete=False) as stream:
            temporary = Path(stream.name)
            result = stream_report(report, stream)
            stream.flush()
            os.fsync(stream.fileno())
        # link is an atomic no-overwrite publication within the same filesystem.
        os.link(temporary, output)
        return result
    except OSError as error:
        raise GlobalRunError('report-write-failed') from error
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Read-only global assessment; no source payloads or network.')
    parser.add_argument('--matrix', required=True)
    parser.add_argument('--ledger', required=True)
    parser.add_argument('--compact', action='store_true', help='Bounded summary; full report hash uses canonical JSON.')
    parser.add_argument('--output', help='Stream full report exclusively to an approved Foo path; stdout is compact.')
    args = parser.parse_args(argv)
    from .coverage import assess, CoverageError
    try:
        result = run(assess(args.matrix, args.ledger))
        if args.output:
            write_report(result, args.output)
        if args.compact or args.output:
            result = compact(result)
    except (CoverageError, GlobalRunError):
        result = {'schemaVersion': 'offmenu-global-run-error/1', 'status': 'failed',
                  'assessmentComplete': False, 'errorCode': 'global-assessment-input-invalid'}
    print(json.dumps(result, sort_keys=True, separators=(',', ':'), allow_nan=False))
    return 0 if result.get('countryCoverageComplete') is True else 2


if __name__ == '__main__':
    raise SystemExit(main())
