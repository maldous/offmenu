"""Opt-in bounded OFF occurrence partition core; no original opener or admission.

The caller supplies a stream under a separately qualified custody/resource
boundary. EOF/count agreement here is not proof of retained-original derivation.
"""
from dataclasses import dataclass, asdict
import hashlib
import os
from pathlib import Path
import re
import shutil
import sqlite3
import tempfile
import time

from .core import RefreshError, canonical, strict_json
from .product_adapters import _safe
from .product_input_witness import _rename_noreplace


@dataclass(frozen=True)
class PartitionLimits:
    max_rows: int
    max_line_bytes: int
    max_expanded_bytes: int
    max_database_bytes: int
    max_output_bytes: int
    max_seconds: int


def partition_stream(lines, destination, *, original_sha256, expected_rows, limits):
    """Classify every supplied occurrence, then emit S/C/Q only after EOF.

    No default real envelope, CLI, source permission constructor or product
    normalization. Original source pin is a declaration, not verified by this API.
    Malformed JSON/framing/truncation/resource failures publish no success result.
    """
    if (type(limits) is not PartitionLimits or any(type(v) is not int or not 0<v<2**63 for v in asdict(limits).values())
            or limits.max_database_bytes<65536 or type(expected_rows) is not int
            or not 1<=expected_rows<=limits.max_rows or type(original_sha256) is not str
            or not re.fullmatch('[0-9a-f]{64}',original_sha256)):
        raise RefreshError('partition-contract-invalid')
    destination=_safe(destination)
    if destination.exists():raise RefreshError('partition-destination-exists')
    parent=_safe(destination.parent)
    pending=Path(tempfile.mkdtemp(prefix='.off-partition-',dir=parent))
    db=None;published=False;started=time.monotonic();expanded=0;count=0;output_bytes=0
    pins={};stream_hash=hashlib.sha256()
    def guard():
        if time.monotonic()-started>limits.max_seconds:raise RefreshError('partition-time-bound')
    planned=set()
    def ordered(sql, parameters=()):
        if sql not in planned:
            if any('TEMP B-TREE' in str(r).upper() for r in db.execute('EXPLAIN QUERY PLAN '+sql,parameters)):
                raise RefreshError('partition-unbounded-sort-refused')
            planned.add(sql)
        return db.execute(sql,parameters)
    def emit(name, iterator):
        nonlocal output_bytes
        h=hashlib.sha256();size=0;rows=0
        with (pending/name).open('xb') as target:
            for value in iterator:
                guard();raw=canonical(value);size+=len(raw);output_bytes+=len(raw);rows+=1
                if output_bytes>limits.max_output_bytes:raise RefreshError('partition-output-bound')
                target.write(raw);h.update(raw)
        pins[name]={'sha256':h.hexdigest(),'bytes':size,'rows':rows}
    try:
        path=pending/'index.sqlite';db=sqlite3.connect(path)
        db.execute('PRAGMA page_size=4096');db.execute('PRAGMA cache_size=-2048')
        db.execute('PRAGMA journal_mode=OFF');db.execute('PRAGMA temp_store=FILE')
        db.execute(f'PRAGMA max_page_count={limits.max_database_bytes//4096}')
        db.execute('CREATE TABLE occurrence (ordinal INTEGER PRIMARY KEY, code TEXT, line_sha TEXT NOT NULL, body_sha TEXT NOT NULL)')
        db.execute('CREATE INDEX occurrence_key ON occurrence(code,ordinal)')
        db.execute('CREATE TABLE keys (code TEXT PRIMARY KEY, multiplicity INTEGER NOT NULL)')
        for raw in lines:
            guard();count+=1
            if count>expected_rows or count>limits.max_rows:raise RefreshError('partition-row-bound')
            if type(raw) is not bytes or not raw.endswith(b'\n') or len(raw)>limits.max_line_bytes:
                raise RefreshError('partition-line-invalid')
            expanded+=len(raw)
            if expanded>limits.max_expanded_bytes:raise RefreshError('partition-expanded-bound')
            stream_hash.update(raw)
            try:
                row=strict_json(raw.decode('utf-8'))
                if type(row) is not dict:raise ValueError()
                body=canonical(row)
            except Exception:raise RefreshError('partition-json-invalid') from None
            code=row.get('code')
            if type(code) is not str or not re.fullmatch('[0-9]{4,32}',code):code=None
            db.execute('INSERT INTO occurrence VALUES(?,?,?,?)',
                (count,code,hashlib.sha256(raw).hexdigest(),hashlib.sha256(body).hexdigest()))
            if code is not None:
                db.execute('INSERT INTO keys VALUES(?,1) ON CONFLICT(code) DO UPDATE SET multiplicity=multiplicity+1',(code,))
        if count!=expected_rows:raise RefreshError('partition-incomplete-stream')
        guard();db.commit()
        database_bytes=path.stat().st_size
        if database_bytes>limits.max_database_bytes:raise RefreshError('partition-db-bound')
        totals={'S':0,'C':0,'Q':0};groups=0
        def occurrences():
            for ordinal,code,line_sha,body_sha in ordered(
                'SELECT ordinal,code,line_sha,body_sha FROM occurrence ORDER BY ordinal'):
                multiplicity=None if code is None else db.execute('SELECT multiplicity FROM keys WHERE code=?',(code,)).fetchone()[0]
                status='Q' if code is None else 'S' if multiplicity==1 else 'C'
                totals[status]+=1
                yield {'ordinal':ordinal,'originalSha256':original_sha256,'table':'products',
                    'code':code,'status':status,'rawLineSha256':line_sha,'canonicalBodySha256':body_sha,
                    'reason':'native-code-invalid' if status=='Q' else 'repeated-native-key' if status=='C' else None}
        emit('occurrences.jsonl',occurrences())
        def singleton_rows():
            for (code,) in ordered('SELECT code FROM keys WHERE multiplicity=1 ORDER BY code COLLATE BINARY'):
                for ordinal,line_sha,body_sha in ordered('SELECT ordinal,line_sha,body_sha FROM occurrence WHERE code=? ORDER BY ordinal',(code,)):
                    yield {'code':code,'ordinal':ordinal,'rawLineSha256':line_sha,'canonicalBodySha256':body_sha}
        emit('singletons.jsonl',singleton_rows())
        def group_rows():
            nonlocal groups
            for code,multiplicity in ordered('SELECT code,multiplicity FROM keys WHERE multiplicity>1 ORDER BY code COLLATE BINARY'):
                groups+=1;h=hashlib.sha256()
                for ordinal,line_sha,body_sha in ordered('SELECT ordinal,line_sha,body_sha FROM occurrence WHERE code=? ORDER BY ordinal',(code,)):
                    guard();h.update(canonical({'ordinal':ordinal,'rawLineSha256':line_sha,'canonicalBodySha256':body_sha}))
                yield {'code':code,'multiplicity':multiplicity,'selectedPrimary':None,
                    'resolution':'unresolved','orderedMembersSha256':h.hexdigest()}
        emit('groups.jsonl',group_rows())
        def members():
            for (code,) in ordered('SELECT code FROM keys WHERE multiplicity>1 ORDER BY code COLLATE BINARY'):
                for ordinal,line_sha,body_sha in ordered('SELECT ordinal,line_sha,body_sha FROM occurrence WHERE code=? ORDER BY ordinal',(code,)):
                    yield {'code':code,'ordinal':ordinal,'rawLineSha256':line_sha,'canonicalBodySha256':body_sha}
        emit('members.jsonl',members())
        if sum(totals.values())!=count:raise RefreshError('partition-accounting-invalid')
        ids=hashlib.sha256()
        for kind in ('nutrientProfile','product'):
            for (code,) in ordered('SELECT code FROM keys WHERE multiplicity=1 ORDER BY code COLLATE BINARY'):
                guard();ids.update(canonical('off:'+kind+':'+code))
        # A membership candidate for later independent scope review, not an
        # accepted SourceContract expected-ID/count binding or a clean oracle.
        result={'schemaVersion':'offmenu-off-partition-stream/1','declaredOriginalSha256':original_sha256,
            'inputStreamRows':count,'inputExpandedBytes':expanded,'inputExpandedSha256':stream_hash.hexdigest(),
            'streamEOF':True,'counts':totals,'repeatedKeyGroups':groups,'files':pins,
            'candidateSingletonProductProfileIdsSha256':ids.hexdigest(),
            'candidateSingletonProductProfileCount':2*totals['S'],
            'sourceCustodyVerified':False,'eligibleCleanScopeWitness':False,'accepted':False,
            'productSemanticsQualified':False,'realScopeOrResourcesAdmitted':False,
            'measurements':{'databaseBytes':database_bytes,'outputPayloadBytes':output_bytes,
                            'elapsedSeconds':time.monotonic()-started},'limits':asdict(limits)}
        raw=canonical(result)
        if output_bytes+len(raw)>limits.max_output_bytes:raise RefreshError('partition-output-bound')
        db.close();db=None;path.unlink()
        (pending/'result.json').write_bytes(raw)
        guard()
        fd=os.open(parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:_rename_noreplace(fd,pending.name,fd,destination.name)
        finally:os.close(fd)
        published=True
        return result
    except sqlite3.Error:raise RefreshError('partition-storage-bound-or-error') from None
    finally:
        if db is not None:db.close()
        if not published:shutil.rmtree(pending)
