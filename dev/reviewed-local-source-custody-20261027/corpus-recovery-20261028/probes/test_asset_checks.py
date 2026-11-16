import unittest,importlib.util,tempfile,os,json,hashlib,types,time
from pathlib import Path
from unittest.mock import patch
p=Path(__file__).with_name('check_six_package_assets.py');s=importlib.util.spec_from_file_location('assetchecks',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Checks(unittest.TestCase):
 def test_exact_match_and_corruption(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);pins={}
   for i in range(6):
    d=root/str(i);d.mkdir();b=b'opaque';(d/'asset.gz').write_bytes(b);raw=json.dumps({'files':[{'key':'asset.gz','bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}]}).encode();(d/'manifest.json').write_bytes(raw);pins[str(i)]=hashlib.sha256(raw).hexdigest()
   with patch.object(m,'ROOT',t),patch.object(m,'PINS',pins),patch.object(m.os,'fstatvfs',return_value=types.SimpleNamespace(f_flag=os.ST_RDONLY)):
    m.START=time.monotonic();m.TOTAL_READ=0;out=m.main();self.assertTrue(out['all_declared_assets_match']);self.assertEqual(out['total_assets_matched'],6)
    (root/'2'/'asset.gz').write_bytes(b'badbad');m.START=time.monotonic();m.TOTAL_READ=0;out=m.main();self.assertFalse(out['all_declared_assets_match']);self.assertEqual(out['packages'][2]['mismatched'],1)
 def test_no_path_escape(self):
  with tempfile.TemporaryDirectory() as t:
   fd=os.open(t,os.O_RDONLY|os.O_DIRECTORY)
   try:
    for key in ('../anything','/etc/passwd','x//y','x/./y'):
     with self.assertRaises(m.Refused):m.open_below(fd,key)
   finally:os.close(fd)
 def test_symlink_not_opened(self):
  with tempfile.TemporaryDirectory() as t:
   Path(t,'link').symlink_to('/etc/passwd');fd=os.open(t,os.O_RDONLY|os.O_DIRECTORY)
   try:
    with self.assertRaises(OSError):m.open_below(fd,'link')
   finally:os.close(fd)
if __name__=='__main__':unittest.main()
