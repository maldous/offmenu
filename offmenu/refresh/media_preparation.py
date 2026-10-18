"""Bounded structural preparation of already received, explicitly admitted originals.

No acquisition, normalization, translation, script execution, or publication.
The fixed Foo caller owns storage roots and source-specific permission evidence.
This module reuses refresh.core's reviewed path/JSON/hash primitives. Parser work
is isolated in a resource-limited process; unsupported stages remain explicit.
"""
from __future__ import annotations

import csv
import hashlib
import importlib.metadata
import importlib.util
import io
import math
import multiprocessing
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import socket
import signal
import selectors
import subprocess
import stat
import struct
import sys
import tempfile
import time
import zipfile
from html.parser import HTMLParser
from xml.etree import ElementTree as ET

from .core import RefreshError, canonical, safe_path, sha, strict_json

SCHEMA = 'offmenu-media-preparation-contract/1'
REPORT_SCHEMA = 'offmenu-media-preparation-result/1'
VERSION = 'bounded-structural-preparation/1'
MiB = 1024 * 1024
MAX_ORIGINAL_BYTES = 1024 * MiB
MAX_PARSE_BYTES = 128 * MiB
MAX_OUTPUT_BYTES = 256 * MiB
MAX_ARCHIVE_BYTES = 128 * MiB
MAX_MEMBER_BYTES = 32 * MiB
MAX_MEMBERS = 512
MAX_OUTPUT_FILES = MAX_MEMBERS + 1  # All bounded archive members plus one private index.
MAX_RATIO = 200
MAX_RECORDS = 1_000_000
MAX_CELLS = 5_000_000
MAX_PAGES = 2000
MAX_SHEETS = 256
MAX_XML_ELEMENTS = 2_000_000
MAX_XML_DEPTH = 128
MAX_FIELD_BYTES = MiB
MAX_SECONDS = 300
MAX_MEMORY_BYTES = 768 * MiB
PLANNING_GUARD_BYTES = 88418025472
POPPLER_PATHS = {'pdfinfo': '/usr/bin/pdfinfo', 'pdftotext': '/usr/bin/pdftotext'}
MIMES = frozenset({
    'application/pdf', 'text/csv', 'text/tab-separated-values', 'application/json',
    'application/xml', 'text/html', 'application/zip', 'application/msword',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/gzip', 'application/x-bzip2', 'application/x-xz',
    'application/x-7z-compressed', 'application/vnd.rar', 'application/vnd.sqlite3',
    'application/vnd.apache.parquet', 'text/plain', 'application/octet-stream',
})
XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
DOCX = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
ENCODINGS = frozenset({'utf-8', 'utf-8-sig', 'utf-16', 'utf-16-le', 'utf-16-be',
                       'cp1252', 'iso-8859-1'})
PARAMETERS = {'encoding', 'delimiter', 'hasHeader', 'jsonRecordPath', 'xmlRecordTag',
              'sheetIndexes', 'pageStart', 'pageEnd'}
ERROR_CODES = frozenset({
    'contract-invalid', 'read-permission-held', 'extract-permission-held',
    'copy-permission-held', 'original-unavailable', 'original-not-regular',
    'original-byte-limit', 'original-identity-mismatch', 'original-changed',
    'deadline-exceeded', 'media-mismatch', 'media-ambiguous', 'html-error-response',
    'unsupported-media', 'parser-unavailable', 'parser-isolation-unavailable',
    'parser-input-limit', 'parser-resource-limit', 'parser-invalid-input',
    'parameters-required', 'parameters-invalid', 'encoding-invalid',
    'record-limit', 'field-limit', 'xml-unsafe', 'xml-structure-limit',
    'archive-unsafe', 'archive-expansion-limit', 'archive-invalid',
    'pdf-encrypted', 'pdf-page-limit', 'pdf-ocr-required',
    'sheet-limit', 'cell-limit', 'output-limit', 'output-unavailable',
    'output-conflict', 'capacity-floor-protected', 'member-contracts-required', 'text-format-contract-required', 'selection-partial',
})


class PreparationError(Exception):
    def __init__(self, code, status='failed', metrics=None):
        self.metrics = metrics
        self.code = code if code in ERROR_CODES else 'parser-invalid-input'
        self.status = status


def _check(deadline):
    if time.monotonic() >= deadline:
        raise PreparationError('deadline-exceeded')


def _identity(s):
    return s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns


def capabilities():
    """Installed capabilities only. Never installs packages or executes a probe."""
    result = {'handlerVersion': VERSION, 'pythonVersion': sys.version.split()[0],
              'isolatedWorker': 'fork' in multiprocessing.get_all_start_methods(),
              'stdlibFormats': ['csv', 'tsv', 'json', 'xml', 'html', 'zip', 'xlsx', 'docx'],
              'optionalParsers': {}}
    for name in ('pypdf', 'xlrd'):
        try:
            available = importlib.util.find_spec(name) is not None
            version = importlib.metadata.version(name) if available else None
        except (ImportError, ValueError, importlib.metadata.PackageNotFoundError):
            available, version = False, None
        result['optionalParsers'][name] = {'available': available, 'version': version}
    poppler = {'available': False, 'version': None}
    try:
        if all(Path(path).is_file() and os.access(path, os.X_OK) for path in POPPLER_PATHS.values()):
            probe = subprocess.run([POPPLER_PATHS['pdftotext'], '-v'], stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, timeout=2, check=False)
            match = re.search(rb'pdftotext version ([0-9][0-9A-Za-z.+_-]{0,63})', probe.stdout[:4096])
            if probe.returncode == 0 and match:
                poppler = {'available': True, 'version': match.group(1).decode('ascii')}
    except (OSError, subprocess.TimeoutExpired):
        pass
    result['optionalParsers']['poppler'] = poppler
    return result


def validate_contract(contract):
    required = {'schemaVersion', 'assetId', 'expectedSHA256', 'expectedBytes',
                'expectedMediaTypes', 'permissions', 'holds', 'parameters'}
    try:
        if not isinstance(contract, dict) or set(contract) != required:
            raise ValueError()
        if (contract['schemaVersion'] != SCHEMA
                or not isinstance(contract['assetId'], str)
                or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:-]{0,191}', contract['assetId'])
                or not isinstance(contract['expectedSHA256'], str)
                or not re.fullmatch(r'[0-9a-f]{64}', contract['expectedSHA256'])
                or type(contract['expectedBytes']) is not int
                or not 0 < contract['expectedBytes'] <= MAX_ORIGINAL_BYTES):
            raise ValueError()
        media = contract['expectedMediaTypes']
        if (not isinstance(media, list) or not 1 <= len(media) <= 8
                or any(not isinstance(x, str) or x not in MIMES for x in media)
                or len(media) != len(set(media))):
            raise ValueError()
        permissions = contract['permissions']
        if (not isinstance(permissions, dict) or set(permissions) != {'read', 'extract', 'copy'}
                or any(type(value) is not bool for value in permissions.values())):
            raise ValueError()
        holds = contract['holds']
        if (not isinstance(holds, list) or len(holds) > 4
                or any(not isinstance(x, str) or x not in {'read', 'extract', 'copy', 'all'} for x in holds)
                or len(holds) != len(set(holds))):
            raise ValueError()
        params = contract['parameters']
        if not isinstance(params, dict) or set(params) - PARAMETERS:
            raise ValueError()
        if 'encoding' in params and params['encoding'] not in ENCODINGS:
            raise ValueError()
        if 'delimiter' in params and params['delimiter'] not in {',', ';', '\t', '|'}:
            raise ValueError()
        if 'hasHeader' in params and type(params['hasHeader']) is not bool:
            raise ValueError()
        for key in ('pageStart', 'pageEnd'):
            if key in params and (type(params[key]) is not int or not 1 <= params[key] <= MAX_PAGES):
                raise ValueError()
        if params.get('pageStart', 1) > params.get('pageEnd', MAX_PAGES):
            raise ValueError()
        if 'sheetIndexes' in params:
            values = params['sheetIndexes']
            if (not isinstance(values, list) or not 1 <= len(values) <= MAX_SHEETS
                    or any(type(x) is not int or not 0 <= x < MAX_SHEETS for x in values)
                    or len(values) != len(set(values))):
                raise ValueError()
        if 'jsonRecordPath' in params:
            values = params['jsonRecordPath']
            if (not isinstance(values, list) or len(values) > 16 or any(
                    not isinstance(x, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.-]{0,127}', x)
                    for x in values)):
                raise ValueError()
        if 'xmlRecordTag' in params and (not isinstance(params['xmlRecordTag'], str)
                or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.-]{0,127}', params['xmlRecordTag'])):
            raise ValueError()
        if len(canonical(contract)) > 16384:
            raise ValueError()
    except (ValueError, TypeError, KeyError, RecursionError):
        raise PreparationError('contract-invalid') from None
    return contract


def _decode(data, params):
    encoding = params.get('encoding')
    if encoding is None:
        encoding = 'utf-16' if data.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig'
    try:
        text = data.decode(encoding, errors='strict')
    except (UnicodeError, LookupError):
        raise PreparationError('encoding-invalid') from None
    if '\x00' in text:
        raise PreparationError('encoding-invalid')
    return text, encoding


def _zip_members(data):
    """Reviewed XLSX validator bounds generalized; never extract to member paths."""
    try:
        # Bound central-directory allocation before ZipFile parses attacker metadata.
        # ZIP64/multidisk are deliberately unsupported by this bounded profile.
        marker = data.rfind(b'PK\x05\x06', max(0, len(data) - 65557))
        if marker < 0 or marker + 22 > len(data):
            raise PreparationError('archive-invalid')
        _, disk, central_disk, on_disk, entries, central_size, central_offset, comment = struct.unpack(
            '<4s4H2IH', data[marker:marker + 22])
        if (disk or central_disk or on_disk != entries or not 1 <= entries <= MAX_MEMBERS
                or central_size > MAX_MEMBERS * 1024 or central_offset + central_size > marker
                or marker + 22 + comment != len(data)):
            raise PreparationError('archive-expansion-limit')
        archive = zipfile.ZipFile(io.BytesIO(data))
        members = archive.infolist()
        if len(members) != entries or not 1 <= len(members) <= MAX_MEMBERS:
            raise PreparationError('archive-expansion-limit')
        names = set()
        total = 0
        for member in members:
            name = member.filename
            parts = PurePosixPath(name)
            mode = member.external_attr >> 16
            if (len(name.encode('utf-8')) > 512 or '\x00' in name or '\\' in name or ':' in name
                    or parts.is_absolute() or '..' in parts.parts or not parts.parts
                    or name.startswith('./') or '//' in name or '/./' in name
                    or name.casefold() in names or member.flag_bits & 1
                    or stat.S_ISLNK(mode) or (stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR))
                    or member.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
                    or name.casefold().endswith(('vbaproject.bin', '.exe', '.dll', '.js', '.vbs', '.ps1'))):
                raise PreparationError('archive-unsafe')
            names.add(name.casefold())
            total += member.file_size
            if (member.file_size > MAX_MEMBER_BYTES or total > MAX_ARCHIVE_BYTES
                    or member.file_size > max(1, member.compress_size) * MAX_RATIO):
                raise PreparationError('archive-expansion-limit')
        return archive, members
    except PreparationError:
        raise
    except (zipfile.BadZipFile, NotImplementedError, ValueError, OSError):
        raise PreparationError('archive-invalid') from None


def _sniff(data, expected, params, complete=True):
    if data.startswith(b'%PDF-'):
        return 'application/pdf', 'magic'
    if data.startswith((b'PK\x03\x04', b'PK\x05\x06', b'PK\x07\x08')):
        if not complete:
            return 'application/zip', 'magic-container-uninspected'
        archive, members = _zip_members(data)
        with archive:
            names = {m.filename for m in members}
        if '[Content_Types].xml' in names and 'xl/workbook.xml' in names:
            return XLSX, 'bounded-container-directory'
        if '[Content_Types].xml' in names and 'word/document.xml' in names:
            return DOCX, 'bounded-container-directory'
        return 'application/zip', 'bounded-container-directory'
    for magic, mime in ((b'\x1f\x8b', 'application/gzip'), (b'BZh', 'application/x-bzip2'),
                        (b'\xfd7zXZ\x00', 'application/x-xz'), (b'7z\xbc\xaf\x27\x1c', 'application/x-7z-compressed'),
                        (b'Rar!\x1a\x07', 'application/vnd.rar'), (b'SQLite format 3\x00', 'application/vnd.sqlite3'),
                        (b'PAR1', 'application/vnd.apache.parquet')):
        if data.startswith(magic):
            return mime, 'magic'
    if data.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'):
        if expected == ['application/vnd.ms-excel']:
            return 'application/vnd.ms-excel', 'ole-container-parser-required'
        if expected == ['application/msword']:
            return 'application/msword', 'ole-container-parser-required'
        return 'application/octet-stream', 'ole-container-ambiguous'
    try:
        # Decode a bounded text prefix without splitting a multibyte sequence.
        prefix = data[:65536]
        if len(data) > len(prefix):
            prefix = prefix[:-4] if params.get('encoding', '').startswith('utf-16') else prefix
            while prefix:
                try:
                    text, _ = _decode(prefix, params)
                    break
                except PreparationError:
                    prefix = prefix[:-1]
                    if len(prefix) < 65528:
                        raise
        else:
            text, _ = _decode(prefix, params)
    except PreparationError:
        return 'application/octet-stream', 'unrecognized-binary'
    lead = text.lstrip('\ufeff \t\r\n').lower()
    if re.match(r'<!doctype\s+html\b|<html\b|<head\b|<body\b', lead):
        if re.search(r'<title[^>]*>\s*(?:access denied|forbidden|error|just a moment|service unavailable|404|403)\b', lead):
            raise PreparationError('html-error-response')
        return 'text/html', 'text-signature'
    if lead.startswith(('{', '[')):
        return 'application/json', 'text-signature-parser-required'
    if lead.startswith('<?xml') or re.match(r'<[a-z_][a-z0-9_.:-]*(?:\s|/?>)', lead):
        return 'application/xml', 'text-signature-parser-required'
    for mime, delimiter in (('text/csv', ','), ('text/tab-separated-values', '\t')):
        if mime in expected and params.get('delimiter', delimiter) in text:
            return mime, 'text-delimiter-parser-required'
    return 'text/plain', 'decoded-text'


def _read_original(path, contract, deadline, retain):
    try:
        path = safe_path(path)
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode):
                raise PreparationError('original-not-regular')
            if not 0 < before.st_size <= MAX_ORIGINAL_BYTES:
                raise PreparationError('original-byte-limit')
            if before.st_size != contract['expectedBytes']:
                raise PreparationError('original-identity-mismatch')
            digest, count, chunks, prefix = hashlib.sha256(), 0, [], b''
            while True:
                _check(deadline)
                block = stream.read(min(MiB, contract['expectedBytes'] - count + 1))
                _check(deadline)
                if not block:
                    break
                count += len(block)
                if count > contract['expectedBytes']:
                    raise PreparationError('original-changed')
                digest.update(block)
                if len(prefix) < 65536:
                    prefix += block[:65536 - len(prefix)]
                if retain:
                    chunks.append(block)
            after = os.fstat(stream.fileno())
        _check(deadline)
        if _identity(before) != _identity(after) or _identity(after) != _identity(path.stat()):
            raise PreparationError('original-changed')
        if count != contract['expectedBytes'] or digest.hexdigest() != contract['expectedSHA256']:
            raise PreparationError('original-identity-mismatch')
        _check(deadline)
        return b''.join(chunks) if retain else prefix, _identity(after)
    except PreparationError:
        raise
    except (OSError, RefreshError, ValueError):
        raise PreparationError('original-unavailable') from None


class _Writer:
    def __init__(self, folder, deadline, maximum_output_bytes, minimum_free_bytes):
        self.folder, self.deadline = folder, deadline
        self.maximum_output_bytes, self.minimum_free_bytes = maximum_output_bytes, minimum_free_bytes
        self.total = 0
        self.outputs = []

    def write(self, blocks, extension, kind):
        _check(self.deadline)
        if len(self.outputs) >= MAX_OUTPUT_FILES:
            raise PreparationError('output-limit')
        name = f'{len(self.outputs):04d}.{extension}'
        target = self.folder / name
        digest, count = hashlib.sha256(), 0
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            for block in blocks:
                _check(self.deadline)
                count += len(block)
                self.total += len(block)
                if self.total > self.maximum_output_bytes:
                    raise PreparationError('output-limit')
                space = os.statvfs(self.folder)
                if space.f_bavail * space.f_frsize < self.minimum_free_bytes + len(block):
                    raise PreparationError('capacity-floor-protected')
                stream.write(block)
                _check(self.deadline)
                digest.update(block)
            stream.flush()
            os.fsync(stream.fileno())
        self.outputs.append({'temporaryName': name, 'sha256': digest.hexdigest(),
                             'bytes': count, 'format': kind, 'extension': extension})

    def records(self, rows):
        def blocks():
            count = 0
            for row in rows:
                count += 1
                if count > MAX_RECORDS:
                    raise PreparationError('record-limit')
                raw = canonical(row)
                if len(raw) > 4 * MiB:
                    raise PreparationError('field-limit')
                yield raw
        self.write(blocks(), 'jsonl', 'source-structure-jsonl')


def _xml(data, deadline):
    # Reject DTD/entity declarations before using stdlib ElementTree. Decode
    # UTF-16 too, so interspersed NULs cannot bypass the declaration check.
    try:
        declared = data.decode('utf-16' if data.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig')
    except UnicodeError:
        raise PreparationError('encoding-invalid') from None
    if re.search(r'<!\s*(?:DOCTYPE|ENTITY)\b', declared, re.I):
        raise PreparationError('xml-unsafe')
    depth = count = 0
    root = None
    try:
        for event, element in ET.iterparse(io.StringIO(declared), events=('start', 'end')):
            _check(deadline)
            if event == 'start':
                depth += 1
                count += 1
                if root is None:
                    root = element
                if depth > MAX_XML_DEPTH or count > MAX_XML_ELEMENTS:
                    raise PreparationError('xml-structure-limit')
            else:
                depth -= 1
        return root, count
    except (ET.ParseError, ValueError):
        raise PreparationError('parser-invalid-input') from None


def _tag(element):
    return element.tag.rsplit('}', 1)[-1]


def _archive_payloads(data, deadline):
    archive, members = _zip_members(data)
    payloads, total = {}, 0
    try:
        with archive:
            for member in members:
                _check(deadline)
                if member.is_dir():
                    continue
                blocks, count = [], 0
                with archive.open(member) as stream:
                    while True:
                        _check(deadline)
                        block = stream.read(min(65536, MAX_MEMBER_BYTES - count + 1))
                        _check(deadline)
                        if not block:
                            break
                        count += len(block)
                        total += len(block)
                        if count > MAX_MEMBER_BYTES or total > MAX_ARCHIVE_BYTES:
                            raise PreparationError('archive-expansion-limit')
                        blocks.append(block)
                if count != member.file_size:
                    raise PreparationError('archive-invalid')
                payloads[member.filename] = b''.join(blocks)
    except (zipfile.BadZipFile, NotImplementedError, RuntimeError, ValueError, EOFError, OSError):
        raise PreparationError('archive-invalid') from None
    return payloads


class _HTMLText(HTMLParser):
    def __init__(self, writer):
        super().__init__(convert_charrefs=True)
        self.writer, self.hidden, self.parts = writer, 0, []
        self.text_bytes = 0
        self.elements = 0

    def handle_starttag(self, tag, attrs):
        self.elements += 1
        _check(self.writer.deadline)
        if self.elements > MAX_XML_ELEMENTS:
            raise PreparationError('xml-structure-limit')
        if tag in ('script', 'style', 'noscript', 'template'):
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript', 'template') and self.hidden:
            self.hidden -= 1

    def handle_data(self, data):
        _check(self.writer.deadline)
        if not self.hidden and data.strip():
            self.text_bytes += len(data.encode('utf-8'))
            if self.text_bytes > MAX_MEMBER_BYTES or len(self.parts) >= MAX_RECORDS:
                raise PreparationError('output-limit')
            self.parts.append({'text': data})


def _prepare(data, media, params, writer, caps):
    metrics = {'recordCount': None, 'pageCount': None, 'sheetCount': None,
               'archiveMemberCount': None, 'ocrNeeded': 'not-applicable'}
    result = {'parser': {'name': 'python-stdlib', 'version': caps['pythonVersion']},
              'parameters': dict(params), 'metrics': metrics, 'nextStage': 'source-specific-processing',
              'nextStageReady': True, 'code': None}
    if media in ('text/csv', 'text/tab-separated-values'):
        if not {'encoding', 'delimiter', 'hasHeader'} <= params.keys():
            raise PreparationError('parameters-required', 'unsupported')
        if media == 'text/tab-separated-values' and params['delimiter'] != '\t':
            raise PreparationError('parameters-invalid')
        text, encoding = _decode(data, params)
        csv.field_size_limit(MAX_FIELD_BYTES)
        reader = csv.reader(io.StringIO(text, newline=''), delimiter=params['delimiter'], strict=True)
        counts = {'rows': 0, 'width': None}
        def rows():
            for row in reader:
                _check(writer.deadline)
                if not row:
                    continue
                if len(row) > 16384 or any(len(x.encode('utf-8')) > MAX_FIELD_BYTES for x in row):
                    raise PreparationError('field-limit')
                if counts['width'] is None:
                    counts['width'] = len(row)
                if len(row) != counts['width']:
                    raise PreparationError('parser-invalid-input')
                counts['rows'] += 1
                yield {'rowIndex': counts['rows'], 'header': params['hasHeader'] and counts['rows'] == 1,
                       'cells': row}
        writer.records(rows())
        metrics.update(recordCount=max(0, counts['rows'] - int(params['hasHeader'])),
                       rowCount=counts['rows'], columnCount=counts['width'])
        result['parameters'].update(encoding=encoding, quoteCharacter='"', escapeMode='double-quote',
                                    blankRows='omitted', values='unmodified-source-strings')
    elif media == 'application/json':
        if 'jsonRecordPath' not in params:
            raise PreparationError('parameters-required', 'unsupported')
        text, encoding = _decode(data, params)
        value = strict_json(text)
        records = value
        for part in params['jsonRecordPath']:
            if not isinstance(records, dict) or part not in records:
                raise PreparationError('parameters-invalid')
            records = records[part]
        if not isinstance(records, (dict, list)):
            raise PreparationError('parameters-invalid')
        count = len(records) if isinstance(records, list) else 1
        if count > MAX_RECORDS:
            raise PreparationError('record-limit')
        writer.write([data], 'json', 'validated-original-json')
        metrics['recordCount'] = count
        result['parameters'].update(encoding=encoding, representation='byte-preserved')
    elif media == 'application/xml':
        if 'xmlRecordTag' not in params:
            raise PreparationError('parameters-required', 'unsupported')
        root, count = _xml(data, writer.deadline)
        metrics.update(recordCount=sum(_tag(e) == params['xmlRecordTag'] for e in root.iter()),
                       elementCount=count)
        if metrics['recordCount'] > MAX_RECORDS:
            raise PreparationError('record-limit')
        writer.write([data], 'xml', 'validated-original-xml')
        result['parameters'].update(dtd='rejected', entities='rejected', representation='byte-preserved')
    elif media == 'text/html':
        text, encoding = _decode(data, params)
        parser = _HTMLText(writer)
        parser.feed(text)
        parser.close()
        writer.records(parser.parts)
        metrics.update(recordCount=len(parser.parts), elementCount=parser.elements)
        result['parameters'].update(encoding=encoding, scripts='never-executed-and-omitted',
                                    externalResources='never-fetched', representation='text-nodes')
    elif media in ('application/zip', XLSX, DOCX):
        payloads = _archive_payloads(data, writer.deadline)
        metrics['archiveMemberCount'] = len(payloads)
        result['parameters'].update(archiveCRC='verified-all-members', nestedArchives='never-recursed')
        if media == 'application/zip':
            private_index = []
            for index, (name, raw) in enumerate(payloads.items()):
                writer.write([raw], 'bin', 'unpacked-source-member')
                private_index.append({'memberIndex': index, 'sourceMemberName': name,
                                      'sha256': sha(raw), 'bytes': len(raw)})
            writer.records(private_index)
            metrics['recordCount'] = len(private_index)
            result.update(nextStage='member-contracts-required', nextStageReady=False,
                          code='member-contracts-required')
        elif media == DOCX:
            text_parts = ['word/document.xml'] + sorted(name for name in payloads if re.fullmatch(
                r'word/(?:header[0-9]+|footer[0-9]+|footnotes|endnotes|comments)\.xml', name))
            rows = []
            for part_index, name in enumerate(text_parts):
                root, _ = _xml(payloads[name], writer.deadline)
                paragraph_index = 0
                for element in root.iter():
                    if _tag(element) == 'p':
                        parts = []
                        for child in element.iter():
                            if _tag(child) == 't':
                                parts.append(child.text or '')
                            elif _tag(child) == 'tab':
                                parts.append('\t')
                            elif _tag(child) in ('br', 'cr'):
                                parts.append('\n')
                        paragraph_index += 1
                        rows.append({'partIndex': part_index, 'paragraphIndex': paragraph_index,
                                     'text': ''.join(parts)})
            writer.records(rows)
            metrics.update(recordCount=len(rows), textPartCount=len(text_parts))
            result['parameters'].update(representation='ordered-text-part-paragraphs',
                                        textParts='main-headers-footers-footnotes-endnotes-comments',
                                        embeddedObjects='never-executed')
        else:
            workbook, _ = _xml(payloads['xl/workbook.xml'], writer.deadline)
            rels, _ = _xml(payloads.get('xl/_rels/workbook.xml.rels', b''), writer.deadline)
            targets = {}
            for item in rels:
                target = item.get('Target', '')
                if item.get('TargetMode') == 'External':
                    raise PreparationError('archive-unsafe')
                normalized = target.lstrip('/') if target.startswith('/xl/') else 'xl/' + target
                if ('..' in PurePosixPath(normalized).parts or '\\' in normalized
                        or not normalized.startswith('xl/') or normalized not in payloads):
                    raise PreparationError('archive-unsafe')
                targets[item.get('Id')] = normalized
            sheets = [e for e in workbook.iter() if _tag(e) == 'sheet']
            metrics['sheetCount'] = len(sheets)
            if not 1 <= len(sheets) <= MAX_SHEETS:
                raise PreparationError('sheet-limit', metrics=metrics)
            selected = params.get('sheetIndexes', list(range(len(sheets))))
            metrics['selectedSheetCount'] = len(selected)
            metrics['selectedExtentComplete'] = set(selected) == set(range(len(sheets)))
            if any(index >= len(sheets) for index in selected):
                raise PreparationError('parameters-invalid')
            strings = []
            if 'xl/sharedStrings.xml' in payloads:
                shared, _ = _xml(payloads['xl/sharedStrings.xml'], writer.deadline)
                strings = [''.join(e.text or '' for e in item.iter() if _tag(e) == 't')
                           for item in shared if _tag(item) == 'si']
            counters = {'rows': 0, 'cells': 0}
            sheet_stats = []
            def rows():
                for index in selected:
                    rel = next((v for k, v in sheets[index].attrib.items() if k.endswith('}id')), None)
                    if rel not in targets:
                        raise PreparationError('archive-invalid')
                    root, _ = _xml(payloads[targets[rel]], writer.deadline)
                    row_count = 0
                    for row in root.iter():
                        if _tag(row) != 'row':
                            continue
                        cells = []
                        for cell in row:
                            if _tag(cell) != 'c':
                                continue
                            counters['cells'] += 1
                            if counters['cells'] > MAX_CELLS:
                                raise PreparationError('cell-limit')
                            value = next((e.text for e in cell if _tag(e) == 'v'), None)
                            formula = next((e.text for e in cell if _tag(e) == 'f'), None)
                            kind = cell.get('t', 'n')
                            if kind == 's':
                                try:
                                    position = int(value)
                                    if position < 0:
                                        raise ValueError()
                                    source_text = strings[position]
                                except (ValueError, TypeError, IndexError):
                                    raise PreparationError('archive-invalid') from None
                            elif kind == 'inlineStr':
                                source_text = ''.join(e.text or '' for e in cell.iter() if _tag(e) == 't')
                            else:
                                source_text = None
                            cells.append({'sourceCell': cell.get('r'), 'sourceType': kind,
                                          'rawValue': value, 'sourceText': source_text, 'formula': formula})
                        counters['rows'] += 1
                        row_count += 1
                        yield {'sheetIndex': index, 'sourceRow': row.get('r'), 'cells': cells}
                    sheet_stats.append({'sheetIndex': index, 'rowCount': row_count})
            writer.records(rows())
            metrics.update(recordCount=counters['rows'], cellCount=counters['cells'], sheets=sheet_stats)
            result['parameters'].update(sheetIndexes=selected, formulas='preserved-never-evaluated',
                                        dates='source-serial-preserved', externalLinks='never-followed')
            if not metrics['selectedExtentComplete']:
                result.update(nextStage='remaining-sheets-required', nextStageReady=False, code='selection-partial')
    elif media == 'application/pdf':
        if b'%%EOF' not in data[-4096:]:
            raise PreparationError('parser-invalid-input')
        parser = caps['optionalParsers']['pypdf']
        if parser['available']:
            from pypdf import PdfReader
            result['parser'] = {'name': 'pypdf', 'version': parser['version']}
            reader = PdfReader(io.BytesIO(data), strict=True)
            if reader.is_encrypted:
                raise PreparationError('pdf-encrypted', 'unsupported')
            count = len(reader.pages)
            extract_page = lambda index: reader.pages[index].extract_text() or ''
        elif caps['optionalParsers']['poppler']['available']:
            parser = caps['optionalParsers']['poppler']
            result['parser'] = {'name': 'poppler-pdftotext', 'version': parser['version']}
            info = _poppler('pdfinfo', ['-'], data, writer.deadline, MiB)
            if re.search(rb'^Encrypted:\s+yes\b', info, re.M | re.I):
                raise PreparationError('pdf-encrypted', 'unsupported')
            pages_match = re.search(rb'^Pages:\s+([0-9]{1,8})\s*$', info, re.M)
            if not pages_match:
                raise PreparationError('parser-invalid-input')
            count = int(pages_match.group(1))
            extract_page = None
        else:
            raise PreparationError('parser-unavailable', 'unsupported')
        metrics['pageCount'] = count
        if not 1 <= count <= MAX_PAGES:
            raise PreparationError('pdf-page-limit', metrics=metrics)
        start, end = params.get('pageStart', 1), params.get('pageEnd', count)
        if not 1 <= start <= end <= count:
            raise PreparationError('parameters-invalid')
        if extract_page is None:
            raw_text = _poppler('pdftotext', ['-enc', 'UTF-8', '-f', str(start), '-l', str(end), '-', '-'],
                                data, writer.deadline, writer.maximum_output_bytes)
            text_pages = raw_text.decode('utf-8', errors='strict').split('\f')
            if text_pages and text_pages[-1] == '':
                text_pages.pop()
            if len(text_pages) != end - start + 1:
                raise PreparationError('parser-invalid-input')
            extract_page = lambda index: text_pages[index - start + 1]
        blank = []
        def rows():
            for index in range(start - 1, end):
                _check(writer.deadline)
                text = extract_page(index)
                if not text.strip():
                    blank.append(index + 1)
                yield {'pageIndex': index + 1, 'text': text}
        writer.records(rows())
        metrics.update(pageCount=count, selectedPageCount=end - start + 1,
                       selectedExtentComplete=start == 1 and end == count,
                       recordCount=end - start + 1, pagesWithoutText=len(blank),
                       ocrNeeded='possible' if blank else 'not-indicated')
        result['parameters'].update(pageStart=start, pageEnd=end, extractionMode='plain',
                                    ocr='not-run', embeddedScripts='never-executed')
        if not metrics['selectedExtentComplete']:
            result.update(nextStage='remaining-pages-required', nextStageReady=False, code='selection-partial')
        if blank:
            result.update(nextStage='ocr-assessment-required', nextStageReady=False, code='pdf-ocr-required')
    elif media == 'application/vnd.ms-excel':
        parser = caps['optionalParsers']['xlrd']
        if not parser['available']:
            raise PreparationError('parser-unavailable', 'unsupported')
        import xlrd
        workbook = xlrd.open_workbook(file_contents=data, on_demand=True)
        result['parser'] = {'name': 'xlrd', 'version': parser['version']}
        metrics['sheetCount'] = workbook.nsheets
        if not 1 <= workbook.nsheets <= MAX_SHEETS:
            raise PreparationError('sheet-limit', metrics=metrics)
        selected = params.get('sheetIndexes', list(range(workbook.nsheets)))
        metrics['selectedSheetCount'] = len(selected)
        metrics['selectedExtentComplete'] = set(selected) == set(range(workbook.nsheets))
        if any(index >= workbook.nsheets for index in selected):
            raise PreparationError('parameters-invalid')
        counts = {'rows': 0, 'cells': 0}
        def rows():
            for index in selected:
                sheet = workbook.sheet_by_index(index)
                counts['cells'] += sheet.nrows * sheet.ncols
                if counts['cells'] > MAX_CELLS:
                    raise PreparationError('cell-limit')
                for row_index in range(sheet.nrows):
                    _check(writer.deadline)
                    counts['rows'] += 1
                    yield {'sheetIndex': index, 'rowIndex': row_index + 1,
                           'cells': [{'sourceType': sheet.cell_type(row_index, col),
                                      'rawValue': sheet.cell_value(row_index, col)}
                                     for col in range(sheet.ncols)]}
                workbook.unload_sheet(index)
        try:
            writer.records(rows())
        finally:
            workbook.release_resources()
        metrics.update(recordCount=counts['rows'], cellCount=counts['cells'])
        result['parameters'].update(sheetIndexes=selected, dates='source-serial-preserved',
                                    formulas='cached-values-only-not-evaluated')
        if not metrics['selectedExtentComplete']:
            result.update(nextStage='remaining-sheets-required', nextStageReady=False, code='selection-partial')
    elif media == 'text/plain':
        raise PreparationError('text-format-contract-required', 'unsupported')
    else:
        raise PreparationError('unsupported-media', 'unsupported')
    return result


def _poppler(tool, arguments, data, deadline, maximum):
    """Feed stdin and drain stdout together, stopping before unbounded capture."""
    _check(deadline)
    process = None
    selector = selectors.DefaultSelector()
    chunks, count, sent = [], 0, 0
    try:
        process = subprocess.Popen([POPPLER_PATHS[tool], *arguments], stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                   close_fds=True)
        os.set_blocking(process.stdin.fileno(), False)
        os.set_blocking(process.stdout.fileno(), False)
        selector.register(process.stdin, selectors.EVENT_WRITE, 'stdin')
        selector.register(process.stdout, selectors.EVENT_READ, 'stdout')
        while selector.get_map():
            _check(deadline)
            for key, _ in selector.select(min(0.05, max(0, deadline - time.monotonic()))):
                _check(deadline)
                if key.data == 'stdin':
                    try:
                        sent += os.write(key.fd, memoryview(data)[sent:sent + 65536])
                    except BlockingIOError:
                        continue
                    except BrokenPipeError:
                        sent = len(data)
                    if sent == len(data):
                        selector.unregister(key.fileobj)
                        key.fileobj.close()
                else:
                    try:
                        block = os.read(key.fd, min(65536, maximum - count + 1))
                    except BlockingIOError:
                        continue
                    _check(deadline)
                    if not block:
                        selector.unregister(key.fileobj)
                        key.fileobj.close()
                        continue
                    count += len(block)
                    if count > maximum:
                        raise PreparationError('output-limit')
                    chunks.append(block)
        process.wait(timeout=max(0.001, deadline - time.monotonic()))
        _check(deadline)
        if process.returncode != 0:
            raise PreparationError('parser-invalid-input')
        return b''.join(chunks)
    except subprocess.TimeoutExpired:
        raise PreparationError('deadline-exceeded') from None
    except OSError:
        raise PreparationError('parser-unavailable', 'unsupported') from None
    finally:
        selector.close()
        if process is not None:
            if process.poll() is None:
                process.kill()
            process.wait()
            for stream in (process.stdin, process.stdout):
                if stream is not None and not stream.closed:
                    stream.close()


def _worker(conn, data, media, params, folder, deadline, caps, maximum_output_bytes, minimum_free_bytes):
    try:
        import resource
        os.setsid()
        conn.send_bytes(canonical({'phase': 'session-ready', 'pid': os.getpid()}))
        # Parser diagnostics can contain raw source text: they are not receipts.
        null = os.open(os.devnull, os.O_WRONLY)
        try:
            os.dup2(null, 1)
            os.dup2(null, 2)
        finally:
            os.close(null)
        seconds = max(1, math.ceil(deadline - time.monotonic()))
        resource.setrlimit(resource.RLIMIT_CPU, (seconds, seconds))
        resource.setrlimit(resource.RLIMIT_AS, (MAX_MEMORY_BYTES, MAX_MEMORY_BYTES))
        resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_OUTPUT_BYTES, MAX_OUTPUT_BYTES))
        # Closed, audited parsers never need the network. Fail unexpected attempts.
        def no_network(*args, **kwargs):
            raise PreparationError('parser-invalid-input')
        socket.socket = no_network
        writer = _Writer(Path(folder), deadline, maximum_output_bytes, minimum_free_bytes)
        result = _prepare(data, media, params, writer, caps)
        result.update(outputs=writer.outputs, status='passed')
    except PreparationError as error:
        result = {'status': error.status, 'code': error.code, 'metrics': error.metrics}
    except (MemoryError, RecursionError):
        result = {'status': 'failed', 'code': 'parser-resource-limit'}
    except BaseException:
        # Never put parser diagnostics, source fragments or filesystem paths in receipts.
        result = {'status': 'failed', 'code': 'parser-invalid-input'}
    try:
        conn.send_bytes(canonical(result))
    finally:
        conn.close()


def _private_directory(path):
    try:
        path = safe_path(path)
        path.mkdir(mode=0o700, exist_ok=True)
        info = path.stat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise PreparationError('output-unavailable')
        return path
    except (OSError, RefreshError):
        raise PreparationError('output-unavailable') from None


def _file_hash(path, deadline):
    digest, count = hashlib.sha256(), 0
    fd = os.open(safe_path(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_OUTPUT_BYTES:
            raise PreparationError('output-conflict')
        while True:
            _check(deadline)
            block = stream.read(MiB)
            _check(deadline)
            if not block:
                break
            count += len(block)
            if count > MAX_OUTPUT_BYTES:
                raise PreparationError('output-limit')
            digest.update(block)
        _check(deadline)
        if (_identity(before) != _identity(os.fstat(stream.fileno()))
                or _identity(before) != _identity(safe_path(path).stat())):
            raise PreparationError('output-conflict')
    _check(deadline)
    return digest.hexdigest(), count


def prepare_asset(asset_contract, original_path, output_dir, absolute_deadline, *,
                  maximum_output_bytes=MAX_OUTPUT_BYTES, minimum_free_bytes=None):
    """Return sanitized stage evidence; never treats receipt/download as extraction approval.

    `absolute_deadline` is time.monotonic() based, bounded again by MAX_SECONDS.
    Original and output paths are caller-owned local Foo paths, never URLs.
    Failed stages never receive ready receipts. Originals stay unchanged.

    Synthetic tests may use private temporary directories; production fixed caller
    binds both paths beneath its admitted Foo custody/output roots.
    """
    report = {'schemaVersion': REPORT_SCHEMA, 'handlerVersion': VERSION,
              'assetId': None, 'contractSHA256': None, 'status': 'failed', 'errorCode': None,
              'stages': {'integrity': 'not-run', 'media': 'not-run', 'extraction': 'not-run'},
              'actualMediaType': None, 'mediaEvidence': None, 'originalSHA256': None,
              'originalBytes': None, 'parser': None, 'parameters': None, 'metrics': None,
              'outputs': [], 'nextStage': None, 'nextStageReady': False,
              'bounds': {'originalBytes': MAX_ORIGINAL_BYTES, 'parseBytes': MAX_PARSE_BYTES,
                         'outputBytes': MAX_OUTPUT_BYTES, 'outputFiles': MAX_OUTPUT_FILES, 'archiveExpandedBytes': MAX_ARCHIVE_BYTES,
                         'archiveMembers': MAX_MEMBERS, 'archiveMemberBytes': MAX_MEMBER_BYTES,
                         'archiveRatio': MAX_RATIO, 'pages': MAX_PAGES, 'sheets': MAX_SHEETS,
                         'records': MAX_RECORDS, 'cells': MAX_CELLS, 'seconds': MAX_SECONDS},
              'networkRequests': 0, 'originalModified': False,
              'normalizationPerformed': False, 'translationPerformed': False,
              'goldAdmissionEstablished': False, 'sourceContentsInReport': False}
    process = None
    parent_conn = None
    owned_process_group = False
    scratch = None
    promoted = []
    current_stage = 'integrity'
    try:
        contract = validate_contract(asset_contract)
        if minimum_free_bytes is None:
            minimum_free_bytes = PLANNING_GUARD_BYTES
        if (type(maximum_output_bytes) is not int or not 1 <= maximum_output_bytes <= MAX_OUTPUT_BYTES
                or type(minimum_free_bytes) is not int or not 0 <= minimum_free_bytes <= 1024 ** 4):
            raise PreparationError('contract-invalid')
        report['outputBudget'] = {'maximumOutputBytes': maximum_output_bytes,
                                  'minimumFreeBytes': minimum_free_bytes}
        report.update(assetId=contract['assetId'], contractSHA256=sha(canonical(contract)))
        if (type(absolute_deadline) not in (int, float) or not math.isfinite(absolute_deadline)):
            raise PreparationError('contract-invalid')
        deadline = min(absolute_deadline, time.monotonic() + MAX_SECONDS)
        _check(deadline)
        permissions, holds = contract['permissions'], contract['holds']
        if not permissions['read'] or 'read' in holds or 'all' in holds:
            raise PreparationError('read-permission-held', 'held')
        allowed_extract = permissions['extract'] and not {'extract', 'all'} & set(holds)
        allowed_copy = permissions['copy'] and not {'copy', 'all'} & set(holds)
        retain = contract['expectedBytes'] <= MAX_PARSE_BYTES
        data, original_identity = _read_original(original_path, contract, deadline, retain)
        _check(deadline)
        report['stages']['integrity'] = 'passed'
        report.update(originalSHA256=contract['expectedSHA256'], originalBytes=contract['expectedBytes'])
        current_stage = 'media'
        media, evidence = _sniff(data, contract['expectedMediaTypes'], contract['parameters'], retain)
        _check(deadline)
        report.update(actualMediaType=media, mediaEvidence=evidence)
        if media not in contract['expectedMediaTypes']:
            raise PreparationError('media-mismatch')
        report['stages']['media'] = 'passed'
        current_stage = 'extraction'
        if not allowed_extract:
            raise PreparationError('extract-permission-held', 'held')
        if not allowed_copy:
            raise PreparationError('copy-permission-held', 'held')
        if not retain:
            raise PreparationError('parser-input-limit', 'unsupported')
        caps = capabilities()
        parser_name = ('pypdf' if caps['optionalParsers']['pypdf']['available'] else 'poppler') if media == 'application/pdf' else 'xlrd' if media == 'application/vnd.ms-excel' else 'python-stdlib'
        parser_version = caps['pythonVersion'] if parser_name == 'python-stdlib' else caps['optionalParsers'][parser_name]['version']
        report.update(parser={'name': parser_name, 'version': parser_version}, parameters=dict(contract['parameters']))
        if not caps['isolatedWorker']:
            raise PreparationError('parser-isolation-unavailable', 'unsupported')
        _check(deadline)
        directory = _private_directory(output_dir)
        if safe_path(original_path).parent == directory:
            raise PreparationError('output-unavailable')
        scratch = Path(tempfile.mkdtemp(prefix='.preparing-', dir=directory))
        ctx = multiprocessing.get_context('fork')
        parent_conn, child_conn = ctx.Pipe(duplex=False)
        process = ctx.Process(target=_worker, args=(child_conn, data, media, contract['parameters'],
                                                   str(scratch), deadline, caps, maximum_output_bytes, minimum_free_bytes), daemon=True)
        process.start()
        child_conn.close()
        while True:
            while not parent_conn.poll(min(0.05, max(0, deadline - time.monotonic()))):
                _check(deadline)
                if not process.is_alive():
                    raise PreparationError('parser-resource-limit')
            try:
                result = strict_json(parent_conn.recv_bytes(1024 * 1024))
            except (EOFError, OSError, ValueError):
                raise PreparationError('parser-resource-limit') from None
            if result.get('phase') == 'session-ready' and result.get('pid') == process.pid:
                owned_process_group = True
                continue
            break
        process.join(max(0, deadline - time.monotonic()))
        _check(deadline)
        if process.is_alive() or process.exitcode != 0:
            raise PreparationError('parser-resource-limit')
        if result['status'] != 'passed':
            report['metrics'] = result.get('metrics')
            raise PreparationError(result['code'], result['status'])
        _check(deadline)
        if _identity(safe_path(original_path).stat()) != original_identity:
            raise PreparationError('original-changed')
        outputs = []
        for item in result['outputs']:
            source = scratch / item['temporaryName']
            digest, count = _file_hash(source, deadline)
            if digest != item['sha256'] or count != item['bytes']:
                raise PreparationError('output-conflict')
            output_id = digest + '.' + item['extension']
            target = safe_path(directory / output_id)
            try:
                os.link(source, target)
                promoted.append((target, _identity(target.stat())))
            except FileExistsError:
                if _file_hash(target, deadline) != (digest, count):
                    raise PreparationError('output-conflict')
            outputs.append({'outputId': output_id, 'sha256': digest, 'bytes': count,
                            'format': item['format']})
        fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        _check(deadline)
        if _identity(safe_path(original_path).stat()) != original_identity:
            raise PreparationError('original-changed')
        _check(deadline)
        report.update(status='ready' if result['nextStageReady'] else 'unsupported',
                      errorCode=result['code'], parser=result['parser'],
                      parameters=result['parameters'], metrics=result['metrics'], outputs=outputs,
                      nextStage=result['nextStage'], nextStageReady=result['nextStageReady'])
        report['stages']['extraction'] = 'passed'
    except PreparationError as error:
        report.update(status=error.status, errorCode=error.code)
        report['stages'][current_stage] = error.status
    except (OSError, RefreshError, ValueError, TypeError, KeyError):
        report.update(status='failed', errorCode='output-unavailable' if current_stage == 'extraction' else 'original-unavailable')
        report['stages'][current_stage] = 'failed'
    finally:
        if process is not None:
            # The handshake proves this is our session. Clean it even if its
            # worker leader died while an inherited Poppler child survived.
            if owned_process_group:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            elif process.is_alive():
                process.kill()
            process.join()
        if parent_conn is not None:
            parent_conn.close()
        if report['status'] in ('failed', 'held'):
            for target, identity in promoted:
                try:
                    if _identity(target.stat()) == identity:
                        target.unlink()
                except OSError:
                    pass
        if scratch is not None:
            shutil.rmtree(scratch, ignore_errors=True)
    return report
