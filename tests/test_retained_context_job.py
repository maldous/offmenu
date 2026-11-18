import contextlib
from dataclasses import asdict, replace
import hashlib
import multiprocessing
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from offmenu.retained_context_job import Budget, Unit, Refused, execute, decode, wire

H = '1'*64


class TestIssuer:
    """Only in tests. Its fenced grant is confined to this test’s temp directory."""
    def __init__(self, unit):
        self.unit=unit
        self.denied=set()
        self.mutate={}
        self.held=False

    @contextlib.contextmanager
    def hold(self,key,purpose):
        if key!=self.unit.key or purpose in self.denied or self.held:
            raise Refused('fence unavailable')
        self.held=True
        try:
            yield dict({'unit':key,'purpose':purpose,'generation':self.unit.generation,
                        'operation':self.unit.operation,'effect_fenced':True,
                        'prior_effects_reconciled':True,'rights_verified':True,'resources_reserved':True,
                        'host_limits_enforced':True,'resources':asdict(self.unit.budget),'offline_only':True,'valid_until':time.time()+self.unit.budget.timeout_seconds+15},**self.mutate)
        finally:
            self.held=False


class JobTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.fd=os.open(self.root,os.O_DIRECTORY|os.O_RDONLY);self.addCleanup(os.close,self.fd)
        s=os.fstat(self.fd)
        self.unit=Unit('off','release-1','queue-1','cohort-114/chunk-00001','op1',4,H,H,H,H,H,s.st_dev,s.st_ino,5,30000,2,Budget(1000,2*1024**3,1,2*1024**3,900))
        self.issuer=TestIssuer(self.unit);self.read=[];self.starts=[]
        self.dir=self.root/self.unit.namespace

    def source(self,start):
        self.starts.append(start)
        for i in range(start,self.unit.max_rows):
            self.assertTrue(self.issuer.held)
            self.read.append(i)
            yield {'ordinal':i,'value':'source-only'}

    def run_job(self, **kw):
        return execute(self.unit,destination_fd=self.fd,guard=self.issuer,
                       produce=kw.pop('produce',self.source),**kw)

    def test_exact_resume_and_terminal_reuse(self):
        def crash(point):
            if point=='after-link:part-00000.json':raise InterruptedError()
        with self.assertRaises(InterruptedError):self.run_job(crash=crash)
        self.assertEqual(self.read,[0,1]);r=self.run_job()
        self.assertEqual(self.read,list(range(5)))
        self.assertEqual(self.starts,[0,2]); self.assertEqual(r['rows'],5)
        self.assertFalse(r['published']); self.assertFalse(r['canonical_acceptance'])
        self.assertEqual(r,self.run_job(produce=lambda _:self.fail('replayed terminal')))

    def test_terminal_carries_text_only_static_and_client_image_contract(self):
        d=self.run_job()['downstream_delivery']
        self.assertEqual(d['corpusDistribution'],'versioned-text-only')
        self.assertIs(d['hostProviderImageBinaries'],False);self.assertIs(d['serverImageProxy'],False)
        self.assertIs(d['runtimeExternalDataApi'],False);self.assertIs(d['runtimeTranslation'],False)
        self.assertEqual(d['providerAcquisitionAndTranslation'],'separately-authorized-scheduled-foo-build-only')
        self.assertEqual(d['externalCitations'],'explicit-user-initiated-navigation-only')
        self.assertEqual(d['visualFallbackOrder'],['direct-client-provider-origin-image-if-terms-and-browser-allow',
                                                  'emoji-or-unicode','local-offmenu-logo'])
        self.assertFalse(any(p.suffix in ('.jpg','.png','.webp','.gif','.jpeg') for p in self.dir.iterdir()))
        d['visualFallbackOrder'].clear()
        self.assertEqual(len(self.run_job()['downstream_delivery']['visualFallbackOrder']),3)

    def test_no_authority_and_mismatch(self):
        for key,val in [('prior_effects_reconciled',False),('rights_verified',False),('effect_fenced',False),
                        ('offline_only',False),('resources_reserved',False),('resources',{}),('host_limits_enforced',False),('valid_until',0),
                        ('operation','old'),('generation',2)]:
            with self.subTest(key=key):
                self.issuer.mutate={key:val}
                with self.assertRaises(Refused):self.run_job()
                self.assertEqual(list(self.root.iterdir()),[]);self.assertEqual(self.read,[])
        self.issuer.mutate={}
        with self.assertRaises(Refused):
            execute(self.unit,destination_fd=self.fd,guard=None,produce=self.source)

    def test_denied_reconciliation_cannot_even_list_private_segments(self):
        self.run_job()
        self.issuer.denied={'reconcile-output'}
        with patch('offmenu.retained_context_job.os.listdir', side_effect=AssertionError('listing without grant')), \
             patch('offmenu.retained_context_job._read',side_effect=AssertionError('read without grant')):
            with self.assertRaisesRegex(Refused,'fence unavailable'):
                self.run_job(produce=lambda n:self.fail())

    def test_expiry_types_and_reservation_cannot_alias_booleans(self):
        self.unit=replace(self.unit,generation=1);self.issuer=TestIssuer(self.unit)
        for key,value in [('generation',True),('valid_until',float('inf')),('valid_until',time.time()+1),
                          ('resources',dict(asdict(self.unit.budget),workers=True))]:
            self.issuer.mutate={key:value}
            with self.assertRaises(Refused):self.run_job()
            self.assertEqual(list(self.root.iterdir()),[])

    def test_fence_rechecked_at_commit(self):
        self.issuer.denied.add('commit-segment')
        with self.assertRaises(Refused):self.run_job()
        self.assertFalse(list(self.dir.glob('part-*')))
        self.assertFalse((self.dir/'receipt.json').exists())

    def test_wrong_generation_existing_scope(self):
        self.run_job()
        other=replace(self.unit,generation=self.unit.generation+1,operation='op2')
        with self.assertRaises(Refused):
            execute(other,destination_fd=self.fd,guard=TestIssuer(other),produce=lambda n:self.fail())

    def test_two_writers_excluded_in_same_shard(self):
        def nested(start):
            with self.assertRaisesRegex(Refused,'writer already active'):
                execute(self.unit,destination_fd=self.fd,guard=TestIssuer(self.unit),produce=lambda n:[])
            yield from self.source(start)
        self.run_job(produce=nested)

    def test_corruption_never_truncated(self):
        self.run_job()
        p=self.dir/'part-00001.json'; altered=p.read_bytes().replace(b'source-only',b'bad-part')
        p.write_bytes(altered)
        with self.assertRaises(Refused):self.run_job(produce=lambda n:self.fail())
        self.assertEqual(p.read_bytes(),altered)
        p.unlink()
        with self.assertRaisesRegex(Refused,'gap'):self.run_job(produce=lambda n:self.fail())

    def test_real_crash_before_and_after_final_visibility(self):
        for marker in ['before-link:part-00000.json','after-link:part-00002.json','after-link:receipt.json']:
            def child():
                def crash(point):
                    if point==marker:os._exit(77)
                self.run_job(crash=crash)
            p=multiprocessing.get_context('fork').Process(target=child);p.start();p.join(4)
            self.assertEqual(p.exitcode,77)
        self.assertEqual(self.run_job(produce=lambda n:self.fail())['rows'],5)
        self.assertTrue(any(self.dir.glob('.pending-*')))

    def test_reject_short_long_and_budget(self):
        for count in [1,6]:
            with tempfile.TemporaryDirectory() as name:
                fd=os.open(name,os.O_DIRECTORY);s=os.fstat(fd)
                u=replace(self.unit,destination_device=s.st_dev,destination_inode=s.st_ino)
                try:
                    with self.assertRaises(Refused):
                        execute(u,destination_fd=fd,guard=TestIssuer(u),produce=lambda n:({'i':i} for i in range(n,count)))
                    self.assertFalse((Path(name)/u.namespace/'receipt.json').exists())
                finally:os.close(fd)
        self.unit=replace(self.unit,max_output_bytes=15);self.issuer=TestIssuer(self.unit)
        with self.assertRaisesRegex(Refused,'exceeds'):self.run_job()

    def test_declared_budget_is_part_of_the_fence(self):
        original=self.unit
        for key,v in [('workers',2),('io_slots',0),('disk_bytes',30000),('cpu_millis',True)]:
            u=replace(original,budget=replace(original.budget,**{key:v}))
            with self.subTest(key=key),self.assertRaises(Refused):
                execute(u,destination_fd=self.fd,guard=TestIssuer(u),produce=self.source)
        u=replace(original,budget=replace(original.budget,timeout_seconds=600))
        self.assertNotEqual(u.key,original.key)
        with self.assertRaises(Refused):execute(u,destination_fd=self.fd,guard=self.issuer,produce=self.source)
        self.assertEqual(list(self.root.iterdir()),[])

    def test_unapproved_destination_and_symlink(self):
        other=replace(self.unit,destination_inode=self.unit.destination_inode+1)
        with self.assertRaises(Refused):execute(other,destination_fd=self.fd,guard=TestIssuer(other),produce=self.source)
        with tempfile.TemporaryDirectory() as outsider:
            self.dir.symlink_to(outsider)
            with self.assertRaises(OSError):self.run_job()
            self.assertEqual(list(Path(outsider).iterdir()),[])
