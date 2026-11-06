import copy,gzip,hashlib,importlib.util,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(ROOT/'tests'))
import derive_north_star_bulk as M
from test_north_star_derivations import fixture,CONTRACT

def sha(b):return hashlib.sha256(b).hexdigest()
def package(root,packets):
    root.mkdir()
    schema=json.loads((ROOT.parent/'selected/corpus/common-data.schema.json').read_text())
    files=[]
    for name,value in [('schema.json',schema),('contract.json',CONTRACT)]:
        b=json.dumps(value).encode();(root/name).write_bytes(b);files.append({'key':name,'bytes':len(b),'sha256':sha(b)})
    counts={k:0 for k in ['packets','resources','assertions','relations','translations']}
    for n,packet in enumerate(packets):
        b=gzip.compress((json.dumps(packet)+'\n').encode(),mtime=0);key=f'part-{n}.jsonl.gz';(root/key).write_bytes(b)
        files.append({'key':key,'bytes':len(b),'sha256':sha(b),'packets':1})
        counts['packets']+=1
        for k in counts:
            if k!='packets':counts[k]+=len(packet[k])
    m={'releaseId':'fixture','files':files,'counts':counts};b=json.dumps(m).encode();(root/'manifest.json').write_bytes(b)
    return sha(b),files[0]['sha256'],files[1]['sha256']

def split_pair():
    p=fixture();product=copy.deepcopy(p);profile=copy.deepcopy(p)
    product['resources']=[p['resources'][0]];product['assertions']=[]
    base=copy.deepcopy(p['assertions'][0]);base.update(id='urn:test:identifier',subjectId='urn:test:product',propertyId=M.PROP+'sourceIdentifier',sourcePath='data.identifiers.0')
    base['value']={'kind':'structure','fields':{'system':{'kind':'identifier','value':'barcode'},'value':{'kind':'identifier','value':'000001'}}}
    product['assertions']=[base]
    profile['resources']=[p['resources'][1]];profile['relations']=[]
    return product,profile

class BulkTests(unittest.TestCase):
    def run_package(self,temp,packets,**kwargs):
        src=Path(temp)/'source';out=Path(temp)/'output';pins=package(src,packets)
        result=M.run(src,out,*pins[:1],workers=1,seconds=60,reserve=0,output_budget=4*1024**3,schema_sha=pins[1],contract_sha=pins[2],**kwargs)
        return src,out,pins,result
    def test_full_cross_packet_join_preserves_leading_zero_and_resume(self):
        with tempfile.TemporaryDirectory() as t:
            src,out,pins,result=self.run_package(t,split_pair())
            self.assertTrue(result['complete']);q=result['consumerIndex']['queries']
            self.assertEqual(q['identifierProductProfileNutrientContextJoins']['count'],1)
            import sqlite3
            db=sqlite3.connect(out/'consumer-index.sqlite');self.assertEqual(db.execute('SELECT lexical FROM identifiers').fetchone()[0],'000001');db.close()
            before=(out/'manifest.json').read_bytes()
            repeated=M.run(src,out,pins[0],workers=1,seconds=60,reserve=0,output_budget=4*1024**3,schema_sha=pins[1],contract_sha=pins[2])
            self.assertEqual(repeated,result);self.assertEqual((out/'manifest.json').read_bytes(),before)
    def test_wrong_target_type_remains_unresolved(self):
        p,q=split_pair();q['resources'][0]['type']=M.TYPE+'FoodIngredient'
        with tempfile.TemporaryDirectory() as t:
            _,_,_,r=self.run_package(t,[p,q]);self.assertEqual(r['consumerIndex']['queries']['productProfileEdgesResolved']['count'],0)
    def test_cross_scope_target_not_resolved(self):
        p,q=split_pair();scope={'visibility':'public','reuseScope':'Different licensed scope'}
        for bucket in ['resources','assertions','citations']:
            for row in q[bucket]:row['scope']=scope
        with tempfile.TemporaryDirectory() as t:
            _,_,_,r=self.run_package(t,[p,q]);self.assertEqual(r['consumerIndex']['queries']['productProfileEdgesResolved']['count'],0)
    def test_superseded_identifier_excluded(self):
        p,q=split_pair();p['assertions'][0]['status']='superseded'
        with tempfile.TemporaryDirectory() as t:
            _,_,_,r=self.run_package(t,[p,q]);self.assertEqual(r['consumerIndex']['queries']['uniqueSourceScopedProductKeys']['count'],0)
    def test_no_empty_derived_packets_emitted(self):
        p,q=split_pair();p['relations']=[]
        with tempfile.TemporaryDirectory() as t:
            _,out,_,r=self.run_package(t,[p]);self.assertEqual(r['counts'].get('sidecarPackets',0),0)
            self.assertEqual(gzip.decompress((out/'shards/000000/derivations.jsonl.gz').read_bytes()),b'')
    def test_changed_output_rejected_before_reuse(self):
        with tempfile.TemporaryDirectory() as t:
            src,out,pins,r=self.run_package(t,split_pair())
            (out/'shards/000000/query-index.jsonl.gz').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'ShardOutputDigestMismatch'):
                M.run(src,out,pins[0],workers=1,seconds=60,reserve=0,schema_sha=pins[1],contract_sha=pins[2])
    def test_wrong_manifest_pin_no_output(self):
        with tempfile.TemporaryDirectory() as t:
            src=Path(t)/'source';out=Path(t)/'output';pins=package(src,split_pair())
            with self.assertRaisesRegex(ValueError,'ManifestPinMismatch'):M.run(src,out,'0'*64)
            self.assertFalse(out.exists())
    def test_private_input_does_not_commit_derivative(self):
        p,q=split_pair();scope={'visibility':'private','ownerId':'fixture-owner'}
        for bucket in ['resources','assertions','relations','citations']:
            for row in p[bucket]:row['scope']=scope
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaisesRegex(ValueError,'NonPublicInputExcluded'):self.run_package(t,[p])
            self.assertFalse((Path(t)/'output/shards/000000').exists())
    def test_unknown_release_identifier_excluded_and_edge_unresolved(self):
        p,q=split_pair();p['citations'][0].pop('revisionId');q['citations'][0].pop('revisionId')
        with tempfile.TemporaryDirectory() as t:
            _,_,_,r=self.run_package(t,[p,q]);queries=r['consumerIndex']['queries']
            self.assertEqual(queries['sourceScopedProductIdentifierKeys']['count'],0)
            self.assertEqual(queries['productProfileEdgesResolved']['count'],0)
    def test_ambiguous_lexical_key_not_counted_as_unique(self):
        p,q=split_pair();p2=copy.deepcopy(p)
        p2['resources'][0]['id']='urn:test:product2'
        p2['assertions'][0]['id']='urn:test:identifier2';p2['assertions'][0]['subjectId']='urn:test:product2'
        p2['relations']=[]
        with tempfile.TemporaryDirectory() as t:
            _,_,_,r=self.run_package(t,[p,p2,q]);queries=r['consumerIndex']['queries']
            self.assertEqual(queries['sourceScopedProductIdentifierKeys']['count'],1)
            self.assertEqual(queries['ambiguousProductKeysNotMerged']['count'],1)
            self.assertEqual(queries['identifierProductProfileJoins']['count'],0)
    def test_time_slice_checkpoint_resumes_same_selection(self):
        with tempfile.TemporaryDirectory() as t:
            src=Path(t)/'source';out=Path(t)/'output';pins=package(src,split_pair())
            first=M.run(src,out,pins[0],workers=1,seconds=1,reserve=0,output_budget=4*1024**3,schema_sha=pins[1],contract_sha=pins[2])
            self.assertFalse(first['complete']);self.assertEqual(first['completedAssets'],0)
            resumed=M.run(src,out,pins[0],workers=1,seconds=60,reserve=0,output_budget=4*1024**3,schema_sha=pins[1],contract_sha=pins[2])
            self.assertTrue(resumed['complete'])
    def test_output_single_writer_lock_is_nonblocking(self):
        import fcntl
        with tempfile.TemporaryDirectory() as t:
            src=Path(t)/'source';out=Path(t)/'output';pins=package(src,split_pair());out.mkdir()
            with (out/'.writer.lock').open('a+b') as lock:
                fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
                with self.assertRaisesRegex(ValueError,'OutputWriterAlreadyActive'):M.run(src,out,pins[0])
    def test_atomic_json_syncs_directory(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'receipt.json'
            with patch.object(M,'fsync_dir',wraps=M.fsync_dir) as sync:
                M.atomic_json(p,{'complete':True});sync.assert_called_once_with(p.parent)
    def test_worker_deadline_leaves_no_committed_or_temporary_shard(self):
        with tempfile.TemporaryDirectory() as t:
            src=Path(t)/'source';out=Path(t)/'output';pins=package(src,split_pair())
            m=json.loads((src/'manifest.json').read_text());entry=m['files'][2]
            schema=json.loads((src/'schema.json').read_text());selection={'manifestByteSha256':pins[0]}
            with self.assertRaises(M.TimeSliceComplete):M.derive_shard((src,out,entry,0,selection,CONTRACT,schema,0))
            self.assertEqual(list((out/'shards').iterdir()),[])
    def test_live_budget_counts_scratch_and_uncommitted_files(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'progress.json').write_bytes(b'abc')
            (root/'sqlite-temp').mkdir();(root/'sqlite-temp/scratch').write_bytes(b'1234567')
            (root/'shards/000000.tmp-own').mkdir(parents=True);(root/'shards/000000.tmp-own/data').write_bytes(b'12345')
            self.assertEqual(M.live_storage(root,11),26)
    def test_post_rename_sync_failure_preserves_committed_shard(self):
        import time
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as t:
            src=Path(t)/'source';out=Path(t)/'output';pins=package(src,split_pair())
            m=json.loads((src/'manifest.json').read_text());entry=m['files'][2]
            schema=json.loads((src/'schema.json').read_text());selection={'manifestByteSha256':pins[0]}
            real=M.fsync_dir
            def fail_parent(path):
                if path==out/'shards':raise OSError('fixture-sync-failure')
                return real(path)
            with patch.object(M,'fsync_dir',side_effect=fail_parent):
                with self.assertRaisesRegex(OSError,'fixture-sync-failure'):
                    M.derive_shard((src,out,entry,0,selection,CONTRACT,schema,time.monotonic()+30))
            self.assertIsNotNone(M.existing_shard(out/'shards/000000',selection))
    def test_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaisesRegex(ValueError,'UnsafeAssetKey'):M.asset_path(Path(t),'../input')

if __name__=='__main__':unittest.main()
