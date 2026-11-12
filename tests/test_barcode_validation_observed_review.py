import json
from pathlib import Path
import tempfile
import unittest
import test_barcode_validation as fixture
from offmenu.refresh import barcode_validation as v
from offmenu.refresh import product_adapters as a


class ObservedReviewRegressions(unittest.TestCase):
    def test_observed_huge_optional_value_and_basis(self):
        huge=10**400
        self.assertEqual(v.nutrient(1,'g',{'amount':huge,'unit':'g'})['state'],'unknown')
        self.assertEqual(v.nutrient(huge,'g',{'amount':100,'unit':'g'})['state'],'unknown')
        context=a.ProductContext('off','fixture','2026-10-25T00:00:00Z','generated','fixture','1'*64,'2'*64)
        product,profile=list(a._off(context,{'code':'012345678905','nutrition_data_per':'100g','nutriments':{'proteins_100g':huge}}))
        self.assertEqual(product['kind'],'product')
        self.assertEqual(profile['data']['nutrientDispositions']['proteins_100g']['sourceAmount'],huge)

    def test_observed_replay_operation_and_count_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);op=fixture.ValidationTests().operation(root)
            op['version']=v.VERSION
            original=v.execute(op,root/'out')
            receipt_path=root/'out'/original['generation']/'receipt.json'
            changed=json.loads(receipt_path.read_text());changed['operationSha256']='0'*64
            changed['counts']['goldAdmitted']=900
            receipt_path.write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError,'receipt-binding-mismatch'):
                v.execute(op,root/'out')


if __name__=='__main__':unittest.main()
