#!/usr/bin/env python3
"""Fixed-scope, offline Foo census. No source bindings or access grants implied."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import stat
import sys
import tempfile

SCHEMA = 'offmenu-global-readiness/1'
CACHE = Path('/srv/offmenu-refresh/cache')
OUTPUT = Path('/srv/offmenu-refresh/outputs')
# These metadata files already belong to the exact trusted source checkout.
# No host mount, home path, network acquisition, or dataset custody is implied.
TRUSTED_ROOT = Path(__file__).absolute().parents[2]
REGISTERED_INPUTS = {'matrix': 'docs/country-delivery-matrix.json',
                     'ledger': 'docs/source-delivery-ledger.json'}
MAX_REPORT = 12 * 1024
MAX_FULL_REPORT = 16 * 1024 * 1024
KINDS = {'runtime', 'coverage'}
REASONS = {'complete', 'metadata-not-registered', 'metadata-unavailable-or-invalid',
           'global-assessment-failed', 'local-report-unavailable', 'resource-observation-partial'}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def observation(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ', value):
        raise ValueError('invalid-observation-time')
    dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    return value


def base(kind, observed):
    return {'schemaVersion': SCHEMA, 'kind': kind, 'observedAt': observation(observed),
            'status': 'blocked', 'reason': 'metadata-not-registered',
            'sourceContentsUploaded': False, 'downloads': 0,
            'sourceWrites': 0, 'minimumReuseDays': 30, 'countryCoverageComplete': False}


def space(path):
    try:
        if any(p.is_symlink() for p in (path, *path.parents)):
            raise OSError()
        s = os.statvfs(path)
        return {'observed': True, 'availableBytes': s.f_bavail * s.f_frsize,
                'availableInodes': max(0, s.f_favail), 'readOnly': bool(s.f_flag & os.ST_RDONLY)}
    except OSError:
        return {'observed': False, 'availableBytes': None, 'availableInodes': None, 'readOnly': None}


def _limit(which):
    values = resource.getrlimit(which)
    return [None if v == resource.RLIM_INFINITY else v for v in values]


def _cgroup_limits():
    # Read only our own unified cgroup; no arbitrary process/cgroup enumeration.
    result = {'observed': False, 'memoryBytes': None, 'cpuQuotaMicros': None,
              'cpuPeriodMicros': None, 'tasks': None}
    try:
        raw = Path('/proc/self/cgroup').read_text()[:8192]
        rows = [row[3:] for row in raw.splitlines() if row.startswith('0::')]
        if len(rows) != 1 or not rows[0].startswith('/') or '..' in Path(rows[0]).parts:
            return result
        root = Path('/sys/fs/cgroup') / rows[0].lstrip('/')
        def read(name):
            value = (root / name).read_text()[:128].strip()
            return None if value == 'max' else int(value)
        memory, tasks = read('memory.max'), read('pids.max')
        cpu = (root / 'cpu.max').read_text()[:128].strip().split()
        if len(cpu) != 2:
            return result
        result.update(observed=True, memoryBytes=memory, tasks=tasks,
                      cpuQuotaMicros=None if cpu[0] == 'max' else int(cpu[0]), cpuPeriodMicros=int(cpu[1]))
    except (OSError, ValueError):
        pass
    return result


def runtime(observed):
    result = base('runtime', observed)
    try:
        affinity = len(os.sched_getaffinity(0))
    except (OSError, AttributeError):
        affinity = None
    result.update(reason='complete', status='complete',
                  pythonVersion=list(sys.version_info[:3]), normalUser=os.getuid() != 0 and os.geteuid() != 0,
                  cpuAffinityCount=affinity, processLimits={'addressSpace': _limit(resource.RLIMIT_AS),
                  'cpuSeconds': _limit(resource.RLIMIT_CPU), 'openFiles': _limit(resource.RLIMIT_NOFILE)},
                  currentCgroupLimits=_cgroup_limits(), cgroupAncestorLimitsVerified=False,
                  scopes={'selectedCache': space(CACHE), 'dedicatedOutput': space(OUTPUT)},
                  expectedServiceLimits={'memoryBytes': 3 * 1024**3, 'cpuPercent': 200, 'tasks': 256},
                  effectiveServiceConfigurationVerified=False, wholeHostCapacityEstablished=False,
                  originalAcquiredAt=None, cacheFreshness='unknown', mtimeUsedForFreshness=False)
    if not all(v['observed'] for v in result['scopes'].values()) or not result['currentCgroupLimits']['observed']:
        result['reason'] = 'resource-observation-partial'
    return result


def _registered_paths():
    # Fixed registration, never caller-supplied paths. Coverage.assess verifies
    # the exact immutable SHA256 and byte-size pins before parsing these bytes.
    expected = {'matrix': 'docs/country-delivery-matrix.json',
                'ledger': 'docs/source-delivery-ledger.json'}
    if type(REGISTERED_INPUTS) is not dict or REGISTERED_INPUTS != expected:
        raise ValueError('metadata-not-registered')
    paths = {}
    for kind, relative in expected.items():
        path = TRUSTED_ROOT / relative
        if any(p.is_symlink() for p in (path, *path.parents)) or not path.is_file():
            raise ValueError('invalid-registration')
        # Checkout metadata need not be a read-only filesystem. Never reuse this
        # as proof that source datasets are mounted read-only or recently acquired.
        paths[kind] = path
    return paths


def _retain(report, digest):
    body = canonical(report)
    if len(body) > MAX_FULL_REPORT or hashlib.sha256(body).hexdigest() != digest:
        raise ValueError('full-report-bound')
    root = OUTPUT / 'global-readiness'
    if any(p.is_symlink() for p in (root, *root.parents)):
        raise ValueError('unsafe-output')
    root.mkdir(mode=0o700, exist_ok=True)
    if root.stat().st_uid != os.getuid() or stat.S_IMODE(root.stat().st_mode) != 0o700:
        raise ValueError('unsafe-output')
    # Private full metadata census never enters stdout or a GitHub artifact.
    with tempfile.NamedTemporaryFile(dir=root, prefix='assessment-', suffix='.json', mode='wb', delete=False) as f:
        f.write(body)
        f.flush()
        os.fsync(f.fileno())
    return True


def coverage(observed):
    result = base('coverage', observed)
    result.update(registeredMetadata=False, metadataPinsVerified=False,
                  fullReportRetainedLocally=False, globalSummary=None,
                  metadataOrigin="trusted-code-checkout", datasetCacheCustodyVerified=False,
                  originalAcquiredAt=None, cacheFreshness='unknown', mtimeUsedForFreshness=False)
    if REGISTERED_INPUTS is None:
        return result
    result['registeredMetadata'] = True
    try:
        paths = _registered_paths()
        from offmenu.refresh import coverage as registry, global_run
        assessed = registry.assess(paths['matrix'], paths['ledger'])
        result['metadataPinsVerified'] = True
    except Exception:
        result['reason'] = 'metadata-unavailable-or-invalid'
        return result
    try:
        report = global_run.run(assessed, limits=global_run.Limits(workers=2))
        summary = global_run.compact(report)
        _summary(summary)
    except Exception:
        result['reason'] = 'global-assessment-failed'
        return result
    try:
        result['fullReportRetainedLocally'] = _retain(report, summary['reportSha256'])
    except Exception:
        result['reason'] = 'local-report-unavailable'
        return result
    # A complete census can describe blocked production; it does not mean accepted countries.
    result.update(status='complete', reason='complete', globalSummary=summary)
    return result


def _number(v, upper=2**63-1, nullable=False):
    if nullable and v is None:
        return
    if type(v) is not int or not 0 <= v <= upper:
        raise ValueError('invalid-count')


def _summary(v):
    keys = {'schemaVersion','status','assessmentComplete','registryComplete','executionComplete',
            'selectedScopeComplete','countryCoverageComplete','summary','stageStatusCounts',
            'reportSha256','reportBytes','networkRequests'}
    if type(v) is not dict or set(v) != keys or v['schemaVersion'] != 'offmenu-global-run-summary/1' or v['status'] != 'incomplete':
        raise ValueError('invalid-summary')
    for name in ('assessmentComplete','registryComplete','executionComplete','selectedScopeComplete','countryCoverageComplete'):
        if type(v[name]) is not bool:
            raise ValueError('invalid-summary')
    if not v['assessmentComplete'] or not v['registryComplete'] or v['countryCoverageComplete'] or v['networkRequests'] != 0 or type(v['networkRequests']) is not int:
        raise ValueError('invalid-summary')
    if type(v['reportSha256']) is not str or not re.fullmatch('[0-9a-f]{64}',v['reportSha256']):
        raise ValueError('invalid-summary')
    _number(v['reportBytes'], MAX_FULL_REPORT)
    expected = {'countries','requiredCountryDomainCells','sources','sourcesComplete','sourcesIncomplete','acceptedCountryDomainCells','sourcesWithHistoricalHandlers','sourcesWithoutHistoricalHandlers'}
    if type(v['summary']) is not dict or set(v['summary']) != expected:
        raise ValueError('invalid-summary')
    for value in v['summary'].values():
        _number(value, 100000)
    counts = v['summary']
    if counts['countries'] != 249 or counts['requiredCountryDomainCells'] != 3237 or counts['sources'] != 1303 or counts['acceptedCountryDomainCells'] != 0 or counts['sourcesComplete']+counts['sourcesIncomplete'] != 1303:
        raise ValueError('invalid-summary')
    if counts['sourcesWithHistoricalHandlers'] + counts['sourcesWithoutHistoricalHandlers'] != 1303:
        raise ValueError('invalid-summary')
    states = {'succeeded','reused','failed','held','unsupported','quarantined','blocked'}
    if type(v['stageStatusCounts']) is not dict or set(v['stageStatusCounts']) != states:
        raise ValueError('invalid-summary')
    for value in v['stageStatusCounts'].values():
        _number(value, 11727)
    if sum(v['stageStatusCounts'].values()) != 1303 * 9:
        raise ValueError('invalid-summary')


def sanitize_report(value):
    if type(value) is not dict or value.get('schemaVersion') != SCHEMA or value.get('kind') not in KINDS:
        raise ValueError('invalid-report')
    template = base(value['kind'], value.get('observedAt'))
    shared = set(template)
    extra = {'originalAcquiredAt','cacheFreshness','mtimeUsedForFreshness'}
    extra |= ({'registeredMetadata','metadataPinsVerified','fullReportRetainedLocally','globalSummary','metadataOrigin','datasetCacheCustodyVerified'} if value['kind']=='coverage' else
              {'pythonVersion','normalUser','cpuAffinityCount','processLimits','currentCgroupLimits','cgroupAncestorLimitsVerified',
               'scopes','expectedServiceLimits','effectiveServiceConfigurationVerified','wholeHostCapacityEstablished'})
    if set(value) != shared | extra or value['reason'] not in REASONS or value['status'] not in {'complete','blocked'}:
        raise ValueError('invalid-report')
    for name in ('sourceContentsUploaded','countryCoverageComplete','mtimeUsedForFreshness'):
        if value[name] is not False:
            raise ValueError('invalid-boundary')
    for name in ('downloads','sourceWrites'):
        if type(value[name]) is not int or value[name] != 0:
            raise ValueError('invalid-boundary')
    if type(value['minimumReuseDays']) is not int or value['minimumReuseDays'] != 30 or value['originalAcquiredAt'] is not None or value['cacheFreshness'] != 'unknown':
        raise ValueError('invalid-freshness')
    if value['kind'] == 'coverage':
        if value['metadataOrigin'] != 'trusted-code-checkout' or value['datasetCacheCustodyVerified'] is not False:
            raise ValueError('invalid-metadata-custody')
        for name in ('registeredMetadata','metadataPinsVerified','fullReportRetainedLocally'):
            if type(value[name]) is not bool:
                raise ValueError('invalid-report')
        if value['status'] == 'complete':
            if value['reason'] != 'complete' or not all(value[n] for n in ('registeredMetadata','metadataPinsVerified','fullReportRetainedLocally')):
                raise ValueError('invalid-completion')
            _summary(value['globalSummary'])
        elif value['globalSummary'] is not None:
            raise ValueError('invalid-blocked-summary')
    else:
        if value['status'] != 'complete' or value['reason'] not in {'complete','resource-observation-partial'}:
            raise ValueError('invalid-runtime')
        for name in ('cgroupAncestorLimitsVerified','effectiveServiceConfigurationVerified','wholeHostCapacityEstablished'):
            if value[name] is not False:
                raise ValueError('invalid-capacity-claim')
        if type(value['normalUser']) is not bool or type(value['pythonVersion']) is not list or len(value['pythonVersion']) != 3:
            raise ValueError('invalid-runtime')
        for n in value['pythonVersion']:
            _number(n,100000)
        _number(value['cpuAffinityCount'],100000,True)
        if type(value['processLimits']) is not dict or set(value['processLimits']) != {'addressSpace','cpuSeconds','openFiles'}:
            raise ValueError('invalid-limits')
        for pair in value['processLimits'].values():
            if type(pair) is not list or len(pair)!=2:
                raise ValueError('invalid-limits')
            for n in pair:
                _number(n,nullable=True)
        cg = value['currentCgroupLimits']
        if type(cg) is not dict or set(cg) != {'observed','memoryBytes','cpuQuotaMicros','cpuPeriodMicros','tasks'} or type(cg['observed']) is not bool:
            raise ValueError('invalid-cgroup')
        for k in set(cg)-{'observed'}:
            _number(cg[k],nullable=True)
        if value['expectedServiceLimits'] != {'memoryBytes':3*1024**3,'cpuPercent':200,'tasks':256}:
            raise ValueError('invalid-expectation')
        if type(value['scopes']) is not dict or set(value['scopes']) != {'selectedCache','dedicatedOutput'}:
            raise ValueError('invalid-scopes')
        for v in value['scopes'].values():
            if type(v) is not dict or set(v) != {'observed','availableBytes','availableInodes','readOnly'} or type(v['observed']) is not bool or (v['readOnly'] is not None and type(v['readOnly']) is not bool):
                raise ValueError('invalid-scopes')
            _number(v['availableBytes'],nullable=True)
            _number(v['availableInodes'],nullable=True)
    raw = canonical(value)
    if len(raw) > MAX_REPORT:
        raise ValueError('report-bound')
    return json.loads(raw)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=sorted(KINDS), required=True)
    parser.add_argument('--observed-at', required=True, type=observation)
    args = parser.parse_args(argv)
    result = sanitize_report((runtime if args.mode=='runtime' else coverage)(args.observed_at))
    print(canonical(result).decode())
    return 0 if result['status']=='complete' else 2


if __name__ == '__main__':
    raise SystemExit(main())
