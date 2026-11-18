"""Bounded, read-only semantic witness for selected retained index partitions.

This is a Foo preflight, not a data collector, signer, database repair or
historical whole-file attestation. No default issuer; no real input discovery.
"""
from collections import Counter
from contextlib import ExitStack, contextmanager
from dataclasses import asdict, dataclass
import hashlib
import math
import os
import re
import sqlite3
import time
from types import MappingProxyType
from .retained_context_job import HASH, NAME, SHARD, need, digest, wire
from .retained_context_source import Pin, _open, _small, _ref
from .retained_context_job import decode


@dataclass(frozen=True)
class Snapshot:
    """Stat identity plus issuer's immutable snapshot/fence ID, NOT a file hash."""
    path: str
    snapshot_id: str
    size: int
    device: int
    inode: int
    mtime_ns: int
    ctime_ns: int

    def stat_key(self):
        return (self.device,self.inode,self.size,self.mtime_ns,self.ctime_ns)


@dataclass(frozen=True)
class Cohort:
    provider: str
    release: str
    number: int
    receipt_sha256: str
    complete_products: int               # Includes other providers in this cohort.
    shards: tuple                        # (shard key, exact count or None if derived)
    selected_products: int                # From pinned batch receipt for this provider.
    receipt: Pin                          # Trusted batch bytes, not an arbitrary count.
    index: Pin                           # Actual trusted per-cohort content SHA.


@dataclass(frozen=True)
class Limits:
    max_selected_rows: int
    max_selected_postings: int
    max_global_postings: int
    max_local_index_bytes: int
    max_sql_steps: int
    timeout_seconds: int
    memory_bytes: int                    # Enforced outside this interpreter.
    io_slots: int = 1
    workers: int = 1

    def check(self):
        for v,m in ((self.max_selected_rows,50000),(self.max_selected_postings,250000),
                    (self.max_global_postings,16000000),(self.max_local_index_bytes,2**31),
                    (self.max_sql_steps,2**32),(self.timeout_seconds,3600),
                    (self.memory_bytes,8*2**30),(self.io_slots,4),(self.workers,1)):
            need(type(v) is int and 0<v<=m,'unbounded index proof')
        need(self.memory_bytes>=256*2**20,'proof memory bound')


def _scope(root,root_fd,snapshot,cohorts,limits):
    limits.check()
    need(type(snapshot) is Snapshot and isinstance(snapshot.snapshot_id,str) and
         NAME.fullmatch(snapshot.snapshot_id) and snapshot.size>0,'snapshot identity')
    need(isinstance(cohorts,tuple) and 0<len(cohorts)<=8,'cohort scope')
    count=0; scopes=set();numbers=set()
    for c in cohorts:
        need(type(c) is Cohort and c.provider in ('off','usda-files') and NAME.fullmatch(c.release)
             and type(c.number) is int and c.number>=0 and HASH.fullmatch(c.receipt_sha256)
             and type(c.complete_products) is int and c.complete_products>0 and type(c.index) is Pin
             and HASH.fullmatch(c.index.sha256) and 0<c.index.size<=limits.max_local_index_bytes
             and type(c.receipt) is Pin and c.receipt.sha256==c.receipt_sha256 and
             type(c.selected_products) is int and 0<c.selected_products<=c.complete_products,'cohort evidence')
        need(c.number not in numbers,'duplicate cohort admission');numbers.add(c.number)
        need(isinstance(c.shards,tuple) and 0<len(c.shards)<=64,'shard count')
        total=0
        for k,n in c.shards:
            need((c.number,c.provider,k) not in scopes and SHARD.fullmatch(k) and
                 int(k.split('/')[0][7:])==c.number and (n is None or type(n) is int and 0<n<=5000),'shard evidence')
            scopes.add((c.number,c.provider,k));total+=n or 0
        need(total<=c.selected_products,'selected denominator exceeds cohort');count+=c.selected_products
    need(count<=limits.max_selected_rows,'selected count exceeds scope')
    r=os.fstat(root_fd)
    return digest(wire({'schema':'offmenu-selected-index-proof/1','root':[root,r.st_dev,r.st_ino],
        'snapshot':asdict(snapshot),'cohorts':[asdict(c) for c in cohorts],'limits':asdict(limits)}))


_issued = object()


@dataclass(frozen=True,init=False,slots=True)
class SelectedProof:
    """Ephemeral approved-writer handoff; construct through qualify_selection.

    Persisting/loading a proof across processes requires the existing issuer's
    authentication of its binding. Untrusted JSON is deliberately not accepted.
    """
    request: str
    snapshot: Snapshot
    _entries: object
    summary: object

    def __init__(self,request,snapshot,entries,summary,*,_issuer=None):
        need(_issuer is _issued,'unissued selected-index proof')
        object.__setattr__(self,'request',request);object.__setattr__(self,'snapshot',snapshot)
        object.__setattr__(self,'_entries',MappingProxyType(dict(entries)))
        object.__setattr__(self,'summary',MappingProxyType(dict(summary)))

    def covers(self,snapshot,unit,receipt,local_pin):
        return (snapshot==self.snapshot and unit.proof_request_sha256==self.request and self._entries.get((unit.provider,unit.release,unit.shard))
               ==(unit.max_rows,receipt,local_pin))

    def count(self,provider,release,shard):
        binding=self._entries.get((provider,release,shard))
        return binding[0] if binding else None

    def metadata(self):
        # No identifiers, postings or paths escape into this portable projection.
        return dict(self.summary)


def qualify_selection(*, root, root_fd, snapshot, cohorts, limits, issuer):
    """Verify local indexes once and perform ONE complete global barcode sweep.

    All raw payload files remain unopened. The sweep can see unrelated index
    metadata; the issuer MUST explicitly admit this cost/scope, hold the same
    immutable view for future users, enforce the declared host resource ceiling,
    and validate provider rights/claims. This function does not invoke a worker.
    """
    need(callable(getattr(issuer,'hold_index_proof',None)),'no proof issuer')
    request=_scope(root,root_fd,snapshot,cohorts,limits)
    with issuer.hold_index_proof(request) as g, ExitStack() as st:
        need(isinstance(g,dict) and g.get('request')==request and g.get('snapshot_id')==snapshot.snapshot_id and
             all(g.get(k) is True for k in ('global_metadata_sweep_allowed','stable_snapshot_held',
                 'provider_rights_and_claims_current','host_limits_enforced','offline_only')) and
             g.get('limits') is not None and wire(g['limits'])==wire(asdict(limits)) and
             type(g.get('valid_until')) in (int,float) and math.isfinite(g['valid_until']) and
             g['valid_until']>=time.time()+limits.timeout_seconds,'missing scoped metadata admission')
        finish=time.monotonic()+limits.timeout_seconds;steps=0
        def tick():
            nonlocal steps
            steps+=1000
            return int(steps>limits.max_sql_steps or time.monotonic()>=finish)
        def clock():
            need(time.monotonic()<finish,'proof deadline')
        def connect(p):
            f=st.enter_context(_open(root,root_fd,p,index=True))
            if isinstance(p,Pin):
                h=hashlib.sha256()
                while a:=f.read(1024*1024):
                    clock();h.update(a)
                need(h.hexdigest()==p.sha256,'trusted cohort content differs')
            db=sqlite3.connect(f'file:/proc/self/fd/{f.fileno()}?mode=ro&immutable=1',uri=True)
            st.callback(db.close)
            db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH,2*1024**2)
            db.execute('PRAGMA query_only=ON');db.execute('PRAGMA trusted_schema=OFF')
            db.execute('PRAGMA temp_store=MEMORY');db.execute('PRAGMA cache_size=-4096')
            db.set_progress_handler(tick,1000)
            return db
        def columns(db, table, wanted):
            row=db.execute("SELECT type FROM sqlite_master WHERE name=?",(table,)).fetchone()
            need(row==('table',),'missing physical index table')
            schema={t[1]:t[5] for t in db.execute('PRAGMA table_info('+table+')')}
            need(set(wanted)<=schema.keys(),'wrong index fields')
            return schema
        global_db=connect(snapshot)
        need(columns(global_db,'completed',{'cohort','products','result_sha'})['cohort']==1,
             'missing unique cohort completion identity')
        need(columns(global_db,'records',{'id','source','release','native_id','ref_sha','cohort','record_shard'})['id']==1,
             'missing indexed unique source identity')
        bcols=columns(global_db,'barcodes',{'code','id','checksum_valid'})
        need((bcols['code'],bcols['id'])==(1,2),'wrong global posting constraint')
        expected={}; entries={}; wanted_counts=Counter();actual_counts=Counter();posting_total=0
        for c in cohorts:
            with _open(root,root_fd,c.receipt) as f:
                b=decode(_small(f,c.receipt,4*1024**2))
            needed=set(dict(c.shards))
            descs=[x for x in b['files'] if isinstance(x,dict) and isinstance(x.get('key'),str)
                   and isinstance(x.get('path'),str) and x['path'].endswith('/'+c.provider+'/'+x['key']+'.jsonl.gz')]
            need(b.get('state')=='SOURCE_STAGING_COMPLETE_CANONICAL_ACCEPTANCE_SEPARATE' and
                 b['counts'].get('products')==c.complete_products and b['sourceCounts'].get(c.provider)==c.selected_products and
                 _ref(b['index'],c.index) and len(descs)==len(needed) and {x['key'] for x in descs}==needed,
                 'selected group is not the pinned provider cohort')
            need(global_db.execute('SELECT products,result_sha FROM completed WHERE cohort=?',(c.number,)).fetchone()
                 ==(c.complete_products,c.receipt_sha256),'cohort completion not anchored')
            local=connect(c.index)
            columns(local,'records',{'local_id','public_id','source','release','native_id','ref_sha','record_shard','wire_sha'})
            columns(local,'barcodes',{'local_id','code','checksum_valid'})
            keys=dict(c.shards)
            for shard,n in c.shards:
                k=(c.provider,c.release,shard);wanted_counts[k]=n
            by_local={}
            args=','.join('?' for _ in keys)
            # One limited local records query per cohort; IDs with zero barcodes are retained.
            query=('SELECT local_id,public_id,native_id,ref_sha,record_shard,wire_sha FROM records '
                   'WHERE source=? AND release=? AND record_shard IN ('+args+')')
            for lid,rid,native,ref,shard,linehash in local.execute(query,(c.provider,c.release,*keys)):
                clock();need(len(expected)<limits.max_selected_rows and rid not in expected and lid not in by_local
                    and re.fullmatch(r'offmenu:product:[a-f0-9]{24}',rid) and isinstance(native,str) and
                    len(native)<=1024 and HASH.fullmatch(ref) and HASH.fullmatch(linehash),'duplicate/invalid local row')
                gr=global_db.execute('SELECT source,release,native_id,ref_sha,cohort,record_shard FROM records WHERE id=?',(rid,)).fetchone()
                need(gr==(c.provider,c.release,native,ref,c.number,shard),'global/private row differs')
                actual_counts[c.provider,c.release,shard]+=1
                expected[rid]=set();by_local[lid]=rid
            for lid,code,flag in local.execute('SELECT local_id,code,checksum_valid FROM barcodes'):
                clock()
                if lid not in by_local:continue
                need(isinstance(code,str) and len(code)<=256 and type(flag) is int and flag in (0,1)
                     and posting_total<limits.max_selected_postings,'local posting bounds')
                target=expected[by_local[lid]]
                need((code,flag) not in target,'duplicate local posting')
                target.add((code,flag));posting_total+=1
            need(sum(actual_counts[c.provider,c.release,k] for k in keys)==c.selected_products,
                 'pinned provider denominator differs')
            for k,n in keys.items():
                actual=actual_counts[c.provider,c.release,k]
                need(0<actual<=5000 and (n is None or n==actual),'per-shard source denominator differs')
                entries[c.provider,c.release,k]=(actual,c.receipt_sha256,c.index)
        need(set(wanted_counts)==set(actual_counts),'missing selected shard')
        rows=0;matched=0
        for code,rid,flag in global_db.execute('SELECT code,id,checksum_valid FROM barcodes'):
            rows+=1;clock();need(rows<=limits.max_global_postings,'global sweep exceeded admission before EOF')
            if rid not in expected:continue
            need(type(flag) is int and (code,flag) in expected[rid],'extra or changed selected posting')
            expected[rid].remove((code,flag));matched+=1
        need(matched==posting_total and all(not x for x in expected.values()),'missing selected posting')
        summary={'schema':'offmenu-selected-index-proof/1','request_sha256':request,
                 'selected_records':len(expected),'selected_postings':matched,'global_postings_examined':rows,
                 'global_sweeps':1,'cohorts':len(cohorts),'whole_file_hash_verified':False,
                 'raw_publisher_data_read':False,'public_distribution_approved':False}
        return SelectedProof(request,snapshot,entries,summary,_issuer=_issued)
