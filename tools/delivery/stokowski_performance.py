"""Version 1 terminal, source-data-only performance projection (no I/O/effects).

Policy: observe only; one sample cannot tune resources, capacity, entitlement or
budget. Collect accepted-work measurements separately. Execution is not source
review, validation, served or functional acceptance; no continuous-operation or
billing claim is made. Missing/malformed/over-bound values are null, never zero.
Usage names are unchanged turn.completed counters, not totals inferred across
turns. No prompts, messages, logs, arbitrary event fields or cost are copied.

Provenance digests are SHA256 of exact worker/helper/config/manifest bytes captured
before execution, plus the existing immutable binding/task digest. They identify
source inputs, not independent review. Historical projections lack these unless
supplied. Only owned terminal results qualified by the caller receive this field.
Elapsed is monotonic from before log/process setup through cleanup and handler
restoration, excluding admission/provider setup and pre-start cancellation;
queue time is unavailable. Cancellation can be
known from supervise even if later source checks change the execution status.
Resource peaks are sampled descendants, affinity is supervisor affinity, neither CPU/IO consumption
nor hard quotas. Raw legacy zero peaks without a recorded sample stay unknown
in this projection. Retry/rework/reuse and attempt ordinal are unavailable here.

Contract bounds: identifiers <=128 ASCII characters, 32 output paths <=240 ASCII
characters with SHA256 values, 256 affinity entries, integers <=2**63-1, elapsed
<=86400 seconds. Canonical serialization is sorted compact JSON (<=16384 bytes).
Rollback this additive field/helper if projection leaks data, changes cleanup or
lease release, loses terminal receipts, or breaks existing receipt consumers;
retain original receipts and immutable blockers, never replay effects to migrate.
"""
import json
import re


VERSION = 'offmenu-stokowski-performance/1'
MAX_BYTES = 16384
COUNTERS = ('input_tokens', 'cached_input_tokens', 'output_tokens')
STATUSES = {'succeeded', 'failed', 'cancelled', 'timed_out', 'uncertain',
            'process_budget', 'memory_budget', 'log_budget'}


def _mapping(value):
    return value if isinstance(value, dict) else {}


def _identifier(value):
    return value if (isinstance(value, str) and
                     re.fullmatch(r'[A-Za-z0-9_.:/-]{1,128}', value)) else None


def _hex(value, width=64):
    return value if (isinstance(value, str) and
                     re.fullmatch('[0-9a-f]{%d}' % width, value)) else None


def _integer(value):
    return value if type(value) is int and 0 <= value <= 2**63-1 else None


def _boolean(value):
    return value if type(value) is bool else None


def _outputs(value):
    if not isinstance(value, dict) or len(value) > 32:
        return None
    result = {}
    for path, sha in value.items():
        if (not isinstance(path, str) or len(path) > 240 or
            not re.fullmatch(r'[A-Za-z0-9_./-]+', path) or
            any(p in ('', '.', '..') for p in path.split('/')) or
            _hex(sha) is None):
            return None
        result[path] = sha
    return dict(sorted(result.items()))


def serialize_observation(observation):
    """Canonical JSON for this fixed projection, also suitable for hashing."""
    return json.dumps(observation, sort_keys=True, separators=(',', ':'), allow_nan=False)


def project_observation(receipt, context=None):
    """Project only known allowlisted scalars; context overrides child identities."""
    receipt = _mapping(receipt)
    context = _mapping(context)
    identity = context if context else receipt
    observed = _mapping(receipt.get('observed_resources'))
    declared = _mapping(identity.get('declared_resources'))
    usage = _mapping(receipt.get('usage'))
    provenance = _mapping(context.get('provenance'))
    samples = _integer(receipt.get('resource_sample_count'))
    sampled = samples is not None and samples > 0
    affinity = observed.get('cpu_affinity')
    if not (isinstance(affinity, list) and len(affinity) <= 256 and
            all(type(cpu) is int and 0 <= cpu <= 65535 for cpu in affinity)):
        affinity = None
    else:
        affinity = sorted(set(affinity))
    elapsed = receipt.get('supervise_elapsed_seconds')
    if not (type(elapsed) in (int, float) and 0 <= elapsed <= 86400):
        elapsed = None
    status = receipt.get('status')
    status = status if isinstance(status, str) and status in STATUSES else None
    # Only the worker's event seam establishes where usage/model were observed.
    completed = receipt.get('turn_completed') is True
    counters = {key: _integer(usage.get(key)) if completed else None for key in COUNTERS}
    result = {
        'schema': VERSION,
        'binding': {
            'issue': _identifier(identity.get('issue')),
            'lease': _identifier(identity.get('lease')),
            'attempt': _identifier(identity.get('attempt')),
            'binding_sha256': _hex(identity.get('binding_sha256')),
            'source_head': _hex(identity.get('source_head'), 40),
            'task_sha256': _hex(identity.get('task_sha256')),
        },
        'provenance': {key: _hex(provenance.get(key)) for key in (
            'worker_sha256', 'helper_sha256', 'capacity_policy_sha256', 'manifest_sha256')},
        'requested': {key: _identifier(identity.get(source)) for key, source in (
            ('model', 'requested_model'), ('effort', 'requested_effort'),
            ('provider', 'provider_route'))},
        'observed': {
            'model': _identifier(receipt.get('resolved_model')) if completed else None,
            'provider': None, 'effort': None,
        },
        'declared_resources': {key: _integer(declared.get(key)) for key in (
            'cpu_millis', 'memory_bytes', 'io_slots', 'output_bytes')},
        'sampled_resources': {
            'peak_processes': _integer(observed.get('peak_processes')) if sampled else None,
            'peak_rss_bytes': _integer(observed.get('peak_rss_bytes')) if sampled else None,
            'cpu_affinity': affinity,
            'semantics': 'sampled-descendants; supervisor-affinity; no-cpu-or-io-usage',
        },
        'timing': {'elapsed_seconds': elapsed, 'queue_seconds': None,
                   'semantics': 'monotonic-supervise-setup-through-cleanup' if elapsed is not None else None},
        'usage': {'source': 'turn.completed.usage' if completed else None,
                  'counters': counters},
        'execution': {'status': status,
                      'child_tree_gone': _boolean(receipt.get('child_tree_gone'))},
        'acceptance': {'accepted_delivery': _boolean(receipt.get('accepted_delivery')),
                       'source_review': 'unknown', 'validation': 'unknown',
                       'served': 'unknown', 'functional': 'unknown'},
        'attempt_metadata': {'ordinal': None, 'retry': None, 'rework': None,
                             'reuse': None, 'cancelled': True if (
                                 status == 'cancelled' or context.get('cancelled') is True) else None},
        'output_sha256': _outputs(receipt.get('output_sha256')),
        'advisory_codes': ['COLLECT_ACCEPTED_WORK_MEASUREMENTS', 'NO_TUNING_FROM_SINGLE_SAMPLE'],
    }
    # Fixed shape and validated bounds keep this assertion independent of input size.
    assert len(serialize_observation(result).encode('utf-8')) <= MAX_BYTES
    return result
