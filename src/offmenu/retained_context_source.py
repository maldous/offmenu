"""Read one previously staged product shard; no acquisition, inference or publication."""
from contextlib import ExitStack, contextmanager
from copy import deepcopy
from dataclasses import dataclass, asdict
import gzip
import hashlib
import json
import os
from pathlib import PurePosixPath
import re
import sqlite3
import stat
from .retained_context_job import DIR, READ, HASH, need, decode, digest, wire

# Historical pure bridge contract identified in the queue. No module is ever
# loaded from an absolute path in a retained assignment.
LEGACY_BRIDGE = '5206a8831bbf190f046bb368ef261e7d6fc6f16d4804f6bd2c290e02c57d5b0f'
ROW_PREFIX = re.compile(rb'^\["(offmenu:product:[0-9a-f]{24})",')
ENCODING = 'typed-exact-decimal-json/1; not an original byte-span hash'
ROLES = {'queue','assignment','cohort_receipt','index','global_index','shard'}


@dataclass(frozen=True)
class Pin:
    path: str       # absolute logical path in original reference
    sha256: str
    size: int
    device: int
    inode: int
    mtime_ns: int
    ctime_ns: int

    def stat_key(self):
        return (self.device,self.inode,self.size,self.mtime_ns,self.ctime_ns)


def signature(s):
    return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)


def input_key(root_path, root_fd, pins):
    s=os.fstat(root_fd)
    return digest(wire({'root':[root_path,s.st_dev,s.st_ino],
                        'pins':{k:asdict(v) for k,v in pins.items()}}))


@contextmanager
def _open(root_path, root_fd, pin, *, index=False):
    p=PurePosixPath(pin.path); root=PurePosixPath(root_path)
    need(root.is_absolute() and p.is_absolute() and p.is_relative_to(root)
         and str(p)==pin.path and '..' not in p.parts and p != root, 'outside registered input root')
    parts=p.relative_to(root).parts
    with ExitStack() as stack:
        d=os.dup(root_fd);stack.callback(os.close,d)
        for name in parts[:-1]:
            d=os.open(name,DIR,dir_fd=d);stack.callback(os.close,d)
        f=stack.enter_context(os.fdopen(os.open(parts[-1],READ,dir_fd=d),'rb'))
        s=os.fstat(f.fileno())
        need(stat.S_ISREG(s.st_mode) and signature(s)==pin.stat_key() and HASH.fullmatch(pin.sha256),
             'input identity changed')
        def still_bound():
            need(signature(os.fstat(f.fileno()))==pin.stat_key() and
                 signature(os.stat(parts[-1],dir_fd=d,follow_symlinks=False))==pin.stat_key(),
                 'input changed during use')
            if index:
                for suffix in ('-wal','-journal','-shm'):
                    try: os.stat(parts[-1]+suffix,dir_fd=d,follow_symlinks=False)
                    except FileNotFoundError: pass
                    else: raise ValueError('index has mutable sidecars')
        still_bound()
        yield f
        still_bound()


def _small(f,pin,limit):
    need(0<pin.size<=limit,'metadata/shard size')
    data=f.read(limit+1)
    need(len(data)==pin.size and digest(data)==pin.sha256,'content pin mismatch')
    return data


def _ref(ref,pin):
    return isinstance(ref,dict) and ref.get('path')==pin.path and ref.get('sha256')==pin.sha256


def _one(seq, predicate, label):
    found=[v for v in seq if predicate(v)]
    need(len(found)==1,label)
    return found[0]


def _one_sql(db, sql, args):
    found=db.execute(sql,args).fetchmany(2)
    need(len(found)==1,'missing or ambiguous index row')
    return found[0]


def _cell(fields, value):
    c=fields if isinstance(fields,dict) else {}; state=c.get('state','not-projected')
    b=json.dumps(value,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
    check=(state in ('present','empty','null') and bool(c.get('pointer'))
           and c.get('evidenceEncoding')==ENCODING and type(c.get('evidenceBytes')) is int
           and c['evidenceBytes']==len(b) and c.get('parsedValueEvidenceSha256')==digest(b))
    return {'state':state,'originalValue':deepcopy(value),'sourcePointer':c.get('pointer'),
            'valueSha256':c.get('parsedValueEvidenceSha256'),'evidenceBytes':c.get('evidenceBytes'),
            'evidenceEncoding':c.get('evidenceEncoding'),'originalSourceAbsenceEstablished':False,
            'projectedValueCommitmentVerified':check,'pointerScope':'retained normalized projection, not original publisher byte span',
            'unresolvedReason':None if check else 'SOURCE_VALUE_NOT_MATERIALIZED_OR_COMMITMENT_UNVERIFIED'}


def _project(row):
    d=row['data'];p=row['provenance'];c=row['curation'];fields=d['sourceFieldStates']
    cf=fields.get('categories',{});lf=fields.get('languages',{})
    triples=(('name',fields,'name','name'),('brand',fields,'brand','brand'),
       ('ingredientDeclaration',fields,'ingredientDeclaration','ingredientsText'),('categories',cf,'categories','categories'),
       ('sourceCategoryFields',cf,'sourceCategoryFields','sourceCategoryFields'),('dataType',cf,'dataType','dataType'),
       ('sourceQuantity',fields,'sourceQuantity','serving'),('names',lf,'names','names'),('nameLanguage',lf,'nameLanguage','nameLanguage'))
    values={name:_cell(f.get(key),d.get(at)) for name,f,key,at in triples}
    binding={k:p[k] for k in ('sourceId','releaseId','recordId','sourceDocumentSha256')}
    binding.update(nativeRecordId=c['sourceRecordReference'],**{k:c[k] for k in
                   ('sourceObservationSha256','inputDatabaseSha256','sourceQualificationSha256')})
    return {'sourceBinding':binding,'identifiers':deepcopy(d.get('identifiers',[])),
            **{k:deepcopy(d.get(k)) for k in ('categories','sourceCategoryFields','dataType','names','sourceLanguageFields')},
            'name':{'originalValue':deepcopy(d.get('name')),'state':values['name']['state'],
                    'language':d.get('nameLanguage'),'pointer':values['name']['sourcePointer']},
            'fieldEvidence':deepcopy(fields),'sourceProductContext':{'schema':'offmenu-source-product-context/1',
            'fields':values,'sourceEvidence':binding,'wholeProductSemanticAssertion':'NOT_INFERRED',
            'packageQuantityInference':'NOT_ALLOWED_FROM_SERVING','sourceTermAssertions':[]},'sourceTermAssertions':[]}


def produce(unit, start, *, root_path, root_fd, pins, verify_index, consume):
    """Caller must hold real read admission on each advancement of this iterator.

    verify_index(pin, fd) recognizes a trusted prior SHA verified against the
    exact immutable stat identity or verifies that already-authorized file once.
    No in-memory name-only cache, arbitrary parser lookup, or unpinned DB fallback.
    consume is trusted reviewed code selected by the issuer's parser digest.
    """
    need(set(pins)==ROLES and input_key(root_path,root_fd,pins)==unit.inputs_sha256,'input manifest')
    need(unit.queue_sha256==pins['queue'].sha256 and unit.assignment_sha256==pins['assignment'].sha256,
         'queue/assignment content identity')
    with ExitStack() as st:
        def metadata(role):
            p=pins[role]
            with _open(root_path,root_fd,p) as f: return decode(_small(f,p,4*1024**2))
        q=metadata('queue');a=metadata('assignment');c=metadata('cohort_receipt')
        need(q['id']==unit.queue and a['status']=='EXACT_HELPER_ASSIGNMENTS_PREPARED_SOURCE_READ_BY19_FALSE',
             'queue identity or assignment status')
        e=_one(q['entries'],lambda v:v['source']==unit.provider and v['key']==unit.shard,'queue membership')
        b=_one(a['assignments'],lambda v:v['source']==unit.provider and v['slice']['key']==unit.shard,
               'assignment membership')
        src=b['slice']
        need(_ref(e['assignment'],pins['assignment']) and e['input']==src and _ref(src,pins['shard'])
             and src['bytes']==pins['shard'].size and b['sourceQualificationSha256']==e['sourceQualificationSha256']
             ==unit.rights_sha256,'shard rights/queue binding')
        need(_ref(q['sourceReceipt'],pins['cohort_receipt']) and _ref(a['cohortReceipt'],pins['cohort_receipt'])
             and _ref(q['cohortIndex'],pins['index']) and _ref(a['cohortIndex'],pins['index'])
             and _ref(c['index'],pins['index']) and a['retainedGlobalIndexPath']==pins['global_index'].path
             and q['sourceBridge']==a['sourceContextBridge'] and q['sourceBridge']['sha256']==LEGACY_BRIDGE,
             'index or projection provenance')
        need(c['state']=='SOURCE_STAGING_COMPLETE_CANONICAL_ACCEPTANCE_SEPARATE'
             and sum(x==src for x in c['files'])==1 and HASH.fullmatch(c['input']['sha256']),'cohort membership')
        need(type(src['uncompressedBytes']) is int and 0<src['uncompressedBytes']<=32*1024**2,'inflated byte limit')
        def db(role):
            p=pins[role];f=st.enter_context(_open(root_path,root_fd,p,index=True))
            need(verify_index(p,f.fileno()) is True,'missing verified immutable index fingerprint')
            con=sqlite3.connect(f'file:/proc/self/fd/{f.fileno()}?mode=ro&immutable=1',uri=True)
            st.callback(con.close);con.execute('PRAGMA query_only=ON');return con
        local=db('index'); glob=db('global_index')
        p=pins['shard']; f=st.enter_context(_open(root_path,root_fd,p))
        need(0<p.size<=32*1024**2,'compressed byte limit')
        h=hashlib.sha256()
        while piece:=f.read(1024*1024):h.update(piece)
        need(h.hexdigest()==p.sha256,'compressed data hash')
        f.seek(0); z=st.enter_context(gzip.GzipFile(fileobj=f,mode='rb'))
        n=0;seen=set();total=0;cohort=int(unit.shard.split('/')[0][7:])
        while line:=z.readline(2*1024**2+1):
            total+=len(line)
            need(total<=src['uncompressedBytes'] and len(line)<=2*1024**2
                 and line.endswith(b'\n') and n<unit.max_rows,'expanded shard bounds')
            m=ROW_PREFIX.match(line);need(m,'wrong stage frame');rid=m[1].decode()
            need(rid not in seen,'duplicate stage identity');seen.add(rid);ordinal=n;n+=1
            if ordinal<start:continue
            lr=_one_sql(local,'SELECT local_id,source,release,native_id,ref_sha,record_shard,wire_sha FROM records WHERE public_id=?',(rid,))
            gr=_one_sql(glob,'SELECT source,release,native_id,ref_sha,cohort,record_shard FROM records WHERE id=?',(rid,))
            need(gr==(lr[1],lr[2],lr[3],lr[4],cohort,lr[5]) and (lr[1],lr[2],lr[5])==
                 (unit.provider,unit.release,unit.shard) and digest(line)==lr[6],'indexed source identity')
            stage_id,items=decode(line);need(stage_id==rid and len(items)==1,'stage singleton')
            row=items[0]
            # Do not project away a hidden provider or household refusal.
            from .retained_context_consumers import check_restrictions
            check_restrictions(row, nested=True)
            d=row['data']; provenance=row['provenance'];context=_project(row);sb=context['sourceBinding']
            need(row['id']==rid and row['kind']=='product' and provenance['visibility']=='source-staging'
                 and (sb['sourceId'],sb['releaseId'],sb['nativeRecordId'],sb['sourceObservationSha256'])==
                 (unit.provider,unit.release,lr[3],lr[4]) and sb['inputDatabaseSha256']==c['input']['sha256']
                 and sb['sourceQualificationSha256']==unit.rights_sha256,'stage evidence')
            codes=sorted(v['value'] for v in context['identifiers'] if isinstance(v,dict) and v.get('system')=='barcode')
            posts=local.execute('SELECT code,checksum_valid FROM barcodes WHERE local_id=? ORDER BY code LIMIT ?',(lr[0],len(codes)+1)).fetchmany(len(codes)+1)
            need([code for code,_ in posts]==codes,'local barcode bindings')
            for code,valid in posts:
                need(valid in (0,1) and _one_sql(glob,'SELECT checksum_valid FROM barcodes WHERE code=? AND id=?',
                                                (code,rid))==(valid,),'global barcode bindings')
            historical={'stageRecordId':rid,'stageRecordWireSha256':lr[6],'sourceBinding':sb,
               'sourceRights':{k:provenance[k] for k in ('visibility','license','attribution','rights') if k in provenance},
               'sourceAdapterInput':context,'literalProjectedFields':{k:d[k] for k in
               ('name','names','nameLanguage','ingredientsText','categories','sourceCategoryFields','sourceLanguageFields','dataType','sourceFieldStates') if k in d},
               'identifiers':context['identifiers'],'barcodePostings':[{'lexicalCode':code,'checksumValid':valid==1} for code,valid in posts],
               'retainedSource':{'cohort':cohort,'recordShard':unit.shard,'compressedShardSha256':p.sha256},
               'meaning':'Retained normalized stage projection, not publisher-original bytes, accepted English translation, canonical identity or public admission.'}
            yield consume(unit.provider,historical,binding={'provider':unit.provider,'release':unit.release,
                'queue':unit.queue_sha256,'shard':unit.shard,'assignment_sha256':unit.assignment_sha256,
                'rights_sha256':unit.rights_sha256,'parser_sha256':unit.parser_sha256,'stage_wire_sha256':lr[6],
                'stage_record_id':rid,'row_ordinal':ordinal,'shard_sha256':p.sha256,'input_database_sha256':c['input']['sha256']})
        need(n==unit.max_rows and total==src['uncompressedBytes'],'source denominator')


def run_qualified(unit, *, source_root, source_fd, destination_fd, pins, issuer, verify_index):
    """Production embedding point, not a CLI: no installed issuer fallback.

    The containing process and its exact source revision are bound by the
    admission. Index receipts are a distinct trusted component, never boolean
    values copied from the input manifest. Both dependencies are mandatory.
    """
    from pathlib import Path
    from . import retained_context_consumers as adapters
    from .retained_context_job import _hold, execute
    unit.check()
    with _hold(issuer,unit,'qualify-route'):
        need(callable(verify_index) and set(pins)==ROLES and
             input_key(source_root,source_fd,pins)==unit.inputs_sha256,'route inputs')
        need(digest(Path(adapters.__file__).read_bytes())==unit.parser_sha256,'parser pin')
    return execute(unit,destination_fd=destination_fd,guard=issuer,produce=lambda n:produce(
        unit,n,root_path=source_root,root_fd=source_fd,pins=pins,
        verify_index=verify_index,consume=adapters.consume_context))
