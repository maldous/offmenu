#!/usr/bin/env python3
"""Private native-selected federation child. No HTTP-selected files or rights."""
import sys, json, hashlib, runpy
from pathlib import Path
from dataclasses import dataclass

ROOT = Path('/home/user/src/offmenu-dev/develop')
CONFIG = Path('/home/user/Documents/Codex/2026-10-22/worker05-federated-consumer-preparation/accepted-current-custody-operation-context.json')
CONFIG_SHA = '994a97393113d2726ca4d633d513b5e22a803dbdd96a1eb5dc123ea1c79190c3'
RECEIPT = Path('/home/user/src/offmenu-data/barcode-identifiers-worker57-full-retained-v1/load-receipt.json')
HELD = Path('/home/user/Documents/Codex/2026-10-21/worker05-general-product-lookup-preparation/held_context_candidate.py')
HELD_SHA = 'cafd21c0f2733b9ef38f8bf4d0d0db4224675ebf4c23e1cd19bcc2fe4c91cdad'
FIELDS = 'assertion_id run_id input_id source_id release_id artifact_sha256 record_ordinal source_record_id native_record_id identity_state parse_job_id asset_id citation_id identifier_ordinal namespace lexical_value symbology source_pointer disposition reason_code input_manifest_sha256 load_state finalization_evidence_sha256 raw_sha256 raw_bytes'.split()
CAP = 262144
BACKEND = 'retained-product-federation-v1'

def pinned(path, digest):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError('native-source-pin-changed')
    return raw

def encode(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()

def output(value):
    raw = value if isinstance(value, bytes) else encode(value)
    if len(raw) > CAP:
        raw = b'{"error":"API_RESPONSE_BOUND","status":503}'
    sys.stdout.buffer.write(raw)

@dataclass(frozen=True)
class Backing:
    role: str
    database: object
    load_receipt_sha256: str
    qualification_sha256: str

def main():
    raw = sys.stdin.buffer.read(8193)
    if len(raw) > 8192:
        raise ValueError('request-bound')
    request = json.loads(raw)
    if type(request) is not dict:
        raise ValueError('request-shape')
    config = json.loads(pinned(CONFIG, CONFIG_SHA))
    for entry in config['sourceClosureAdmission']['actualAcceptedSourceClosure']:
        pinned(entry['path'], entry['sha256'])
    pinned(config['currentTrustedCustodyReceipt']['path'], config['currentTrustedCustodyReceipt']['sha256'])
    manifest = json.loads(pinned(config['manifest']['path'], config['manifest']['sha256']))
    pinned(config['currentOperation']['path'], config['currentOperation']['sha256'])
    receipt = json.loads(pinned(RECEIPT, manifest['identifierLoadReceiptSha256']))
    if receipt['databaseSha256'] != manifest['identifierDatabaseSha256'] or not receipt['loadComplete']:
        raise ValueError('identifier-receipt-binding')
    metadata = {'databaseLoaded': True, 'queryAvailable': True,
        'databaseSha256': manifest['identifierDatabaseSha256'],
        'receiptSha256': manifest['identifierLoadReceiptSha256'], 'runId': receipt['runId'],
        'schemaVersion': receipt['schemaVersion'], 'loadComplete': True,
        'pointInTimeOnly': True, 'scope': 'selected retained OFF and USDA source observations; not worldwide or canonical gold',
        'summary': receipt['summary'], 'accepted': False, 'assurance': 'lexical-source-observations-only',
        'limitMax': 25, 'queryMatchTotal': None, 'productDetailsSupported': True,
        'detailBackend': BACKEND, 'detailDatabaseSha256': None,
        'detailSelectionSha256': config['manifest']['sha256'], 'detailGenerationId': manifest['generationId']}
    if request == {'action': 'status'}:
        output(metadata)
        return
    if (set(request) - {'action', 'namespace', 'lexical_value', 'after', 'limit', 'include'}
            or request.get('action') != 'query' or request.get('include') != [BACKEND]):
        raise ValueError('query-shape')
    namespace, lexical = request.get('namespace'), request.get('lexical_value')
    limit, after = request.get('limit', 10), request.get('after', 0)
    if (namespace not in ('barcode', 'USDA-FDC') or type(lexical) is not str or not 1 <= len(lexical) <= 128
            or type(limit) is not int or not 1 <= limit <= 25 or type(after) is not int or after < 0):
        raise ValueError('query-input')
    sys.path.insert(0, str(ROOT))
    from offmenu.refresh import product_detail_federated_query as api
    from offmenu.refresh import identifier_database
    pinned(identifier_database.__file__, '53d7aea20dde26f19e5176d2261d40a7d13e700396ac71036a96b61653995cb1')
    for entry in config['sourceClosureAdmission']['actualAcceptedSourceClosure']:
        name = entry['repoPath'].removesuffix('.py').replace('/', '.').removesuffix('.__init__')
        if Path(sys.modules[name].__file__).resolve() != Path(entry['path']):
            raise ValueError('native-import-path')
    page = identifier_database.query_identifiers(receipt, namespace=namespace, lexical_value=lexical,
        after_assertion_id=after, limit=limit, max_steps=100000, max_seconds=5, max_result_bytes=CAP)
    page['rows'] = [{key: row.get(key) for key in FIELDS} for row in page['rows']]
    page.update(metadata=metadata, queryMatchTotal=None)
    # After current identifier rows exist, every detail failure preserves them.
    composer = None
    try:
        for key in ('context', 'composer', 'safeErrors'):
            entry = config['caller'][key]
            pinned(entry['path'], entry['sha256'])
        pinned(HELD, HELD_SHA)
        composer = runpy.run_path(config['caller']['composer']['path'])['compose_federated_page']
        context = runpy.run_path(config['caller']['context']['path'])['selected_federated_wire']
        helper = runpy.run_path(str(HELD))
        safe_codes = set(json.loads(Path(config['caller']['safeErrors']['path']).read_text())['fixedCodes'])
        backings = []
        for entry in config['nativeOnlyContexts']:
            selected = helper['SelectedDatabase'](Path(entry['nativeConfigPath']), tuple(entry['fiveTupleAsOf']), entry['databaseSha256'])
            if entry['role'] == 'identifier':
                identifier = selected
            else:
                backings.append(Backing(entry['role'], selected, entry['loadReceiptSha256'], entry['qualificationSha256']))
        wire = context(page, selection=api.FederatedQuerySelection(**config['proposedSelection']),
            identifier_database=identifier, identifier_run_id=receipt['runId'], backing_selections=tuple(backings),
            selected_manifest=manifest, selected_coverage=config['expectedCoverage'], store_api=api,
            held_readonly=helper['held_readonly'], canonical=api.canonical, compose=composer,
            safe_error_code=lambda error: str(error) if str(error) in safe_codes else 'FEDERATED_DETAIL_UNAVAILABLE')
        output(wire)
    except Exception:
        page['details'] = {'detailDatabaseSha256': None, 'detailBackend': BACKEND,
            'detailSelectionSha256': config['manifest']['sha256'], 'detailGenerationId': manifest['generationId'],
            'accepted': False, 'state': 'unavailable', 'error': {'reasonCode': 'FEDERATED_DETAIL_UNAVAILABLE'},
            'sourceProducts': [], 'productDetailAvailability': []}
        output(page)

try:
    main()
except (ValueError, TypeError, KeyError, OSError):
    output({'error': 'PINNED_FEDERATION_HOST_UNAVAILABLE', 'status': 503})
