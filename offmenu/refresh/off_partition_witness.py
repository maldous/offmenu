"""Opt-in bounded OFF occurrence partition core; no original opener or admission.

The caller supplies a stream under a separately qualified custody/resource
boundary. EOF/count agreement here is not proof of retained-original derivation.
"""
from dataclasses import dataclass, asdict
from contextlib import contextmanager
import hashlib
import errno
import os
from pathlib import Path
import re
import secrets
import stat
import sqlite3
import threading
import time

from .core import RefreshError, canonical, strict_json
from .product_adapters import _safe
from .product_input_witness import _rename_noreplace


def _inode(info):
    return info.st_dev,info.st_ino


def _descriptor_snapshot():
    """Observe this process, closing listdir's own temporary descriptor first."""
    result={}
    for name in os.listdir('/proc/self/fd'):
        try:result[int(name)]=os.fstat(int(name))
        except FileNotFoundError:continue
        except OSError as error:
            if error.errno!=errno.EBADF:raise
    return result


class _OwnedStage:
    """Pinned scratch/evidence handles; no destructive pathname cleanup."""
    def __init__(self,parent):
        self.parent=parent;self.fd=None;self.evidence_fd=None;self.index_fd=None;self.files={};self.created=False
        self.database_fds=[];self.database_verified=False
        self.parent_fd=os.open(parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        self.parent_inode=_inode(os.fstat(self.parent_fd))
        try:
            if _inode(os.stat(_safe(parent),follow_symlinks=False))!=self.parent_inode:
                raise RefreshError('partition-parent-custody-changed')
            self.name='.off-partition-'+secrets.token_hex(16)
            os.mkdir(self.name,0o700,dir_fd=self.parent_fd)
            self.created=True
            before=os.stat(self.name,dir_fd=self.parent_fd,follow_symlinks=False)
            self.fd=os.open(self.name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=self.parent_fd)
            self.inode=_inode(os.fstat(self.fd))
            if self.inode!=_inode(before):raise RefreshError('partition-stage-custody-changed')
            os.mkdir('evidence',0o700,dir_fd=self.fd)
            self.evidence_fd=os.open('evidence',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=self.fd)
            self.evidence_inode=_inode(os.fstat(self.evidence_fd))
        except BaseException as error:
            if self.created:self.retain(error)
            if self.evidence_fd is not None:os.close(self.evidence_fd)
            if self.fd is not None:os.close(self.fd)
            os.close(self.parent_fd)
            raise

    def check(self,evidence=True):
        try:
            if (_inode(os.stat(_safe(self.parent),follow_symlinks=False))!=self.parent_inode
                    or _inode(os.stat(self.name,dir_fd=self.parent_fd,follow_symlinks=False))!=self.inode):
                raise ValueError()
            if evidence and _inode(os.stat('evidence',dir_fd=self.fd,follow_symlinks=False))!=self.evidence_inode:
                raise ValueError()
            if self.index_fd is not None and _inode(os.stat('index.sqlite',dir_fd=self.fd,follow_symlinks=False))!=_inode(os.fstat(self.index_fd)):
                raise ValueError()
        except (OSError,ValueError):raise RefreshError('partition-stage-custody-changed') from None

    @contextmanager
    def create(self,name):
        self.check()
        scratch=name=='index.sqlite'
        fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,
                   dir_fd=self.fd if scratch else self.evidence_fd)
        if scratch:self.index_fd=os.dup(fd)
        else:self.files[name]=_inode(os.fstat(fd))
        with os.fdopen(fd,'wb') as stream:yield stream

    def info(self,name):
        info=os.stat(name,dir_fd=self.fd if name=='index.sqlite' else self.evidence_fd,follow_symlinks=False)
        expected=_inode(os.fstat(self.index_fd)) if name=='index.sqlite' else self.files[name]
        if not stat.S_ISREG(info.st_mode) or _inode(info)!=expected:
            raise RefreshError('partition-stage-file-custody-changed')
        return info

    def bind_database(self,before):
        # Before invoking caller code, a single-threaded SQLite main open must
        # account for exactly one new regular descriptor. Pin that OPEN object,
        # not a pathname reopened after connect. Any ambiguity fails closed.
        after=_descriptor_snapshot()
        opened=[fd for fd,info in after.items()
                if fd not in before or _inode(info)!=_inode(before[fd])]
        for fd in opened:
            if stat.S_ISREG(after[fd].st_mode):self.database_fds.append(os.dup(fd))
        if (threading.active_count()!=1 or len(os.listdir('/proc/self/task'))!=1
                or len(opened)!=1 or len(self.database_fds)!=1):
            raise RefreshError('partition-sqlite-descriptor-ambiguous')
        if _inode(os.fstat(self.database_fds[0]))!=_inode(os.fstat(self.index_fd)):
            raise RefreshError('partition-sqlite-inode-mismatch')
        self.database_verified=True

    def publish(self,destination):
        self.check()
        if set(os.listdir(self.evidence_fd))!=set(self.files):raise RefreshError('partition-stage-inventory-changed')
        for name in self.files:self.info(name)
        _rename_noreplace(self.fd,'evidence',self.parent_fd,destination)
        # renameat2 conditions on names, not a source inode. Attest the object
        # actually moved AFTER the real syscall, before any successful return.
        published=os.open(destination,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=self.parent_fd)
        try:
            if _inode(os.fstat(published))!=self.evidence_inode:
                error=RefreshError('partition-published-identity-mismatch')
                error.preserved_publication_location=os.readlink(f'/proc/self/fd/{published}')
                error.preserved_publication_identity=_inode(os.fstat(published))
                raise error
            self.check(evidence=False)
            if set(os.listdir(published))!=set(self.files):raise RefreshError('partition-published-inventory-changed')
            for name in self.files:
                if _inode(os.stat(name,dir_fd=published,follow_symlinks=False))!=self.files[name]:
                    raise RefreshError('partition-published-file-identity-changed')
        finally:os.close(published)

    def retained(self):
        def location(fd):
            try:return os.readlink(f'/proc/self/fd/{fd}')
            except OSError:return None
        database_fd=self.database_fds[0] if len(self.database_fds)==1 else self.index_fd
        return {'stageIdentity':getattr(self,'inode',None),'stageLocation':location(self.fd),
            'createdStageEntry':getattr(self,'name',None),'parentIdentity':self.parent_inode,
            'evidenceIdentity':getattr(self,'evidence_inode',None),'evidenceLocation':location(self.evidence_fd),
            'databaseIdentity':_inode(os.fstat(database_fd)) if database_fd is not None else None,
            'databaseLocation':location(database_fd),
            'databaseBytes':os.fstat(database_fd).st_size if database_fd is not None else None,
            'databaseConnectionVerified':self.database_verified,
            'createdDatabaseIdentity':_inode(os.fstat(self.index_fd)) if self.index_fd is not None else None,
            'createdDatabaseLocation':location(self.index_fd),
            'ambiguousConnectionFiles':[{'identity':_inode(os.fstat(fd)),
                'location':location(fd),'bytes':os.fstat(fd).st_size} for fd in self.database_fds]
                if len(self.database_fds)>1 else [],
            'automaticDeletion':False,'resourceObligationActive':True}

    def retain(self,error):
        error.partition_retained_state=self.retained()

    def close(self):
        for fd in self.database_fds:os.close(fd)
        if self.index_fd is not None:os.close(self.index_fd)
        os.close(self.evidence_fd)
        os.close(self.fd);os.close(self.parent_fd)


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
    stage=_OwnedStage(parent)
    db=None;started=time.monotonic();expanded=0;count=0;output_bytes=0
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
        with stage.create(name) as target:
            for value in iterator:
                guard();raw=canonical(value);size+=len(raw);output_bytes+=len(raw);rows+=1
                if output_bytes>limits.max_output_bytes:raise RefreshError('partition-output-bound')
                target.write(raw);h.update(raw)
        pins[name]={'sha256':h.hexdigest(),'bytes':size,'rows':rows}
    try:
        with stage.create('index.sqlite'):pass
        if threading.active_count()!=1 or len(os.listdir('/proc/self/task'))!=1:
            raise RefreshError('partition-sqlite-serialized-setup-required')
        before=_descriptor_snapshot()
        # The directory is pinned, but the SQLite open still resolves a mutable
        # leaf. Force main open, then bind its actual descriptor before writes.
        path=Path(f'/proc/self/fd/{stage.fd}/index.sqlite');db=sqlite3.connect(path)
        db.execute('PRAGMA user_version').fetchone()
        stage.bind_database(before)
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
        guard();stage.check();db.commit()
        stage.info('index.sqlite')
        database_bytes=os.fstat(stage.database_fds[0]).st_size
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
            'retainedScratch':{k:v for k,v in stage.retained().items()
                               if k not in ('evidenceIdentity','evidenceLocation')},
            'publicationDirectoryIdentity':stage.evidence_inode,
            'measurements':{'databaseBytes':database_bytes,'outputPayloadBytes':output_bytes,
                            'elapsedSeconds':time.monotonic()-started},'limits':asdict(limits)}
        raw=canonical(result)
        if output_bytes+len(raw)>limits.max_output_bytes:raise RefreshError('partition-output-bound')
        db.close();db=None
        with stage.create('result.json') as target:target.write(raw)
        guard()
        stage.publish(destination.name)
        return result
    except sqlite3.Error as cause:
        error=RefreshError('partition-storage-bound-or-error');stage.retain(error)
        raise error from cause
    except BaseException as error:
        stage.retain(error)
        raise
    finally:
        try:
            if db is not None:db.close()
        finally:stage.close()
