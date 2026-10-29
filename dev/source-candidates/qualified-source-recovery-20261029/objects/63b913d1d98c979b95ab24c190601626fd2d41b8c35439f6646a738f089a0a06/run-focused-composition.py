import os,sys,unittest
from pathlib import Path
root=Path(sys.argv[1]).resolve();modules=sys.argv[2:]
sys.path[:0]=[str(root),str(root/'tests')]
def source_guard(event,args):
 if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
  p=os.fsdecode(args[0])
  if p.startswith('/home/user/Documents/') or p.startswith('/home/user/src/offmenu-data/') or p.startswith('/home/user/src/offmenu-workers/'):
   raise AssertionError('Composition prohibits retained source/control access: '+p)
sys.addaudithook(source_guard)
suite=unittest.defaultTestLoader.loadTestsFromNames(modules)
result=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
