"""Real code paths; all rows, SQLite indexes, rights-shaped fixtures, and leases synthetic."""
from contextlib import ExitStack
from dataclasses import replace
import gzip
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from offmenu import retained_context_consumers as adapters
from offmenu.retained_context_job import Unit, Refused, digest, wire
from offmenu.retained_context_source import Pin, LEGACY_BRIDGE, ENCODING, signature, input_key, run_qualified
from test_retained_context_job import TestIssuer

def fixture(where, provider, *, mismatch=False):
    root=where/'inputs';root.mkdir(mode=0o700); dest=where/'outputs';dest.mkdir(mode=0o700)
    def save(name,data): p=root/name;p.write_bytes(data);return p
    def ref(path):return dict(path=str(path),sha256=digest(path.read_bytes()))
    def meta(name,data):return save(name,wire(data))
    rel,rights=adapters.PROVIDERS[provider]; cohort=114 if provider=='off' else 112
    key=f'cohort-{cohort:03d}/chunk-00001';shard_rows=[];loc=[];glo=[]; lcode=[];gcode=[]
    dbsha='b'*64
    for n in range(3):
        rid=f'offmenu:product:{n+1:024x}'; native=f'{provider}:product:00{n}'; obs=digest(str(n).encode())
        ptr='/data/' if provider=='off' else '/0/data/'
        def ev(k,v):
            b=json.dumps(v,ensure_ascii=False,separators=(',',':')).encode()
            return {'state':'present','pointer':ptr+k,'evidenceEncoding':ENCODING,
                    'evidenceBytes':len(b),'parsedValueEvidenceSha256':digest(b)}
        fields={'name':ev('name','Fixture'),'categories':{},'languages':{}}
        d={'sourceFieldStates':fields,'name':'Fixture','identifiers':[{'system':'barcode','value':'00123'}]}
        if provider=='off':
            d['names']={'en':'Fixture'};fields['languages']['names']=ev('names',d['names'])
        else:
            d['ingredientsText']='1/2  OZ';d['dataType']='Fixture type'
            fields['ingredientDeclaration']=ev('ingredientsText',d['ingredientsText'])
            fields['categories']['dataType']=ev('dataType',d['dataType'])
        row={'id':rid,'kind':'product','data':d,'curation':{'sourceRecordReference':native,
             'sourceObservationSha256':obs,'inputDatabaseSha256':dbsha,'sourceQualificationSha256':rights},
             'provenance':{'sourceId':provider,'releaseId':rel,'recordId':f'00{n}',
             'sourceDocumentSha256':'d'*64,'visibility':'source-staging','license':'Fixture terms','attribution':'Synthetic publisher'}}
        line=wire([rid,[row]]);shard_rows.append(line)
        loc.append((n,rid,provider,rel,native,obs,key,digest(line)))
        glo.append((rid,provider,('wrong' if mismatch else rel),native,obs,cohort,key))
        lcode.append(('00123',0,n));gcode.append(('00123',0,rid))
    def db(name,lr,bc,ss,bb):
        p=root/name
        with sqlite3.connect(p) as con:
            con.execute('create table records('+ss+')');con.execute('create table barcodes('+bb+')')
            for tab,rows in [('records',lr),('barcodes',bc)]:
                con.executemany('insert into '+tab+' values('+','.join('?' for _ in rows[0])+')',rows)
        return p
    idx=db('cohort.sqlite',loc,lcode,'local_id,public_id,source,release,native_id,ref_sha,record_shard,wire_sha','code,checksum_valid,local_id')
    glob=db('global.sqlite',glo,gcode,'id,source,release,native_id,ref_sha,cohort,record_shard','code,checksum_valid,id')
    raw=b''.join(shard_rows);gz=save('shard.gz',gzip.compress(raw,mtime=0))
    desc=dict(ref(gz),key=key,bytes=gz.stat().st_size,uncompressedBytes=len(raw))
    cohort_path=meta('batch.json',dict(index=ref(idx),input={'sha256':dbsha},files=[desc],state='SOURCE_STAGING_COMPLETE_CANONICAL_ACCEPTANCE_SEPARATE'))
    bridge={'path':'inactive-reference-to-verified-source','sha256':LEGACY_BRIDGE}
    aa=meta('assign.json',dict(status='EXACT_HELPER_ASSIGNMENTS_PREPARED_SOURCE_READ_BY19_FALSE',assignments=[dict(source=provider,slice=desc,sourceQualificationSha256=rights)],
        cohortReceipt=ref(cohort_path),cohortIndex=ref(idx),sourceContextBridge=bridge,retainedGlobalIndexPath=str(glob)))
    queue=meta('queue.json',dict(id='fixture-queue',entries=[dict(source=provider,key=key,input=desc,sourceQualificationSha256=rights,assignment=ref(aa))],
        sourceReceipt=ref(cohort_path),cohortIndex=ref(idx),sourceBridge=bridge))
    allpaths=dict(queue=queue,assignment=aa,cohort_receipt=cohort_path,index=idx,global_index=glob,shard=gz)
    pins={}
    for k,p in allpaths.items():
        s=p.stat();pins[k]=Pin(str(p),digest(p.read_bytes()),s.st_size,s.st_dev,s.st_ino,s.st_mtime_ns,s.st_ctime_ns)
    return root,dest,pins,rel,rights,key


class RouteTest(unittest.TestCase):
    def run_synthetic(self, provider='off', *, mutation=None, mismatch=False):
        with tempfile.TemporaryDirectory() as td, ExitStack() as stack:
            root,dest,pins,rel,rights,key=fixture(Path(td),provider,mismatch=mismatch)
            sfd=os.open(root,os.O_DIRECTORY);dfd=os.open(dest,os.O_DIRECTORY);stack.callback(os.close,sfd);stack.callback(os.close,dfd)
            d=os.fstat(dfd); parser=digest(Path(adapters.__file__).read_bytes())
            u=Unit(provider,rel,'fixture-queue',key,'op',1,pins['queue'].sha256,pins['assignment'].sha256,rights,parser,
               input_key(str(root),sfd,pins),d.st_dev,d.st_ino,3,128*1024,2)
            def verify(p,fd):
                # No real database or implicit OK; independently hash the already-open fixture.
                return digest(os.pread(fd,p.size,0))==p.sha256
            if mutation: u,pins,verify=mutation(root,u,pins,verify)
            issuer=TestIssuer(u)
            args=dict(source_root=str(root),source_fd=sfd,destination_fd=dfd,pins=pins,issuer=issuer,verify_index=verify)
            result=run_qualified(u,**args)
            rows=[]
            for p in sorted((dest/u.namespace).glob('part-*.json')):rows+=json.loads(p.read_bytes())['rows']
            self.assertEqual(result['rows'],len(rows));self.assertEqual(len(rows),3)
            # Completed immutable ledger returns its bound receipt without re-reading an input index.
            args['verify_index']=lambda p,fd:self.fail('terminal source replay')
            self.assertEqual(result,run_qualified(u,**args))
            return rows
    def test_off_source_to_terminal(self):
        rows=self.run_synthetic()
        self.assertEqual([r['selectedEnglishName'] for r in rows],['Fixture']*3)
        self.assertTrue(all(not r['goldAdmitted'] for r in rows))
    def test_usda_source_to_terminal(self):
        rows=self.run_synthetic('usda-files')
        self.assertTrue(all(r['semanticResolution']['status']=='unresolved' for r in rows))
    def test_index_reconciliation_and_pin(self):
        with self.assertRaisesRegex(Refused,'indexed source identity'):self.run_synthetic(mismatch=True)
        with self.assertRaisesRegex(Refused,'verified immutable index'):
            self.run_synthetic(mutation=lambda root,u,p,v:(u,p,lambda pin,fd:False))
    def test_wrong_claimed_queue_parser_and_release(self):
        for k,val in [('queue','other'),('parser_sha256','c'*64),('rights_sha256','c'*64),('release','yesterday')]:
            with self.subTest(k=k), self.assertRaises(Refused):
                self.run_synthetic(mutation=lambda root,u,p,v:(replace(u,**{k:val}),p,v))
    def test_no_symlink_or_late_file_swap(self):
        def swap(root,u,p,v):
            path=root/'shard.gz'; path.rename(root/'moved.gz');path.symlink_to(root/'moved.gz')
            return u,p,v
        with self.assertRaises(OSError):self.run_synthetic(mutation=swap)
    def test_index_sidecar_refused_even_with_verifier(self):
        def side(root,u,p,v):
            (root/'global.sqlite-wal').touch()
            return u,p,v
        with self.assertRaisesRegex(ValueError,'sidecars'): self.run_synthetic(mutation=side)
    def test_no_network_or_process_launcher(self):
        with patch('socket.socket',side_effect=AssertionError('network')),patch('subprocess.Popen',side_effect=AssertionError('subprocess')):
            self.run_synthetic()
