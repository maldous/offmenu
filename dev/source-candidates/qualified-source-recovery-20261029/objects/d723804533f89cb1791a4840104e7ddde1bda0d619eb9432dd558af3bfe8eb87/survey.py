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
MAX_FR_SOURCE_REPORT = 64 * 1024
MAX_CHILD_OUTPUT = 72 * 1024
MAX_INPUT = 32 * 1024 * 1024
MAX_BUNDLE = 64 * 1024 * 1024
CPU_SECONDS = 90
WALL_SECONDS = 100
PROBE_WALL_SECONDS = 30
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


PHASES = frozenset(('not-started', 'startup', 'resource-limits', 'audit-setup',
                    'input-verification', 'source-import', 'source-parse',
                    'source-sanitize', 'country-sanitize', 'encoding', 'emitting',
                    'complete', 'parent-launch', 'parent-read', 'parent-decode',
                    'parent-sanitize', 'unknown', 'asset-read-entry', 'asset-read-complete',
                    'source-parse-entry', 'source-parse-complete',
                    'source-decode-entry', 'source-decode-complete',
                    'source-depth-scan-entry', 'source-depth-scan-complete',
                    'source-json-decoder-entry', 'source-json-decoder-complete',
                    'source-structural-walk-entry', 'source-structural-walk-complete',
                    'source-float-hook-entry', 'source-float-hook-complete',
                    'source-decimal-zero-entry', 'source-decimal-zero-complete'))
EXCEPTIONS = frozenset(('PermissionError', 'FileNotFoundError', 'ImportError',
                       'ModuleNotFoundError', 'MemoryError', 'ValueError', 'TypeError',
                       'KeyError', 'RecursionError', 'RuntimeError', 'OSError',
                       'AttributeError', 'TimeoutExpired', 'SurveyError', 'OverflowError',
                       'BrokenPipeError', 'JSONDecodeError', 'KeyboardInterrupt', 'SystemExit', 'Other'))


def _diagnostics(phase='not-started', error=None):
    name = type(error).__name__ if error is not None else None
    number = getattr(error, 'errno', None)
    return {'phase': phase if phase in PHASES else 'unknown',
            'exceptionClass': name if name in EXCEPTIONS else ('Other' if name else None),
            'errno': number if type(number) is int and 0 < number < 4096 else None,
            'exitCode': None, 'stdoutBytes': 0, 'stderrBytes': 0,
            'resourceLimitsBefore': None, 'resourceLimitsAfter': None, 'progress': []}


# A tiny fixed-token stderr protocol survives SIGSEGV even when stdout is empty.
# It never contains source values, paths, exception text, or traceback fragments.
MARKER_PREFIX = b'OFFMENU_SURVEY_V1 '
MAX_MARKERS = 96
_PROGRESS_COUNTRY = None
_PROGRESS_RESOURCE = None


def _mark(phase, asset=None):
    if _PROGRESS_COUNTRY is None:
        return
    if phase not in PHASES or (asset is not None and asset not in ASSETS):
        raise ValueError('invalid-survey-progress')
    rss = 0
    if _PROGRESS_RESOURCE is not None:
        rss = int(_PROGRESS_RESOURCE.getrusage(_PROGRESS_RESOURCE.RUSAGE_SELF).ru_maxrss)
    size = ASSETS[asset][1] if asset is not None else 0
    line = f'OFFMENU_SURVEY_V1 {_PROGRESS_COUNTRY} {phase} {asset or "-"} {size} {rss}\n'.encode('ascii')
    try:
        os.write(2, line)
    except OSError:
        pass


def _validate_progress(rows, country=None):
    if type(rows) is not list or len(rows) > MAX_MARKERS:
        raise ValueError('invalid-survey-progress')
    allowed = set(ASSETS) if country is None else {'NATIONAL_ACQUISITION', COUNTRIES[country]['prior'], *COUNTRIES[country]['raw']}
    for row in rows:
        exact(row, ('phase', 'asset', 'inputBytes', 'peakRssKiB'))
        asset = row['asset']
        if (row['phase'] not in PHASES or (asset is not None and asset not in allowed) or
                type(row['inputBytes']) is not int or row['inputBytes'] != (ASSETS[asset][1] if asset else 0) or
                type(row['peakRssKiB']) is not int or not 0 <= row['peakRssKiB'] <= 2**32):
            raise ValueError('invalid-survey-progress')
    return rows


def _parse_markers(raw, country):
    rows = []
    for line in raw.splitlines():
        if len(line) > 192 or not line.startswith(MARKER_PREFIX):
            continue
        try:
            prefix, observed, phase, asset, size, rss = line.decode('ascii').split(' ')
            if prefix != 'OFFMENU_SURVEY_V1' or observed != country:
                continue
            if not size.isdecimal() or not rss.isdecimal():
                continue
            row = {'phase': phase, 'asset': None if asset == '-' else asset,
                   'inputBytes': int(size), 'peakRssKiB': int(rss)}
            _validate_progress([row], country)
        except (ValueError, TypeError, KeyError, UnicodeError):
            continue
        if len(rows) < MAX_MARKERS:
            rows.append(row)
    return rows


def _resource_limits(resource):
    return {name: list(resource.getrlimit(which)) for name, which in (
        ('addressSpaceBytes', resource.RLIMIT_AS), ('cpuSeconds', resource.RLIMIT_CPU),
        ('fileBytes', resource.RLIMIT_FSIZE))}


def _validate_diagnostics(value):
    exact(value, ('phase', 'exceptionClass', 'errno', 'exitCode', 'stdoutBytes', 'stderrBytes',
                  'resourceLimitsBefore', 'resourceLimitsAfter', 'progress'))
    if value['phase'] not in PHASES or value['exceptionClass'] not in EXCEPTIONS | {None}:
        raise ValueError('invalid-survey-diagnostics')
    if value['errno'] is not None and (type(value['errno']) is not int or not 0 < value['errno'] < 4096):
        raise ValueError('invalid-survey-diagnostics')
    if value['exitCode'] is not None and (type(value['exitCode']) is not int or not -128 <= value['exitCode'] <= 255):
        raise ValueError('invalid-survey-diagnostics')
    for key in ('stdoutBytes', 'stderrBytes'):
        if type(value[key]) is not int or not 0 <= value[key] <= MAX_CHILD_OUTPUT + 8192:
            raise ValueError('invalid-survey-diagnostics')
    for key in ('resourceLimitsBefore', 'resourceLimitsAfter'):
        limits = value[key]
        if limits is not None:
            exact(limits, ('addressSpaceBytes', 'cpuSeconds', 'fileBytes'))
            for pair in limits.values():
                if (type(pair) is not list or len(pair) != 2 or
                        any(type(n) is not int or not -1 <= n <= 2**63-1 for n in pair)):
                    raise ValueError('invalid-survey-diagnostics')
    _validate_progress(value['progress'])
    return dict(value)


def _error_country(country, code, *, verified=False, submitted=None, diagnostics=None):
    if code not in ERRORS:
        code = 'survey-internal-error'
    return {'country': country, 'sourceId': COUNTRIES[country]['sourceId'],
            'releaseId': COUNTRIES[country]['releaseId'], 'status': 'held',
            'inputPinsVerified': verified, 'readOnlyViewVerified': verified,
            'sourceBodiesSubmitted': submitted, 'errorCode': code, 'survey': None,
            'diagnostics': diagnostics if diagnostics is not None else _diagnostics()}


def _worker(country, *, python_scanner=False):
    verified, submitted, phase = False, 0, 'input-verification'
    spec = COUNTRIES[country]
    _mark(phase)
    if os.getuid() == 0 or os.geteuid() == 0:
        return _error_country(country, 'normal-user-required', submitted=0,
                              diagnostics=_diagnostics(phase))
    try:
        needed = ('NATIONAL_ACQUISITION', spec['prior'], *spec['raw'])
        if sum(ASSETS[key][1] for key in needed) > MAX_BUNDLE:
            raise SurveyError('input-limit')
        # Verified in-memory bytes, never a source path, reach the parser.
        blobs = {}
        for asset_id in needed:
            relative, size, digest = ASSETS[asset_id]
            _mark('asset-read-entry', asset_id)
            body = _read_asset(CACHE, relative, size, digest)
            _mark('asset-read-complete', asset_id)
            if asset_id in spec['raw']:
                blobs[relative.split('/')[-1]] = body
        verified, phase = True, 'source-import'
        _mark(phase)
        module = _module(country)
        phase, submitted = 'source-parse', len(spec['raw'])
        _mark(phase)
        asset_names = {ASSETS[key][0].split('/')[-1]: key for key in spec['raw']}
        def progress(event, name):
            if 'source-' + event not in PHASES or name not in asset_names:
                raise ValueError('invalid-survey-progress')
            _mark('source-' + event, asset_names[name])
        result = module.survey(blobs, progress=progress, **({'python_scanner': True} if python_scanner else {}))
        phase = 'source-sanitize'
        _mark(phase)
        result = module.sanitize_report(result)
        if len(canonical(result)) > (MAX_FR_SOURCE_REPORT if country == 'FR' else MAX_SOURCE_REPORT):
            raise SurveyError('worker-output-limit')
        return {'country': country, 'sourceId': spec['sourceId'], 'releaseId': spec['releaseId'],
                'status': result['status'], 'inputPinsVerified': True, 'readOnlyViewVerified': True,
                'sourceBodiesSubmitted': len(spec['raw']), 'errorCode': None, 'survey': result,
                'diagnostics': _diagnostics('complete')}
    except SurveyError as error:
        return _error_country(country, str(error), verified=verified, submitted=submitted,
                              diagnostics=_diagnostics(phase, error))
    except Exception as error:
        return _error_country(country, 'survey-internal-error', verified=verified, submitted=submitted,
                              diagnostics=_diagnostics(phase, error))


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


def _run_worker_attempt(country, lock_fd, *, python_scanner=False):
    command = [sys.executable, '-I', '-B', str(Path(__file__).resolve()),
               '--worker-python-scanner' if python_scanner else '--worker', country]
    environment = {'PATH': os.defpath, 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'TZ': 'UTC'}
    try:
        process = subprocess.Popen(command, cwd=ROOT, env=environment, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, pass_fds=(lock_fd,))
    except (OSError, ValueError) as error:
        return _error_country(country, 'worker-failed', diagnostics=_diagnostics('parent-launch', error))
    out, err = bytearray(), bytearray()
    code, diagnostic = None, _diagnostics('parent-read')
    deadline = time.monotonic() + (PROBE_WALL_SECONDS if python_scanner else WALL_SECONDS)
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
                        err.extend(chunk)
                    if len(out) > MAX_CHILD_OUTPUT or len(err) > MAX_CHILD_OUTPUT:
                        code = 'worker-output-limit'
                        break
                if code:
                    break
            if code is None:
                try:
                    process.wait(timeout=max(0.01, deadline - time.monotonic()))
                except subprocess.TimeoutExpired as error:
                    code, diagnostic = 'worker-timeout', _diagnostics('parent-read', error)
    except (OSError, ValueError) as error:
        code, diagnostic = 'worker-failed', _diagnostics('parent-read', error)
    finally:
        _stop(process)
        process.stdout.close()
        process.stderr.close()
    transport = {'exitCode': process.returncode, 'stdoutBytes': len(out), 'stderrBytes': len(err)}
    markers = _parse_markers(err, country)
    transport['progress'] = markers
    diagnostic.update(transport)
    if code:
        if markers:
            diagnostic['phase'] = markers[-1]['phase']
        return _error_country(country, code, diagnostics=diagnostic)
    # A worker may emit a useful structured failure and exit nonzero. Preserve
    # that diagnostic instead of throwing it away under a generic exit status.
    phase = 'parent-decode'
    try:
        value = strict_json(out)
        phase = 'parent-sanitize'
        result = sanitize_country(value, country)
        result['diagnostics'].update(transport)
        if process.returncode != 0 and result['errorCode'] is None:
            return _error_country(country, 'worker-failed', verified=result['inputPinsVerified'],
                                  submitted=result['sourceBodiesSubmitted'], diagnostics=result['diagnostics'])
        return result
    except (ValueError, TypeError, KeyError, RecursionError) as error:
        diagnostic = _diagnostics(phase, error)
        diagnostic.update(transport)
        if markers:
            diagnostic['phase'] = markers[-1]['phase']
        if process.returncode < 0 and not out:
            diagnostic['exceptionClass'] = None
        return _error_country(country, 'worker-failed' if process.returncode else 'worker-report-invalid',
                              diagnostics=diagnostic)



JSON_CRASH_PHASES = frozenset(('source-json-decoder-entry', 'source-float-hook-entry',
                             'source-float-hook-complete', 'source-decimal-zero-entry',
                             'source-decimal-zero-complete'))


def _native_decoder_failure(value):
    diagnostic = value['diagnostics']
    return (value['errorCode'] == 'worker-failed' and
            type(diagnostic['exitCode']) is int and diagnostic['exitCode'] in (-4, -6, -7, -8, -11) and
            diagnostic['phase'] in JSON_CRASH_PHASES)


def _run_worker(country, lock_fd):
    result = _run_worker_attempt(country, lock_fd)
    if country == 'NO' and _native_decoder_failure(result):
        # One diagnostic retry only; original failure remains the primary result.
        # It re-verifies identical fixed pins, with identical numeric/key hooks,
        # memory/CPU/audit limits, and a smaller 30-second wall budget.
        probe = _run_worker_attempt(country, lock_fd, python_scanner=True)
        result['decoderProbe'] = {'scanner': 'stdlib-python',
            'trigger': 'native-default-json-decoder-failure', 'result': probe}
    return result


def sanitize_country(value, country, *, allow_probe=True):
    if isinstance(value, dict) and 'decoderProbe' in value:
        if country != 'NO' or not allow_probe:
            raise ValueError('invalid-survey-probe')
        primary = {key: item for key, item in value.items() if key != 'decoderProbe'}
        clean = sanitize_country(primary, country, allow_probe=False)
        probe = value['decoderProbe']
        exact(probe, ('scanner', 'trigger', 'result'))
        if (not _native_decoder_failure(clean) or probe['scanner'] != 'stdlib-python' or
                probe['trigger'] != 'native-default-json-decoder-failure'):
            raise ValueError('invalid-survey-probe')
        clean['decoderProbe'] = {**probe, 'result': sanitize_country(probe['result'], country, allow_probe=False)}
        return clean
    exact(value, ('country', 'sourceId', 'releaseId', 'status', 'inputPinsVerified',
                  'readOnlyViewVerified', 'sourceBodiesSubmitted', 'errorCode', 'survey', 'diagnostics'))
    _validate_diagnostics(value['diagnostics'])
    _validate_progress(value['diagnostics']['progress'], country)
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
                (value['inputPinsVerified'] is True and value['sourceBodiesSubmitted'] not in (0, len(COUNTRIES[country]['raw']))) or
                (value['inputPinsVerified'] is False and value['sourceBodiesSubmitted'] not in (None, 0)) or
                value != _error_country(country, value['errorCode'],
                                        verified=value['inputPinsVerified'], submitted=value['sourceBodiesSubmitted'], diagnostics=value['diagnostics']) or
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
            except (OSError, ValueError) as error:
                countries[country] = _error_country(country, 'worker-failed',
                                                    diagnostics=_diagnostics('parent-read', error))
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
    global _PROGRESS_COUNTRY, _PROGRESS_RESOURCE
    if (len(sys.argv) != 3 or sys.argv[1] not in ('--worker', '--worker-python-scanner') or
            sys.argv[2] not in COUNTRIES or not sys.flags.isolated or
            (sys.argv[1] == '--worker-python-scanner' and sys.argv[2] != 'NO')):
        return 2
    country, phase, before, after = sys.argv[2], 'startup', None, None
    python_scanner = sys.argv[1] == '--worker-python-scanner'
    resource = None
    _PROGRESS_COUNTRY = country
    _mark(phase)
    try:
        import resource
        _PROGRESS_RESOURCE = resource
        phase = 'resource-limits'
        _mark(phase)
        before = _resource_limits(resource)
        resource.setrlimit(resource.RLIMIT_AS, (MEMORY_BYTES, MEMORY_BYTES))
        resource.setrlimit(resource.RLIMIT_CPU, (CPU_SECONDS, CPU_SECONDS))
        resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_REPORT, MAX_REPORT))
        after = _resource_limits(resource)
        phase = 'audit-setup'
        _mark(phase)
        signal.alarm(PROBE_WALL_SECONDS if python_scanner else WALL_SECONDS)
        sys.dont_write_bytecode = True
        sys.path.insert(0, str(ROOT))
        sys.addaudithook(_audit_guard)
        report = _worker(country, python_scanner=python_scanner)
        phase = 'country-sanitize'
        _mark(phase)
        report = sanitize_country(report, country)
        report['diagnostics'].update(resourceLimitsBefore=before, resourceLimitsAfter=after)
        phase = 'encoding'
        _mark(phase)
        encoded = canonical(report)
        if len(encoded) > MAX_CHILD_OUTPUT:
            raise SurveyError('worker-output-limit')
        phase = 'emitting'
        _mark(phase)
        sys.stdout.buffer.write(encoded)
        sys.stdout.buffer.flush()
        _mark('complete')
        return 0
    except BaseException as error:
        # Only fixed phase/class/errno and numeric limits cross this boundary.
        # No traceback, exception message, source fragment or path is emitted.
        diagnostic = _diagnostics(phase, error)
        if resource is not None:
            try:
                after = _resource_limits(resource)
            except BaseException:
                pass
        diagnostic.update(resourceLimitsBefore=before, resourceLimitsAfter=after)
        report = _error_country(country, 'worker-failed', diagnostics=diagnostic)
        try:
            os.write(1, canonical(sanitize_country(report, country)))
        except BaseException:
            # A broken output channel cannot carry a report. Parent transport
            # diagnostics still preserve exit status and bounded byte counts.
            pass
        return 2


if __name__ == '__main__':
    raise SystemExit(_worker_main())
