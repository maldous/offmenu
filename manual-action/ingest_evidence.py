"""Bounded, optional self-reporting for the next natural ``./run``.

Only already-collected descriptors and engine-owned observations are consumed.
No source is opened, no SQLite connection is created, no worker is started, and
no diagnostic result grants ingestion eligibility. Public values are fixed enums
and counts; private descriptor examples never enter the public projection.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import time
import uuid

from ingest_api import DOMAINS, source_key

SCHEMA = 'offmenu-ingest-evidence/1'
PRIVATE_SCHEMA = 'offmenu-ingest-evidence-private/1'
MAX_COUNT = 10**15
MAX_PRIVATE_BYTES = 1024 * 1024
STAMP = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\Z')
ADAPTERS = {'barcodes': 'ingest_existing', 'ingredients': 'ingest_recipes',
    'recipes': 'ingest_recipes', 'dietary': 'ingest_misc',
    'user_profiles': 'ingest_existing', 'inventory': 'ingest_existing',
    'suppliers': 'ingest_suppliers', 'citations': 'ingest_misc'}
FORMATS = frozenset('json jsonl csv tsv sqlite parquet html pdf text markdown xml rdf '
    'osm-pbf osm-xml archive xlsx xls unknown other'.split())
SHAPES = frozenset('recipe_jsonld recipe_structured menu_structured product nutrient '
    'place citation tabular_unknown structured_unknown not_sampled private_redacted other'.split())
SHAPE_BASES = frozenset(('reviewed_adapter_contract', 'catalog_sample_fields', 'not_sampled', 'private_redacted', 'other'))
FIELDS = frozenset('id name title description recipeingredient recipeinstructions ingredients '
    'instructions steps directions recipes menuitems menusection hasmenusection hasmenuitem '
    'dish dishes menus barcode gtin productname fdcid nutrientid nutrients energykcal '
    'nutrientname geometry latitude longitude supplier citation citations bibliography '
    'recipe_id menu_id dish_id ingredient_id other'.split())
FIELD_TYPES = frozenset(('string', 'number', 'boolean', 'null', 'object', 'array', 'unknown', 'other'))
ELIGIBILITY = frozenset('candidate readonly_reuse adapter_required held unsupported '
    'unqualified failed awaiting_input other'.split())
ELIGIBILITY_COLUMNS = tuple(sorted(ELIGIBILITY))
ADAPTER_ROUTES = ('retained_dispatcher', 'foodista_common_pile', 'forkrecipe',
    'medlineplus_healthy_recipes', 'fr_cnous_menus', 'fr_begles_menus',
    'fr_toulouse_menus', 'other')
PHASES = frozenset(('pre', 'checkpoint', 'post'))
NEXT_ACTIONS = frozenset('continue_current_ingest resume_local_catalog continue_evidence_scan '
    'review_source_errors review_unsupported_shapes review_held_sources provide_private_input '
    'verify_application_binding repair_report_delivery inspect_metadata_unavailable '
    'review_resource_limit restore_source_read_access retained_ingest_complete'.split())
CATALOG_REASONS = frozenset(('read_permission_denied', 'source_missing', 'schema_shape_unrecognized',
    'reviewed_adapter_contract', 'catalog_descriptor', 'other'))
ACQUIRED_REASONS = frozenset('schema_unknown required_field_missing record_not_object '
    'unsupported_role unsupported_format csv_duplicate_header csv_row_width xml_dtd_forbidden '
    'xml_entity_forbidden xml_invalid xml_depth_cap xml_record_cap xml_no_menu_nodes '
    'ambiguous_join_scope reference_without_native_id source_error encoding_invalid csv_invalid '
    'source_size_cap acquisition_unverified json_record_invalid json_line_cap json_framing_invalid'.split())
ACQUIRED_REASONS = frozenset('acquired_menu_' + x for x in ACQUIRED_REASONS) | {'other'}
RECIPE_REASONS = frozenset('''acquired_recipe_source_error acquired_recipe_ingredient_count_cap
    acquired_recipe_step_count_cap acquired_recipe_process_node_cap acquired_recipe_projection_size_cap
    acquisition_receipt_not_verified archive_member_count_cap archive_notice_size_cap
    archive_recipe_size_cap duplicate_archive_member_name duplicate_archive_notice
    expanded_byte_cap invalid_expansion_limit unsafe_archive_member unselected_acquired_adapter
    foodista_record_shape foodista_record_size_cap foodista_repeated_section
    foodista_sections_ambiguous foodista_step_number_sequence foodista_text_missing
    foodista_title_missing foodista_empty_or_ambiguous_sections forkrecipe_ingredient_shape
    forkrecipe_instruction_shape forkrecipe_missing_full_recipe_fields forkrecipe_process_node_shape
    html_structure_cap medline_headingless_ingredients_ambiguous medline_html_size_cap
    medline_ingredient_heading_missing medline_recipe_body_missing
    medline_recipe_sections_ambiguous medline_title_ambiguous
    javascript_depth_cap javascript_duplicate_key javascript_input_not_text
    javascript_invalid_binding javascript_invalid_parser_limit javascript_invalid_unicode
    javascript_invalid_unicode_escape javascript_legacy_octal_escape javascript_nonfinite_number
    javascript_nonliteral_value javascript_numeric_limit javascript_object_key_not_literal
    javascript_prototype_key javascript_recipe_root_not_object javascript_size_cap
    javascript_string_linebreak javascript_template_interpolation javascript_token_cap
    javascript_unpaired_surrogate javascript_unsupported_escape javascript_unsupported_export
    javascript_unsupported_structure javascript_unsupported_token javascript_unterminated_comment
    javascript_unterminated_string duplicate_json_key nonfinite_json invalid_json invalid_unicode
    archive_invalid compressed_source_invalid source_changed_during_read recipe_title_missing
    recipe_field_type ingredient_not_text_or_object instruction_depth_cap instruction_not_text
    wrong_acquired_recipe_domain'''.split())
ACQUIRED_REASONS = ACQUIRED_REASONS | RECIPE_REASONS
ACQUIRED_REASON_COLUMNS = tuple(sorted(ACQUIRED_REASONS))
SCHEMA_NEED_COLUMNS = ('acquired_menu_schema_unknown', 'acquired_menu_xml_no_menu_nodes',
    'acquired_menu_required_field_missing', 'acquired_menu_ambiguous_join_scope',
    'acquired_menu_reference_without_native_id', 'other')
ADAPTER_COUNT_COLUMNS = ('input_records', 'emitted_records', 'documents_examined',
    'non_recipe_documents', 'quarantined_records', 'projected_recipes',
    'ingredient_mentions', 'citations', 'duplicate_records', 'archive_members',
    'archive_non_recipe_members', 'template_members')
METRICS = ('read', 'written', 'unchanged', 'reused_rows', 'skipped', 'errors',
    'failed_sources', 'accepted_rows', 'stored_records', 'unresolved_references',
    'deduplicated_records', 'coverage_records')
PERFORMANCE_FIELDS = ('elapsed_ms', 'active_source_elapsed_ms', 'since_last_progress_ms',
    'active_source_bytes', 'sources_timed', 'completed_source_elapsed_ms')
RESOURCE_FIELDS = ('workers', 'elapsed_seconds', 'disk_free_bytes', 'reserve_bytes',
    'max_seconds', 'max_rows_per_source', 'process_peak_rss_bytes', 'process_cpu_seconds')
CURSOR_FIELDS = ('assignments_inspected', 'cursor_known', 'cursor_sum',
    'read_complete', 'resumable', 'written_known', 'written_sum')
QUALITY_CODES = frozenset(('collector_failed', 'private_write_failed',
    'descriptor_invalid', 'counter_invalid', 'checkpoint_sample_incomplete'))


def _utc():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def _mapping(value):
    return value if type(value) is dict else {}


def _count(value, default=None):
    return value if type(value) is int and 0 <= value <= MAX_COUNT else default


def _enum(value, allowed, default):
    return value if type(value) is str and value in allowed else default


def _hist(value, allowed, other='other'):
    """Unknown labels coalesce into a fixed bucket; valid counts are never lost."""
    result = {}
    for key, count in _mapping(value).items():
        if _count(count) is not None and count:
            key = _enum(key, allowed, other)
            result[key] = result.get(key, 0) + count
    return dict(sorted(result.items()))


def _vector(value, size, signed=False):
    value = value if type(value) is list and len(value) == size else [None] * size
    return [x if type(x) is int and (-MAX_COUNT if signed else 0) <= x <= MAX_COUNT
            else None for x in value]


def _reason_vector(value, columns=ACQUIRED_REASON_COLUMNS):
    if type(value) is list:
        return [_count(x, 0) for x in value] if len(value) == len(columns) else [0] * len(columns)
    counts = _hist(value, columns)
    return [counts.get(code, 0) for code in columns]


def sanitize_evidence(value):
    """Allowlisted public schema. Sanitization is not validation of hostile input."""
    value = _mapping(value)
    catalog = _mapping(value.get('catalog'))
    observations = _mapping(value.get('observations'))
    cursor = _mapping(value.get('cursors'))
    resources = _mapping(value.get('resources'))
    schema_details = _mapping(value.get('schema_details'))
    diagnostics = _mapping(value.get('adapter_diagnostics'))
    performance = _mapping(value.get('performance'))
    safe = {'schema': SCHEMA,
        'status': _enum(value.get('status'), ('available', 'partial', 'unknown'), 'unknown'),
        'phase': _enum(value.get('phase'), PHASES, 'checkpoint'),
        'observed_at': value.get('observed_at') if type(value.get('observed_at')) is str and STAMP.fullmatch(value['observed_at']) else '1970-01-01T00:00:00Z',
        'snapshot_scope': 'independent_observations_not_atomic',
        'source_order': 'acquired_adapter_groups_then_retained_one_writer_per_domain',
        'catalog': {'total': _count(catalog.get('total'), 0),
            'inspected': _count(catalog.get('inspected'), 0),
            'remaining': _count(catalog.get('remaining'), 0),
            'discovery_complete': catalog.get('discovery_complete') is True,
            'formats': _hist(catalog.get('formats'), FORMATS),
            'shapes': _hist(catalog.get('shapes'), SHAPES),
            'shape_bases': _hist(catalog.get('shape_bases'), SHAPE_BASES),
            'eligibility': _hist(catalog.get('eligibility'), ELIGIBILITY),
            'reason_codes': _hist(catalog.get('reason_codes'), CATALOG_REASONS),
            'field_presence': _hist(catalog.get('field_presence'), FIELDS),
            'field_types': _hist(catalog.get('field_types'), FIELD_TYPES, 'unknown'),
            'fields_omitted': _count(catalog.get('fields_omitted'), 0),
            'eligibility_columns': list(ELIGIBILITY_COLUMNS),
            'adapter_route_columns': list(ADAPTER_ROUTES),
            'domain_mappings': {}},
        'schema_details': {'status': _enum(schema_details.get('status'), ('available', 'partial', 'unavailable'), 'unavailable'),
            'artifact': 'ingest-schema.private.json',
            'artifact_sha256': schema_details.get('artifact_sha256') if type(schema_details.get('artifact_sha256')) is str and re.fullmatch('[a-f0-9]{64}', schema_details['artifact_sha256']) else None,
            'representatives': _count(schema_details.get('representatives'), 0),
            'unknown_shape_descriptors': _count(schema_details.get('unknown_shape_descriptors'), 0),
            'field_types_basis': 'explicit_descriptor_metadata_else_unknown'},
        'metric_columns': list(METRICS),
        'metric_scope': 'engine_observed_source_rows_not_distinct_entities',
        'observations': {},
        'cursor_columns': list(CURSOR_FIELDS),
        'cursors': {'status': _enum(cursor.get('status'), ('available', 'partial', 'unavailable'), 'unavailable'),
            'detail_rows_total': _count(cursor.get('detail_rows_total')),
            'detail_rows_inspected': _count(cursor.get('detail_rows_inspected'), 0),
            'unit': 'adapter_output_ordinals_not_physical_lines', 'domains': {}},
        'resources': {k: _count(resources.get(k)) for k in RESOURCE_FIELDS},
        'performance': {'columns': list(PERFORMANCE_FIELDS),
            'scope': 'current_invocation_wall_clock_not_cpu_stops_at_domain_completion',
            'byte_scope': 'active_source_catalog_file_size_not_processed_bytes',
            'source_timing_scope': 'ingest_calls_including_completed_cursor_checks',
            'domains': {}},
        'adapter_diagnostics': {
            'scope': 'current_invocation_completed_source_summaries_not_durable_error_entries',
            'reason_columns': list(ACQUIRED_REASON_COLUMNS),
            'schema_need_columns': list(SCHEMA_NEED_COLUMNS),
            'count_columns': list(ADAPTER_COUNT_COLUMNS),
            'count_scope': 'observed_parser_projections_not_store_acceptance_or_global_dedup',
            'source_summaries_total': _count(diagnostics.get('source_summaries_total'), 0),
            'source_summaries_inspected': _count(diagnostics.get('source_summaries_inspected'), 0),
            'remaining': _count(diagnostics.get('remaining'), 0),
            'domains': {}},
        'next_actions': sorted({x for x in value.get('next_actions', []) if type(x) is str and x in NEXT_ACTIONS}) if type(value.get('next_actions')) is list else [],
        'quality_codes': sorted({x for x in value.get('quality_codes', []) if type(x) is str and x in QUALITY_CODES}) if type(value.get('quality_codes')) is list else [],
        'next_run': 'existing_run_collects_again_without_fetch_or_diagnostic_gate'}
    for domain in DOMAINS:
        safe['performance']['domains'][domain] = _vector(_mapping(performance.get('domains')).get(domain), len(PERFORMANCE_FIELDS))
        mapping = _mapping(_mapping(catalog.get('domain_mappings')).get(domain))
        safe['catalog']['domain_mappings'][domain] = {'adapter': ADAPTERS[domain],
            'assignments': _count(mapping.get('assignments'), 0),
            'eligibility': _vector(mapping.get('eligibility', [0] * len(ELIGIBILITY_COLUMNS)), len(ELIGIBILITY_COLUMNS)),
            'adapter_routes': _vector(mapping.get('adapter_routes', [0] * len(ADAPTER_ROUTES)), len(ADAPTER_ROUTES))}
        row = _mapping(observations.get(domain))
        safe['observations'][domain] = {
            'before': _vector(row.get('before'), len(METRICS)),
            'current': _vector(row.get('current'), len(METRICS)),
            'delta': _vector(row.get('delta'), len(METRICS), signed=True)}
        safe['cursors']['domains'][domain] = _vector(_mapping(cursor.get('domains')).get(domain), len(CURSOR_FIELDS))
        diagnostic = _mapping(_mapping(diagnostics.get('domains')).get(domain))
        safe['adapter_diagnostics']['domains'][domain] = {
            'reason_counts': _reason_vector(diagnostic.get('reason_counts')),
            'schema_need_counts': _reason_vector(diagnostic.get('schema_need_counts'), SCHEMA_NEED_COLUMNS),
            'parser_counts': _vector(diagnostic.get('parser_counts'), len(ADAPTER_COUNT_COLUMNS))}
    # The existing report's error_telemetry is authoritative; duplication would
    # waste receipt space and obscure the different durable/observed populations.
    error_histograms = _mapping(value.get('error_histograms'))
    safe['error_histograms'] = {'location': 'domains.error_telemetry_scoped_class_origin_reason_counts',
        'domains_available': min(8, _count(error_histograms.get('domains_available'), 0))}
    return safe


def validate_evidence(value):
    """Strict transport boundary, including types (bool must not equal int)."""
    safe = sanitize_evidence(value)
    if json.dumps(value, sort_keys=True, allow_nan=False) != json.dumps(safe, sort_keys=True, allow_nan=False):
        raise ValueError('invalid_ingest_evidence')
    catalog = safe['catalog']
    diagnostics = safe['adapter_diagnostics']
    if diagnostics['source_summaries_inspected'] + diagnostics['remaining'] != diagnostics['source_summaries_total']:
        raise ValueError('invalid_ingest_evidence_counts')
    if catalog['inspected'] + catalog['remaining'] != catalog['total']:
        raise ValueError('invalid_ingest_evidence_counts')
    for field in ('formats', 'shapes', 'shape_bases', 'eligibility', 'reason_codes'):
        if sum(catalog[field].values()) != catalog['inspected']:
            raise ValueError('invalid_ingest_evidence_counts')
    for row in catalog['domain_mappings'].values():
        if (any(x is None for x in row['eligibility'] + row['adapter_routes'])
                or sum(row['eligibility']) != row['assignments']
                or sum(row['adapter_routes']) != row['assignments']):
            raise ValueError('invalid_ingest_evidence_counts')
    return value


def _domains(source):
    raw = source.get('domains', source.get('domain', []))
    if type(raw) is str:
        raw = [raw]
    return [d for d in DOMAINS if type(raw) in (list, tuple) and d in raw]


def _eligibility(source, domain=None):
    meta = _mapping(source.get('metadata'))
    if domain in ('user_profiles', 'inventory') and not (meta.get('user_supplied') is True and meta.get('household_scope') is True):
        return 'awaiting_input'
    disposition = source.get('disposition')
    if source.get('restricted') or source.get('incomplete') or disposition in ('restricted', 'restricted-held', 'blocked', 'incomplete-hold', 'skip'):
        return 'held'
    if disposition in ('documentation', 'metadata-only', 'duplicate', 'excluded', 'historical-demo', 'unclassified', 'deferred'):
        return 'unqualified'
    if disposition in ('missing', 'unreadable'):
        return 'failed'
    if disposition == 'unsupported':
        return 'unsupported'
    if disposition == 'adapter-required':
        return 'adapter_required'
    if disposition == 'existing-store' or source.get('existing_store'):
        return 'readonly_reuse'
    return 'candidate' if disposition in (None, 'candidate') else 'other'


def _shape(source):
    if set(_domains(source)) & {'user_profiles', 'inventory'}:
        return 'private_redacted'
    hint = source.get('schema_shape')
    if type(hint) is str and hint in SHAPES:
        return hint
    fields = source.get('fields')
    if type(fields) is not list or not fields:
        return 'not_sampled'
    fields = {re.sub('[^a-z0-9]', '', field[:128].lower())
              for field in fields[:100] if type(field) is str}
    if fields & {'recipeingredient', 'recipeinstructions'}:
        return 'recipe_jsonld'
    if {'ingredients', 'steps'} <= fields or {'ingredients', 'instructions'} <= fields or fields & {'directions', 'recipes'}:
        return 'recipe_structured'
    if fields & {'menuitems', 'menusection', 'hasmenusection', 'hasmenuitem'}:
        return 'menu_structured'
    if fields & {'barcode', 'gtin', 'productname', 'fdcid'}:
        return 'product'
    if fields & {'nutrientid', 'nutrients', 'energykcal', 'nutrientname'}:
        return 'nutrient'
    if fields & {'geometry', 'latitude', 'longitude', 'supplier'}:
        return 'place'
    if fields & {'citation', 'citations', 'bibliography'}:
        return 'citation'
    return 'tabular_unknown' if source.get('format') in ('csv', 'tsv', 'sqlite', 'parquet') else 'structured_unknown'


def _blank_catalog(total, complete):
    return {'total': total, 'inspected': 0, 'remaining': total, 'discovery_complete': complete,
        'formats': {}, 'shapes': {}, 'shape_bases': {}, 'eligibility': {}, 'reason_codes': {},
        'field_presence': {}, 'field_types': {}, 'fields_omitted': 0,
        'domain_mappings': {d: {'adapter': ADAPTERS[d], 'assignments': 0,
            'eligibility': [0] * len(ELIGIBILITY_COLUMNS),
            'adapter_routes': [0] * len(ADAPTER_ROUTES)} for d in DOMAINS}}


def _increment(mapping, key):
    mapping[key] = mapping.get(key, 0) + 1


def _safe_path(path):
    path = Path(path).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('symlink_evidence_path')
    return path


def _read_private(path):
    """Bounded regular-file read; a corrupted/FIFO checkpoint cannot block work."""
    path = _safe_path(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError('evidence_checkpoint_not_regular')
        raw = stream.read(MAX_PRIVATE_BYTES + 1)
    if len(raw) > MAX_PRIVATE_BYTES:
        raise ValueError('evidence_private_size_limit')
    return raw


def _atomic_private(path, value):
    path = _safe_path(path)
    raw = (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
    if len(raw) > MAX_PRIVATE_BYTES:
        raise ValueError('evidence_private_size_limit')
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = path.with_name('.' + path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with os.fdopen(os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), 'wb') as stream:
            stream.write(raw)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


class EvidenceCollector:
    """Incremental descriptor scan, never an ingest prerequisite.

    ``pending_private`` is the snapshot ALREADY obtained by the engine's existing
    metadata collector; do not open/requery a database to manufacture this input.
    Caps bound each side-work slice. Uninspected counts and cursor coverage remain
    explicit; subsequent natural checkpoints/runs continue rather than hiding it.
    """
    def __init__(self, sources, config, catalog=None):
        self.sources = sources if type(sources) is list else list(sources)
        self.config = config
        self.path = Path(config['state_dir']) / 'ingest-evidence.private.json'
        self.catalog_id = config.get('catalog_sha256')
        self.catalog = _blank_catalog(len(self.sources), not config.get('catalog_truncated', False))
        self.before = None
        self.examples = []
        self.schema_examples = []
        self.schema_digest = None
        self.schema_representatives = 0
        self.quality = set()
        self.max_items = min(10000, max(1, int(config.get('evidence_max_items', 2000))))
        self.max_seconds = min(.25, max(.001, float(config.get('evidence_max_seconds', .05))))
        self._restore()

    def _restore(self):
        # Only our fixed-name, bounded checkpoint is read; never source content.
        try:
            raw = _read_private(self.path)
            previous = json.loads(raw)
            if (not isinstance(self.catalog_id, str) or not re.fullmatch('[a-f0-9]{64}', self.catalog_id)
                    or previous.get('schema') != PRIVATE_SCHEMA or previous.get('catalog_sha256') != self.catalog_id):
                return
            summary = validate_evidence(previous['summary'])
            if summary['catalog']['total'] == len(self.sources):
                self.catalog = summary['catalog']
                self.catalog['discovery_complete'] = not self.config.get('catalog_truncated', False)
                self.schema_digest = summary['schema_details']['artifact_sha256']
                self.schema_representatives = summary['schema_details']['representatives']
                if self.schema_digest:
                    try:
                        raw_schema = _read_private(self.path.with_name('ingest-schema.private.json'))
                        if hashlib.sha256(raw_schema).hexdigest() != self.schema_digest:
                            raise ValueError('evidence_artifact_changed')
                    except (OSError, ValueError):
                        self.schema_digest = None
                        self.schema_representatives = 0
                # Prior examples are diagnostic only, and their local contents
                # are not needed to resume aggregate counts.
        except (OSError, ValueError, TypeError, KeyError, RecursionError):
            pass

    def _scan(self, deadline):
        scanned = 0
        while self.catalog['inspected'] < len(self.sources) and scanned < self.max_items and time.monotonic() < deadline:
            index = self.catalog['inspected']
            source = self.sources[index]
            if type(source) is not dict:
                source = {}
                self.quality.add('descriptor_invalid')
            fmt = _enum(source.get('format'), FORMATS, 'other')
            shape = _shape(source)
            eligibility = _eligibility(source)
            _increment(self.catalog['formats'], fmt)
            _increment(self.catalog['shapes'], shape)
            explicit_shape = type(source.get('schema_shape')) is str and source.get('schema_shape') in SHAPES
            reviewed_contract = _mapping(source.get('metadata')).get('schema_shape_basis') == 'reviewed_manifest_adapter_contract_not_parsed'
            basis = ('private_redacted' if shape == 'private_redacted' else
                'reviewed_adapter_contract' if explicit_shape or reviewed_contract else
                'not_sampled' if shape == 'not_sampled' else 'catalog_sample_fields')
            _increment(self.catalog['shape_bases'], basis)
            _increment(self.catalog['eligibility'], eligibility)
            reason = source.get('reason')
            reason = ('read_permission_denied' if reason in ('read_permission_denied', 'PermissionError') else
                'source_missing' if reason in ('selected_path_not_present', 'source_missing', 'FileNotFoundError') else
                'schema_shape_unrecognized' if shape in ('tabular_unknown', 'structured_unknown', 'not_sampled') else
                'reviewed_adapter_contract' if explicit_shape else 'catalog_descriptor')
            _increment(self.catalog['reason_codes'], reason)
            fields = source.get('fields')
            if type(fields) is not list and shape == 'not_sampled' and len(self.schema_examples) < 32:
                self.schema_examples.append({'source_key': source_key(source), 'descriptor_index': index,
                    'format': fmt, 'shape': shape, 'domains': _domains(source), 'fields': [],
                    'required_action': 'review_unsupported_shapes', 'reason': 'schema_fields_unavailable',
                    'source_rows_collected': False})
            if type(fields) is list and shape != 'private_redacted':
                self.catalog['fields_omitted'] += max(0, len(fields) - 100)
                types = _mapping(source.get('field_types'))
                for field in fields[:100]:
                    if type(field) is not str:
                        self.catalog['fields_omitted'] += 1
                        continue
                    token = re.sub('[^a-z0-9]', '', field[:128].lower())
                    _increment(self.catalog['field_presence'], _enum(token, FIELDS, 'other'))
                    _increment(self.catalog['field_types'], _enum(types.get(field), FIELD_TYPES, 'unknown'))
                if (shape in ('tabular_unknown', 'structured_unknown', 'not_sampled')
                        and len(self.schema_examples) < 32):
                    self.schema_examples.append({'source_key': source_key(source), 'descriptor_index': index,
                        'format': fmt, 'shape': shape, 'domains': _domains(source),
                        'fields': [f[:128] for f in fields[:100] if type(f) is str],
                        'required_action': 'review_unsupported_shapes',
                        'reason': 'schema_shape_unrecognized', 'source_rows_collected': False})
            for domain in _domains(source):
                row = self.catalog['domain_mappings'][domain]
                row['assignments'] += 1
                row['eligibility'][ELIGIBILITY_COLUMNS.index(_eligibility(source, domain))] += 1
                route = source.get('acquired_adapter')
                route = 'retained_dispatcher' if route is None else _enum(route, ADAPTER_ROUTES, 'other')
                row['adapter_routes'][ADAPTER_ROUTES.index(route)] += 1
            # Bounded representatives point into the existing private catalog.
            # No source rows/exception strings are collected, even privately.
            if len(self.examples) < 64 and not set(_domains(source)) & {'user_profiles', 'inventory'}:
                self.examples.append({'source_key': source_key(source), 'descriptor_index': index,
                    'format': fmt, 'shape': shape, 'eligibility': eligibility,
                    'domains': _domains(source)})
            self.catalog['inspected'] += 1
            self.catalog['remaining'] -= 1
            scanned += 1

    def _metrics(self, report, results):
        current = {}
        pending = _mapping(_mapping(report.get('pending_work')).get('domains'))
        for domain in DOMAINS:
            row = _mapping(_mapping(report.get('domains')).get(domain))
            owned = _mapping(_mapping(results).get(domain))
            values = {k: row.get(k) for k in METRICS}
            # Optional values are accepted only when the owning worker supplied
            # them; written+unchanged is NOT falsely relabelled accepted/unique.
            for key in ('accepted_rows', 'stored_records', 'unresolved_references', 'deduplicated_records', 'coverage_records'):
                values[key] = owned.get(key, row.get(key))
            values['failed_sources'] = _mapping(pending.get(domain)).get('failed')
            current[domain] = [_count(values[k]) for k in METRICS]
            if any(v is not None and _count(v) is None for v in values.values()):
                self.quality.add('counter_invalid')
        return current

    def _cursors(self, pending_private, deadline):
        rows = _mapping(pending_private).get('sources')
        result = {'status': 'unavailable', 'detail_rows_total': None, 'detail_rows_inspected': 0,
            'domains': {d: [None] * len(CURSOR_FIELDS) for d in DOMAINS}}
        if type(rows) is not list:
            return result
        result.update(status='available', detail_rows_total=len(rows),
            domains={d: [0] * len(CURSOR_FIELDS) for d in DOMAINS})
        for row in rows:
            if result['detail_rows_inspected'] >= self.max_items or time.monotonic() >= deadline:
                result['status'] = 'partial'
                break
            result['detail_rows_inspected'] += 1
            if type(row) is not dict or row.get('domain') not in DOMAINS or row.get('synthetic_requirement'):
                continue
            values = result['domains'][row['domain']]
            values[0] += 1
            cursor = _count(row.get('cursor'))
            written = _count(row.get('written'))
            values[1] += cursor is not None
            values[2] += cursor or 0
            values[3] += row.get('read_complete') is True
            values[4] += cursor is not None and not row.get('read_complete') and row.get('status') == 'partial'
            values[5] += written is not None
            values[6] += written or 0
            if any(x > MAX_COUNT for x in values):
                self.quality.add('counter_invalid')
                result['status'] = 'partial'
        return result

    def _resources(self, report):
        result = {key: _count(report.get(key, self.config.get(key))) for key in RESOURCE_FIELDS}
        try:
            result['disk_free_bytes'] = shutil.disk_usage(_safe_path(self.path.parent)).free
        except (OSError, ValueError):
            pass
        try:
            import resource
            import sys
            usage = resource.getrusage(resource.RUSAGE_SELF)
            result['process_peak_rss_bytes'] = int(usage.ru_maxrss * (1 if sys.platform == 'darwin' else 1024))
            result['process_cpu_seconds'] = int(usage.ru_utime + usage.ru_stime)
        except (ImportError, OSError, ValueError):
            pass
        return result

    def _diagnostics(self, results, deadline):
        rows = {d: _mapping(_mapping(results).get(d)).get('sources', []) for d in DOMAINS}
        rows = {d: value if type(value) is list else [] for d, value in rows.items()}
        total = sum(len(value) for value in rows.values())
        result = {'source_summaries_total': total, 'source_summaries_inspected': 0,
            'remaining': total, 'domains': {d: {'reason_counts': {}, 'schema_need_counts': {},
                'parser_counts': [None] * len(ADAPTER_COUNT_COLUMNS)} for d in DOMAINS}}
        for domain, sources in rows.items():
            for row in sources:
                if result['source_summaries_inspected'] >= self.max_items or time.monotonic() >= deadline:
                    return result
                result['source_summaries_inspected'] += 1
                result['remaining'] -= 1
                diagnostics = _mapping(_mapping(row).get('diagnostics'))
                stats = {**_mapping(_mapping(row).get('record_kinds')), **diagnostics}
                for i, key in enumerate(ADAPTER_COUNT_COLUMNS):
                    if _count(stats.get(key)) is not None:
                        vector = result['domains'][domain]['parser_counts']
                        vector[i] = (vector[i] or 0) + stats[key]
                for name, source_name in (('reason_counts', 'reason_counts'), ('schema_need_counts', 'schema_needs')):
                    counts = _hist(diagnostics.get(source_name), ACQUIRED_REASONS)
                    for code, count in counts.items():
                        target = result['domains'][domain][name]
                        target[code] = target.get(code, 0) + count
        return result

    def _actions(self, report):
        actions = {'verify_application_binding'}
        pending = _mapping(report.get('pending_work'))
        totals = _mapping(pending.get('totals'))
        if not self.catalog['discovery_complete']:
            actions.add('resume_local_catalog')
        if self.catalog['remaining']:
            actions.add('continue_evidence_scan')
        if pending.get('status') != 'available':
            actions.add('inspect_metadata_unavailable')
        if _count(totals.get('files_remaining'), 0):
            actions.add('continue_current_ingest')
        if _count(totals.get('unsupported'), 0) or self.catalog['eligibility'].get('adapter_required'):
            actions.add('review_unsupported_shapes')
        if any(self.catalog['shapes'].get(k) for k in ('tabular_unknown', 'structured_unknown', 'not_sampled')):
            actions.add('review_unsupported_shapes')
        if _count(totals.get('held'), 0):
            actions.add('review_held_sources')
        if pending.get('awaiting_input_domains'):
            actions.add('provide_private_input')
        if _count(report.get('report_delivery_errors'), 0):
            actions.add('repair_report_delivery')
        if self.catalog['reason_codes'].get('read_permission_denied'):
            actions.add('restore_source_read_access')
        for row in _mapping(report.get('domains')).values():
            row = _mapping(row)
            if _count(row.get('errors'), 0) or _mapping(row.get('error_telemetry')).get('class_counts'):
                actions.add('review_source_errors')
            codes = row.get('error_codes')
            if type(codes) is list and set(codes) & {'BudgetExceeded', 'resource_cap', 'resource_budget', 'resource_limit'}:
                actions.add('review_resource_limit')
        if (report.get('status') == 'complete' and pending.get('status') == 'available'
                and self.catalog['discovery_complete'] and not self.catalog['remaining']
                and not any(_count(totals.get(k), 0) for k in ('files_remaining', 'failed', 'unsupported', 'unknown', 'partial'))):
            actions.add('retained_ingest_complete')
        return sorted(actions)

    def capture(self, phase, report, *, results=None, pending_private=None):
        """Best-effort pre/checkpoint/post hook; reporter failures never escape."""
        try:
            started = time.monotonic()
            # Separate bounded slices prevent a large descriptor page from
            # starving cursor visibility; no full-source parsing is performed.
            self._scan(started + self.max_seconds)
            current = self._metrics(report, results)
            if self.before is None:
                self.before = current
            cursors = self._cursors(pending_private, time.monotonic() + self.max_seconds)
            diagnostics = self._diagnostics(results, time.monotonic() + self.max_seconds)
            quality = set(self.quality)
            if cursors['status'] == 'partial':
                quality.add('checkpoint_sample_incomplete')
            if diagnostics['remaining']:
                quality.add('checkpoint_sample_incomplete')
            summary = sanitize_evidence({'status': 'partial' if self.catalog['remaining'] or quality else 'available',
                'phase': phase, 'observed_at': _utc(), 'catalog': self.catalog,
                'observations': {d: {'before': self.before[d], 'current': current[d],
                    'delta': [b - a if a is not None and b is not None else None for a, b in zip(self.before[d], current[d])]} for d in DOMAINS},
                'cursors': cursors, 'resources': self._resources(report),
                'performance': {'domains': {d: [_mapping(_mapping(_mapping(report.get('domains')).get(d)).get('timing')).get(k) for k in PERFORMANCE_FIELDS] for d in DOMAINS}},
                'adapter_diagnostics': diagnostics,
                'error_histograms': {'domains_available': sum(type(_mapping(_mapping(report.get('domains')).get(d)).get('error_telemetry')) is dict for d in DOMAINS)},
                'quality_codes': sorted(quality), 'next_actions': self._actions(report)})
            unknown_shapes = sum(self.catalog['shapes'].get(k, 0) for k in ('tabular_unknown', 'structured_unknown', 'not_sampled'))
            if self.schema_examples:
                detail = {'schema': 'offmenu-ingest-schema-private/1',
                    'catalog_sha256': self.catalog_id, 'observed_at': summary['observed_at'],
                    'basis': 'catalog_descriptor_fields_not_source_rows',
                    'representatives': self.schema_examples}
                try:
                    _atomic_private(self.path.with_name('ingest-schema.private.json'), detail)
                    # Hash the exact canonical artifact bytes without rereading.
                    raw = (json.dumps(detail, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
                    self.schema_digest = hashlib.sha256(raw).hexdigest()
                    self.schema_representatives = len(self.schema_examples)
                except Exception:
                    self.schema_digest = None
                    self.schema_representatives = 0
                    summary['quality_codes'] = sorted(set(summary['quality_codes']) | {'private_write_failed'})
                    summary['status'] = 'partial'
            summary['schema_details'] = {'status': 'unavailable' if unknown_shapes and not self.schema_digest else 'partial' if self.schema_representatives < unknown_shapes else 'available',
                'artifact': 'ingest-schema.private.json', 'artifact_sha256': self.schema_digest,
                'representatives': self.schema_representatives, 'unknown_shape_descriptors': unknown_shapes,
                'field_types_basis': 'explicit_descriptor_metadata_else_unknown'}
            if any(any(r['schema_need_counts']) for r in summary['adapter_diagnostics']['domains'].values()):
                summary['next_actions'] = sorted(set(summary['next_actions']) | {'review_unsupported_shapes'})
            validate_evidence(summary)
            try:
                _atomic_private(self.path, {'schema': PRIVATE_SCHEMA, 'catalog_sha256': self.catalog_id,
                    'summary': summary, 'descriptor_examples': self.examples,
                    'private_catalog_reference': 'catalog.private.json',
                    'source_rows_collected': False})
            except Exception:
                summary['quality_codes'] = sorted(set(summary['quality_codes']) | {'private_write_failed'})
                summary['status'] = 'partial'
            return summary
        except Exception:
            # Preserve fixed schema even if malformed optional metadata fails.
            return sanitize_evidence({'status': 'unknown', 'phase': phase, 'observed_at': _utc(),
                'quality_codes': ['collector_failed'], 'next_actions': ['inspect_metadata_unavailable'],
                'catalog': _blank_catalog(len(self.sources), False)})
