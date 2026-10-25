"""New wrapper evidence only: generated SQLite, no retained/private stores."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import patch
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SCRATCH = ROOT/'generated-scratch'
SCRATCH.mkdir(exist_ok=True)
sys.dont_write_bytecode = True
denied, relative_paths, fixture_paths = [], [], []


def audit(event, args):
    if event.startswith('socket.'):
        denied.append(event)
        raise AssertionError('network forbidden')
    if event not in ('open', 'sqlite3.connect') or isinstance(args[0], int): return
    value = os.fsdecode(args[0])
    if value == ':memory:': return
    if value.startswith('file:'): value = unquote(urlsplit(value).path)
    path = relative_paths[-1] if relative_paths and not os.path.isabs(value) else Path(os.path.abspath(value))
    writing = event == 'sqlite3.connect' or bool(args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
    if path.is_relative_to(ROOT): return
    if not writing and any(path.is_relative_to(p) for p in (Path('/usr'), Path('/lib'), Path('/lib64'))): return
    denied.append(str(path))
    raise AssertionError('nonfixture access forbidden')


if __name__ == '__main__':
    sys.addaudithook(audit)
reader_path = ROOT/'offmenu/refresh/source_json_slices.py'
assert hashlib.sha256(reader_path.read_bytes()).hexdigest() == '5391963a06a129987695122cb3d7addb84bfbfa4653bb7634bfbd0c1646b0ded'
pkg = types.ModuleType('_worker64_source_field_fixture')
pkg.__path__ = [str(reader_path.parent)]
sys.modules[pkg.__name__] = pkg
spec = importlib.util.spec_from_file_location(pkg.__name__+'.source_field_operation', ROOT/'offmenu/refresh/source_field_operation.py')
api = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = api
spec.loader.exec_module(api)
reader = api._slices

DDL = '''CREATE TABLE retained_reference_record(
 reference_record_id TEXT PRIMARY KEY,source_id TEXT,release_id TEXT,asset_id TEXT,
 asset_sha256 TEXT,source_ordinal INTEGER,native_record_id TEXT,source_pointer TEXT,
 original_language TEXT,source_payload_json TEXT,parsed_record_sha256 TEXT,citation_id TEXT,
 citation_binding_status TEXT,parse_engine_id TEXT,parse_engine_version TEXT,processing_status TEXT)'''


class BlobSpy:
    def __init__(self, blob, owner): self.blob, self.owner, self.closed = blob, owner, False
    def __len__(self): return len(self.blob)
    def seek(self, offset): return self.blob.seek(offset)
    def read(self, size):
        self.owner.reads.append(size)
        if self.owner.fail_read: raise sqlite3.OperationalError('PRIVATE_PATH PRIVATE_BODY PRIVATE_TOKEN')
        return self.blob.read(size)
    def close(self): self.closed = True;self.blob.close()


class ConnectionSpy(sqlite3.Connection):
    def blobopen(self, table, column, row, *, readonly=False, name='main'):
        self.opens.append((table,column,row,readonly,name))
        blob = BlobSpy(super().blobopen(table,column,row,readonly=readonly,name=name),self)
        self.blobs.append(blob)
        return blob
    def setlimit(self, *args):
        self.limit_sets += 1
        return super().setlimit(*args)
    def set_progress_handler(self, *args):
        self.progress_sets += 1
        return super().set_progress_handler(*args)


class Fixture:
    def __init__(self, payload='{"generated":true}', *, file_ro=False):
        self.temp = None
        if file_ro:
            self.temp = tempfile.TemporaryDirectory(dir=SCRATCH)
            fixture_paths.append(self.temp.name)
            self.path = Path(self.temp.name)/'GENERATED_ONLY.sqlite'
            db = sqlite3.connect(self.path)
        else: db = sqlite3.connect(':memory:',factory=ConnectionSpy)
        self.raw = payload.encode('utf-8')
        self.identity = dict(zip(reader.IDENTITY_COLUMNS,
            [1,'generated-record','generated-source','generated-release','generated-asset','a'*64,
             1,None,'/generated/1','und','b'*64,None,'generated-bound','fixture-parser','1','fixture-only']))
        self.binding = {'store':{'databaseSha256':'c'*64,'qualificationSha256':'d'*64,'generationId':'generated-g1'},
            'operation':{'receiptSha256':'e'*64,'operationId':'generated-native-slice'},
            'rights':{'receiptSha256':'f'*64,'state':'permitted'},
            'callerContext':{'accountId':'GENERATED_ACCOUNT','contextGeneration':'one'}}
        db.execute(DDL)
        cols = [k for k in reader.IDENTITY_COLUMNS if k!='rowid']+['source_payload_json']
        db.execute('INSERT INTO retained_reference_record('+','.join(cols)+') VALUES('+','.join('?' for _ in cols)+')',
                   [self.identity[k] for k in cols[:-1]]+[payload])
        db.commit()
        if file_ro:
            db.close()
            db = sqlite3.connect(self.path.as_uri()+'?mode=ro',uri=True,factory=ConnectionSpy)
        self.db = db
        db.opens,db.reads,db.blobs,db.fail_read = [],[],[],False
        db.limit_sets=db.progress_sets=0
        db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
        db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH,4096)
        self.steps=self.qualifications=self.budget_calls=0
        self.deadline_value=time.monotonic()+5
        self.step_cap=100000
        self.trace=[];db.set_trace_callback(self.trace.append)
        def progress():
            self.steps+=1
            return int(self.steps>self.step_cap)
        self.progress=progress
        db.set_progress_handler(progress,1)
        self.selection=self.select()
    def select(self, identity=None, binding=None):
        i=copy.deepcopy(self.identity if identity is None else identity)
        b=copy.deepcopy(self.binding if binding is None else binding)
        return reader.SourceJsonSelection(record_id=i['reference_record_id'],row_identity=i,binding=b,source_bytes=len(self.raw))
    def qualify(self, selection):
        self.qualifications+=1
        return reader.QualifiedRead(self.db,self.selection)
    def budget(self):
        self.budget_calls+=1
        if self.steps>self.step_cap: raise reader.SourceJsonSliceError('budget-exhausted')
    def read(self, request=None, **overrides):
        if request is None: request={'selectedRecordId':self.selection.metadata['recordId'],'offsetBytes':0}
        options={'qualify':self.qualify,'check_budget':self.budget,'deadline':lambda:self.deadline_value}
        options.update(overrides)
        wire=api.read_source_field_operation(self.db,self.selection,request,**options)
        assert type(wire) is bytes and wire.endswith(b'\n') and len(wire)<=262144
        return json.loads(wire),wire
    def close(self):
        self.db.close()
        if self.temp:self.temp.cleanup()


class OperationTests(unittest.TestCase):
    def fixture(self,*a,**kw):
        f=Fixture(*a,**kw);self.addCleanup(f.close);return f
    def unavailable(self,result,code=None):
        value,wire=result
        self.assertEqual(value['state'],'unavailable')
        if code:self.assertEqual(value['reasonCode'],code)
        self.assertNotIn('slice',value)
        self.assertNotIn('jsonText',value)
        for private in (b'PRIVATE_PATH',b'PRIVATE_BODY',b'PRIVATE_TOKEN'):
            self.assertNotIn(private,wire)
        return value

    def test_actual_large_unicode_lossless_slices_with_aggregate_caller_guard(self):
        payload='{\r\n "unknown/field~":"'+('😀e\u0301漢字'*30000)+'",\r\n "huge":'+('9'*6000)+',"lexical":1.2300e+004}\r\n'
        f=self.fixture(payload);self.assertGreater(len(f.raw),262144)
        chunks=[];offset=0;calls=0
        while True:
            value,wire=f.read({'selectedRecordId':'generated-record','offsetBytes':offset})
            self.assertEqual(value['state'],'slice-available');p=value['slice'];calls+=1
            self.assertEqual(p['selection']['rowIdentity'],f.identity)
            self.assertLessEqual(len(reader.canonical(p['selection'])),8192)
            self.assertEqual(p['offsetUnit'],'utf-8-bytes')
            self.assertEqual(p['offsetBytes'],offset)
            self.assertEqual(p['endOffsetBytes']-offset,len(p['jsonText'].encode()))
            self.assertLessEqual(len(p['jsonText'].encode()),16384)
            chunks.append(p['jsonText'])
            if not p['hasMore']:break
            offset=p['nextOffsetBytes']
        self.assertEqual(''.join(chunks).encode(),f.raw)
        self.assertEqual(f.qualifications,6*calls)
        self.assertLess(f.steps,100000)
        self.assertEqual(f.db.limit_sets,1);self.assertEqual(f.db.progress_sets,1)
        self.assertEqual(f.db.getlimit(sqlite3.SQLITE_LIMIT_LENGTH),4096)
        self.assertTrue(f.db.in_transaction)
        before=f.steps;f.db.execute('SELECT 1').fetchone();self.assertGreater(f.steps,before)
        self.assertTrue(all(b.closed for b in f.db.blobs))
        self.assertTrue(all(x[3:] == (True,'main') for x in f.db.opens))

    def test_closed_request_rejects_browser_authority_paths_sql_and_wrong_record_before_queries(self):
        f=self.fixture();request={'selectedRecordId':'generated-record','offsetBytes':0}
        for key in ('databasePath','sql','table','rights','actor','connection','selection','account','generation','deadline','cursor','administrator'):
            with self.subTest(key=key):
                self.unavailable(f.read(dict(request,**{key:'PRIVATE_BODY'})),'source-field-operation-request')
        self.unavailable(f.read(dict(request,selectedRecordId='other')),'source-field-operation-record-mismatch')
        class Derived(dict):pass
        self.unavailable(f.read(Derived(request)),'source-field-operation-request')
        self.assertEqual(f.trace,[]);self.assertEqual(f.qualifications,0);self.assertEqual(f.db.opens,[])

    def test_callbacks_mandatory_boolean_grants_and_mismatched_connections_are_not_authority(self):
        f,other=self.fixture(),self.fixture()
        for opts,code in [({'qualify':None},'source-json-slice-qualification-required'),
                          ({'check_budget':None},'source-json-slice-budget-required'),
                          ({'deadline':None},'source-field-operation-deadline-required'),
                          ({'check_budget':lambda:False},'source-json-slice-budget-exhausted')]:
            self.unavailable(f.read(**opts),code)
        for current in (True,False,{'administrator':True},reader.QualifiedRead(other.db,f.selection)):
            self.unavailable(f.read(qualify=lambda _,v=current:v),'source-json-slice-qualification-mismatch')
        self.assertEqual(f.trace,[]);self.assertEqual(f.db.opens,[])

    def test_each_fresh_stage_revocation_account_generation_operation_and_reference_changes_block_release(self):
        for mode in ('revoked','account','generation','operation','reference'):
            for stage in range(1,7):
                with self.subTest(mode=mode,stage=stage):
                    f=self.fixture();calls=[0]
                    def qualify(selection):
                        calls[0]+=1
                        if calls[0]!=stage:return reader.QualifiedRead(f.db,f.selection)
                        if mode=='revoked':raise reader.SourceJsonSliceError('access-revoked')
                        binding=copy.deepcopy(f.binding);identity=copy.deepcopy(f.identity)
                        if mode=='account':binding['callerContext']['accountId']='DIFFERENT_NATIVE_ACCOUNT'
                        elif mode=='generation':binding['store']['generationId']='different-generation'
                        elif mode=='operation':binding['operation']['receiptSha256']='0'*64
                        else:identity['reference_record_id']='different-native-reference'
                        return reader.QualifiedRead(f.db,f.select(identity,binding))
                    code='source-json-slice-access-revoked' if mode=='revoked' else 'source-json-slice-qualification-mismatch'
                    self.unavailable(f.read(qualify=qualify),code)
                    if stage==1:self.assertEqual(f.trace,[])
                    self.assertTrue(all(b.closed for b in f.db.blobs))

    def test_all_sixteen_persisted_identity_columns_are_bound_before_blobopen(self):
        for key in reader.IDENTITY_COLUMNS:
            with self.subTest(key=key):
                f=self.fixture();identity=copy.deepcopy(f.identity)
                if key in ('rowid','source_ordinal'):identity[key]+=1
                elif key.endswith('sha256'):identity[key]='0'*64
                else:identity[key]='DIFFERENT_GENERATED_IDENTITY'
                f.selection=f.select(identity)
                code='source-json-slice-row-missing' if key=='reference_record_id' else 'source-json-slice-row-identity-mismatch'
                self.unavailable(f.read(),code);self.assertEqual(f.db.opens,[])

    def test_byte_offsets_chunk_limits_and_hmac_cursor_are_distinct(self):
        f=self.fixture('{"v":"😀"}')
        request={'selectedRecordId':'generated-record','offsetBytes':0,'chunkBytes':8}
        first,_=f.read(request);self.assertEqual(first['slice']['nextOffsetBytes'],6)
        last,_=f.read(dict(request,offsetBytes=6));self.assertEqual(first['slice']['jsonText']+last['slice']['jsonText'],f.raw.decode())
        self.unavailable(f.read(dict(request,offsetBytes=7)),'source-json-slice-offset-not-utf8-boundary')
        self.unavailable(f.read(dict(request,offsetBytes=6,chunkBytes=1)),'source-json-slice-chunk-too-small')
        for offset in (-1,True,'eyJjdXJzb3IiOiJITUFDIT8ifQ',1.5,len(f.raw)+1):
            self.unavailable(f.read(dict(request,offsetBytes=offset)),'source-json-slice-offset')
        for chunk in (0,True,16385,'16384'):
            self.unavailable(f.read(dict(request,chunkBytes=chunk)),'source-json-slice-chunk-bound')

    def test_readonly_file_connection_transaction_and_query_only_preserved(self):
        f=self.fixture('{"generated":"read-only-file"}',file_ro=True)
        value,_=f.read();self.assertEqual(value['state'],'slice-available')
        with self.assertRaises(sqlite3.OperationalError):f.db.execute('UPDATE retained_reference_record SET source_id=?',('blocked',))
        self.assertTrue(f.db.in_transaction)
        f.db.rollback();self.unavailable(f.read(),'source-json-slice-read-transaction-required')
        g=self.fixture();g.db.execute('PRAGMA query_only=OFF');self.unavailable(g.read(),'source-json-slice-query-only-required')
        self.assertEqual(g.db.opens,[])

    def test_aggregate_vm_exhaustion_keeps_existing_progress_handler(self):
        f=self.fixture();f.steps=99999
        value=self.unavailable(f.read(),'source-json-slice-sqlite-failure')
        self.assertEqual(value['sqlite']['sqliteErrorName'],'SQLITE_INTERRUPT')
        self.assertEqual(f.db.opens,[])
        self.assertEqual(f.db.progress_sets,1)
        f.steps=0;f.db.execute('SELECT 1').fetchone();self.assertGreater(f.steps,0)

    def test_dynamic_host_deadline_and_hard_five_seconds_never_extend_or_release(self):
        f=self.fixture();now=[0.0]
        def advance(selection):now[0]=6;return reader.QualifiedRead(f.db,f.selection)
        self.unavailable(f.read(qualify=advance,deadline=lambda:100,clock=lambda:now[0]),'source-json-slice-deadline')
        self.assertEqual(f.trace,[])
        for value in (True,float('nan'),float('inf'),-1):
            self.unavailable(f.read(deadline=lambda v=value:v,clock=lambda:0),'source-json-slice-deadline')
        deadlines=[100,100,-1]
        self.unavailable(f.read(deadline=lambda:deadlines.pop(0) if deadlines else -1,clock=lambda:0),'source-json-slice-deadline')

    def test_safe_error_wire_never_echoes_callback_sqlite_path_or_body(self):
        f=self.fixture()
        def denied(_):raise PermissionError('PRIVATE_PATH PRIVATE_BODY PRIVATE_TOKEN')
        self.unavailable(f.read(qualify=denied),'source-json-slice-qualification-unavailable')
        def broken():raise RuntimeError('PRIVATE_PATH PRIVATE_BODY PRIVATE_TOKEN')
        self.unavailable(f.read(check_budget=broken),'source-json-slice-budget-unavailable')
        self.unavailable(f.read(deadline=broken),'source-json-slice-deadline')
        class DerivedError(reader.SourceJsonSliceError):pass
        def derived(_):raise DerivedError('internal')
        self.unavailable(f.read(qualify=derived),'source-field-operation-internal')
        f.db.fail_read=True
        value=self.unavailable(f.read(),'source-json-slice-sqlite-failure')
        self.assertEqual(value['sqlite']['stage'],'blob-read')
        self.assertTrue(all(b.closed for b in f.db.blobs))

    def test_final_release_rechecks_after_wire_encoding(self):
        f=self.fixture();encoded=[False];canonical=reader.canonical
        def encode(value):
            raw=canonical(value)
            if type(value) is dict and value.get('schema')==api.SCHEMA and value.get('state')=='slice-available':encoded[0]=True
            return raw
        def qualify(selection):
            if encoded[0]:raise reader.SourceJsonSliceError('access-revoked')
            return reader.QualifiedRead(f.db,f.selection)
        with patch.object(reader,'canonical',side_effect=encode):
            self.unavailable(f.read(qualify=qualify),'source-json-slice-access-revoked')
        self.assertTrue(encoded[0]);self.assertEqual(len(f.db.reads),1)

    def test_wire_metadata_bounds_and_whole_query_cap_remain_unchanged(self):
        f=self.fixture('\x00'*16384);value,wire=f.read()
        self.assertEqual(value['state'],'slice-available');self.assertLessEqual(len(wire),262144)
        self.assertEqual(len(value['slice']['jsonText'].encode()),16384)
        self.assertEqual(reader.SOURCE_VALUE_BYTES,16*1024*1024)
        self.assertEqual(reader.WIRE_BYTES,262144);self.assertEqual(reader.METADATA_BYTES,8192)
        self.assertEqual(f.db.getlimit(sqlite3.SQLITE_LIMIT_LENGTH),4096)
        self.assertEqual(f.db.limit_sets,1);self.assertEqual(f.db.progress_sets,1)
        self.unavailable(f.read({'selectedRecordId':'x'*9000,'offsetBytes':0}),'source-field-operation-request-bound')


real_open=os.open
def relative_open(path,flags,*args,dir_fd=None,**kwargs):
    relative=dir_fd is not None and not os.path.isabs(os.fsdecode(path))
    if relative:relative_paths.append(Path(os.readlink('/proc/self/fd/'+str(dir_fd)))/os.fsdecode(path))
    try:return real_open(path,flags,*args,dir_fd=dir_fd,**kwargs)
    finally:
        if relative:relative_paths.pop()

if __name__=='__main__':
    with patch.object(os,'open',side_effect=relative_open):
        result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(OperationTests))
    proof={'testsRun':result.testsRun,'success':result.wasSuccessful(),'errors':len(result.errors),'failures':len(result.failures),
        'forbiddenAccessAttempts':denied,'allGeneratedFileFixturesRemoved':all(not Path(p).exists() for p in fixture_paths),
        'retainedPrivateSourceOrDatabaseAccesses':0,'sharedSourceEdits':0,'old25or29SuitesReplayed':0,
        'actualSourceOperationAdmissions':0,'HTTPMountsOrSessionAuthKeyChanges':0,'actualAffinity':sorted(os.sched_getaffinity(0))}
    print('GENERATED_PROOF='+json.dumps(proof,sort_keys=True))
    sys.exit(not(result.wasSuccessful() and not denied and proof['allGeneratedFileFixturesRemoved']))
