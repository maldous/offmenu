"""Generated data/in-memory HTTP fixtures only. Never contacts a public source."""
import copy
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest import mock
import urllib.error
import urllib.request

SPEC = importlib.util.spec_from_file_location('fetch_sources_fixture', Path(__file__).resolve().parents[1] / 'fetch_sources.py')
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)
DATA = b'<menus><menu>Generated fixture</menu></menus>'


class Response(io.BytesIO):
    def __init__(self, body=DATA, status=200, headers=None, url='https://example.test/data.xml'):
        super().__init__(body)
        self.status = status
        self.headers = {'Content-Type': 'text/xml', 'Content-Length': str(len(body)), **(headers or {})}
        self.url = url
        self.redirect_chain = []
    def geturl(self):
        return self.url


def source(sid='generated', body=DATA, kind='xml', sha=True):
    return {'id': sid, 'production_enabled': True, 'already_retained': False,
            'rights_status': 'verified_open_content', 'access_status': 'public_no_registration',
            'lineage_family': sid, 'revision': 'generated1', 'license': 'CC0',
            'license_evidence': ['https://example.test/license'], 'attribution': 'Generated fixture',
            'request_interval_seconds': 0,
            'artifacts': [{'name': 'generated.' + kind, 'url': 'https://example.test/data.xml',
                'allowed_hosts': ['example.test'], 'format': kind, 'max_bytes': 1024**2,
                'max_expanded_bytes': 2 * 1024**2, 'expected_bytes': len(body),
                'sha256': hashlib.sha256(body).hexdigest() if sha else None}]}


def manifest(sources):
    return {'schema': 'offmenu-fetch-sources/1', 'execution_host': 'Foo',
            'operation': 'acquisition_only', 'ingestion_enabled': False,
            'production_enabled': True, 'sources': sources}


class FetchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.budget = m.Budget(self.root, seconds=30, reserve=0)
        self.budget.delay = lambda seconds: self.budget.check() if seconds <= 30 else (_ for _ in ()).throw(m.Refusal('rate_limit_deferred'))
        self.s = source()
        self.a = self.s['artifacts'][0]
    def tearDown(self):
        self.tmp.cleanup()
    def fetch(self, transport=None, attempts=1):
        return m.fetch_artifact(self.s, self.a, self.root, self.budget, transport or (lambda *a: Response()), attempts)
    def partial(self, body, etag='"v1"', committed=None):
        final, part, checkpoint, receipt = m.artifact_paths(self.root, self.a)
        part.write_bytes(body)
        m.atomic_json(checkpoint, {'artifact_key': m.artifact_key(self.s, self.a), 'url': self.a['url'],
            'bytes': len(body) if committed is None else committed, 'etag': etag, 'last_modified': None})
        return final, part, checkpoint, receipt
    def test_real_manifest_validates_offline(self):
        value = m.validate_manifest(m.read_json(m.MANIFEST))
        self.assertTrue(value['production_enabled'])
        self.assertFalse(value['ingestion_enabled'])
        self.assertTrue(any(s['id'] == 'foodista_common_pile' and s['production_enabled'] for s in value['sources']))
    def test_download_reuse_no_second_request(self):
        first = self.fetch()
        self.assertEqual(first['status'], 'complete')
        second = self.fetch(lambda *a: self.fail('no network on reuse'))
        self.assertEqual(second['status'], 'reused')
        self.assertEqual(first['sha256'], second['sha256'])
    def test_resume_range_and_hash(self):
        self.partial(DATA[:10])
        def transport(a, headers, timeout):
            self.assertEqual(headers['Range'], 'bytes=10-')
            self.assertEqual(headers['If-Range'], '"v1"')
            return Response(DATA[10:], 206, {'ETag': '"v1"', 'Content-Range': f'bytes 10-{len(DATA)-1}/{len(DATA)}'})
        self.assertEqual(self.fetch(transport)['status'], 'complete')
    def test_ignored_range_restarts_owned_part(self):
        self.partial(DATA[:10])
        self.assertEqual(self.fetch(lambda *a: Response(DATA, headers={'ETag': '"v2"'}))['status'], 'complete')
        self.assertEqual((self.root / self.a['name']).read_bytes(), DATA)
    def test_uncommitted_old_prefix_discarded(self):
        self.a['sha256'] = None
        self.partial(b'<r>OLD', etag='"new"', committed=0)
        def transport(a, headers, timeout):
            self.assertNotIn('Range', headers)
            return Response(DATA)
        self.assertEqual(self.fetch(transport)['status'], 'complete')
    def test_shorter_than_checkpoint_refused(self):
        self.partial(DATA[:3], committed=10)
        with self.assertRaisesRegex(m.Refusal, 'checkpoint_invalid'):
            self.fetch()
    def test_invalid_range_not_promoted(self):
        self.partial(DATA[:10])
        with self.assertRaisesRegex(m.Refusal, 'range_invalid'):
            self.fetch(lambda *a: Response(DATA[10:], 206, {'Content-Range': f'bytes 9-{len(DATA)-1}/{len(DATA)}'}))
        self.assertFalse((self.root/self.a['name']).exists())
    def test_changed_etag_refused(self):
        self.partial(DATA[:10])
        with self.assertRaisesRegex(m.Refusal, 'source_changed'):
            self.fetch(lambda *a: Response(DATA[10:], 206, {'ETag':'"v2"','Content-Range':f'bytes 10-{len(DATA)-1}/{len(DATA)}'}))
    def test_checksum_rejected_temp_does_not_poison_resume(self):
        bad = b'<menus><menu>Wrong fixture!!!!!!!</menu></menus>'
        self.a['expected_bytes'] = None
        with self.assertRaisesRegex(m.Refusal, 'checksum_mismatch'):
            self.fetch(lambda *a: Response(bad))
        self.assertTrue((self.root/(self.a['name']+'.rejected')).exists())
        self.assertEqual(self.fetch()['status'], 'complete')
    def test_auth_denial_not_retried(self):
        calls=[]
        def denied(*args):
            calls.append(1)
            raise urllib.error.HTTPError(self.a['url'],403,'denied',{},None)
        with self.assertRaisesRegex(m.Refusal,'http_auth_denied'):
            self.fetch(denied,3)
        self.assertEqual(len(calls),1)
    def test_retry_after_persists_and_blocks_sibling_artifact(self):
        self.s['artifacts'].append({**self.a,'name':'second.xml'})
        calls=[]
        def limited(*args):
            calls.append(1)
            raise urllib.error.HTTPError(self.a['url'],429,'limited',{'Retry-After':'3600'},None)
        result=m.fetch_source(self.s,self.root,self.budget,limited)
        self.assertEqual(result['status'],'blocked')
        self.assertEqual(len(calls),1)
        self.assertTrue((self.root/'host-rate-limits.private.json').exists())
    def test_retry_after_http_date_and_invalid(self):
        self.assertEqual(m.retry_delay('not-a-date',2),4)
        self.assertEqual(m.retry_delay('0',2),0)
        self.assertEqual(m.retry_delay('inf',2),4)
    def test_unknown_size_receipt_orphan_recovers_without_network(self):
        self.a['expected_bytes']=None; self.a['sha256']=None
        final,part,checkpoint,receipt=self.partial(DATA)
        m.atomic_json(receipt,{'artifact_key':m.artifact_key(self.s,self.a),'status':'complete','bytes':len(DATA),'sha256':hashlib.sha256(DATA).hexdigest()})
        self.assertEqual(self.fetch(lambda *a:self.fail('no GET on receipt recovery'))['status'],'complete')
        self.assertTrue(final.exists())
    def test_html_error_rejected(self):
        self.a['expected_bytes']=None
        with self.assertRaisesRegex(m.Refusal,'html_or_auth_payload'):
            self.fetch(lambda *a:Response(b'<html>login</html>',headers={'Content-Type':'text/html'}))
    def test_mislabelled_html_rejected_without_publisher_hash(self):
        self.a['expected_bytes']=None;self.a['sha256']=None
        with self.assertRaisesRegex(m.Refusal,'html_or_auth_payload'):
            self.fetch(lambda *a:Response(b'<html>login</html>'))
    def test_xml_entities_rejected(self):
        self.a['expected_bytes']=None;self.a['sha256']=None
        with self.assertRaisesRegex(m.Refusal,'invalid_payload'):
            self.fetch(lambda *a:Response(b'<!DOCTYPE menus [<!ENTITY x SYSTEM "file:///etc/passwd">]><menus>&x;</menus>'))
    def test_utf16_doctype_rejected(self):
        body='<?xml version="1.0" encoding="UTF-16"?><!DOCTYPE r [<!ENTITY x "EXPANDED">]><r>&x;</r>'.encode('utf-16')
        self.a['expected_bytes']=None;self.a['sha256']=None
        with self.assertRaisesRegex(m.Refusal,'invalid_payload'):
            self.fetch(lambda *a:Response(body))
    def test_json_list_validated_data_only(self):
        body=b'[{"dish":"generated"}]'
        self.s=source(body=body,kind='json');self.a=self.s['artifacts'][0]
        self.assertEqual(self.fetch(lambda *a:Response(body,headers={'Content-Type':'application/json'}))['status'],'complete')
    def test_jsonl_gzip_validates_crc_and_object_rows(self):
        body=gzip.compress(b'{"id":"generated"}\n')
        self.s=source(body=body,kind='jsonl.gz');self.a=self.s['artifacts'][0]
        self.assertEqual(self.fetch(lambda *a:Response(body,headers={'Content-Type':'application/gzip'}))['status'],'complete')
    def archive(self, bad_crc=False, symlink=False):
        data=io.BytesIO()
        with tarfile.open(fileobj=data,mode='w') as tf:
            item=tarfile.TarInfo('generated.js');payload=b'throw new Error("NEVER EXECUTE");'
            if symlink:item.type=tarfile.SYMTYPE;item.linkname='/etc/passwd'
            else:item.size=len(payload)
            tf.addfile(item,None if symlink else io.BytesIO(payload))
        body=bytearray(gzip.compress(data.getvalue()))
        if bad_crc:body[-8]^=0xff
        return bytes(body)
    def test_archive_js_is_inert_and_not_extracted(self):
        body=self.archive();self.s=source(body=body,kind='tar.gz');self.a=self.s['artifacts'][0]
        self.assertEqual(self.fetch(lambda *a:Response(body))['status'],'complete')
        self.assertFalse((self.root/'generated.js').exists())
    def test_archive_bad_gzip_crc_rejected(self):
        body=self.archive(True);self.s=source(body=body,kind='tar.gz');self.a=self.s['artifacts'][0]
        with self.assertRaisesRegex(m.Refusal,'invalid_payload'):self.fetch(lambda *a:Response(body))
    def test_archive_symlink_rejected(self):
        body=self.archive(symlink=True);self.s=source(body=body,kind='tar.gz');self.a=self.s['artifacts'][0]
        with self.assertRaisesRegex(m.Refusal,'invalid_payload'):self.fetch(lambda *a:Response(body))
    def test_decompression_cap(self):
        body=gzip.compress(b'{"x":"'+b'a'*10000+b'"}\n')
        self.s=source(body=body,kind='jsonl.gz');self.a=self.s['artifacts'][0];self.a['max_expanded_bytes']=100
        with self.assertRaisesRegex(m.Refusal,'invalid_payload'):self.fetch(lambda *a:Response(body))
    def test_disk_reserve_before_write(self):
        with mock.patch.object(m.shutil,'disk_usage',return_value=mock.Mock(free=0)):
            with self.assertRaisesRegex(m.Refusal,'disk_reserve'):self.fetch()
        self.assertFalse((self.root/self.a['name']).exists())
    def test_byte_budget_before_write(self):
        self.budget.max_bytes=1
        with self.assertRaisesRegex(m.Refusal,'byte_budget'):self.fetch()
    def test_cancel_preserves_state(self):
        self.budget.cancelled.set()
        with self.assertRaisesRegex(m.Refusal,'cancelled'):self.fetch()
    def test_symlink_cache_refused(self):
        target=self.root/'target';target.mkdir();link=self.root/'link';link.symlink_to(target)
        with self.assertRaisesRegex(m.Refusal,'unsafe_path'):m.safe_path(link/'nested',create=True)
    def test_exact_http_exception_no_downgrade(self):
        url='http://example.test:8080/data.xml'
        self.assertEqual(m.checked_url(url,['example.test'],url),url)
        with self.assertRaises(m.Refusal):m.checked_url(url,['example.test'])
        redirect=m.RestrictedRedirect({'example.test'})
        with self.assertRaisesRegex(m.Refusal,'redirect_refused'):
            redirect.redirect_request(urllib.request.Request('https://example.test/data.xml'),None,302,'',{},url)
        self.assertEqual(m.clean_url(url+'?secret=redacted'),url)
    def test_unreviewed_redirect_and_credentials_refused(self):
        for url in ['https://evil.test/data','https://u:p@example.test/data','file:///tmp/data','http://example.test/data']:
            with self.assertRaises(m.Refusal):m.checked_url(url,['example.test'])
    def test_manifest_rejects_retained_enabled_duplicate_and_false_rights(self):
        for key,val in [('already_retained',True),('rights_status','unknown'),('access_status','requires_key')]:
            s=copy.deepcopy(self.s);s[key]=val
            with self.assertRaises(ValueError):m.validate_manifest(manifest([s]))
        other=copy.deepcopy(self.s);other['id']='second'
        with self.assertRaises(ValueError):m.validate_manifest(manifest([self.s,other]))
    def test_source_isolation_and_summary_safe_projection(self):
        good=source('good');bad=source('bad');bad['artifacts'][0]['url']='https://example.test/bad'
        def transport(a,*args):
            if a['url'].endswith('/bad'):raise urllib.error.HTTPError(a['url'],403,'private-text',{},None)
            return Response()
        result=m.run_fetch(manifest([bad,good]),self.root/'cache',self.root/'summary.json',workers=2,seconds=30,reserve=0,transport=transport)
        self.assertEqual(result['status'],'partial')
        self.assertEqual({s['status'] for s in result['sources']},{'blocked','complete'})
        result['leak']='PRIVATE RAW';result['sources'][0]['payload']='PRIVATE RAW'
        clean=m.sanitize_report(result)
        self.assertNotIn('PRIVATE',json.dumps(clean))
        self.assertNotIn(str(self.root),json.dumps(clean))
    def test_summary_contradictions_rejected(self):
        result=m.run_fetch(manifest([self.s]),self.root/'cache',self.root/'summary.json',seconds=30,reserve=0,transport=lambda *a:Response())
        for key,value in [('raw_data_uploaded',True),('database_mutations',1),('execution_host','cloud'),('downloaded_code_executed',True)]:
            bad=copy.deepcopy(result);bad[key]=value
            with self.assertRaises(ValueError):m.sanitize_report(bad)
        result['sources']=[]
        with self.assertRaises(ValueError):m.sanitize_report(result)
    def test_cli_cloud_host_refuses_before_network(self):
        with mock.patch.object(m.socket,'gethostname',return_value='cloud-fixture'),mock.patch.object(m.Transport,'__call__',side_effect=AssertionError('network')):
            with self.assertRaises(SystemExit):m.main([])
    def test_robots_denial_blocks_html(self):
        self.s['robots_url']='https://example.test/robots.txt'
        self.s['artifacts'][0]['format']='html_recipe'
        calls=[]
        def transport(*args):
            calls.append(1);return Response(b'User-agent: *\nDisallow: /\n',headers={'Content-Type':'text/plain'})
        result=m.fetch_source(self.s,self.root,self.budget,transport)
        self.assertEqual(result['status'],'blocked');self.assertEqual(len(calls),1)


if __name__ == '__main__':
    unittest.main()
