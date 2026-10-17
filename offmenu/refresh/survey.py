"""Fixed-selection read-only national schema survey; never an adapter admission.

Only six exact NO/FR source assets and three corroborating receipts are readable.
Workers expose structural dictionaries and aggregate diagnostics, never food rows.
The shared refresh CLI owns this diagnostic entry point; candidate lifecycles and
all synthetic/historical adapter gates are deliberately unchanged.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import re
import selectors
import signal
import sqlite3
import stat
import subprocess
import sys
import tempfile
import time
import uuid
import zlib
import pyexpat

SCHEMA = 'offmenu-selected-schema-survey/1'
WORKER_SCHEMA = 'offmenu-selected-schema-worker/1'
CACHE = Path('/srv/offmenu-refresh/cache')
OUTPUT = Path('/srv/offmenu-refresh/outputs')
ROOT = Path(__file__).resolve().parents[2]
MAX_REPORT = 96 * 1024
MAX_SOURCE_REPORT = 32 * 1024
MAX_CHILD_OUTPUT = 48 * 1024
MAX_INPUT = 32 * 1024 * 1024
MAX_BUNDLE = 64 * 1024 * 1024
CPU_SECONDS = 90
WALL_SECONDS = 100
MEMORY_BYTES = 1024 * 1024 * 1024
HEX = re.compile(r'[0-9a-f]{64}\Z')
# Sizes/hashes independently observed on Foo in diagnostics run 39077114923.
# Paths are fixed code, never taken from source files, receipt labels or callers.
ASSETS = {
 'NO_EN_FOODS': ('norway/en-foods.json', 13690405, '89b8f5f494a79731bf7d8d98065ee66c55263ccdbb519e7c87941218be6c948d'),
 'NO_NB_FOODS': ('norway/nb-foods.json', 13690645, '7c7ebb52109433ea15032a29f495843a5da229313bbcf4a4fe7ebcc45b9c9b33'),
 'NO_EN_NUTRIENTS': ('norway/en-nutrients.json', 13081, '15a95f0ebd0682daa293685203dad9aaa28b07df4e9b943ca03269161fbefd91'),
 'NO_EN_SOURCES': ('norway/en-sources.json', 97245, '71917dadc84a5218bb3a78327cda6945c48eb6b2e72e4ee7fbf0c23ab7f6778d'),
 'FR_WORKBOOK': ('ciqual/Table Ciqual 2025_ENG_2025_11_03.xlsx', 1537602, '2c3495c8136d17356c50db410918da2102cb28096cb497c9cdf83c5f8ecb10ba'),
 'FR_IDENTITIES': ('ciqual/alim_2025_11_03.xml', 1581031, 'e0b1de25b3039028205e9d54a96892e403e1b313c2efeb41180fabe132627478'),
 'NATIONAL_ACQUISITION': ('metadata/national-acquisition.json', 8970, '654f91bd14d83b7b55a058777a0b8fd836674310e3dc38235638ec9435dc4edc'),
 'NO_PRIOR_MANIFEST': ('metadata/no-prior-manifest.json', 2217, '8b6eb6d3adc99c3aab9053bd0fc373d7755ad1638769c72bafaf4f3a510b94a9'),
 'FR_PRIOR_MANIFEST': ('metadata/fr-prior-manifest.json', 1930, 'df4df008991e573c1a0f23111611b5fff2f68b62640546d9bb0360fe760cf9ab'),
}
COUNTRIES = {
 'NO': {'sourceId': 'matvaretabellen', 'releaseId': '2026',
        'raw': ('NO_EN_FOODS', 'NO_NB_FOODS', 'NO_EN_NUTRIENTS', 'NO_EN_SOURCES'),
        'prior': 'NO_PRIOR_MANIFEST', 'module': 'survey_norway'},
 'FR': {'sourceId': 'ciqual', 'releaseId': '2025',
        'raw': ('FR_WORKBOOK', 'FR_IDENTITIES'),
        'prior': 'FR_PRIOR_MANIFEST', 'module': 'survey_ciqual'},
}
ERRORS = frozenset(('selected-asset-unavailable', 'selected-path-unsafe', 'selected-not-regular',
                   'selected-size-mismatch', 'selected-hash-mismatch', 'selected-changed',
                   'selected-view-not-read-only', 'selected-multiple-links', 'input-limit',
                   'worker-timeout', 'worker-output-limit', 'worker-failed',
                   'worker-report-invalid', 'survey-internal-error', 'normal-user-required'))
BOUNDARIES = {'sourceWrites': 0, 'sourceCopies': 0, 'downloads': 0, 'foodRowsExported': 0,
              'candidateGenerationEnabled': False, 'acceptance': 'not-performed',
              'publicExport': 'not-enabled', 'countryCoverageComplete': False,
              'historicalAdapterAdmission': 'not-enabled', 'sourceUseDecision': 'not-performed',
              'freshness': 'unknown', 'originalAcquiredAt': None, 'minimumReuseDays': 30,
              'mtimeUsedForFreshness': False, 'revalidationResetsAcquisitionAge': False,
              'osNetworkConfinementVerified': False}


class SurveyError(ValueError):
    pass


def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def strict_json(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ValueError('duplicate-json-key')
            value[key] = item
        return value
    def invalid(_):
        raise ValueError('nonfinite-json-number')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def exact(value, keys):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError('invalid-survey-report')


def _sig(s):
    return (s.st_dev, s.st_ino, s.st_mode, s.st_nlink, s.st_size, s.st_mtime_ns, s.st_ctime_ns)


def _read_asset(root, relative, size, digest):
    """Anchored no-follow read; verified in-memory bytes are the parsed bytes."""
    parts = Path(root).parts
    if not Path(root).is_absolute() or '..' in parts or any(x in ('', '.', '..') for x in relative.split('/')):
        raise SurveyError('selected-path-unsafe')
    handles, ancestry = [], []
    try:
        fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
        handles.append(fd)
        for part in (*parts[1:], *relative.split('/')[:-1]):
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            handles.append(child)
            ancestry.append((fd, part, child, _sig(os.fstat(child))))
            fd = child
        name = relative.split('/')[-1]
        before = os.stat(name, dir_fd=fd, follow_symlinks=False)
        if not stat.S_ISREG(before.st_mode):
            raise SurveyError('selected-not-regular')
        if before.st_nlink != 1:
            raise SurveyError('selected-multiple-links')
        if before.st_size != size or not 0 < size <= MAX_INPUT:
            raise SurveyError('selected-size-mismatch')
        source = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        handles.append(source)
        if _sig(os.fstat(source)) != _sig(before):
            raise SurveyError('selected-changed')
        if not os.fstatvfs(source).f_flag & os.ST_RDONLY:
            raise SurveyError('selected-view-not-read-only')
        body = bytearray()
        while len(body) < size:
            chunk = os.read(source, min(65536, size - len(body)))
            if not chunk:
                raise SurveyError('selected-changed')
            body.extend(chunk)
        if (_sig(os.fstat(source)) != _sig(before) or
                _sig(os.stat(name, dir_fd=fd, follow_symlinks=False)) != _sig(before)):
            raise SurveyError('selected-changed')
        for parent, component, child, original in ancestry:
            if (_sig(os.fstat(child)) != original or
                    _sig(os.stat(component, dir_fd=parent, follow_symlinks=False)) != original):
                raise SurveyError('selected-changed')
        if not os.fstatvfs(source).f_flag & os.ST_RDONLY:
            raise SurveyError('selected-view-not-read-only')
        body = bytes(body)
        if sha(body) != digest:
            raise SurveyError('selected-hash-mismatch')
        return body
    except SurveyError:
        raise
    except OSError as error:
        if error.errno in (20, 40):
            raise SurveyError('selected-path-unsafe') from None
        raise SurveyError('selected-asset-unavailable') from None
    finally:
        for fd in reversed(handles):
            os.close(fd)


def _module(country):
    if country == 'NO':
        from offmenu.refresh import survey_norway
        return survey_norway
    if country == 'FR':
        from offmenu.refresh import survey_ciqual
        return survey_ciqual
    raise ValueError('unknown-survey-country')


def _error_country(country, code, *, verified=False, submitted=None):
    if code not in ERRORS:
        code = 'survey-internal-error'
    return {'country': country, 'sourceId': COUNTRIES[country]['sourceId'],
            'releaseId': COUNTRIES[country]['releaseId'], 'status': 'held',
            'inputPinsVerified': verified, 'readOnlyViewVerified': verified,
            'sourceBodiesSubmitted': submitted, 'errorCode': code, 'survey': None}


def _worker(country):
    verified, submitted = False, 0
    spec = COUNTRIES[country]
    if os.getuid() == 0 or os.geteuid() == 0:
        return _error_country(country, 'normal-user-required', submitted=0)
    try:
        needed = ('NATIONAL_ACQUISITION', spec['prior'], *spec['raw'])
        if sum(ASSETS[key][1] for key in needed) > MAX_BUNDLE:
            raise SurveyError('input-limit')
        # Receipt pins corroborate release/provenance only, never confer adapter
        # admission or a new legal decision. Every needed asset is independently
        # reverified in this invocation before any source body is interpreted.
        blobs = {}
        for asset_id in needed:
            relative, size, digest = ASSETS[asset_id]
            body = _read_asset(CACHE, relative, size, digest)
            if asset_id in spec['raw']:
                blobs[relative.split('/')[-1]] = body
        verified, submitted = True, len(spec['raw'])
        module = _module(country)
        result = module.sanitize_report(module.survey(blobs))
        if len(canonical(result)) > MAX_SOURCE_REPORT:
            raise SurveyError('worker-output-limit')
        return {'country': country, 'sourceId': spec['sourceId'], 'releaseId': spec['releaseId'],
                'status': result['status'], 'inputPinsVerified': True, 'readOnlyViewVerified': True,
                'sourceBodiesSubmitted': len(spec['raw']), 'errorCode': None, 'survey': result}
    except SurveyError as error:
        return _error_country(country, str(error), verified=verified, submitted=submitted)
    except Exception:
        return _error_country(country, 'survey-internal-error', verified=verified, submitted=submitted)


def _audit_guard(event, args):
    if event.startswith(('socket.', 'subprocess.', 'ctypes.')) or event in {
            'os.system', 'os.exec', 'os.posix_spawn', 'os.fork', 'os.forkpty',
            'os.remove', 'os.rename', 'os.rmdir', 'os.mkdir', 'os.link', 'os.symlink',
            'os.chmod', 'os.chown', 'os.truncate', 'os.utime'}:
        raise RuntimeError('read-only-survey-operation-denied')
    if event == 'open':
        _, mode, flags = args
        if (isinstance(mode, str) and any(x in mode for x in 'wa+')) or flags & (
                os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
            raise RuntimeError('read-only-survey-operation-denied')


def _stop(process):
    # Workers cannot spawn. Keep them in the coordinator process group so the
    # dispatcher's group cancellation reaches both; kill this child on timeout.
    try:
        process.kill()
    except ProcessLookupError:
        pass
    process.wait()


def _run_worker(country, lock_fd):
    command = [sys.executable, '-I', '-B', str(Path(__file__).resolve()), '--worker', country]
    environment = {'PATH': os.defpath, 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'TZ': 'UTC'}
    process = subprocess.Popen(command, cwd=ROOT, env=environment, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, pass_fds=(lock_fd,))
    out, err_count = bytearray(), 0
    code = None
    deadline = time.monotonic() + WALL_SECONDS
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ, True)
            selector.register(process.stderr, selectors.EVENT_READ, False)
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    code = 'worker-timeout'
                    break
                for key, _ in selector.select(min(remaining, 0.2)):
                    chunk = os.read(key.fileobj.fileno(), 8192)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    if key.data:
                        out.extend(chunk)
                    else:
                        err_count += len(chunk)
                    if len(out) > MAX_CHILD_OUTPUT or err_count > MAX_CHILD_OUTPUT:
                        code = 'worker-output-limit'
                        break
                if code:
                    break
            if code is None:
                try:
                    returncode = process.wait(timeout=max(0.01, deadline - time.monotonic()))
                    if returncode != 0:
                        code = 'worker-failed'
                except subprocess.TimeoutExpired:
                    code = 'worker-timeout'
    finally:
        _stop(process)
        process.stdout.close()
        process.stderr.close()
    if code:
        return _error_country(country, code)
    try:
        return sanitize_country(strict_json(out), country)
    except (ValueError, TypeError, KeyError, RecursionError):
        return _error_country(country, 'worker-report-invalid')


def sanitize_country(value, country):
    exact(value, ('country', 'sourceId', 'releaseId', 'status', 'inputPinsVerified',
                  'readOnlyViewVerified', 'sourceBodiesSubmitted', 'errorCode', 'survey'))
    expected = {'country': country, 'sourceId': COUNTRIES[country]['sourceId'],
                'releaseId': COUNTRIES[country]['releaseId']}
    if any(value[k] != v for k, v in expected.items()):
        raise ValueError('invalid-survey-report')
    if value['errorCode'] is not None:
        if (type(value['inputPinsVerified']) is not bool or
                value['readOnlyViewVerified'] is not value['inputPinsVerified'] or
                (value['sourceBodiesSubmitted'] is not None and
                 (type(value['sourceBodiesSubmitted']) is not int or
                  value['sourceBodiesSubmitted'] not in (0, len(COUNTRIES[country]['raw'])))) or
                (value['inputPinsVerified'] is True and value['sourceBodiesSubmitted'] != len(COUNTRIES[country]['raw'])) or
                (value['inputPinsVerified'] is False and value['sourceBodiesSubmitted'] not in (None, 0)) or
                value != _error_country(country, value['errorCode'],
                                        verified=value['inputPinsVerified'], submitted=value['sourceBodiesSubmitted']) or
                value['errorCode'] not in ERRORS):
            raise ValueError('invalid-survey-report')
        return dict(value)
    if (value['inputPinsVerified'] is not True or value['readOnlyViewVerified'] is not True or
            type(value['sourceBodiesSubmitted']) is not int or
            value['sourceBodiesSubmitted'] != len(COUNTRIES[country]['raw'])):
        raise ValueError('invalid-survey-report')
    survey = _module(country).sanitize_report(value['survey'])
    if value['status'] != survey['status']:
        raise ValueError('invalid-survey-report')
    return {**value, 'survey': survey}


def runtime():
    return {'python': platform.python_version(), 'implementation': platform.python_implementation(),
            'zlib': zlib.ZLIB_RUNTIME_VERSION, 'sqlite': sqlite3.sqlite_version,
            'expat': pyexpat.EXPAT_VERSION}


def code_identity():
    files = sorted((ROOT / 'offmenu/refresh').glob('*.py'))
    pins = {str(path.relative_to(ROOT)): {'bytes': path.stat().st_size, 'sha256': sha(path.read_bytes())}
            for path in files}
    return sha(canonical({'files': pins, 'runtime': runtime()}))


def input_lock():
    return {key: {'bytes': value[1], 'sha256': value[2]} for key, value in sorted(ASSETS.items())}


def sanitize_report(value):
    exact(value, ('schemaVersion', 'operationId', 'status', 'surveyComplete', 'codeFingerprint',
                  'selectionSha256', 'inputPins', 'runtime', 'boundaries', 'countries'))
    if (value['schemaVersion'] != SCHEMA or not isinstance(value['operationId'], str) or
            not re.fullmatch('[0-9a-f]{32}', value['operationId']) or
            value['inputPins'] != input_lock() or value['selectionSha256'] != sha(canonical(ASSETS)) or
            value['boundaries'] != BOUNDARIES or not isinstance(value['codeFingerprint'], str) or
            not HEX.fullmatch(value['codeFingerprint'])):
        raise ValueError('invalid-survey-report')
    exact(value['runtime'], ('python', 'implementation', 'zlib', 'sqlite', 'expat'))
    for key, item in value['runtime'].items():
        if (not isinstance(item, str) or not 1 <= len(item) <= 64 or
                not re.fullmatch(r'[A-Za-z0-9._+ -]+', item)):
            raise ValueError('invalid-survey-report')
    exact(value['countries'], COUNTRIES)
    countries = {country: sanitize_country(value['countries'][country], country) for country in COUNTRIES}
    complete = all(row['survey'] is not None and row['survey']['evidenceComplete'] is True
                   for row in countries.values())
    status = 'surveyed' if all(row['status'] == 'surveyed' for row in countries.values()) else 'held'
    if value['surveyComplete'] is not complete or value['status'] != status:
        raise ValueError('invalid-survey-report')
    clean = {**value, 'countries': countries}
    if len(canonical(clean)) > MAX_REPORT:
        raise ValueError('survey-report-limit')
    return clean


def _safe_directory(path):
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts:
        raise SurveyError('output-path-unsafe')
    for parent in (*reversed(path.parents), path):
        if parent.is_symlink():
            raise SurveyError('output-path-unsafe')
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    s = path.stat()
    if not stat.S_ISDIR(s.st_mode) or s.st_uid != os.getuid():
        raise SurveyError('output-directory-owner-invalid')
    return path


def _write_new(path, value):
    """Atomic, immutable diagnostic evidence; no existing record is replaced."""
    payload = canonical(value)
    if len(payload) > MAX_REPORT:
        raise SurveyError('survey-report-limit')
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.survey-', delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path, follow_symlinks=False)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def survey_selected(workspace):
    """CLI boundary: fixed input root and approved Foo output area only."""
    workspace = Path(workspace)
    if not workspace.is_absolute() or not workspace.is_relative_to(OUTPUT) or workspace == OUTPUT:
        raise SurveyError('survey-workspace-outside-output-root')
    if os.getuid() == 0 or os.geteuid() == 0:
        raise SurveyError('normal-user-required')
    workspace = _safe_directory(workspace)
    import fcntl
    fd = os.open(workspace / 'survey.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        operation_id = uuid.uuid4().hex
        run = _safe_directory(workspace / operation_id)
        fingerprint = code_identity()
        _write_new(run / 'started.json', {'schemaVersion': 'offmenu-selected-schema-run/1',
                   'operationId': operation_id, 'codeFingerprint': fingerprint,
                   'selectionSha256': sha(canonical(ASSETS)), 'inputPins': input_lock(),
                   'runtime': runtime(), 'boundaries': dict(BOUNDARIES)})
        countries = {}
        # One bounded isolated worker at a time; a failed source never suppresses
        # the other source. Each durable per-source result precedes the next run.
        for country in COUNTRIES:
            try:
                countries[country] = _run_worker(country, fd)
            except (OSError, ValueError):
                countries[country] = _error_country(country, 'worker-failed')
            _write_new(run / (country + '.json'), countries[country])
        if code_identity() != fingerprint:
            raise SurveyError('survey-code-changed-during-run')
        complete = all(row['survey'] is not None and row['survey']['evidenceComplete'] is True
                       for row in countries.values())
        report = {'schemaVersion': SCHEMA, 'operationId': operation_id,
                  'status': 'surveyed' if all(row['status'] == 'surveyed' for row in countries.values()) else 'held',
                  'surveyComplete': complete, 'codeFingerprint': fingerprint,
                  'selectionSha256': sha(canonical(ASSETS)), 'inputPins': input_lock(),
                  'runtime': runtime(), 'boundaries': dict(BOUNDARIES), 'countries': countries}
        report = sanitize_report(report)
        _write_new(run / 'report.json', report)
        return report
    finally:
        os.close(fd)


def _worker_main():
    if len(sys.argv) != 3 or sys.argv[1] != '--worker' or sys.argv[2] not in COUNTRIES or not sys.flags.isolated:
        return 2
    import resource
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_BYTES, MEMORY_BYTES))
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_SECONDS, CPU_SECONDS))
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_REPORT, MAX_REPORT))
    signal.alarm(WALL_SECONDS)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(ROOT))
    sys.addaudithook(_audit_guard)
    try:
        report = sanitize_country(_worker(sys.argv[2]), sys.argv[2])
        encoded = canonical(report)
        if len(encoded) > MAX_CHILD_OUTPUT:
            return 2
        sys.stdout.buffer.write(encoded)
        return 0
    except BaseException:
        return 2


if __name__ == '__main__':
    raise SystemExit(_worker_main())
