"""Read-only error metadata; never reads records, source files or exception text.

Durable counts cover ALL retained source versions, not this run's failed rows.
Reasons cover observed adapter callbacks in THIS invocation only. Older stores
did not record reasons and must not be retrospectively assigned one.
"""
from __future__ import annotations

from pathlib import Path
import sqlite3
import time

from ingest_api import DOMAINS

ERROR_CLASSES = frozenset('BudgetExceeded SourceChanged OSError IOError EOFError '
    'ValueError TypeError KeyError RuntimeError DatabaseError OperationalError '
    'IntegrityError JSONDecodeError UnicodeDecodeError UnicodeError PermissionError '
    'FileNotFoundError Error UnsupportedSource MalformedRecord MalformedSupplierRow '
    'UnsupportedSupplierSource DuplicateField DocumentTooLarge OverflowError source_error'.split())

# Curated exact first-argument tokens emitted by reviewed adapters, not regex
# extraction from an arbitrary message. Other messages collapse to one fixed
# bucket. Keep this finite set small enough for the existing 64 KiB receipts.
ERROR_REASONS = frozenset('other_or_unavailable unrecognized_recipe_or_lead_only '
    'recipe_ingredient_grain_unknown not_a_supported_recipe_record '
    'not_a_supported_menu_record ingredient_name_missing csv_no_header '
    'text_recipe_sections_unknown '
    'raw_pdf_requires_supported_parsed_cache unsupported_recipe_format '
    'compressed_sqlite_unsupported sqlite_recipe_schema_unknown sqlite_table_unknown '
    'optional_html_dependencies_missing '
    'html_no_supported_jsonld_or_parser duplicate_json_key nonfinite_json '
    'json_framing json_record_size_cap invalid_json json_root_key '
    'json_root_not_object_or_array json_trailing_data wrapper_depth_cap '
    'recipe_field_type ingredient_not_text_or_object instruction_depth_cap '
    'instruction_not_text pdf_cache_sections_missing pdf_cache_grain_conflict '
    'recipe_title_missing menu_name_missing menu_child_not_object '
    'product_ingredient_type record_not_object declared_table_missing '
    'declared_code_column_missing existing_database_changed record_size_cap '
    'unsupported_record_format '
    'unsupported_retained_format unsupported_supplier_format '
    'unsupported_text_compression parquet_dependency_unavailable '
    'no_supported_supplier_table source_changed_before_read '
    'source_changed_during_read source_changed_during_ingestion '
    'cancelled wall_time_cap disk_reserve acquired_cache_read_permission_denied '
    'acquired_cache_file_missing acquired_cache_unreadable'.split())

ORIGINS = ('adapter_callback', 'record_or_stream')


def classify_error(exc):
    name = type(exc).__name__
    args = getattr(exc, 'args', ())
    reason = args[0] if len(args) == 1 and type(args[0]) is str else None
    return (name if name in ERROR_CLASSES else 'source_error',
            reason if reason in ERROR_REASONS else 'other_or_unavailable')


def _counts(value, allowed):
    if not isinstance(value, dict):
        return {}
    return {key: count for key, count in sorted(value.items(), key=lambda row: str(row[0]))
            if type(key) is str and key in allowed and type(count) is int and 0 < count <= 10**15}


def sanitize_error_telemetry(value):
    value = value if isinstance(value, dict) else {}
    return {'status': value.get('status') if value.get('status') in ('available', 'not_created') else 'unknown',
            'durable_scope': 'all_retained_source_versions',
            'class_counts': _counts(value.get('class_counts'), ERROR_CLASSES),
            'origin_counts': {key: _counts(value.get('origin_counts'), ORIGINS).get(key, 0) for key in ORIGINS},
            'reason_scope': 'current_run_adapter_callbacks',
            'reason_counts': _counts(value.get('reason_counts'), ERROR_REASONS),
            'historical_reasons': 'not_recorded'}


def collect_error_snapshot(state_dir, observed=None):
    """Metadata-only snapshot; independent read-only connections, no schema writes.

    ``observed`` maps domains to (opaque source key, class, reason) -> count.
    Private detail keeps source/version grouping; only ``summary`` is publishable.
    Failure is explicitly unknown, never a false claim of zero errors.
    """
    observed = observed or {}
    snapshot = {'schema': 'offmenu-ingest-error-details/1', 'summary': {}, 'domains': {}}
    for domain in DOMAINS:
        telemetry = sanitize_error_telemetry({})
        details = {'sources': [], 'observed_adapter_events': []}
        for (key, error_class, reason), count in sorted(observed.get(domain, {}).items()):
            safe_class = error_class if error_class in ERROR_CLASSES else 'source_error'
            safe_reason = reason if reason in ERROR_REASONS else 'other_or_unavailable'
            details['observed_adapter_events'].append({'source_key': key, 'error_class': safe_class,
                                                       'reason_code': safe_reason, 'count': count})
            telemetry['reason_counts'][safe_reason] = telemetry['reason_counts'].get(safe_reason, 0) + count
        path = Path(state_dir).absolute() / ('private-household' if domain in ('user_profiles', 'inventory') else '.') / 'staging' / (domain + '.sqlite3')
        try:
            if any(p.is_symlink() for p in (path, *path.parents)):
                raise ValueError('unsafe_output_path')
            if not path.exists():
                telemetry['status'] = 'not_created'
            else:
                db = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=.25)
                try:
                    deadline = time.monotonic() + 2
                    db.set_progress_handler(lambda: int(time.monotonic() >= deadline), 10000)
                    db.execute('PRAGMA query_only=ON')
                    db.execute('PRAGMA trusted_schema=OFF')
                    db.execute('BEGIN')
                    meta = dict(db.execute('SELECT key,value FROM ingest_meta'))
                    if (meta.get('domain') != domain or meta.get('binding') != 'additive_staging_not_app_bound'
                            or meta.get('schema_version') != '1'):
                        raise ValueError('unowned_store')
                    classes, origins = {}, dict.fromkeys(ORIGINS, 0)
                    for key, version, adapter, error_class, count in db.execute(
                            'SELECT source_key,source_version,row_number<0,error_class,COUNT(*) '
                            'FROM source_errors GROUP BY source_key,source_version,row_number<0,error_class'):
                        safe_class = error_class if error_class in ERROR_CLASSES else 'source_error'
                        origin = 'adapter_callback' if adapter else 'record_or_stream'
                        classes[safe_class] = classes.get(safe_class, 0) + count
                        origins[origin] += count
                        details['sources'].append({'source_key': key, 'source_version': version,
                                                  'error_class': safe_class, 'origin': origin, 'count': count})
                    telemetry.update(status='available', class_counts=classes, origin_counts=origins)
                finally:
                    db.close()
        except (OSError, ValueError, sqlite3.Error):
            # Do not expose failure messages or partial query totals.
            telemetry.update(status='unknown', class_counts={}, origin_counts=dict.fromkeys(ORIGINS, 0))
            details['sources'] = []
        snapshot['summary'][domain] = sanitize_error_telemetry(telemetry)
        snapshot['domains'][domain] = details
    return snapshot
