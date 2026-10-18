import copy,hashlib,importlib.util,io,json,os,struct,tempfile,time,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('retained_preparation_diagnostic',ROOT/'scripts/diagnose-retained-preparation.py')
d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)

def deadline():return time.monotonic()+10

def zipped(items,compression=zipfile.ZIP_STORED):
 stream=io.BytesIO()
 with zipfile.ZipFile(stream,'w',compression=compression) as z:
  for name,value in items:z.writestr(name,value)
 return stream.getvalue()

def relations(items):
 return ('<Relationships>'+''.join('<Relationship '+ ' '.join(k+'="'+v+'"' for k,v in x.items())+'/>' for x in items)+'</Relationships>').encode()

def xlsx(items):
 return zipped([('xl/_rels/workbook.xml.rels',relations(items)),('xl/worksheets/sheet1.xml',b'<worksheet/>')])

class Tests(unittest.TestCase):
 def entry(self,folder,data=b'abc',media='application/pdf',code='pdf-encrypted'):
  entry=dict(d.ENTRIES[2]);p=folder/'body';p.write_bytes(data);entry.update(path=str(p),size=len(data),sha256=hashlib.sha256(data).hexdigest(),media=media,priorCode=code);return entry
 def asset(self,e):return {'assetId':e['assetId'],'sourceStageHolds':[],'preparationContract':{'permissions':{'read':True,'extract':True,'copy':True},'holds':[]}}
 def archive(self,data,rels=False):return d.archive_facts(io.BytesIO(data),len(data),deadline(),rels)
 def test_fixed_exact_22_unique(self):
  self.assertEqual(len(d.ENTRIES),22);self.assertEqual(len({e['assetId'] for e in d.ENTRIES}),22)
  self.assertLess(sum(e['size'] for e in d.ENTRIES),d.MAX_HASH_BYTES)
 def test_safe_relationship(self):
  v=self.archive(xlsx([{'Id':'r1','Target':'worksheets/sheet1.xml','Type':'x/worksheet'}]),True)
  self.assertEqual(v['relationships']['internal'],1);self.assertEqual(sum(v['relationships']['reasons'].values()),0)
 def test_absolute_xl_relationship(self):
  v=self.archive(xlsx([{'Id':'r1','Target':'/xl/worksheets/sheet1.xml'}]),True)
  self.assertEqual(sum(v['relationships']['reasons'].values()),0)
 def test_external_relationship_no_target_echo(self):
  v=self.archive(xlsx([{'Id':'r1','Target':'https://secret.example/token','TargetMode':'External'}]),True)
  self.assertEqual(v['relationships']['reasons']['external'],1);self.assertNotIn('secret',json.dumps(v))
 def test_parent_relationship_count(self):
  v=self.archive(xlsx([{'Id':'r1','Target':'../docProps/core.xml'}]),True)
  self.assertEqual(v['relationships']['reasons']['parent-component'],1)
 def test_missing_relationship_count(self):
  v=self.archive(xlsx([{'Id':'r1','Target':'worksheets/missing.xml'}]),True)
  self.assertEqual(v['relationships']['reasons']['missing-target'],1)
 def test_backslash_relationship_count(self):
  v=self.archive(xlsx([{'Id':'r1','Target':'worksheets\\bad.xml'}]),True)
  self.assertEqual(v['relationships']['reasons']['backslash'],1)
 def test_duplicate_and_missing_ids(self):
  v=self.archive(xlsx([{'Id':'r1','Target':'worksheets/sheet1.xml'},{'Id':'r1','Target':'worksheets/sheet1.xml'},{'Target':'worksheets/sheet1.xml'}]),True)
  self.assertEqual(v['relationships']['reasons']['duplicate-id'],1);self.assertEqual(v['relationships']['reasons']['missing-id'],1)
 def test_dtd_refused(self):
  data=zipped([('xl/_rels/workbook.xml.rels',b'<!DOCTYPE a [<!ENTITY b "x">]><a/>')])
  with self.assertRaisesRegex(ValueError,'relationship-xml-unsafe'):self.archive(data,True)
 def test_utf16_dtd_refused(self):
  data=zipped([('xl/_rels/workbook.xml.rels','<!DOCTYPE a><a/>'.encode('utf-16'))])
  with self.assertRaisesRegex(ValueError,'relationship-xml-unsafe'):self.archive(data,True)
 def test_null_padded_dtd_refused(self):
  data=zipped([('xl/_rels/workbook.xml.rels','<!DOCTYPE a><a/>'.encode('utf-16-le'))])
  with self.assertRaisesRegex(ValueError,'relationship-xml-unsafe'):self.archive(data,True)
 def test_relationship_limit(self):
  data=zipped([('xl/_rels/workbook.xml.rels',b' '*4097)])
  with patch.object(d,'MAX_XML_BYTES',4096),self.assertRaisesRegex(ValueError,'relationship-metadata-limit'):self.archive(data,True)
 def test_member_size_limit(self):
  with patch.object(d,'MAX_MEMBER_BYTES',2):self.assertIn('member-size',self.archive(zipped([('x',b'abc')]))['reasons'])
 def test_expanded_total_limit(self):
  with patch.object(d,'MAX_ARCHIVE_BYTES',3):self.assertIn('expanded-total',self.archive(zipped([('x',b'abc'),('y',b'abc')]))['reasons'])
 def test_ratio_limit(self):
  self.assertIn('compression-ratio',self.archive(zipped([('x',b'a'*100000)],zipfile.ZIP_DEFLATED))['reasons'])
 def test_traversal_not_extracted(self):self.assertIn('member-name',self.archive(zipped([('../escape',b'x')]))['reasons'])
 def test_special_and_executable(self):
  z=io.BytesIO()
  with zipfile.ZipFile(z,'w') as f:
   i=zipfile.ZipInfo('x.exe');i.external_attr=0o120777<<16;f.writestr(i,b'bad')
  v=self.archive(z.getvalue());self.assertIn('special-member',v['reasons']);self.assertIn('executable-member',v['reasons'])
 def test_eocd_count_checked_before_zip_parse(self):
  raw=bytearray(zipped([('x',b'x')]));at=raw.rfind(b'PK\x05\x06');struct.pack_into('<HH',raw,at+8,513,513)
  with patch.object(d.zipfile,'ZipFile',side_effect=AssertionError('must not parse')):self.assertIn('entry-count',self.archive(raw)['reasons'])
 def test_zip64_locator_refused(self):
  raw=bytearray(zipped([('x',b'x')]));at=raw.rfind(b'PK\x05\x06');raw[at-20:at-16]=b'PK\x06\x07'
  with patch.object(d.zipfile,'ZipFile',side_effect=AssertionError('must not parse')):self.assertIn('zip64-unsupported',self.archive(raw)['reasons'])
 def test_deadline(self):
  with self.assertRaisesRegex(ValueError,'diagnostic-deadline'):d.archive_facts(io.BytesIO(b''),0,time.monotonic()-1)
 def test_current_hold_no_read(self):
  e=d.ENTRIES[0];a=self.asset(e);a['sourceStageHolds']=['read']
  with patch.object(d,'safe_open',side_effect=AssertionError('no read')):r=d.diagnose_one(e,a,deadline(),[0],None)
  self.assertEqual(r['errorCode'],'current-stage-held')
 def test_top_level_stage_holds_no_read(self):
  for hold in ('read','extract','copy','all'):
   with self.subTest(hold=hold):
    e=d.ENTRIES[0];a=self.asset(e);a['holds']=[hold]
    with patch.object(d,'safe_open',side_effect=AssertionError('no read')):r=d.diagnose_one(e,a,deadline(),[0],None)
    self.assertEqual(r['errorCode'],'current-stage-held');self.assertEqual(r['bytesHashed'],0)
 def test_permission_no_read(self):
  e=d.ENTRIES[0];a=self.asset(e);a['preparationContract']['permissions']['read']=False
  with patch.object(d,'safe_open',side_effect=AssertionError('no read')):r=d.diagnose_one(e,a,deadline(),[0],None)
  self.assertEqual(r['errorCode'],'read-permission-unestablished')
 def test_extent_mismatch(self):
  with tempfile.TemporaryDirectory() as t:
   e=self.entry(Path(t));e['size']+=1;r=d.diagnose_one(e,self.asset(e),deadline(),[0],None)
   self.assertEqual(r['errorCode'],'extent-mismatch');self.assertEqual(r['bytesHashed'],0)
 def test_digest_mismatch(self):
  with tempfile.TemporaryDirectory() as t:
   e=self.entry(Path(t));e['sha256']='0'*64;r=d.diagnose_one(e,self.asset(e),deadline(),[0],None)
   self.assertEqual(r['errorCode'],'digest-mismatch');self.assertFalse(r['identityVerified'])
 def test_symlink_refused(self):
  with tempfile.TemporaryDirectory() as t:
   e=self.entry(Path(t));p=Path(t)/'link';p.symlink_to(e['path']);e['path']=str(p)
   r=d.diagnose_one(e,self.asset(e),deadline(),[0],None);self.assertEqual(r['errorCode'],'unsafe-path')
 def test_pdf_exact_prior_encrypted_unknown_password(self):
  with tempfile.TemporaryDirectory() as t:
   e=self.entry(Path(t));detail={'metrics':None,'parser':{'name':'poppler'}}
   with patch.object(d,'prior_item',return_value=detail):r=d.diagnose_one(e,self.asset(e),deadline(),[0],(None,None))
   self.assertEqual(r['status'],'observed');self.assertTrue(r['pdf']['encryptedFlagObserved']);self.assertIsNone(r['pdf']['passwordRequired'])
 def test_pdf_blank_counts_from_pinned_detail(self):
  with tempfile.TemporaryDirectory() as t:
   e=self.entry(Path(t),code='pdf-ocr-required');detail={'metrics':{'pageCount':8,'selectedPageCount':8,'pagesWithoutText':2},'parser':{'name':'poppler-pdftotext'}}
   with patch.object(d,'prior_item',return_value=detail):r=d.diagnose_one(e,self.asset(e),deadline(),[0],(None,None))
   self.assertEqual(r['pdf']['pagesWithText'],6);self.assertFalse(r['pdf']['imageOnlyEstablished'])
 def test_missing_pdf_detail_no_guess(self):
  with tempfile.TemporaryDirectory() as t:
   e=self.entry(Path(t));r=d.diagnose_one(e,self.asset(e),deadline(),[0],None)
   self.assertEqual(r['errorCode'],'prior-detail-unavailable');self.assertIsNone(r['pdf']['pagesWithoutText'])
 def test_byte_budget(self):
  with tempfile.TemporaryDirectory() as t:
   e=self.entry(Path(t));budget=[d.MAX_HASH_BYTES]
   r=d.diagnose_one(e,self.asset(e),deadline(),budget,None)
   self.assertEqual(r['errorCode'],'diagnostic-byte-budget');self.assertEqual(r['bytesHashed'],0)
 def test_parent_rename_during_archive_check_blocks(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);folder=root/'current';folder.mkdir();e=self.entry(folder,zipped([('x',b'abc')]),'application/zip','member-contracts-required')
   original=d.archive_facts
   def raced(*args,**kwargs):
    value=original(*args,**kwargs);folder.rename(root/'renamed');return value
   with patch.object(d,'archive_facts',side_effect=raced):r=d.diagnose_one(e,self.asset(e),deadline(),[0],None)
   self.assertEqual(r['errorCode'],'changed-during-read');self.assertEqual(r['status'],'blocked');self.assertFalse(r['identityVerified'])
 def test_parent_symlink_substitution_blocks(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);folder=root/'current';folder.mkdir();e=self.entry(folder,zipped([('x',b'abc')]),'application/zip','member-contracts-required')
   original=d.archive_facts
   def raced(*args,**kwargs):
    value=original(*args,**kwargs);folder.rename(root/'renamed');folder.symlink_to(root/'renamed',target_is_directory=True);return value
   with patch.object(d,'archive_facts',side_effect=raced):r=d.diagnose_one(e,self.asset(e),deadline(),[0],None)
   self.assertEqual(r['errorCode'],'changed-during-read');self.assertEqual(r['status'],'blocked');self.assertFalse(r['identityVerified'])
 def test_original_unchanged(self):
  with tempfile.TemporaryDirectory() as t:
   data=zipped([('x',b'abc')]);e=self.entry(Path(t),data,'application/zip','member-contracts-required');before=Path(e['path']).stat()
   r=d.diagnose_one(e,self.asset(e),deadline(),[0],None)
   after=Path(e['path']).stat();self.assertEqual(r['status'],'observed');self.assertEqual(before.st_mtime_ns,after.st_mtime_ns);self.assertEqual(Path(e['path']).read_bytes(),data)
 def test_full_22_blocked_complete_closed_report(self):
  r=d.run_diagnostics('/bad',deadline(),assets=[])
  self.assertEqual(len(r['items']),22);self.assertEqual(r['status'],'complete-with-blocked');self.assertLess(len(d.canonical(r)),d.MAX_REPORT_BYTES)
  for forbidden in ('path','URL','rawText'):self.assertNotIn('"'+forbidden+'"',d.canonical(r).decode())
 def test_closed_report_rejects_extension(self):
  r=d.run_diagnostics('/bad',deadline(),assets=[]);r['items'][0]['path']='/secret'
  with self.assertRaises(ValueError):d.sanitize_diagnostics(r)
 def test_independent_item_failure_continuation(self):
  with patch.object(d,'OUTPUT_ROOT',Path('/synthetic')),patch.object(d.os,'getuid',return_value=d.EXPECTED_UID),patch.object(d,'prior_preparations',side_effect=FileNotFoundError):
   r=d.run_diagnostics('/synthetic',deadline(),assets=[])
   self.assertEqual(len(r['items']),22);self.assertTrue(all(x['errorCode']=='current-asset-unresolved' for x in r['items']))
 def test_pinned_json_no_changed_content(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'meta';p.write_bytes(b'{"a":1}\n')
   self.assertEqual(d.read_json(p,d.sha(p.read_bytes()),deadline()),{'a':1})
   with self.assertRaisesRegex(ValueError,'prior-detail-invalid'):d.read_json(p,'0'*64,deadline())
 def test_nonfinite_deadline_rejected(self):
  r=d.run_diagnostics(d.OUTPUT_ROOT,float('nan'),assets=[])
  self.assertTrue(all(x['errorCode']=='diagnostic-invalid' for x in r['items']))
 def test_report_counter_consistency(self):
  r=d.run_diagnostics('/bad',deadline(),assets=[]);r['bytesHashed']=1
  with self.assertRaises(ValueError):d.sanitize_diagnostics(r)


class IntegrationTests(unittest.TestCase):
 asset=Tests.asset
 # Exercise real fixed report cardinality with synthetic originals and hash-bound prior files.
 def test_full_prior_checkpoint_roundtrip(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);folder=root/'collection/global-collection'/d.MANIFEST_SHA256;folder.mkdir(parents=True)
   entries=[];assets=[];checkpoints=[]
   for n,original in enumerate(d.ENTRIES):
    data=(xlsx([{'Id':'r1','Target':'worksheets/sheet1.xml','Type':'x/worksheet'}]) if original['media'].endswith('sheet') else zipped([('a',b'abc')]) if original['media']=='application/zip' else b'%PDF-synthetic')
    path=root/str(n);path.write_bytes(data);entry=dict(original,path=str(path),size=len(data),sha256=d.sha(data))
    detail={'metrics':{'pageCount':8,'selectedPageCount':8,'pagesWithoutText':2},'parser':{'name':'poppler-pdftotext'}}
    entry['priorDetailSHA256']=d.sha(d.canonical(detail))
    checkpoint={'assetId':entry['assetId'],'manifestSHA256':d.MANIFEST_SHA256,'detail':{'preparation':detail}}
    raw=d.canonical(checkpoint);digest=d.sha(raw);(folder/('asset-'+str(entry['assetIndex'])+'-'+digest+'.json')).write_bytes(raw);checkpoints.append([entry['assetIndex'],digest])
    entries.append(entry);assets.append(self.asset(entry))
   raw=d.canonical({'schemaVersion':'offmenu-global-collection-detail/1','checkpoints':checkpoints});digest=d.sha(raw);(folder/('result-'+digest+'.json')).write_bytes(raw)
   before={p: (p.stat().st_size,p.stat().st_mtime_ns) for p in root.rglob('*') if p.is_file()}
   with patch.object(d,'ENTRIES',tuple(entries)),patch.object(d,'OUTPUT_ROOT',root),patch.object(d,'GLOBAL_DETAIL_SHA256',digest),patch.object(d.os,'getuid',return_value=d.EXPECTED_UID):
    report=d.run_diagnostics(root,deadline(),assets=assets)
    self.assertEqual(report['status'],'complete');self.assertEqual(len(report['items']),22)
    self.assertTrue(all(x['priorDetailVerified'] for x in report['items']));self.assertLess(len(d.canonical(report)),16384)
   after={p: (p.stat().st_size,p.stat().st_mtime_ns) for p in root.rglob('*') if p.is_file()};self.assertEqual(before,after)

if __name__=="__main__":unittest.main()
