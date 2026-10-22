"""Bounded, memory-only app-schema preparation; never activate application state.

Only fixed reviewed checkout sources are read. The helper must report successful
empty-schema checks before preparation is reported ready; deployment and runtime
wiring remain explicitly unverified. Failures never authorize private imports.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys

SCHEMA = 'offmenu-household-schema-preparation/1'
BASELINE = 'af99cdfb4bac3bce9f4badae34333921a0074a76'
BASE_SQL_SHA256 = '48bad7a6e855478f3364f7e43292ccc34aa54802571c943ed9226a3a7270e380'
HELPER = 'scripts/prepare_household_schema.py'
PLAN = 'docs/schema/household-schema-preparation-plan-v1.json'
SQL_PATHS = ('cloud/schema.sql', 'cloud/migrations/20261022-byoc-security-v1.sql',
             'cloud/migrations/20261022-household-domain-v1.sql')
SOURCE_PATHS = (HELPER, PLAN, *SQL_PATHS)
MAX_SOURCE_BYTES = 2 * 1024 * 1024
TIMEOUT_SECONDS = 15
MAX_OUTPUT_BYTES = 16384
HEX = re.compile(r'[0-9a-f]{64}\Z')
REASONS = frozenset(('verified_in_memory', 'sources_unavailable', 'unsafe_source',
    'source_size_limit', 'plan_invalid', 'dependency_mismatch', 'baseline_mismatch',
    'helper_timeout', 'helper_failed', 'invalid_helper_result', 'source_changed',
    'invocation_failed'))
UNAVAILABLE_REASONS = frozenset(('sources_unavailable', 'unsafe_source', 'source_size_limit'))
FALSE_FIELDS = ('external_sources_required', 'private_data_copied', 'credentials_loaded',
    'existing_database_opened', 'deployment_performed', 'application_wiring_verified',
    'artifact_written')


def unavailable(reason='sources_unavailable'):
    return {'schema': SCHEMA, 'status': 'preparation_unavailable', 'reason': reason,
        'operation': 'in_memory_schema_validation_only', 'source_baseline': BASELINE,
        'application_wiring_verified': False, 'deployment_performed': False,
        'security_activation': 'not_performed',
        'source_sha256': {'helper': None, 'plan': None, 'sql': [None] * 3},
        'domain_table_count': None, 'private_rows': None,
        'foreign_key_check': 'not_verified', 'integrity_check': 'not_verified'}


def validate_preparation(value):
    """Strict optional supplement field; no paths, free text or unknown keys."""
    template = unavailable()
    if type(value) is not dict or set(value) != set(template):
        raise ValueError('invalid_household_preparation')
    for key in ('schema', 'operation', 'source_baseline', 'security_activation'):
        if value[key] != template[key]:
            raise ValueError('invalid_household_preparation')
    if value['application_wiring_verified'] is not False or value['deployment_performed'] is not False:
        raise ValueError('invalid_household_preparation')
    if value['status'] not in ('schema_prepared_app_wiring_pending', 'preparation_unavailable', 'preparation_failed') or value['reason'] not in REASONS:
        raise ValueError('invalid_household_preparation')
    sources = value['source_sha256']
    if type(sources) is not dict or set(sources) != {'helper', 'plan', 'sql'} or type(sources['sql']) is not list or len(sources['sql']) != 3:
        raise ValueError('invalid_household_preparation')
    hashes = [sources['helper'], sources['plan'], *sources['sql']]
    if any(item is not None and (type(item) is not str or not HEX.fullmatch(item)) for item in hashes):
        raise ValueError('invalid_household_preparation')
    if ((value['status'] == 'preparation_unavailable' and value['reason'] not in UNAVAILABLE_REASONS)
            or (value['status'] == 'preparation_failed' and value['reason'] in UNAVAILABLE_REASONS)):
        raise ValueError('invalid_household_preparation')
    prepared = value['status'] == 'schema_prepared_app_wiring_pending'
    if prepared:
        if (value['reason'] != 'verified_in_memory' or any(item is None for item in hashes)
                or sources['sql'][0] != BASE_SQL_SHA256
                or type(value['domain_table_count']) is not int or value['domain_table_count'] != 31
                or type(value['private_rows']) is not int or value['private_rows'] != 0
                or value['foreign_key_check'] != 'passed' or value['integrity_check'] != 'passed'):
            raise ValueError('invalid_household_preparation')
    elif (value['reason'] == 'verified_in_memory' or value['domain_table_count'] is not None
          or value['private_rows'] is not None or value['foreign_key_check'] != 'not_verified'
          or value['integrity_check'] != 'not_verified'):
        raise ValueError('invalid_household_preparation')
    return value


def _read_source(root, relative):
    path = root / relative
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise ValueError('unsafe_source')
    if not path.is_file():
        raise FileNotFoundError('sources_unavailable')
    with path.open('rb') as stream:
        raw = stream.read(MAX_SOURCE_BYTES + 1)
    if len(raw) > MAX_SOURCE_BYTES:
        raise ValueError('source_size_limit')
    return raw


def _decode(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate_json_key')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique)


def _kill(proc):
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    try:
        proc.communicate(timeout=2)
    except subprocess.TimeoutExpired:
        # Do not wait indefinitely even if an unexpected descendant kept a pipe.
        for stream in (proc.stdout, proc.stderr):
            if stream is not None:
                stream.close()


def run_preparation(root):
    """Execute only the reviewed no-argument helper; cancellation is not failure."""
    root = Path(root).absolute()
    result = unavailable('sources_unavailable')
    raw = {}
    try:
        for relative in SOURCE_PATHS:
            raw[relative] = _read_source(root, relative)
            digest = hashlib.sha256(raw[relative]).hexdigest()
            if relative == HELPER:
                result['source_sha256']['helper'] = digest
            elif relative == PLAN:
                result['source_sha256']['plan'] = digest
            else:
                result['source_sha256']['sql'][SQL_PATHS.index(relative)] = digest
    except OSError:
        return validate_preparation(result)
    except ValueError as exc:
        result['reason'] = str(exc)
        return validate_preparation(result)
    result['status'] = 'preparation_failed'
    try:
        plan = _decode(raw[PLAN])
        expected = [{'path': path, 'sha256': digest} for path, digest in zip(SQL_PATHS, result['source_sha256']['sql'])]
        if (type(plan) is not dict or set(plan) != {'schema', 'source_baseline', 'purpose', 'ordered_sql'}
                or plan.get('schema') != 'offmenu-household-schema-preparation-plan/1'
                or plan.get('source_baseline') != BASELINE
                or type(plan.get('ordered_sql')) is not list or len(plan['ordered_sql']) != 3):
            result['reason'] = 'plan_invalid'
            return validate_preparation(result)
        if plan['ordered_sql'] != expected:
            result['reason'] = 'dependency_mismatch'
            return validate_preparation(result)
        if result['source_sha256']['sql'][0] != BASE_SQL_SHA256:
            result['reason'] = 'baseline_mismatch'
            return validate_preparation(result)
    except (ValueError, TypeError, RecursionError):
        result['reason'] = 'plan_invalid'
        return validate_preparation(result)
    try:
        proc = subprocess.Popen([sys.executable, '-I', '-B', str(root / HELPER)],
            cwd=root, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, start_new_session=True, env={})
        try:
            stdout, _ = proc.communicate(timeout=TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            _kill(proc)
            result['reason'] = 'helper_timeout'
            return validate_preparation(result)
        except KeyboardInterrupt:
            try:
                _kill(proc)
            except Exception:
                pass  # Cleanup failure cannot convert cancellation into ingestion.
            raise
        if proc.returncode:
            result['reason'] = 'helper_failed'
            return validate_preparation(result)
        if len(stdout) > MAX_OUTPUT_BYTES:
            raise ValueError('invalid_helper_result')
        value = _decode(stdout)
        expected_keys = {'schema', 'source_baseline', 'schema_status', 'prepared_schema_version',
            'security_schema_version', 'domain_table_count', 'private_rows', 'foreign_key_check',
            'integrity_check', 'sql_sha256', *FALSE_FIELDS}
        if (type(value) is not dict or set(value) != expected_keys
                or value['schema'] != 'offmenu-household-schema-readiness/1'
                or value['source_baseline'] != BASELINE
                or value['schema_status'] != 'schema_prepared_app_wiring_pending'
                or value['prepared_schema_version'] != 'offmenu-household-domain/1'
                or value['security_schema_version'] != 'offmenu-byoc-security/1'
                or type(value['domain_table_count']) is not int or value['domain_table_count'] != 31
                or type(value['private_rows']) is not int or value['private_rows'] != 0
                or any(value[key] is not False for key in FALSE_FIELDS)
                or value['foreign_key_check'] != 'passed' or value['integrity_check'] != 'passed'
                or value['sql_sha256'] != result['source_sha256']['sql']):
            raise ValueError('invalid_helper_result')
        if any(_read_source(root, path) != content for path, content in raw.items()):
            result['reason'] = 'source_changed'
            return validate_preparation(result)
        result.update(status='schema_prepared_app_wiring_pending', reason='verified_in_memory',
            domain_table_count=31, private_rows=0, foreign_key_check='passed', integrity_check='passed')
    except (ValueError, TypeError, RecursionError):
        result['reason'] = 'invalid_helper_result'
    except OSError:
        result['reason'] = 'invocation_failed'
    return validate_preparation(result)
