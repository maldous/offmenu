"""Executable source qualification only. Never opens/evaluates a product record."""
from pathlib import Path
from types import ModuleType
import hashlib
import json
import sys

ROOT = Path('/home/user/src/offmenu-data/runtime/layout-migration/worker00/private10300-local-integration-20261026/r8-generic-caller-candidate-20261027')
EXPECTED = '08f5630496a7efe516735a77cda9286a0e69b4f196481facc3031c1b3b67b92b'
path = ROOT / 'r8_caller.py'
raw = path.read_bytes()
assert hashlib.sha256(raw).hexdigest() == EXPECTED
module = ModuleType('offmenu_integrated_r8_caller')
module.__file__ = str(path)
exec(compile(raw, str(path), 'exec'), module.__dict__)
caller = module.R8Caller()
assert len(caller.frozen.bytes) == 29
assert len(caller.gate.engine.rules) == len(caller.gate.engine.accepted) == 86
assert len(caller.legacy.REVIEWED.engine.rules) == len(caller.legacy.REVIEWED.engine.accepted) == 83
assert len(caller.new_rules) == 3
assert caller.registry_sha == '1c416151ab4c06abe898d9ff3289182ca9fa9f2879539be2f3ac9e5f538db879'
assert caller.type_receipt_sha == '112e3cc7d1ec644d716d43fa79262ce32b9cfed82482e7e13cf9e81f163445eb'
assert len(caller.types['acceptedConditionalRelations']) == 16
print(json.dumps({'status': 'PASS_EXACT_REVIEWED_CALLER_SOURCE_BOUND_AND_CONSTRUCTED_NO_RECORD_EVALUATION',
                  'callerPath': str(path), 'callerSha256': EXPECTED,
                  'pythonExecutable': sys.executable, 'pythonVersion': sys.version.split()[0],
                  'dependencyCount': len(caller.frozen.bytes), 'legacyAcceptedRules': 83,
                  'gatedAcceptedRules': 86, 'newGatedRules': 3, 'conditionalTypeRelations': 16,
                  'actualProductEvaluations': 0, 'populationStarted': False,
                  'runtimeAdoption': False, 'publication': False, 'sourceRightsGranted': False}))
