"""Source-only caller: unchanged reviewed83 dispatcher plus qualified R9 gate.
No source population or runtime admission is performed by this module.
"""
import builtins
import hashlib
import json
from pathlib import Path
from copy import deepcopy
from types import ModuleType, SimpleNamespace

HERE = Path(__file__).resolve().parent
PIN_MANIFEST_SHA = '758f2d53ed4699bd943ddfb8ff792ad8a4f0ebe960a53460bc89d222fdaf379f'

class FrozenModules:
    """Load pinned Python/JSON bytes once, without global path/module monkeypatches."""
    def __init__(self, pins):
        self.bytes = {}
        self.modules = {}
        for path, expected in pins.items():
            raw = Path(path).read_bytes()
            if hashlib.sha256(raw).hexdigest() != expected:
                raise ValueError('Caller dependency pin mismatch')
            self.bytes[str(Path(path).resolve())] = raw
        owner = self
        class SnapshotPath(type(Path())):
            def read_bytes(self):
                key = str(self.resolve())
                if key not in owner.bytes:
                    raise ValueError('Unpinned caller dependency read')
                return owner.bytes[key]
            def read_text(self, encoding=None, errors=None):
                return self.read_bytes().decode(encoding or 'utf-8', errors or 'strict')
        self.path_type = SnapshotPath
        self.util = SimpleNamespace(
            spec_from_file_location=lambda name, path: SimpleNamespace(name=name, origin=str(path), loader=self),
            module_from_spec=self.module_from_spec)

    def module_from_spec(self, spec):
        module = ModuleType(spec.name)
        module.__file__ = spec.origin
        return module

    def exec_module(self, module):
        path = str(Path(module.__file__).resolve())
        raw = self.bytes[path]
        module.__dict__['__builtins__'] = {**vars(builtins), '__import__': self.import_module}
        exec(compile(raw, path, 'exec'), module.__dict__)
        self.modules[path] = module

    def load(self, path, name):
        path = str(Path(path).resolve())
        if path not in self.modules:
            module = self.module_from_spec(SimpleNamespace(name=name, origin=path))
            self.exec_module(module)
        return self.modules[path]

    def import_module(self, name, globals=None, locals=None, fromlist=(), level=0):
        if name == 'pathlib':
            return SimpleNamespace(Path=self.path_type)
        if name == 'importlib.util':
            return self.util if fromlist else SimpleNamespace(util=self.util)
        if name == 'sys':
            return SimpleNamespace(path=[])
        if name == 'context_rules':
            return self.load(self.engine_path, 'r9_frozen_context')
        return builtins.__import__(name, globals, locals, fromlist, level)

class R9Caller:
    def __init__(self):
        raw = (HERE / 'dependency-pins.json').read_bytes()
        if hashlib.sha256(raw).hexdigest() != PIN_MANIFEST_SHA:
            raise ValueError('Caller dependency manifest changed')
        self.frozen = FrozenModules(json.loads(raw))
        interface_path = str(HERE / 'frozen-interface-and-ownership-release.json')
        # Ownership receipt is not used as a runtime permission grant.
        interface = json.loads(self.frozen.bytes[interface_path])
        accepted_pin = interface['frozenSources']['acceptedInput']
        self.input = json.loads(self.frozen.bytes[accepted_pin['path']])
        cut = self.input['requiredCut']
        self.frozen.engine_path = cut['engine']['path']
        self.legacy = self.frozen.load(interface['frozenSources']['legacy83Dispatcher']['path'], 'r9_legacy83')
        gate_module = self.frozen.load(cut['qualifiedGateMandatoryForFiveWholeFamilies']['path'], 'r9_gate')
        receipt = cut['realAcceptedRuleReceipt']
        self.gate = gate_module.QualifiedWholeFamilyEvaluator(
            acceptance_path=receipt['path'], acceptance_sha256=receipt['sha256'])
        self.gated_rules = frozenset(self.input['scope']['mandatoryGateRuleIds'])
        self.types = json.loads(self.frozen.bytes[cut['separateAcceptedTypeReceipt']['path']])
        self.registry_sha = cut['registry']['sha256']
        self.type_receipt_sha = cut['separateAcceptedTypeReceipt']['sha256']

    def map_record(self, record):
        # Existing category output and all legacy/USDA behavior remain authoritative.
        out = self.legacy.map_record(record)
        if record.get('sourceBinding', {}).get('sourceId') != 'off':
            return out
        gate = self.gate.evaluate(record, diagnostics=False)
        resolution = gate.get('engineResolution')
        candidates = resolution.get('candidateTargets', []) if resolution else []
        new_hit = any(c.get('ruleId') in self.gated_rules for c in candidates)
        suppressed = any(c.get('ruleId') in self.gated_rules for c in gate.get('suppressedCandidates', []))
        if not new_hit and not suppressed:
            # Failed new-family qualification never substitutes bare engine targets.
            if gate.get('qualification') != 'passed':
                out['qualifiedWholeFamilyResolution'] = deepcopy(gate)
            return out
        out['qualifiedWholeFamilyResolution'] = deepcopy(gate)
        if suppressed or gate.get('qualification') != 'passed' or gate.get('status') != 'eligible-staged-resolution':
            context = deepcopy(out['wholeProductContextResolution'])
            context.update(status=gate['status'], classificationAccepted=False,
                           productTypeAccepted=False, candidateTargets=[], variantAssertions=[],
                           sourceAttributeClaims=[], entityKind=None, conceptId=None,
                           canonicalEnglishKey=None, canonicalEnglishLabel=None,
                           unresolvedReasons=deepcopy(gate['reasons']), mappingRevision=self.registry_sha)
        else:
            context = deepcopy(resolution)
        out['wholeProductContextResolution'] = context
        out['classificationAccepted'] = context['classificationAccepted']
        out['productTypeAccepted'] = context['productTypeAccepted']
        out['wholeProductClassificationDisposition'] = context['status']
        out['contextMappingRevision'] = self.registry_sha
        out['normalizationComplete'] = False
        # Links are evidence-bound annotations, never a whole-product/phase grant.
        links = []
        if context.get('status') == 'accepted-classification' and context.get('entityKind') == 'ingredient':
            for relation in self.types['acceptedConditionalRelations']:
                if relation['sourceRuleId'] not in self.gated_rules:
                    continue
                if not all(out['sourceBinding'].get(k) == v for k,v in relation['sourceScope'].items()):
                    continue
                if context.get('conceptId') != relation['baseConceptId'] or context.get('canonicalEnglishKey') != relation['canonicalEnglishBaseKey']:
                    continue
                if not any(c.get('semanticAccepted') is True and c.get('ruleId') == relation['sourceRuleId'] and c.get('target', {}).get('conceptId') == relation['baseConceptId'] for c in context['candidateTargets']):
                    continue
                links.append({'relation':deepcopy(relation), 'acceptedTypeReceiptSha256':self.type_receipt_sha,
                              'sourceBinding':deepcopy(out['sourceBinding']),
                              'stageAssertionBinding':deepcopy(out['stageAssertionBinding']),
                              'foundationQualified':False})
        out['qualifiedWholeFamilyTypeRelations'] = links
        return out

_DEFAULT = None
def map_record(record):
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = R9Caller()
    return _DEFAULT.map_record(record)
