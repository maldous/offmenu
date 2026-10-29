import ast,subprocess,unittest
from offmenu.refresh import core
raw=subprocess.check_output(['git','show','d0088ff93ae641e7862b0b46b8a44942e20d8cac:offmenu/refresh/core.py'],text=True)
node=next(n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name=='writer_lock')
exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),'base-core-writer-lock','exec'),core.__dict__)
suite=unittest.defaultTestLoader.loadTestsFromName('test_refresh_writer_lock')
r=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(not r.wasSuccessful())
