"""OFF-LIVE held-context delta. Requires accepted26 implementation and stores.

Uses existing reviewed05 held_readonly/SelectedDatabase mechanism when installed
by soleUI/05. No current code import, database opening or activation at import.
"""
from contextlib import ExitStack
import hashlib
import json


def selected_federated_wire(page, *, selection, identifier_database,
                            identifier_run_id, backing_selections,
                            selected_manifest, selected_coverage,
                            store_api, held_readonly, canonical, compose,
                            safe_error_code):
    """Keyword configuration is native-selected; never accept HTTP config.

    backing_selections is immutable tuple of native-selected objects with role,
    database(SelectedDatabase), load_receipt_sha256, qualification_sha256.
    store_api must be exact accepted product_detail_federated_query namespace.
    canonical must be accepted core.canonical UTF8+LF, not acceptance.canonical.
    """
    if (type(selection) is not store_api.FederatedQuerySelection
            or type(backing_selections) is not tuple
            or identifier_database.digest != selection.identifier_database_sha256):
        raise ValueError('independent-federation-selection-required')
    encoded = canonical(selected_manifest)
    if len(encoded) > 262144 or hashlib.sha256(encoded).hexdigest() != selection.input_manifest_sha256:
        raise ValueError('federation-selection-manifest-binding')
    manifest = json.loads(encoded)  # frozen private snapshot, no caller mutation
    pins = [{'role': b.role, 'databaseSha256': b.database.digest,
             'loadReceiptSha256': b.load_receipt_sha256,
             'qualificationSha256': b.qualification_sha256} for b in backing_selections]
    roles = [b.role for b in backing_selections]
    if (len(set(roles)) != len(roles)
            or set(roles) - {'off-subset', 'usda-products', 'usda-profiles'}
            or ('usda-products' in roles) != ('usda-profiles' in roles)):
        raise ValueError('federation-role-selection')
    with ExitStack() as stack:
        index, check = stack.enter_context(held_readonly(identifier_database))
        index.execute('PRAGMA query_only=ON')  # own connection only; no database write
        checks = [check]
        stores = []
        for b in backing_selections:
            db, check = stack.enter_context(held_readonly(b.database))
            db.execute('PRAGMA query_only=ON')  # required by frozen counts-v2 API
            checks.append(check)
            stores.append(store_api.FederatedStoreEvidence(
                b.role, db, b.database.digest, b.load_receipt_sha256, b.qualification_sha256))
        try:
            result = store_api.read_federated_product_details(
                page['rows'], selection=selection,
                identifier_evidence=store_api.FederatedIdentifierEvidence(
                    index, identifier_run_id, identifier_database.digest),
                stores=tuple(stores), selected_manifest=manifest,
                max_candidates=100, max_result_bytes=262144,
                max_steps=100000, max_seconds=5)
        except Exception as error:
            # Native source-specific allowlist maps to fixed safe codes, not str(error).
            failure = compose(page, selected_generation=selection.generation_id,
                              selected_manifest_sha256=selection.input_manifest_sha256,
                              selected_operation_sha256=selection.operation_selection_sha256,
                              selected_backing_stores=pins, selected_coverage=selected_coverage,
                              detail_error=safe_error_code(error))
            return json.dumps(failure, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()
        envelope = compose(page, selected_generation=selection.generation_id,
                           selected_manifest_sha256=selection.input_manifest_sha256,
                           selected_operation_sha256=selection.operation_selection_sha256,
                           selected_backing_stores=pins, selected_coverage=selected_coverage,
                           result=result)
        wire = json.dumps(envelope, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()
        if len(wire) > 262144:
            raise ValueError('federation-final-wire-bound')
        for check in checks:
            check()
        return wire  # held/name custody checked through completed serialization
