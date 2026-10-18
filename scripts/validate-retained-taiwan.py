#!/usr/bin/env python3
"""Inactive, exact-byte Taiwan recovery proposal; never mutate custody or download.

Call only under the existing collection writer lease. A successful result is a
proposal for a separately reviewed additive disposition, never an applied one.
The original BOM and every old failed record remain byte-for-byte untouched.
"""
from contextlib import ExitStack, contextmanager
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import selectors
import signal
import stat
import subprocess
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('taiwan_recovery_boundary', ROOT / 'scripts/diagnose-retained-taiwan.py')
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)
OBSERVATION_COMMIT = '3bbb6835568dcc58ff147f8b1c459c5e37dfc3e0'
OBSERVATION_RESULT = '7e844aae16ed22b088c2643fec3f9722110cdad30b9f0fcc264c2db57eba4795'
PINS = {
    'tw41-eastern-afa-14101-regional-bento-original': {
        'bodySHA256': 'b49be9438831bd5446669172408c7d9aab9307f0b1cc008b73e72414501500a0',
        'intentSHA256': '86386346048d13a891fea396ea9d271734cbdc4d54595f92e54fa8da7a62e43b'},
    'tw41-eastern-afa-14102-regional-bento-original': {
        'bodySHA256': '188749647a3aa866fccaf4c038928b7327caf37821d1193c631fb8ff3cd7b88b',
        'intentSHA256': 'd58b3dc4f6387dc810e863c5bc72cc47c228b2486dcbe2f218b39401dbb0ad22'},
    'tw41-eastern-afa-14103-regional-bento-original': {
        'bodySHA256': '133041c9bdd981977434165c9978d95537d7e8ae42cbcd866fcb7b17f2ce461e',
        'intentSHA256': 'd5a1614fe2f2bf585d5b1be27f13704d159d72bdc20891fa080f62e4cec7872f'},
}
TOOLS = {'limit': '/usr/bin/prlimit', 'pdfinfo': '/usr/bin/pdfinfo', 'pdftotext': '/usr/bin/pdftotext'}
MAX_PAGES = 2000
MAX_TEXT_BYTES = 16 * 1024 * 1024
MAX_MEMORY_BYTES = 768 * 1024 * 1024
MAX_SECONDS = 60
ERRORS = set(d.ERRORS) | {'recovery-source-unselected', 'recovery-identity-mismatch',
    'recovery-boundary-mismatch', 'parser-unavailable', 'parser-isolation-unavailable',
    'parser-output-limit', 'parser-invalid-input', 'parser-diagnostic-present',
    'parser-version-mismatch', 'parser-interrupted', 'pdf-encrypted', 'pdf-page-limit'}
SAFETY = {'networkRequests': 0, 'sourceBodiesModified': False, 'oldFailedRecordsModified': False,
    'sourceBytesUploaded': 0, 'dispositionApplied': False, 'publisherChecksumEstablished': False,
    'historicalBodyIdentityEstablished': False, 'strictISOConformanceEstablished': False,
    'normalizationPerformed': False, 'semanticOrGoldAdmission': False}


def selected_entry(source):
    key = source.get('sourceKey') if isinstance(source, dict) else None
    if not isinstance(key, str) or key not in PINS:
        raise ValueError('recovery-source-unselected')
    entry = next(e for e in d.ENTRIES if d.item_template(e)['sourceKey'] == key)
    source_raw = (json.dumps(source, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')
    if hashlib.sha256(source_raw).hexdigest() != entry[1]:
        raise ValueError('recovery-source-unselected')
    return entry


def exact_selected_bom_identity(source, data):
    """Source/digest-restricted hook; never a generic PDF sniffing exception."""
    entry = selected_entry(source)
    return (len(data) == entry[3] and hashlib.sha256(data).hexdigest() == PINS[source['sourceKey']]['bodySHA256']
        and bool(re.match(rb'\xef\xbb\xbf%PDF-(?:1\.[0-7]|2\.0)(?:\r\n|\r|\n)', data))
        and bool(re.search(rb'%%EOF[\x00\x09\x0a\x0c\x0d\x20]*$', data[-4096:])))


class _ParserInterrupted(BaseException):
    """Unwind parser ownership without being mistaken for a validation result."""


@contextmanager
def termination_scope():
    """Defer termination through PID registration and cleanup, then redeliver.

    The handler only records a signal: raising inside Popen could lose a newly
    created session before its owner receives the Popen object. Keep it active
    until all owned children have been killed/reaped. Ignored signals remain
    ignored, and all prior handlers are restored before redelivery.
    """
    if threading.current_thread() is not threading.main_thread():
        raise ValueError('parser-isolation-unavailable')
    received, previous = [], {}

    def record(signum, frame):
        if not received:
            received.append(signum)

    def check():
        if received:
            raise _ParserInterrupted()

    try:
        for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
            previous[signum] = signal.getsignal(signum)
            if previous[signum] != signal.SIG_IGN:
                signal.signal(signum, record)
        yield check
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)
        if received:
            signal.raise_signal(received[0])
            # A prior custom handler may return. Abort this validation anyway;
            # a default terminating handler never reaches this branch.
            raise ValueError('parser-interrupted')


def run_tool(tool, arguments, data, deadline, stdout_limit, retain_stdout=True, retain_stderr=False):
    """Bounded installed-tool stdin validation, with resource limits and no shell."""
    d.check_deadline(deadline)
    for name in ('limit', tool):
        path = Path(TOOLS[name])
        try:
            info = path.stat()
        except OSError:
            raise ValueError('parser-isolation-unavailable' if name == 'limit' else 'parser-unavailable') from None
        if not stat.S_ISREG(info.st_mode) or not os.access(path, os.X_OK):
            raise ValueError('parser-unavailable')
    seconds = max(1, min(MAX_SECONDS, math.ceil(deadline - time.monotonic())))
    command = [TOOLS['limit'], '--as=' + str(MAX_MEMORY_BYTES), '--cpu=' + str(seconds),
        '--fsize=0', '--nofile=32', '--', TOOLS[tool], *arguments]
    with termination_scope() as check_signal:
        return _run_owned_tool(command, data, deadline, stdout_limit, retain_stdout, retain_stderr, check_signal)


def _run_owned_tool(command, data, deadline, stdout_limit, retain_stdout, retain_stderr, check_signal):
    process, selector = None, None
    sent = output_count = diagnostic_count = 0
    output, diagnostics = [], []
    try:
        check_signal()
        selector = selectors.DefaultSelector()
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, close_fds=True, start_new_session=True,
            env={'PATH': '/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C', 'HOME': '/nonexistent'})
        check_signal()
        for stream, event, name in ((process.stdin, selectors.EVENT_WRITE, 'in'),
                (process.stdout, selectors.EVENT_READ, 'out'), (process.stderr, selectors.EVENT_READ, 'err')):
            os.set_blocking(stream.fileno(), False)
            if name == 'in' and not data:
                stream.close()
            else:
                selector.register(stream, event, name)
        while selector.get_map():
            check_signal()
            d.check_deadline(deadline)
            for key, _ in selector.select(min(0.05, max(0, deadline - time.monotonic()))):
                check_signal()
                d.check_deadline(deadline)
                if key.data == 'in':
                    try:
                        sent += os.write(key.fd, memoryview(data)[sent:sent + 65536])
                    except BlockingIOError:
                        continue
                    except BrokenPipeError:
                        sent = len(data)
                    if sent == len(data):
                        selector.unregister(key.fileobj)
                        key.fileobj.close()
                    continue
                try:
                    block = os.read(key.fd, min(65536, (stdout_limit - output_count + 1) if key.data == 'out' else (16384 - diagnostic_count + 1)))
                except BlockingIOError:
                    continue
                if not block:
                    selector.unregister(key.fileobj)
                    key.fileobj.close()
                    continue
                if key.data == 'out':
                    output_count += len(block)
                    if output_count > stdout_limit:
                        raise ValueError('parser-output-limit')
                    if retain_stdout:
                        output.append(block)
                else:
                    diagnostic_count += len(block)
                    if diagnostic_count > 16384:
                        raise ValueError('parser-output-limit')
                    if retain_stderr:
                        diagnostics.append(block)
        while process.poll() is None:
            check_signal()
            d.check_deadline(deadline)
            try:
                process.wait(timeout=min(0.05, max(0.001, deadline - time.monotonic())))
            except subprocess.TimeoutExpired:
                continue
        check_signal()
        d.check_deadline(deadline)
        return {'returnCode': process.returncode, 'stdout': b''.join(output),
            'stderr': b''.join(diagnostics), 'stdoutBytes': output_count, 'diagnosticBytes': diagnostic_count}
    except subprocess.TimeoutExpired:
        raise ValueError('diagnostic-deadline-exceeded') from None
    except OSError:
        raise ValueError('parser-unavailable') from None
    finally:
        if selector is not None:
            selector.close()
        if process is not None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
            for stream in (process.stdin, process.stdout, process.stderr):
                if stream is not None and not stream.closed:
                    stream.close()


def parser_template():
    return {'name': 'poppler', 'pdfinfoVersion': None, 'pdftotextVersion': None,
        'pageCount': None, 'encrypted': None, 'pdfinfoExitCode': None,
        'pdftotextExitCode': None, 'diagnosticBytes': 0, 'textBytesExamined': 0,
        'allPagesTraversed': False, 'status': 'not-run', 'errorCode': None}


def parser_check(data, deadline):
    result = parser_template()
    try:
        # Version probes write their fixed version output to stderr; capture it
        # through the published utility '-v' output without a document input.
        versions = []
        for tool in ('pdfinfo', 'pdftotext'):
            probe = run_tool(tool, ['-v'], b'', min(deadline, time.monotonic() + 2), 4096, retain_stderr=True)
            version_output = probe['stdout'] + probe['stderr']
            match = re.search((tool + r' version ([0-9][0-9A-Za-z.+_-]{0,63})').encode(), version_output[:4096])
            if probe['returnCode'] != 0 or len(version_output) > 4096 or not match:
                raise ValueError('parser-unavailable')
            version = match.group(1).decode('ascii')
            result[tool + 'Version'] = version
            versions.append(version)
        if len(set(versions)) != 1:
            raise ValueError('parser-version-mismatch')
        info = run_tool('pdfinfo', ['-'], data, deadline, 65536)
        result.update(pdfinfoExitCode=info['returnCode'], diagnosticBytes=info['diagnosticBytes'])
        if info['returnCode'] != 0:
            raise ValueError('parser-invalid-input')
        if info['diagnosticBytes']:
            raise ValueError('parser-diagnostic-present')
        encrypted = re.findall(rb'^Encrypted:\s+(yes|no)\b', info['stdout'], re.M)
        pages = re.findall(rb'^Pages:\s+([0-9]{1,8})\s*$', info['stdout'], re.M)
        if len(encrypted) != 1 or len(pages) != 1:
            raise ValueError('parser-invalid-input')
        result.update(encrypted=encrypted[0] == b'yes', pageCount=int(pages[0]))
        if result['encrypted']:
            raise ValueError('pdf-encrypted')
        if not 1 <= result['pageCount'] <= MAX_PAGES:
            raise ValueError('pdf-page-limit')
        text = run_tool('pdftotext', ['-enc', 'UTF-8', '-f', '1', '-l', str(result['pageCount']), '-', '-'],
            data, deadline, MAX_TEXT_BYTES, retain_stdout=False)
        result.update(pdftotextExitCode=text['returnCode'], diagnosticBytes=result['diagnosticBytes'] + text['diagnosticBytes'],
            textBytesExamined=text['stdoutBytes'])
        if text['returnCode'] != 0:
            raise ValueError('parser-invalid-input')
        if text['diagnosticBytes']:
            raise ValueError('parser-diagnostic-present')
        result.update(status='passed', allPagesTraversed=True)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        code = str(error) if isinstance(error, ValueError) and str(error) in ERRORS else 'parser-unavailable'
        result.update(status='blocked', errorCode=code)
    return result


def report_template(source_key):
    source_key = source_key if isinstance(source_key, str) and source_key in PINS else None
    entry = next((e for e in d.ENTRIES if d.item_template(e)['sourceKey'] == source_key), None)
    return {'schemaVersion': 'offmenu-retained-taiwan-recovery-proposal/1',
        'sourceKey': source_key if source_key in PINS else None,
        'sourceContractSHA256': entry[1] if entry else None,
        'priorFailedDetailSHA256': entry[2] if entry else None,
        'observationCommit': OBSERVATION_COMMIT, 'observationResultSHA256': OBSERVATION_RESULT,
        'retainedBytes': entry[3] if entry else None,
        'retainedSHA256': PINS[source_key]['bodySHA256'] if entry else None,
        'oldFailedIntentSHA256': PINS[source_key]['intentSHA256'] if entry else None,
        'status': 'blocked', 'errorCode': None, 'parser': parser_template(),
        'proposedDisposition': None, **SAFETY}


def validate_selected(source, output_root, absolute_deadline):
    report = report_template(source.get('sourceKey') if isinstance(source, dict) else None)
    try:
        entry = selected_entry(source)
        deadline = min(absolute_deadline, time.monotonic() + MAX_SECONDS)
        if os.getuid() != d.EXPECTED_UID or os.geteuid() != d.EXPECTED_UID:
            raise ValueError('owner-identity-mismatch')
        with ExitStack() as stack:
            root = d.open_root(stack, output_root)
            root_before = d.owned(root, True)
            work = d.open_child(stack, root, 'collection', True)
            work_before = d.owned(work, True)
            observation = d.diagnose_one(work, entry, deadline)
            if observation['status'] != 'observed':
                raise ValueError(observation['errorCode'])
            pin = PINS[source['sourceKey']]
            if observation['observedBodySHA256'] != pin['bodySHA256'] or observation['intentSHA256'] != pin['intentSHA256']:
                raise ValueError('recovery-identity-mismatch')
            originals = d.open_child(stack, work, 'private-originals', True)
            originals_before = d.owned(originals, True)
            folder = d.open_child(stack, originals, entry[1], True)
            folder_before = d.owned(folder, True)
            _, _, old_intent_check = d.read_metadata(stack, folder, 'successor-intent.json', pin['intentSHA256'])
            fd = d.open_child(stack, folder, 'original.partial')
            before = d.owned(fd)
            if before[2] != entry[3]:
                raise ValueError('recovery-identity-mismatch')
            blocks, count = [], 0
            while count < entry[3]:
                d.check_deadline(deadline)
                block = os.read(fd, min(65536, entry[3] - count))
                if not block:
                    raise ValueError('custody-changed-during-read')
                count += len(block)
                blocks.append(block)
            data = b''.join(blocks)
            if not exact_selected_bom_identity(source, data):
                raise ValueError('recovery-boundary-mismatch')
            report['parser'] = parser_check(data, deadline)
            if report['parser']['status'] != 'passed':
                raise ValueError(report['parser']['errorCode'])
            d.check_deadline(deadline)
            d.unchanged(fd, folder, 'original.partial', before)
            d.unchanged(*old_intent_check)
            d.unchanged(folder, originals, entry[1], folder_before)
            d.unchanged(originals, work, 'private-originals', originals_before)
            d.unchanged(work, root, 'collection', work_before)
            current_root = d.open_root(stack, output_root)
            if d.owned(current_root, True) != root_before:
                raise ValueError('custody-changed-during-read')
            report.update(status='validated-proposal', proposedDisposition={
                'kind': 'validated-retained-original-reference/1',
                'relativePath': 'collection/private-originals/' + entry[1] + '/original.partial',
                'sourceContractSHA256': entry[1], 'sha256': pin['bodySHA256'], 'bytes': entry[3],
                'preserveOriginalBytes': True, 'preserveFailedIntent': True,
                'originalAcquiredAt': None, 'scope': 'private-unchanged-original-structural-validation-only'})
    except (OSError, ValueError, TypeError, KeyError, RecursionError) as error:
        code = str(error) if isinstance(error, ValueError) and str(error) in ERRORS else 'local-read-failed'
        report.update(status='blocked', errorCode=code, proposedDisposition=None)
    return sanitize_report(report)


def sanitize_report(report):
    if not isinstance(report, dict):
        raise ValueError('invalid-taiwan-recovery-proposal')
    base = report_template(report.get('sourceKey'))
    if (set(report) != set(base) or any(type(report[k]) is not type(v) or report[k] != v
            for k, v in base.items() if k not in {'status', 'errorCode', 'parser', 'proposedDisposition'}) or
            report['status'] not in {'blocked', 'validated-proposal'}):
        raise ValueError('invalid-taiwan-recovery-proposal')
    p = report['parser']
    if not isinstance(p, dict) or set(p) != set(parser_template()) or p['name'] != 'poppler':
        raise ValueError('invalid-taiwan-recovery-proposal')
    for key in ('pdfinfoVersion', 'pdftotextVersion'):
        if p[key] is not None and (not isinstance(p[key], str) or not re.fullmatch('[0-9][0-9A-Za-z.+_-]{0,63}', p[key])):
            raise ValueError('invalid-taiwan-recovery-proposal')
    for key in ('pdfinfoExitCode', 'pdftotextExitCode'):
        if p[key] is not None and (type(p[key]) is not int or not -128 <= p[key] <= 255):
            raise ValueError('invalid-taiwan-recovery-proposal')
    if (p['pageCount'] is not None and (type(p['pageCount']) is not int or not 0 <= p['pageCount'] <= 99999999)):
        raise ValueError('invalid-taiwan-recovery-proposal')
    if (p['encrypted'] is not None and type(p['encrypted']) is not bool) or type(p['allPagesTraversed']) is not bool:
        raise ValueError('invalid-taiwan-recovery-proposal')
    if any(type(p[k]) is not int or not 0 <= p[k] <= limit
            for k, limit in (('diagnosticBytes', 32768), ('textBytesExamined', MAX_TEXT_BYTES))):
        raise ValueError('invalid-taiwan-recovery-proposal')
    if p['status'] not in {'not-run', 'blocked', 'passed'}:
        raise ValueError('invalid-taiwan-recovery-proposal')
    if p['status'] == 'passed':
        if (p['errorCode'] is not None or not p['allPagesTraversed'] or p['encrypted'] is not False or
                type(p['pageCount']) is not int or not 1 <= p['pageCount'] <= MAX_PAGES or
                p['pdfinfoVersion'] is None or p['pdfinfoVersion'] != p['pdftotextVersion'] or
                p['pdfinfoExitCode'] != 0 or p['pdftotextExitCode'] != 0 or p['diagnosticBytes'] != 0):
            raise ValueError('invalid-taiwan-recovery-proposal')
    elif p['status'] == 'blocked':
        if p['errorCode'] not in ERRORS or p['allPagesTraversed']:
            raise ValueError('invalid-taiwan-recovery-proposal')
    elif p != parser_template():
        raise ValueError('invalid-taiwan-recovery-proposal')
    if report['status'] == 'blocked':
        if report['errorCode'] not in ERRORS or report['proposedDisposition'] is not None:
            raise ValueError('invalid-taiwan-recovery-proposal')
    else:
        expected = {'kind': 'validated-retained-original-reference/1',
            'relativePath': 'collection/private-originals/' + str(report['sourceContractSHA256']) + '/original.partial',
            'sourceContractSHA256': report['sourceContractSHA256'], 'sha256': report['retainedSHA256'],
            'bytes': report['retainedBytes'], 'preserveOriginalBytes': True, 'preserveFailedIntent': True,
            'originalAcquiredAt': None, 'scope': 'private-unchanged-original-structural-validation-only'}
        if report['sourceKey'] not in PINS or report['errorCode'] is not None or p['status'] != 'passed' or d.canonical(report['proposedDisposition']) != d.canonical(expected):
            raise ValueError('invalid-taiwan-recovery-proposal')
    if len(d.canonical(report)) > 8192:
        raise ValueError('invalid-taiwan-recovery-proposal')
    return json.loads(d.canonical(report))
