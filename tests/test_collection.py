import importlib.util
import json
import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path

path = Path(__file__).parent.parent / 'scripts/collect-usda.py'
spec = importlib.util.spec_from_file_location('collector', path)
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)


class CollectionTests(unittest.TestCase):
    def test_complete_tables_resume_and_changed_archive_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = root / 'release.zip'
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr('release/food.csv', 'fdc_id,description\n0001,"Rice, cooked"\n0002,\n')
                z.writestr('release/details.csv', 'Food ID,Note\n0001,NT\n')
                z.writestr('release/dictionary.xlsx', b'original workbook')
            first = collector.collect(archive, root / 'result')
            self.assertEqual(first['rawRows'], 3)
            self.assertEqual(len(first['members']), 3)
            second = collector.collect(archive, root / 'result')
            self.assertEqual(second['tables'], first['tables'])
            db = sqlite3.connect(root / 'result/source.sqlite')
            self.assertEqual(db.execute('SELECT fdc_id,description FROM food ORDER BY _ingestion_row').fetchall(), [('0001', 'Rice, cooked'), ('0002', '')])
            db.close()
            with zipfile.ZipFile(archive, 'a') as z:
                z.writestr('release/more.csv', 'id\n1\n')
            with self.assertRaisesRegex(ValueError, 'Archive changed'):
                collector.collect(archive, root / 'result')

    def test_malformed_table_never_commits_as_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with zipfile.ZipFile(root / 'bad.zip', 'w') as z:
                z.writestr('food.csv', 'id,name\n1,Rice,Extra\n')
            with self.assertRaisesRegex(ValueError, 'Malformed row'):
                collector.collect(root / 'bad.zip', root / 'result')
            self.assertFalse((root / 'result/manifest.json').exists())
