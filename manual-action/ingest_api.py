"""Stable adapter contract for local retained-data ingestion (stdlib only).

Adapter: ``run_domain(domain, sources, context) -> dict``. Sources are plain
JSON-safe dictionaries: ``id`` (stable opaque id), ``path`` (private local path),
``format`` (jsonl/json/csv/tsv/sqlite/etc), ``domain``, optional ``license``,
``restricted`` (bool), ``loaded`` (bool), ``target`` and format-specific keys.
Catalogs must explicitly mark restricted inputs. Paths/payloads stay local.

Context is an IngestContext object; also supports context['name']/get(name).
* context.store: per-domain DomainStore, one process-wide writer per DB.
* context.store.ingest(source, iterable_of_record_dicts): transactional batched
  idempotent writes and checkpointing; returns source summary. Records may use
  ``id``/``source_id`` for stable ids; all fields are kept as JSON and simple
  scalar fields in a queryable record_fields relation (bounded normalized-field
  indexing; full input payload remains intact). Optional ``relations``
  list ({kind,target_domain,target_id,...}) is preserved relationally.
* context.ingest(source, records): alias to store.ingest with budget handling.
* context.progress(**counts): emits sanitized counters, never payloads.
* context.check_budget(): raises BudgetExceeded on disk/time/record caps.
* context.report_error(source, exc): durably records sanitized error class per source;
  private log holds opaque source id/class only, not raw payload or exception text.
  Source completion with parse errors remains partial on unchanged repeat.
* context.config: runtime settings; context.state_dir: private local directory.
* context.cancelled: threading.Event. Stop iteration if set.

Store returns counts: read, written, unchanged, errors, skipped; complete,
partial, skipped, failed status. Source-level errors MUST NOT stop other sources.
Do not open arbitrary existing DBs for writing: context.store is additive staging.
Existing loaded database bindings are read-only catalog evidence until a proven
compatible adapter explicitly selects them. No downloads or code execution.
"""
from __future__ import annotations

DOMAINS = ('barcodes', 'ingredients', 'recipes', 'dietary', 'user_profiles',
           'inventory', 'suppliers', 'citations')
COUNTERS = ('read', 'written', 'unchanged', 'errors', 'skipped')
GLOBAL_BUDGET_DEFAULTS = {'reserve_bytes': 2 * 1024**3, 'max_seconds': 0,
                         'max_rows_per_source': 0}
GLOBAL_BUDGET_REASONS = frozenset(('cancelled', 'wall_time_cap', 'disk_reserve'))


def budget_seconds(value):
    """Bounded finite seconds; fractional configured limits remain exact."""
    import math
    return value if type(value) in (int, float) and 0 <= value <= 10**15 and math.isfinite(value) else None


def sanitize_budget_stop(value):
    """First global stop observation, separate from source/row error counts."""
    if (not isinstance(value, dict) or type(value.get('reason')) is not str
            or value['reason'] not in GLOBAL_BUDGET_REASONS):
        return None
    fields = ('elapsed_ms', 'disk_free_bytes', 'reserve_bytes', 'max_rows_per_source')
    return {'reason': value['reason'],
        **{key: raw if type(raw) is int and 0 <= raw <= 10**15 else None
           for key in fields for raw in [value.get(key)]},
        'max_seconds': budget_seconds(value.get('max_seconds'))}

class BudgetExceeded(RuntimeError):
    """A resource cap stopped work cleanly; durable batches remain resumable."""

class SourceChanged(RuntimeError):
    """A retained source changed while it was being read."""


def source_key(source):
    """Stable opaque identifier; never expose source filename in public reports."""
    import hashlib
    raw = str(source.get('id') or source.get('path') or 'unknown')
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()[:24]
