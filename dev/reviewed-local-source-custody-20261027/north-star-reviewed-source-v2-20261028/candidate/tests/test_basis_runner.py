import copy,gzip,hashlib,json,tempfile,unittest,sys,sqlite3,fcntl
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'candidate/scripts'));sys.path.insert(0,str(ROOT/'candidate/tests'))
import run_north_star_basis_restoration as R
from test_basis_restoration import inputs

def prepare(temp,records=None,packets=None):
    root=Path(temp);native=root/'native';bulk=root/'bulk';out=root/'output';native.mkdir();bulk.mkdir()
    record,entry,packet=inputs();entry['rawSourcePayloadPublished']=False
    records=[record] if records is None else records;packets=[packet] if packets is None else packets
    nf=[]
    for source,rs in [('off',records),('usda-files',[])]:
        key='records/'+source+'/000.jsonl.gz';p=native/key;p.parent.mkdir(parents=True)
        b=gzip.compress((json.dumps(['fixture',rs])+'\n').encode(),mtime=0);p.write_bytes(b);nf.append({'key':key,'bytes':len(b),'sha256':R.sha_bytes(b)})
    off=dict(entry,records=len(records));usda=dict(entry,sourceId='usda-files',records=0)
    nm={'files':nf,'sources':{'off':off,'usda-files':usda},'status':'curated-release-ready','privateProviderData':False};nb=R.encoded(nm);(native/'manifest.json').write_bytes(nb)
    bf=[]
    for selected,key in [('common-data.schema.json','schema.json'),('common-data-contract.json','contract.json')]:
        b=(ROOT/'selected/corpus'/selected).read_bytes();(bulk/key).write_bytes(b);bf.append({'key':key,'bytes':len(b),'sha256':R.sha_bytes(b)})
    b=gzip.compress(('\n'.join(json.dumps(p) for p in packets)+'\n').encode(),mtime=0);(bulk/'part.jsonl.gz').write_bytes(b)
    bf.append({'key':'part.jsonl.gz','bytes':len(b),'sha256':R.sha_bytes(b),'packets':len(packets)})
    bm={'files':bf,'counts':{'packets':len(packets),'resources':sum(len(p['resources']) for p in packets)}};bb=R.encoded(bm);(bulk/'manifest.json').write_bytes(bb)
    return native,bulk,out,{'native_sha':R.sha_bytes(nb),'bulk_sha':R.sha_bytes(bb),'schema_sha':R.sha_file(bulk/'schema.json'),'contract_sha':R.sha_file(bulk/'contract.json'),'budget':100*1024**2,'reserve':0,'seconds':60}

class BasisRunnerTests(unittest.TestCase):
    def test_both_phases_exact_join_provenance_and_idempotent_resume(self):
        with tempfile.TemporaryDirectory() as t:
            n,b,o,kw=prepare(t);i=R.run('index',n,b,o,**kw);self.assertTrue(i['complete']);self.assertEqual(i['counts']['nativeProfiles'],1)
            db=sqlite3.connect(o/'native-index.sqlite');self.assertEqual(db.execute('PRAGMA page_size').fetchone()[0],16384);db.close()
            m=R.run('restore',n,b,o,**kw);self.assertTrue(m['complete']);q=m['consumerProof']['queries']
            self.assertEqual(q['normalizedResourceLocators']['count'],1);self.assertEqual(q['restoredNutrientBasisTargets']['count'],2);self.assertEqual(q['nativeProfilesWithoutNormalizedMatch']['count'],0)
            side=json.loads(gzip.decompress((o/m['files'][0]['key']).read_bytes()))
            self.assertEqual(side['inputNativeSelection']['assetRecordOrdinal'],0);self.assertEqual(side['inputNormalizedSelection']['packetOrdinal'],0)
            self.assertEqual(side['inputNativeSelection']['manifestByteSha256'],kw['native_sha']);self.assertFalse(side['publicationEligible'])
            before=(o/'manifest.json').read_bytes();self.assertEqual(R.run('restore',n,b,o,**kw),m);self.assertEqual((o/'manifest.json').read_bytes(),before)
    def test_source_index_has_no_raw_body(self):
        with tempfile.TemporaryDirectory() as t:
            n,b,o,kw=prepare(t);R.run('index',n,b,o,**kw);db=sqlite3.connect(o/'native-index.sqlite');blob=db.execute('SELECT payload FROM projections').fetchone()[0];db.close()
            import zlib
            p=json.loads(zlib.decompress(blob));self.assertNotIn('data',p);self.assertNotIn('provenance',p);self.assertIn('expectedQuantitySha256',p['metrics']['sodium'])
    def test_changed_quantity_fails_without_rewriting_source(self):
        r,e,p=inputs();next(a for a in p['assertions'] if a['propertyId'].endswith(':nutrientObservation'))['value']['value']=99
        with tempfile.TemporaryDirectory() as t:
            n,b,o,kw=prepare(t,packets=[p]);source=(b/'part.jsonl.gz').read_bytes();R.run('index',n,b,o,**kw)
            with self.assertRaisesRegex(ValueError,'quantity fidelity mismatch'):R.run('restore',n,b,o,**kw)
            self.assertEqual((b/'part.jsonl.gz').read_bytes(),source);self.assertFalse((o/'manifest.json').exists())
    def test_duplicate_native_identity_rejected(self):
        r,_,_=inputs()
        with tempfile.TemporaryDirectory() as t:
            n,b,o,kw=prepare(t,records=[r,copy.deepcopy(r)])
            with self.assertRaises(sqlite3.IntegrityError):R.run('index',n,b,o,**kw)
            self.assertFalse((o/'native-index-manifest.json').exists())
    def test_native_source_without_normalized_target_is_explicit(self):
        _,_,p=inputs();p['resources'][0]['id']='urn:test:unmatched'
        with tempfile.TemporaryDirectory() as t:
            n,b,o,kw=prepare(t,packets=[p]);R.run('index',n,b,o,**kw);m=R.run('restore',n,b,o,**kw)
            self.assertEqual(m['consumerProof']['queries']['nativeProfilesWithoutNormalizedMatch']['count'],1)
            self.assertFalse(m['allSelectedNativeProfilesMatched']);self.assertEqual(m['sourceCoverage']['nativeProfilesUnmatched'],1)
            self.assertNotIn('all-selected-native-projections-joined',m['status'])
    def test_deadline_resume_same_selection(self):
        with tempfile.TemporaryDirectory() as t:
            n,b,o,kw=prepare(t);short=dict(kw,seconds=1);m=R.run('index',n,b,o,**short);self.assertFalse(m['complete']);self.assertTrue(R.run('index',n,b,o,**kw)['complete'])
    def test_wrong_manifest_pin_leaves_no_output(self):
        with tempfile.TemporaryDirectory() as t:
            n,b,o,kw=prepare(t);kw['native_sha']='0'*64
            with self.assertRaisesRegex(ValueError,'SourceManifestPinMismatch'):R.run('index',n,b,o,**kw)
            self.assertFalse(o.exists())
    def test_tampered_completed_native_index_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            n,b,o,kw=prepare(t);R.run('index',n,b,o,**kw)
            with (o/'native-index.sqlite').open('ab') as f:f.write(b'changed')
            with self.assertRaisesRegex(ValueError,'NativeIndexBindingMismatch'):R.run('restore',n,b,o,**kw)
    def test_native_asset_digest_mismatch_not_committed(self):
        with tempfile.TemporaryDirectory() as t:
            n,b,o,kw=prepare(t);(n/'records/off/000.jsonl.gz').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'InputAssetDigestMismatch'):R.run('index',n,b,o,**kw)
            db=sqlite3.connect(o/'native-index.sqlite');self.assertEqual(db.execute('SELECT count(*) FROM imported').fetchone()[0],0);db.close()
    def test_interrupted_native_transaction_rolls_back_partial_asset(self):
        from unittest.mock import patch
        r,_,_=inputs();r2=copy.deepcopy(r);r2['id']='synthetic:profile:2';r2['provenance']['recordId']='second-record'
        with tempfile.TemporaryDirectory() as t:
            n,b,o,kw=prepare(t,records=[r,r2]);original=R.native_projection
            def interrupted(record,source,entry):
                if record['id']==r2['id']:raise R.TimeSliceComplete('fixture-deadline')
                return original(record,source,entry)
            with patch.object(R,'native_projection',side_effect=interrupted):self.assertFalse(R.run('index',n,b,o,**kw)['complete'])
            db=sqlite3.connect(o/'native-index.sqlite');self.assertEqual(db.execute('SELECT count(*) FROM projections').fetchone()[0],0);db.close()
            self.assertEqual(R.run('index',n,b,o,**kw)['counts']['nativeProfiles'],2)
    def test_phase_budget_is_enforced_before_asset_processing(self):
        with tempfile.TemporaryDirectory() as t:
            n,b,o,kw=prepare(t);kw['budget']=1
            with self.assertRaisesRegex(ValueError,'OwnedOutputBudgetExceeded'):R.run('index',n,b,o,**kw)
            self.assertFalse((o/'native-index-manifest.json').exists())
    def test_single_writer_lock(self):
        with tempfile.TemporaryDirectory() as t:
            n,b,o,kw=prepare(t);o.mkdir()
            with (o/'.writer.lock').open('a+b') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                with self.assertRaisesRegex(ValueError,'OutputWriterAlreadyActive'):R.run('index',n,b,o,**kw)

if __name__=='__main__':unittest.main()
