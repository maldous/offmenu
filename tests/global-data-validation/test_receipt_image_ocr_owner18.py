import importlib.util
import io
from pathlib import Path
import shutil
import unittest
from PIL import Image, ImageDraw, ImageFont
spec = importlib.util.spec_from_file_location('ocr18', Path(__file__).resolve().parents[2] / 'scripts/receipt-image-ocr-owner18.py')
ocr = importlib.util.module_from_spec(spec); spec.loader.exec_module(ocr)
def context():
    return {'accountId':'a','sourceId':'private-user','now':100,'retainUntil':400,'ownerConfirmed':True,
            'consent':{'accountId':'a','receiptReview':True,'expiresAt':500},'rights':{'sourceId':'private-user','privateUse':True,'expiresAt':500}}
def data():
    out=io.BytesIO();Image.new('RGB',(300,100),'white').save(out,'PNG');return out.getvalue()
def proposal(data, c, **options):
    return ocr.image_proposal(data,c,recheck=lambda:c,**options)
def tokens(_):return [{'text':'R1CE','lineId':'1','box':[10,10,100,30],'confidence':.4}]
def reviews(p):return [{'id':line['id'],'decision':'include','name':'Rice','quantity':None,'unit':None} for line in p['helperInput']['ocr']['lines']]
class ReceiptImage(unittest.TestCase):
    def test_unknown_source_and_user_corrections(self):
        p=proposal(data(),context(),extractor=tokens)
        self.assertEqual(p['tokens'][0]['box'],[10,10,100,30]);self.assertIsNone(p['price']);self.assertIsNone(p['helperInput']['ocr']['lines'][0]['quantity'])
        r=ocr.review_proposal(p,context(),receipt_id='r',confirmed=True,reviews=reviews(p))
        rs=reviews(p);rs[0]['price']={'amount':'2.00','currency':'AUD','basis':'user-reviewed line price'};rs[0]['purchaseDate']='2026-10-14';priced=ocr.review_proposal(p,context(),receipt_id='r2',confirmed=True,reviews=rs);self.assertEqual(priced['reviewedFields'][0]['price']['amount'],'2.00');self.assertEqual(priced['reviewedFields'][0]['purchaseDate'],'2026-10-14');self.assertEqual(r['helperReview']['lines'][0]['name'],'Rice');self.assertFalse(r['inventoryAuthority']);self.assertEqual(p['tokens'][0]['text'],'R1CE')
    def test_duplicate_image_receipt_and_account_scope(self):
        p=proposal(data(),context(),extractor=tokens);r=ocr.review_proposal(p,context(),receipt_id='r',confirmed=True,reviews=reviews(p));ledger=[r['ledgerEntry']]
        self.assertEqual(proposal(data(),context(),extractor=lambda _:self.fail('should not extract'),ledger=ledger)['status'],'duplicate-image')
        self.assertEqual(ocr.review_proposal({**p,'imageDigest':'b'*64,'helperInput':{**p['helperInput'],'contentDigest':'b'*64}},context(),receipt_id='r',confirmed=True,reviews=reviews(p),ledger=ledger)['status'],'duplicate')
        ledger[0]['accountId']='b';self.assertEqual(ocr.review_proposal(p,context(),receipt_id='r',confirmed=True,reviews=reviews(p),ledger=ledger)['status'],'reviewed-proposal')
    def test_permissions_precede_extraction(self):
        for key in ('ownerConfirmed','consent','rights'):
            c=context();c[key]=False if key=='ownerConfirmed' else {}
            with self.assertRaises(ValueError):proposal(data(),c,extractor=lambda _:self.fail('not authorized'))
        c=context();c['consent']['expiresAt']=100
        with self.assertRaises(ValueError):proposal(data(),c,extractor=tokens)
    def test_bounds_scope_and_explicit_review(self):
        with self.assertRaises(ValueError):proposal(b'x'*(ocr.MAX_BYTES+1),context(),extractor=tokens)
        with self.assertRaises(ValueError):proposal(data(),context(),extractor=lambda _:[{'text':'x','lineId':'1','box':[290,0,20,2],'confidence':.8}])
        p=proposal(data(),context(),extractor=tokens)
        for confirmed,rs in [(False,reviews(p)),(True,[])]:
            with self.assertRaises(ValueError):ocr.review_proposal(p,context(),receipt_id='r',confirmed=confirmed,reviews=rs)
        c=context();c['accountId']='b';c['consent']['accountId']='b'
        with self.assertRaises(ValueError):ocr.review_proposal(p,c,receipt_id='r',confirmed=True,reviews=reviews(p))
    def test_retention(self):
        c=context();self.assertTrue(ocr.retention_plan(c,image_retained=True,image_until=200)['deleteImage']);c['consent']['retainImage']=True
        self.assertTrue(ocr.retention_plan(c,image_retained=True,image_until=200)['originalRetentionPermitted'])
        p=ocr.retention_plan(c,withdrawn=True,image_retained=True,image_until=200)
        self.assertTrue(all(p[k] for k in ('deleteImage','deleteTokens','deleteProposal','deleteLedger')))
        c['consent']['expiresAt']=100;self.assertTrue(ocr.retention_plan(c,image_retained=True,image_until=200)['deleteTokens']);c['now']=400;self.assertTrue(ocr.retention_plan(c)['deleteTokens'])
    def test_capture_and_current_recheck(self):
        for mutation in ('scope','withdraw','expiry','owner'):
            c=context()
            def changed(_):
                if mutation=='scope':
                    c['accountId']='b';c['sourceId']='other'
                    c['consent']['accountId']='b';c['rights']['sourceId']='other'
                elif mutation=='withdraw':c['consent']['receiptReview']=False
                elif mutation=='expiry':c['now']=500
                else:c['ownerConfirmed']=False
                return tokens(None)
            with self.assertRaises(ValueError):proposal(data(),c,extractor=changed)
        c=context();authoritative=context()
        def changed(_):
            c['accountId']='untrusted-mutated';return tokens(None)
        p=ocr.image_proposal(data(),c,extractor=changed,recheck=lambda:authoritative)
        self.assertEqual(p['helperInput']['accountId'],'a')
        c=context()
        with self.assertRaises(ValueError):ocr.image_proposal(data(),c,extractor=lambda _:self.fail('missing admission provider'))
        class Custom(dict):
            def items(self):self.fail('custom mapping invoked')
        with self.assertRaises(ValueError):ocr.image_proposal(data(),Custom(c),extractor=tokens,recheck=lambda:c)
        # Real owner clock can advance while permissions remain valid.
        c=context();live=context();live['now']=101
        self.assertEqual(ocr.image_proposal(data(),c,extractor=tokens,recheck=lambda:live)['status'],'needs-review')
    @unittest.skipUnless(shutil.which('tesseract'),'Actual OCR blocked: no Tesseract')
    def test_one_actual_synthetic_receipt(self):
        image=Image.new('RGB',(900,400),'white');font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',36)
        ImageDraw.Draw(image).multiline_text((30,30),'SYNTHETIC RECEIPT\nRICE 2.00\nTOTAL 2.00',font=font,fill='black',spacing=25)
        out=io.BytesIO();image.save(out,'PNG');p=proposal(out.getvalue(),context())
        self.assertIn('RICE',[t['text'] for t in p['tokens']]);self.assertTrue(all(0<=t['confidence']<=1 for t in p['tokens']))
        self.assertTrue(all(line['quantity'] is None for line in p['helperInput']['ocr']['lines']))
        rs=[{'id':line['id'],'decision':'include' if 'RICE' in line['originalText'] else 'exclude','name':'Rice','quantity':None,'unit':None} for line in p['helperInput']['ocr']['lines']]
        r=ocr.review_proposal(p,context(),receipt_id='synthetic-only',confirmed=True,reviews=rs)
        self.assertEqual(r['status'],'reviewed-proposal');self.assertFalse(ocr.retention_plan(context())['originalRetentionPermitted'])
if __name__=='__main__':unittest.main()
