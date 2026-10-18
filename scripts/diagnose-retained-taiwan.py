#!/usr/bin/env python3
"""Read-only boundary diagnostics for three already-retained, pinned partials.

The caller must hold the existing collection/fixed-selection.lock writer lease.
No network, subprocess, parser, custody write, retry, repair or promotion occurs.
Boundary observations describe current bytes, not historical integrity or PDF validity.
"""
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import time

OUTPUT_ROOT = Path('/home/user/src/offmenu-data/owner-collection-runtime')
EXPECTED_UID = 1000
SOURCE_COMMIT = 'd97316cf3bdd9fce2d415b87a708d071ad8074e7'
REPORT_COMMIT = 'c041a0ce815747414df8454865fee01a07149fec'
RESULT_SHA256 = '213b9c4fb27fa961f26ae0211db29fe7040c5c9e30dac626b0e1a98e1ae5ce6e'
HANDOVER = {'handoffId': 'owner-local-global-20261018-001',
    'runtimeConfigSHA256': '8dd3372dd9c2f4f0ec5f845cdc1a97c64addf8fe12ccecc26603128bb2bf514b',
    'dispatchHoldSHA256': 'fa87ebcb5463ffdec2f7bbfe0141da0c518b40a59c29297646b92a0644e165f1',
    'executionContext': 'owner-manual-foo', 'runnerResumeRequiresOutcomeImport': True}
ENTRIES = (
    ('14101', '7904c23aecb10a1a87b9a166fbffcdf58fd2274dc92351976642a97d89232bfc',
     '1abb104dea5275b1d1cdd557e7b26017fb30bf9b134be3ec656f030ccf523e9b', 2290082),
    ('14102', '40a144d090ad51ae2c9c2a949c844c114e455d195339b2e65d8a8bd7dcc55d39',
     '7106964b9e0f792523f3c2fc952005b45b4fd506ccb94c9e44224c4a138f68d2', 1136770),
    ('14103', '7c7242814c51532617e432ac8fce965e5997b779a9f29c07de0f102e545251a9',
     'df0e955daedeef00e594d174ec9e64bda282b89469433737fe1606c6c7b71c62', 3063624),
)
MAX_METADATA = 128 * 1024
PDF_WHITESPACE = b'\x00\x09\x0a\x0c\x0d\x20'
ERRORS = {'root-unavailable', 'owner-identity-mismatch', 'unsafe-custody-path',
    'metadata-pin-mismatch', 'prior-failure-evidence-mismatch', 'failed-intent-mismatch',
    'unsafe-custody-file', 'partial-extent-mismatch', 'custody-changed-during-read',
    'diagnostic-deadline-exceeded', 'local-read-failed', 'custody-state-conflict'}
SAFETY = {'networkRequests': 0, 'sourceBodyBytesUploaded': 0, 'sourceClaimsChanged': False,
    'sourceBodiesChanged': False, 'acquisitionEnabled': False,
    'semanticParsingPerformed': False, 'historicalBodyIdentityEstablished': False}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def check_deadline(deadline):
    if time.monotonic() >= deadline:
        raise ValueError('diagnostic-deadline-exceeded')


def identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns,
            info.st_ctime_ns, info.st_uid, info.st_mode, info.st_nlink)


def owned(fd, directory=False):
    info = os.fstat(fd)
    if (info.st_uid != EXPECTED_UID or info.st_mode & 0o077 or
            not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)) or
            (not directory and info.st_nlink != 1)):
        raise ValueError('unsafe-custody-file')
    return identity(info)


def open_child(stack, parent, name, directory=False):
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC
    if directory:
        flags |= os.O_DIRECTORY
    fd = os.open(name, flags, dir_fd=parent)
    stack.callback(os.close, fd)
    return fd


def open_root(stack, path):
    # Directory descriptors pin every component; no symlink ancestor is followed.
    if Path(path) != OUTPUT_ROOT or not Path(path).is_absolute() or '..' in Path(path).parts:
        raise ValueError('unsafe-custody-path')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    stack.callback(os.close, fd)
    for component in Path(path).parts[1:]:
        fd = open_child(stack, fd, component, directory=True)
    owned(fd, directory=True)
    return fd


def unchanged(fd, parent, name, before):
    if (identity(os.fstat(fd)) != before or
            identity(os.stat(name, dir_fd=parent, follow_symlinks=False)) != before):
        raise ValueError('custody-changed-during-read')


def read_metadata(stack, parent, name, expected_sha=None):
    fd = open_child(stack, parent, name)
    before = owned(fd)
    if before[2] > MAX_METADATA:
        raise ValueError('unsafe-custody-file')
    raw = os.read(fd, MAX_METADATA + 1)
    unchanged(fd, parent, name, before)
    if len(raw) != before[2]:
        raise ValueError('custody-changed-during-read')
    digest = hashlib.sha256(raw).hexdigest()
    if expected_sha is not None and digest != expected_sha:
        raise ValueError('metadata-pin-mismatch')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('metadata-pin-mismatch')
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=unique,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError('metadata-pin-mismatch')))
    if not isinstance(value, dict):
        raise ValueError('metadata-pin-mismatch')
    return value, digest, (fd, parent, name, before)


def boundary_facts(prefix, tail, count):
    offset = prefix.find(b'%PDF-')
    eof = tail.rfind(b'%%EOF')
    trailing = tail[eof + 5:] if eof >= 0 else None
    starts_pdf = prefix.startswith(b'%PDF-')
    terminal = bool(re.search(rb'%%EOF[\x00\x09\x0a\x0c\x0d\x20]*$', tail))
    prefix_kind = ('pdf-at-zero' if starts_pdf else
        'utf8-bom-before-pdf' if prefix.startswith(b'\xef\xbb\xbf%PDF-') else
        'pdf-whitespace-before-pdf' if offset > 0 and not prefix[:offset].strip(PDF_WHITESPACE) else
        'html-like-prefix' if prefix.lstrip(PDF_WHITESPACE).lower().startswith((b'<!doctype html', b'<html')) else
        'other')
    return {'prefixWindowBytes': len(prefix), 'tailWindowBytes': len(tail),
        'pdfSignatureAtByteZero': starts_pdf,
        'pdfSignatureOffsetInFirst1024': offset if offset >= 0 else None,
        'prefixClassification': prefix_kind, 'terminalEOFMatchesCurrentRule': terminal,
        'lastEOFOffsetFromEnd': len(tail) - eof if eof >= 0 else None,
        'bytesAfterLastEOF': len(trailing) if trailing is not None else None,
        'onlyPDFWhitespaceAfterLastEOF': not trailing.strip(PDF_WHITESPACE) if trailing is not None else None,
        'currentValidatorFailurePoint': 'pdf-prefix' if not starts_pdf else 'pdf-terminal-eof' if not terminal else 'none'}


def item_template(entry):
    number, contract, detail, size = entry
    return {'sourceKey': 'tw41-eastern-afa-' + number + '-regional-bento-original',
        'sourceContractSHA256': contract, 'priorDetailSHA256': detail,
        'expectedLocalBytes': size, 'status': 'blocked', 'errorCode': None,
        'localBodyBytesRead': 0, 'observedBodySHA256': None, 'intentSHA256': None,
        'boundaryFacts': None}


def diagnose_one(work, entry, deadline):
    result = item_template(entry)
    number, contract, detail_sha, size = entry
    try:
        check_deadline(deadline)
        with ExitStack() as stack:
            detail, _, detail_check = read_metadata(stack, work,
                'private-original-result-' + detail_sha + '.json', detail_sha)
            if (detail.get('schemaVersion') != 'offmenu-private-original-save-detail/1' or
                    detail.get('sourceKey') != result['sourceKey'] or detail.get('selectionSHA256') != contract or
                    detail.get('status') != 'failed' or detail.get('errorCode') != 'source-header-mismatch' or
                    detail.get('privateSaveState') != 'partial-retained' or detail.get('localBodyBytes') != size or
                    detail.get('network') != {'requests': 1, 'bodyBytesRead': size} or
                    detail.get('responseMetadata', {}).get('httpStatus') != 200 or
                    detail.get('responseMetadata', {}).get('contentType') != 'application/pdf'):
                raise ValueError('prior-failure-evidence-mismatch')
            originals = open_child(stack, work, 'private-originals', True)
            originals_before = owned(originals, True)
            folder = open_child(stack, originals, contract, True)
            folder_before = owned(folder, True)
            intent, intent_sha, intent_check = read_metadata(stack, folder, 'successor-intent.json')
            expected = {'schemaVersion': 'offmenu-private-original-successor/1',
                'sourceKey': result['sourceKey'], 'sourceContractSHA256': contract,
                'url': 'https://erb.afa.gov.tw/index.php?act=download&ids=' + number,
                'owner': EXPECTED_UID, 'ownerHandover': HANDOVER, 'state': 'failed-no-retry',
                'errorCode': 'source-header-mismatch', 'privateSaveState': 'partial-retained',
                'localBodyBytes': size, 'network': {'requests': 1, 'bodyBytesRead': size}}
            if any(intent.get(key) != value for key, value in expected.items()):
                raise ValueError('failed-intent-mismatch')
            for name in ('original.pdf', 'provenance.json', 'reservation.bin'):
                try:
                    os.stat(name, dir_fd=folder, follow_symlinks=False)
                except FileNotFoundError:
                    continue
                raise ValueError('custody-state-conflict')
            fd = open_child(stack, folder, 'original.partial')
            before = owned(fd)
            if before[2] != size:
                raise ValueError('partial-extent-mismatch')
            prefix, tail, digest = b'', b'', hashlib.sha256()
            while result['localBodyBytesRead'] < size:
                check_deadline(deadline)
                block = os.read(fd, min(65536, size - result['localBodyBytesRead']))
                if not block:
                    raise ValueError('custody-changed-during-read')
                result['localBodyBytesRead'] += len(block)
                prefix = (prefix + block)[:1024]
                tail = (tail + block)[-4096:]
                digest.update(block)
            check_deadline(deadline)
            for check in (detail_check, intent_check, (fd, folder, 'original.partial', before),
                    (folder, originals, contract, folder_before),
                    (originals, work, 'private-originals', originals_before)):
                unchanged(*check)
            result.update(status='observed', observedBodySHA256=digest.hexdigest(),
                intentSHA256=intent_sha, boundaryFacts=boundary_facts(prefix, tail, size))
    except (OSError, ValueError, TypeError, KeyError, OverflowError, RecursionError) as error:
        code = str(error) if isinstance(error, ValueError) and str(error) in ERRORS else 'local-read-failed'
        result.update(errorCode=code, observedBodySHA256=None, intentSHA256=None, boundaryFacts=None)
    return result


def run_diagnostics(output_root, absolute_deadline):
    report = {'schemaVersion': 'offmenu-retained-taiwan-diagnostic/1',
        'sourceCommit': SOURCE_COMMIT, 'priorReportCommit': REPORT_COMMIT,
        'priorResultSHA256': RESULT_SHA256, 'status': 'complete-with-errors',
        'items': [item_template(entry) for entry in ENTRIES], **SAFETY}
    try:
        check_deadline(absolute_deadline)
        if os.getuid() != EXPECTED_UID or os.geteuid() != EXPECTED_UID:
            raise ValueError('owner-identity-mismatch')
        with ExitStack() as stack:
            root = open_root(stack, output_root)
            work = open_child(stack, root, 'collection', True)
            owned(work, True)
            report['items'] = [diagnose_one(work, entry, absolute_deadline) for entry in ENTRIES]
    except (OSError, ValueError, TypeError) as error:
        code = str(error) if isinstance(error, ValueError) and str(error) in ERRORS else 'root-unavailable'
        for item in report['items']:
            item['errorCode'] = code
    if all(item['status'] == 'observed' for item in report['items']):
        report['status'] = 'complete'
    return sanitize_diagnostics(report)


def sanitize_diagnostics(report):
    template = {'schemaVersion': 'offmenu-retained-taiwan-diagnostic/1',
        'sourceCommit': SOURCE_COMMIT, 'priorReportCommit': REPORT_COMMIT,
        'priorResultSHA256': RESULT_SHA256, **SAFETY}
    if (not isinstance(report, dict) or set(report) != set(template) | {'status', 'items'} or
            any(type(report[k]) is not type(v) or report[k] != v for k, v in template.items()) or
            report['status'] not in {'complete', 'complete-with-errors'} or
            not isinstance(report['items'], list) or len(report['items']) != 3):
        raise ValueError('invalid-taiwan-diagnostic')
    for item, entry in zip(report['items'], ENTRIES):
        base = item_template(entry)
        if (not isinstance(item, dict) or set(item) != set(base) or
                any(type(item[k]) is not type(base[k]) or item[k] != base[k]
                    for k in ('sourceKey', 'sourceContractSHA256', 'priorDetailSHA256', 'expectedLocalBytes')) or
                item['status'] not in {'observed', 'blocked'} or
                type(item['localBodyBytesRead']) is not int or not 0 <= item['localBodyBytesRead'] <= entry[3]):
            raise ValueError('invalid-taiwan-diagnostic')
        if item['status'] == 'blocked':
            if (item['errorCode'] not in ERRORS or any(item[k] is not None
                    for k in ('observedBodySHA256', 'intentSHA256', 'boundaryFacts'))):
                raise ValueError('invalid-taiwan-diagnostic')
            continue
        if (item['errorCode'] is not None or item['localBodyBytesRead'] != entry[3] or
                any(not isinstance(item[k], str) or not re.fullmatch('[a-f0-9]{64}', item[k])
                    for k in ('observedBodySHA256', 'intentSHA256'))):
            raise ValueError('invalid-taiwan-diagnostic')
        facts = item['boundaryFacts']
        fact_keys = set(boundary_facts(b'', b'', 0))
        if (not isinstance(facts, dict) or set(facts) != fact_keys or
                facts['prefixWindowBytes'] != min(1024, entry[3]) or
                facts['tailWindowBytes'] != min(4096, entry[3]) or
                facts['prefixClassification'] not in {'pdf-at-zero', 'utf8-bom-before-pdf',
                    'pdf-whitespace-before-pdf', 'html-like-prefix', 'other'} or
                any(type(facts[k]) is not bool for k in ('pdfSignatureAtByteZero', 'terminalEOFMatchesCurrentRule'))):
            raise ValueError('invalid-taiwan-diagnostic')
        offset, eof, trailing = (facts[k] for k in ('pdfSignatureOffsetInFirst1024', 'lastEOFOffsetFromEnd', 'bytesAfterLastEOF'))
        if (offset is not None and (type(offset) is not int or not 0 <= offset <= facts['prefixWindowBytes'] - 5)):
            raise ValueError('invalid-taiwan-diagnostic')
        if facts['pdfSignatureAtByteZero'] != (offset == 0) or (facts['prefixClassification'] == 'pdf-at-zero') != (offset == 0):
            raise ValueError('invalid-taiwan-diagnostic')
        if eof is None:
            if trailing is not None or facts['onlyPDFWhitespaceAfterLastEOF'] is not None or facts['terminalEOFMatchesCurrentRule']:
                raise ValueError('invalid-taiwan-diagnostic')
        elif (type(eof) is not int or not 5 <= eof <= facts['tailWindowBytes'] or
                type(trailing) is not int or trailing != eof - 5 or
                type(facts['onlyPDFWhitespaceAfterLastEOF']) is not bool or
                facts['terminalEOFMatchesCurrentRule'] != facts['onlyPDFWhitespaceAfterLastEOF']):
            raise ValueError('invalid-taiwan-diagnostic')
        point = 'pdf-prefix' if not facts['pdfSignatureAtByteZero'] else 'pdf-terminal-eof' if not facts['terminalEOFMatchesCurrentRule'] else 'none'
        if facts['currentValidatorFailurePoint'] != point:
            raise ValueError('invalid-taiwan-diagnostic')
    if (report['status'] == 'complete') != all(i['status'] == 'observed' for i in report['items']):
        raise ValueError('invalid-taiwan-diagnostic')
    if len(canonical(report)) > 16384:
        raise ValueError('invalid-taiwan-diagnostic')
    return json.loads(canonical(report))
