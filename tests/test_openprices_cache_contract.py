"""Synthetic retained-price metadata and packets; no real cache/body IO."""
import copy
import hashlib
import json
import subprocess
import unittest

from offmenu.refresh.openprices_cache_contract import (
    MAX_LINE, NOTICE, PriceValidator, qualification_gaps, select_manifest,
)
from offmenu.refresh.product_clock import UNKNOWN, validate_clock


def wire(value):
    return (json.dumps(value,ensure_ascii=False,separators=(',',':'))+'\n').encode()


def manifest():
    return {'schemaVersion':'offmenu-collection/1','sourceId':'prices',
        'releaseId':'2026-10-12','status':'normalized','license':'ODbL',
        'attribution':'Open Prices','url':'https://prices.openfoodfacts.org',
        'publication':'local only; no production corpus storage enabled',
        'archiveSha256':'a'*64,'counts':{'raw':257,'accepted':256,'duplicates':0,
        'quarantined':0,'excluded':1,'records':256},'kinds':{'priceObservation':256},
        'partitions':[{'key':f'{i:02x}.jsonl.gz','records':1,'bytes':100,
                       'sha256':hashlib.sha256(str(i).encode()).hexdigest()} for i in range(256)]}


def select(obj):
    raw=wire(obj)
    return select_manifest(raw,hashlib.sha256(raw).hexdigest())


def record():
    return {'schemaVersion':'1.0','kind':'priceObservation','id':'prices:priceObservation:fixture',
        'countries':['DE'],'provenance':{'sourceId':'prices','recordId':'fixture',
        'url':'https://prices.openfoodfacts.org/','license':'ODbL','attribution':'Open Prices',
        'fetchedAt':'2026-10-13T03:00:00Z','sourceDate':'2026-10-12','visibility':'public',
        'transform':'offmenu-bulk/1','rights':NOTICE,'releaseId':'2026-10-12',
        'archiveSha256':'a'*64,'sourceRow':2},'data':{'identifiers':[{'system':'barcode','value':'00123'}],
        'amount':0,'currency':'EUR','observedAt':'2026-10-12',
        'retailer':{'name':'Synthetic Shop','externalId':'7','location':'Synthetic place'},
        'unitPrice':None,'unit':None,'promotion':False,'discountType':None,
        'regularAmount':None,'duplicateOf':None,'proofId':None,'availability':'unknown',
        'priceType':'dated-observation'}}


class RetainedOpenPricesTests(unittest.TestCase):
    def setUp(self):
        self.selection=select(manifest())
        self.check=PriceValidator(self.selection)
        self.key=hashlib.sha256(b'fixture').hexdigest()[:2]+'.jsonl.gz'

    def issues(self,row):
        return self.check.validate_line(wire([row]),partition=self.key,line=1)

    def test_projection_preserves_zero_false_null_and_leading_zero_source_assertion(self):
        row=record();before=copy.deepcopy(row)
        self.assertEqual(self.issues(row),())
        self.assertEqual(row,before)
        self.assertEqual(row['data']['identifiers'][0]['value'],'00123')
        self.assertEqual(row['data']['amount'],0)
        self.assertIs(row['data']['promotion'],False)

    def test_missing_native_currency_date_identifiers_and_price_stay_unknown(self):
        row=record();row['data'].update(currency=None,observedAt=None,identifiers=[],amount=None)
        row['provenance']['sourceDate']=None
        self.assertEqual(self.issues(row),())
        self.assertFalse(qualification_gaps()['familyQualified'])

    def test_manifest_pin_and_current_partition_pins_are_exact(self):
        obj=manifest();raw=wire(obj)
        with self.assertRaisesRegex(ValueError,'pin-mismatch'):
            select_manifest(raw,'0'*64)
        obj['partitions'][0]['sha256']='f'*64
        changed=select(obj)
        self.assertNotEqual(changed.manifest_sha256,self.selection.manifest_sha256)
        self.assertNotEqual(changed.input_assets()[0],self.selection.input_assets()[0])
        self.assertEqual(sum(a.bytes for a in changed.input_assets()),25600)
        self.assertEqual(changed.records,256) # Same count does not make pins equal.

    def test_manifest_identity_status_rights_and_counts_fail_closed(self):
        for field,value in (('sourceId','off'),('releaseId','2026-10-13'),('license','CC0'),
                            ('attribution','other'),('status','collecting'),('kinds',{'product':256})):
            obj=manifest();obj[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):select(obj)
        for field,value in (('raw',258),('records',255),('duplicates',True),('quarantined',1)):
            obj=manifest();obj['counts'][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):select(obj)

    def test_manifest_partition_inventory_paths_bounds_and_pins_fail_closed(self):
        changes=[lambda o:o['partitions'].pop(),
                 lambda o:o['partitions'].__setitem__(0,o['partitions'][1]),
                 lambda o:o['partitions'][0].update(key='../00.jsonl.gz'),
                 lambda o:o['partitions'][0].update(records=True),
                 lambda o:o['partitions'][0].update(records=2),
                 lambda o:o['partitions'][0].update(bytes=0),
                 lambda o:o['partitions'][0].update(sha256='bad'),
                 lambda o:o['partitions'][0].update(extra='unknown')]
        for change in changes:
            obj=manifest();change(obj)
            with self.assertRaises(ValueError):select(obj)
        for raw in (b'{"x":1,"x":2}',b'\xff',b'[]',b'{"x":NaN}'):
            with self.assertRaises(ValueError):select_manifest(raw,hashlib.sha256(raw).hexdigest())

    def test_source_identity_release_archive_row_transform_and_rights_rejected(self):
        for key,value in (('sourceId','off'),('releaseId','other'),('archiveSha256','b'*64),
                          ('sourceRow',0),('sourceRow',258),('sourceRow',True),
                          ('transform','other'),('license','CC0'),('attribution','Other'),
                          ('visibility','private'),('recordId','other')):
            row=record();row['provenance'][key]=value
            with self.subTest(key=key):self.assertTrue(self.issues(row))
        row=record();row['id']='other';self.assertIn('prices-record-identity',self.issues(row))

    def test_product_identity_relationship_and_private_payload_fields_rejected(self):
        for key,value in (('kind','product'),('schemaVersion','2.0'),('ingredientEdges',[])):
            row=record();row[key]=value;self.assertTrue(self.issues(row))
        for field in ('user_id','comment','image','proofUrl','productIri','ingredients','gtinVerified'):
            row=record();row['data'][field]='invented';self.assertTrue(self.issues(row))
        row=record();row['provenance']['user']='private';self.assertTrue(self.issues(row))

    def test_exact_source_shard_and_partition_line_bounds(self):
        raw=wire([record()])
        other='00.jsonl.gz' if self.key!='00.jsonl.gz' else '01.jsonl.gz'
        self.assertEqual(self.check.validate_line(raw,partition=other,line=1),('prices-record-shard',))
        for key,line in (('../x',1),(self.key,0),(self.key,2),(self.key,True),([],1)):
            self.assertTrue(self.check.validate_line(raw,partition=key,line=line))

    def test_json_packet_line_size_duplicates_nan_and_overflow_rejected(self):
        for raw in (b'{}\n',wire([record(),record()]),wire([]),wire([record()]).rstrip(),
                    b'{"x":1,"x":2}\n',b'\xff\n',b'x'*MAX_LINE+b'\n',
                    b'[{"x":1e999}]\n',b'[{"x":NaN}]\n'):
            self.assertTrue(self.check.validate_line(raw,partition=self.key,line=1))

    def test_price_date_clock_and_stock_constraints_are_narrow(self):
        for key,value in (('amount',-1),('amount',True),('availability','in-stock'),
                          ('priceType','current-offer'),('duplicateOf',0),
                          ('promotion',1),('proofId',{})):
            row=record();row['data'][key]=value;self.assertTrue(self.issues(row))
        for stamp in ('yesterday','2026-10-13T03:00:00'):
            row=record();row['provenance']['fetchedAt']=stamp;self.assertTrue(self.issues(row))
        row=record();row['data']['observedAt']='2026-02-30';row['provenance']['sourceDate']='2026-02-30'
        self.assertTrue(self.issues(row))
        row=record();row['provenance']['sourceDate']=None
        self.assertIn('prices-source-date-mismatch',self.issues(row))

    def test_accepted_unknown_clock_rejects_prices_not_blanket_source_approval_gap(self):
        with self.assertRaisesRegex(ValueError,'retained-clock-contract-invalid'):
            validate_clock('prices',None,UNKNOWN,'a'*64)
        gaps=qualification_gaps()
        for field in ('familyQualified','sourceContractConstructed','relationshipInputReady','executionAdmitted'):
            self.assertIs(gaps[field],False)
        self.assertEqual(len(gaps['missingBindings']),4)

    def test_source_schema_matches_actual_accepted_js_projection_on_synthetic_input(self):
        # Invoke only the pure accepted normalizer with an authored row, never
        # collect-jsonl, a cache file, source.sqlite or an acquisition adapter.
        code="""import {normalizePrices} from './public/unified-data.js';
        import {sourceById} from './public/sources.js';
        const rows=normalizePrices({items:[{id:'fixture',product_code:'00123',price:0,
          currency:'EUR',date:'2026-10-12',location_id:7,price_is_discounted:false,
          location:{osm_name:'Synthetic Shop',osm_display_name:'Synthetic place',osm_address_country_code:'de'}}]},sourceById('prices'));
        rows[0].provenance={...rows[0].provenance,fetchedAt:'2026-10-13T03:00:00Z',
          releaseId:'2026-10-12',archiveSha256:'a'.repeat(64),transform:'offmenu-bulk/1',sourceRow:2};
        console.log(JSON.stringify(rows));"""
        result=subprocess.run(['/bin/node','--input-type=module','-e',code],capture_output=True,check=True)
        self.assertEqual(self.check.validate_line(result.stdout,partition=self.key,line=1),())
        self.assertEqual(json.loads(result.stdout)[0],record())


if __name__=='__main__':unittest.main()
