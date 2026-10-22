#!/usr/bin/env python3
"""Finite reviewed checkout/pull/database-stage/return loop; standard library only.

No shell from plans, downloads, archive execution, or raw source uploads.
Git output and private supplier details are never echoed or persisted.
"""
from __future__ import annotations

import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import tempfile
import datetime
import time

BRANCH = 'integration/manual-actions-20261022'
REMOTE_URLS = {'git@github.com:maldous/offmenu.git', 'https://github.com/maldous/offmenu.git',
               'ssh://git@github.com/maldous/offmenu.git'}
RETURN_DIR = 'manual-action/returns/run'
RECEIPT_SCHEMA = 'offmenu-run-receipt/1'
COMMIT_MESSAGE = 'Return sanitized supplier check [skip ci]'
INGEST_COMMIT_MESSAGE = 'Return sanitized retained ingest checkpoint [skip ci]'
DOMAINS = ('barcodes','ingredients','recipes','dietary','user_profiles','inventory','suppliers','citations')
PENDING_SCHEMA = 'offmenu-pending-work/1'
PENDING_ASSIGNMENTS = ('completed','reused','not_yet_read','partial','failed','unsupported','held','unqualified','awaiting_input','unknown')
PENDING_COUNTS = ('assignments_total', *PENDING_ASSIGNMENTS, 'files_remaining',
    'source_bytes_known','source_bytes_unknown','records_remaining_known','records_remaining_unknown')
PENDING_NULLABLE = ('records_remaining','records_to_write')
DOMAIN_STATUSES = frozenset('pending running complete completed imported reused schema_only unavailable missing existing_loaded not_applicable awaiting_user_input skipped partial failed blocked no_inputs'.split())
ERROR_CODES = frozenset('BudgetExceeded SourceChanged OSError IOError EOFError ValueError TypeError KeyError RuntimeError DatabaseError OperationalError IntegrityError JSONDecodeError UnicodeDecodeError PermissionError FileNotFoundError Error UnsupportedSource MalformedRecord MalformedSupplierRow resource_cap catalog_skip partial_source missing unreadable already_loaded incomplete_source unsupported_supplier_format unsupported_text_compression parquet_dependency_unavailable resource_budget UnsupportedSupplierSource DuplicateField existing_binding_reused source_error restricted_input awaiting_user_input no_recognized_sources schema_uncertain unsupported_format unavailable adapter_unavailable resource_limit'.split())
ERROR_CODES = ERROR_CODES | frozenset(('UnicodeError', 'DocumentTooLarge', 'OverflowError'))
HEX = re.compile(r'[0-9a-f]{64}\Z')
RECEIPT_NAME = re.compile(r'[0-9a-f]{64}-(?:completed|blocked-[0-9a-f]{16}|(?:running|partial|blocked|completed)-[0-9a-f]{64})\.json\Z')
STAMP = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\Z')
REASONS = frozenset('missing unreadable refused_or_unreadable sha256_prefix_mismatch '
    'compressed_archive_limit compressed_archive_changed_or_limit archive_changed '
    'expanded_archive_limit archive_member_limit unsafe_member_name unsafe_member_path '
    'secret_looking_member_path dataset_looking_member_path duplicate_member_path '
    'unsafe_member_type member_size_limit unsupported_archive_metadata member_length_mismatch '
    'non_source_member_extension non_utf8_member binary_or_secret_looking_content '
    'json_not_named_as_source_metadata invalid_source_metadata_json json_rows_refused '
    'trailing_archive_payload empty_source_archive symlink_path_refused not_regular_file '
    'wall_time_limit inspection_error OSError EOFError ReadError CompressionError '
    'HeaderError ExtractError ValueError error BadGzipFile PermissionError '
    'FileNotFoundError sql_not_schema_ddl'.split())


class Stop(Exception):
    pass


def announce(message):
    print(message, flush=True)


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + '\n').encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def exact_keys(value, required, optional=()):
    if not isinstance(value, dict) or not set(required) <= set(value) or set(value) - set(required) - set(optional):
        raise Stop('invalid_sanitized_schema')


def safe_path(path):
    path = Path(os.path.abspath(path))
    for node in (path, *path.parents):
        try:
            if stat.S_ISLNK(node.lstat().st_mode):
                raise Stop('symlink_path_refused')
        except FileNotFoundError:
            pass
    return path


def read_json(path):
    path = safe_path(path)
    with path.open('rb') as stream:
        raw = stream.read(65537)
    if len(raw) > 65536:
        raise Stop('json_size_limit')
    try:
        return json.loads(raw)
    except (ValueError, RecursionError):
        raise Stop('invalid_json') from None


def validate_plan(plan):
    exact_keys(plan, {'schema', 'max_parallel', 'jobs'}, {'receipt_transport'})
    if plan.get('receipt_transport', 'legacy-same-branch') not in ('legacy-same-branch', 'isolated-branch-v1'):
        raise Stop('unsupported_receipt_transport')
    if not isinstance(plan['jobs'], list) or len(plan['jobs']) != 1:
        raise Stop('unsupported_jobs')
    job = plan['jobs'][0]
    exact_keys(job, {'id', 'version', 'operation', 'depends_on'})
    common = type(job['version']) is int and 1 <= job['version'] <= 1000000 and job['depends_on'] == []
    legacy = (plan['schema'] == 'offmenu-run-plan/1' and plan['max_parallel'] == 1
              and job['id'] == 'supplier-source-inspection' and job['operation'] == 'supplier_inspect')
    ingest = (plan['schema'] == 'offmenu-run-plan/2' and type(plan['max_parallel']) is int
              and 1 <= plan['max_parallel'] <= 8 and job['id'] == 'retained-eight-domain-ingest'
              and job['operation'] == 'retained_ingest_all')
    normalization = (plan['schema'] == 'offmenu-run-plan/3' and type(plan['max_parallel']) is int
              and 1 <= plan['max_parallel'] <= 22 and job['id'] == 'retained-six-domain-normalization'
              and job['operation'] == 'normalize_staged_databases'
              and plan.get('receipt_transport') == 'isolated-branch-v1')
    if not common or not (legacy or ingest or normalization):
        raise Stop('unsupported_job')
    return job


def unknown_pending_work():
    # Zero counters are not an assertion of zero remaining work: status is
    # explicitly unknown and totals are null whenever no evidence is available.
    row = {**dict.fromkeys(PENDING_COUNTS, 0),
           **dict.fromkeys(PENDING_NULLABLE, None), 'processed_bytes': None}
    return {'schema': PENDING_SCHEMA, 'status': 'unknown',
        'binding': 'additive_staging_not_app_bound', 'catalog_complete': False,
        'catalog_sources': 0, 'unassigned_sources': 0, 'awaiting_input_domains': [],
        'domains': {domain: dict(row) for domain in DOMAINS}, 'totals': dict(row)}


def validate_pending_work(value):
    # Deliberately independent of the optional reporter: old receipt recovery
    # must work even when a local pending-work helper cannot be imported.
    exact_keys(value, {'schema','status','binding','catalog_complete',
        'catalog_sources','unassigned_sources','awaiting_input_domains','domains','totals'}, {'scope'})
    if (value['schema'] != PENDING_SCHEMA or value['status'] not in ('available','unknown')
        or value['binding'] != 'additive_staging_not_app_bound'
        or type(value['catalog_complete']) is not bool):
        raise Stop('invalid_pending_work_schema')
    for field in ('catalog_sources','unassigned_sources'):
        if type(value[field]) is not int or not 0 <= value[field] <= 10**15:
            raise Stop('invalid_pending_work_count')
    awaiting=value['awaiting_input_domains']
    if (not isinstance(awaiting,list) or any(d not in ('user_profiles','inventory') for d in awaiting)
        or awaiting != [d for d in ('user_profiles','inventory') if d in awaiting]):
        raise Stop('invalid_pending_work_status')
    exact_keys(value['domains'], set(DOMAINS))
    for row in [*value['domains'].values(), value['totals']]:
        exact_keys(row, {*PENDING_COUNTS, *PENDING_NULLABLE, 'processed_bytes'})
        for field in PENDING_COUNTS:
            if type(row[field]) is not int or not 0 <= row[field] <= 10**15:
                raise Stop('invalid_pending_work_count')
        for field in PENDING_NULLABLE:
            if row[field] is not None and (type(row[field]) is not int or not 0 <= row[field] <= 10**15):
                raise Stop('invalid_pending_work_count')
        # Physical processed bytes cannot be inferred from row cursors or
        # compressed-file size. This version does not make that claim.
        if row['processed_bytes'] is not None:
            raise Stop('invalid_pending_work_count')
        if row['assignments_total'] != sum(row[key] for key in PENDING_ASSIGNMENTS):
            raise Stop('invalid_pending_work_count')
    if any(value['totals'][key] != sum(row[key] for row in value['domains'].values()) for key in PENDING_COUNTS):
        raise Stop('invalid_pending_work_count')
    if 'scope' in value:
        scope = value['scope']
        exact_keys(scope, {'policy', 'app_managed_assignments'})
        if scope['policy'] != 'external_ingest_only':
            raise Stop('invalid_pending_work_scope')
        exact_keys(scope['app_managed_assignments'], {'user_profiles', 'inventory'})
        if any(type(count) is not int or not 0 <= count <= 10**15 for count in scope['app_managed_assignments'].values()):
            raise Stop('invalid_pending_work_scope')
        if value['awaiting_input_domains']:
            raise Stop('invalid_pending_work_scope')
        for domain in ('user_profiles', 'inventory'):
            if any(value['domains'].get(domain, {}).get(key) != 0 for key in PENDING_COUNTS):
                raise Stop('invalid_pending_work_scope')
    return value


def evidence_ref(value):
    exact_keys(value, {'schema', 'sha256', 'bytes'})
    if (value['schema'] != 'offmenu-ingest-evidence-ref/1'
            or not isinstance(value['sha256'], str) or not HEX.fullmatch(value['sha256'])
            or type(value['bytes']) is not int or not 1 <= value['bytes'] <= 65536):
        raise Stop('invalid_evidence_reference')
    return value


def supplement_relpath(reference):
    reference = evidence_ref(reference)
    return RETURN_DIR + '/evidence/' + reference['sha256'] + '.json'


def validate_supplement(value):
    exact_keys(value, {'schema'}, {'ingest_evidence', 'relational_targets', 'household_schema_preparation', 'storage_sizes'})
    if value['schema'] != 'offmenu-ingest-supplement/1' or len(value) < 2:
        raise Stop('invalid_ingest_supplement')
    try:
        if 'storage_sizes' in value:
            from ingest_storage_sizes import validate_storage_sizes
            validate_storage_sizes(value['storage_sizes'])
        if 'household_schema_preparation' in value:
            from ingest_household_preparation import validate_preparation
            validate_preparation(value['household_schema_preparation'])
        if 'ingest_evidence' in value:
            from ingest_evidence import validate_evidence
            validate_evidence(value['ingest_evidence'])
        if 'relational_targets' in value:
            from ingest_relational_targets import sanitize_relational_summary
            if sanitize_relational_summary(value['relational_targets']) != value['relational_targets']:
                raise ValueError('invalid_relational_summary')
    except (ImportError, ValueError, TypeError):
        raise Stop('invalid_ingest_supplement') from None
    if len(canonical(value)) > 65536:
        raise Stop('sanitized_supplement_size_limit')
    return value


def build_supplement(report):
    value = {'schema': 'offmenu-ingest-supplement/1'}
    if 'storage_sizes' in report:
        from ingest_storage_sizes import validate_storage_sizes
        value['storage_sizes'] = validate_storage_sizes(report['storage_sizes'])
    if 'household_schema_preparation' in report:
        from ingest_household_preparation import validate_preparation
        value['household_schema_preparation'] = validate_preparation(report['household_schema_preparation'])
    if 'ingest_evidence' in report:
        try:
            from ingest_evidence import sanitize_evidence
            value['ingest_evidence'] = sanitize_evidence(report['ingest_evidence'])
        except Exception:
            pass
    if 'relational_targets' in report:
        try:
            from ingest_relational_targets import sanitize_relational_summary
            value['relational_targets'] = sanitize_relational_summary(report['relational_targets'])
        except Exception:
            pass
    return validate_supplement(value) if len(value) > 1 else None


def reference_for_supplement(value):
    raw = canonical(validate_supplement(value))
    return {'schema': 'offmenu-ingest-evidence-ref/1', 'sha256': digest(raw), 'bytes': len(raw)}


def ingest_progress_digest(summary):
    # v2 receipts published before pending-work reporting hashed domains alone.
    # Keep those exact bytes recoverable; bind new optional counters when present.
    extras = {key: summary[key] for key in ('pending_work', 'ingest_evidence', 'relational_targets', 'evidence_ref') if key in summary}
    evidence = {'domains': summary['domains'], **extras} if extras else summary['domains']
    return digest(canonical(evidence))


def error_telemetry(value, strict=False):
    # Optional extension: old receipts need no new fields and retain their exact
    # digest. Only the reviewed fixed-schema helper may construct new telemetry.
    directory = str(Path(__file__).resolve().parent)
    if directory not in sys.path:
        sys.path.insert(0, directory)
    from ingest_errors import sanitize_error_telemetry
    safe = sanitize_error_telemetry(value)
    if strict and (value != safe or any(type(count) is not int
            for field in ('class_counts', 'origin_counts', 'reason_counts')
            for count in value.get(field, {}).values())):
        raise Stop('invalid_sanitized_error_telemetry')
    return safe


def validate_ingest_receipt(value):
    exact_keys(value, {'schema','job_id','job_version','operation','job_key',
        'implementation_sha256','input_sha256','observed_at','outcome','ingest'})
    if (value['schema'] != 'offmenu-run-receipt/2' or value['job_id'] != 'retained-eight-domain-ingest'
        or value['operation'] != 'retained_ingest_all' or type(value['job_version']) is not int
        or not 1 <= value['job_version'] <= 1000000 or value['outcome'] not in ('running','completed','partial','blocked')
        or not isinstance(value['observed_at'],str) or not STAMP.fullmatch(value['observed_at'])):
        raise Stop('invalid_sanitized_schema')
    for key in ('job_key','implementation_sha256','input_sha256'):
        if not isinstance(value[key],str) or not HEX.fullmatch(value[key]):
            raise Stop('invalid_sanitized_digest')
    summary=value['ingest']
    exact_keys(summary,{'binding','domains','progress_sha256'},{'pending_work','ingest_evidence','relational_targets','evidence_ref'})
    if summary['binding'] != 'additive_staging_not_app_bound':
        raise Stop('invalid_sanitized_schema')
    exact_keys(summary['domains'],set(DOMAINS))
    for domain, row in summary['domains'].items():
        exact_keys(row,{'status','read','written','unchanged','errors','skipped','reused_rows','reused_stores','source_count','error_codes'}, {'error_telemetry'})
        if row['status'] not in DOMAIN_STATUSES:
            raise Stop('invalid_sanitized_status')
        for key in ('read','written','unchanged','errors','skipped','reused_rows','reused_stores','source_count'):
            if type(row[key]) is not int or not 0 <= row[key] <= 10**15:
                raise Stop('invalid_sanitized_count')
        if not isinstance(row['error_codes'],list) or row['error_codes'] != sorted(set(row['error_codes'])) or any(code not in ERROR_CODES for code in row['error_codes']):
            raise Stop('invalid_sanitized_reason')
        if 'error_telemetry' in row:
            error_telemetry(row['error_telemetry'], strict=True)
    if 'pending_work' in summary:
        validate_pending_work(summary['pending_work'])
    if 'evidence_ref' in summary:
        evidence_ref(summary['evidence_ref'])
    if 'ingest_evidence' in summary:
        try:
            from ingest_evidence import validate_evidence
            validate_evidence(summary['ingest_evidence'])
        except (ImportError, ValueError, TypeError):
            raise Stop('invalid_ingest_evidence') from None
    if 'relational_targets' in summary:
        try:
            from ingest_relational_targets import sanitize_relational_summary
            if sanitize_relational_summary(summary['relational_targets']) != summary['relational_targets']:
                raise ValueError('invalid_relational_summary')
        except (ImportError, ValueError, TypeError):
            raise Stop('invalid_relational_summary') from None
    if summary['progress_sha256'] != ingest_progress_digest(summary):
        raise Stop('invalid_progress_digest')
    if len(canonical({'sha256': '0' * 64, 'receipt': value})) > 65536:
        raise Stop('sanitized_receipt_size_limit')
    return value


def validate_receipt(value):
    if isinstance(value, dict) and value.get('schema') == 'offmenu-run-receipt/3':
        directory = str(Path(__file__).resolve().parent)
        if directory not in sys.path:
            sys.path.insert(0, directory)
        from normalization_receipts import validate_receipt as validate_normalization_receipt
        try:
            return validate_normalization_receipt(value)
        except (ValueError, TypeError):
            raise Stop('invalid_sanitized_normalization_receipt') from None
    if isinstance(value,dict) and value.get('schema') == 'offmenu-run-receipt/2':
        return validate_ingest_receipt(value)
    exact_keys(value, {'schema', 'job_id', 'job_version', 'operation', 'job_key',
        'implementation_sha256', 'input_sha256', 'observed_at', 'outcome', 'supplier',
        'data_loads', 'source_review', 'source_upload'})
    if (value['schema'] != RECEIPT_SCHEMA or value['job_id'] != 'supplier-source-inspection'
            or value['operation'] != 'supplier_inspect' or type(value['job_version']) is not int
            or not 1 <= value['job_version'] <= 1000000 or value['data_loads'] != 'not_implemented'
            or value['source_review'] != 'manual_review_required' or value['source_upload'] != 'NOT_UPLOADED'
            or not isinstance(value['observed_at'], str) or not STAMP.fullmatch(value['observed_at'])):
        raise Stop('invalid_sanitized_schema')
    for key in ('job_key', 'implementation_sha256'):
        if not isinstance(value[key], str) or not HEX.fullmatch(value[key]):
            raise Stop('invalid_sanitized_digest')
    if value['input_sha256'] is not None and (not isinstance(value['input_sha256'], str) or not HEX.fullmatch(value['input_sha256'])):
        raise Stop('invalid_sanitized_digest')
    sup = value['supplier']
    exact_keys(sup, {'status', 'member_count', 'transfer'}, {'reason', 'expected_sha256_prefix', 'observed_sha256', 'compressed_bytes', 'source_bytes'})
    if sup['transfer'] != 'NOT_UPLOADED' or type(sup['member_count']) is not int or not 0 <= sup['member_count'] <= 256:
        raise Stop('invalid_sanitized_schema')
    if 'reason' in sup and sup['reason'] not in REASONS:
        raise Stop('invalid_sanitized_reason')
    if 'expected_sha256_prefix' in sup and sup['expected_sha256_prefix'] != 'e2508555':
        raise Stop('invalid_sanitized_digest')
    if 'observed_sha256' in sup and (not isinstance(sup['observed_sha256'], str) or not HEX.fullmatch(sup['observed_sha256'])):
        raise Stop('invalid_sanitized_digest')
    for key, maximum in (('compressed_bytes', 16 * 1024 * 1024), ('source_bytes', 32 * 1024 * 1024)):
        if key in sup and (type(sup[key]) is not int or not 0 <= sup[key] <= maximum):
            raise Stop('invalid_sanitized_count')
    if value['outcome'] == 'completed':
        if (sup['status'] != 'inspection_pass_manual_review_required' or 'reason' in sup
                or not {'observed_sha256', 'expected_sha256_prefix', 'compressed_bytes', 'source_bytes'} <= set(sup)
                or sup['observed_sha256'] != value['input_sha256']):
            raise Stop('invalid_completion')
    elif value['outcome'] != 'blocked' or sup['status'] != 'blocked' or 'reason' not in sup:
        raise Stop('invalid_outcome')
    return value


def runtime_summary(value):
    if value.get('schema') == 'offmenu-run-receipt/2':
        return value['ingest']
    if value.get('schema') == 'offmenu-run-receipt/3':
        return value['normalization']
    raise Stop('unsupported_runtime_receipt')


def validate_runtime_receipt(value):
    validate_receipt(value)
    runtime_summary(value)
    return value


def receipt_relpath(value):
    validate_receipt(value)
    if value['schema'] == 'offmenu-run-receipt/3':
        suffix = value['outcome']+'-'+runtime_summary(value)['progress_sha256']
    elif value['schema'] == 'offmenu-run-receipt/2':
        suffix='completed' if value['outcome']=='completed' else value['outcome']+'-'+runtime_summary(value)['progress_sha256']
    else:
        suffix = 'completed' if value['outcome'] == 'completed' else 'blocked-' + digest(canonical(value['supplier']))[:16]
    return f"{RETURN_DIR}/{value['job_key']}-{suffix}.json"


def validate_return_path(path):
    if not isinstance(path, str) or str(Path(path).parent) != RETURN_DIR or not RECEIPT_NAME.fullmatch(Path(path).name):
        raise Stop('non_receipt_path_refused')


class Runner:
    def __init__(self, root):
        self.root = safe_path(root)
        self.gitdir = safe_path(self.root / '.git')
        self.state = self.gitdir / 'offmenu-runner'
        self.lock = None
        self.remote_head = None
        self.receipt_transport = 'legacy-same-branch'
        self.receipt_publisher = None
        self._commit_identity_cache = None

    def git(self, *args, check=True, input_data=None, env_overrides=None):
        env = dict(os.environ, GIT_TERMINAL_PROMPT='0', GIT_OPTIONAL_LOCKS='0')
        if args[0] in ('commit', 'commit-tree'):
            env.update(self.commit_identity_env())
        if env_overrides:
            if set(env_overrides) != {'GIT_INDEX_FILE'} or Path(env_overrides['GIT_INDEX_FILE']).parent != self.state:
                raise Stop('private_receipt_index_override_refused')
            env.update(env_overrides)
        command = ['git', '-C', str(self.root), '-c', 'core.hooksPath=/dev/null',
            '-c', 'core.fsmonitor=false', '-c', 'submodule.recurse=false',
            '-c', 'commit.gpgsign=false', '-c', 'push.followTags=false',
            '-c', 'push.recurseSubmodules=no', '-c', 'remote.origin.mirror=false', *args]
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                stdin=subprocess.PIPE if input_data is not None else None,
                                env=env, start_new_session=True)
        try:
            out, stderr = proc.communicate(input=input_data, timeout=120)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.communicate()
            raise Stop('git_timeout_local_work_preserved') from None
        except KeyboardInterrupt:
            # User cancellation is not a transport failure: do not start or
            # continue ingestion after an interrupted startup Git operation.
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.communicate()
            raise
        if check and proc.returncode:
            operation = args[0].replace('-', '_')
            detail = stderr.decode('utf-8', errors='replace').lower()
            category = 'failed'
            if args[0] in ('commit', 'commit-tree'):
                if any(text in detail for text in ('unable to auto-detect email address', 'author identity unknown', 'committer identity unknown', 'empty ident name', 'auto-detection is disabled')):
                    category = 'identity_not_configured'
                elif 'index.lock' in detail:
                    category = 'index_locked'
                elif any(text in detail for text in ('no space left on device', 'disk quota exceeded')):
                    category = 'storage_unavailable'
                elif 'permission denied' in detail:
                    category = 'permission_denied'
                elif 'nothing to commit' in (out.decode('utf-8', errors='replace').lower() + detail):
                    category = 'no_changes'
            raise Stop('git_' + operation + '_' + category + '_local_work_preserved')
        return proc.returncode, out

    def commit_identity_env(self):
        # Explicitly approved fallback, only for this commit and missing fields.
        # Never persist Git configuration or replace an already usable identity.
        if self._commit_identity_cache is not None:
            return dict(self._commit_identity_cache)
        result = {}
        for role in ('AUTHOR', 'COMMITTER'):
            code, identity = self.git('var', 'GIT_' + role + '_IDENT', check=False)
            if code == 0 and re.fullmatch(rb'.+ <[^<>]+> [0-9]+ [+-][0-9]{4}\n?', identity):
                continue
            for field, fallback in (('NAME', 'OffMenu Runner'), ('EMAIL', 'offmenu-runner@localhost')):
                variable = 'GIT_' + role + '_' + field
                value = os.environ.get(variable)
                if value is None:
                    for key in (role.lower() + '.' + field.lower(), 'user.' + field.lower()):
                        code, raw = self.git('config', '--get', key, check=False)
                        if code == 0:
                            value = raw.decode('utf-8', errors='strict').strip()
                            break
                        if code != 1:
                            raise Stop('git_identity_config_unreadable_preserved')
                if value is None and field == 'EMAIL':
                    value = os.environ.get('EMAIL')
                if not value or not value.strip():
                    result[variable] = fallback
        if result:
            announce('Using per-command OffMenu Runner fallback for missing Git identity fields; no configuration changed.')
        self._commit_identity_cache = dict(result)
        return result

    def textgit(self, *args):
        return self.git(*args)[1].decode('utf-8').strip()

    def check_remote(self):
        # Test harness subclasses this method for generated local bare remotes only.
        urls = self.textgit('remote', 'get-url', '--all', 'origin').splitlines()
        pushes = self.textgit('remote', 'get-url', '--push', '--all', 'origin').splitlines()
        if len(urls) != 1 or len(pushes) != 1 or urls[0] not in REMOTE_URLS or pushes[0] not in REMOTE_URLS:
            raise Stop('expected_private_offmenu_remote_required')

    def preconditions(self):
        if any(key in os.environ for key in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_COMMON_DIR', 'GIT_OBJECT_DIRECTORY', 'GIT_ALTERNATE_OBJECT_DIRECTORIES')):
            raise Stop('git_environment_override_refused')
        if not self.gitdir.is_dir() or self.textgit('rev-parse', '--show-toplevel') != str(self.root):
            raise Stop('isolated_repository_root_required')
        if self.textgit('symbolic-ref', '--short', 'HEAD') != BRANCH:
            raise Stop('expected_manual_action_branch_required')
        self.check_remote()
        staged = self.git('diff', '--no-ext-diff', '--no-textconv', '--cached', '--name-status', '-z')[1]
        recovery = self.recovery_receipt() if staged else None
        expected_stage = b'A\0' + recovery[0].encode() + b'\0' if recovery else b''
        if staged and (not recovery or staged != expected_stage or self.git('show', ':' + recovery[0])[1] != recovery[1]
                or not self.regular_receipt_mode(recovery[0])):
            raise Stop('preexisting_staged_changes_preserved_unstage_manually')
        if any((self.gitdir / name).exists() for name in ('MERGE_HEAD', 'CHERRY_PICK_HEAD', 'REVERT_HEAD', 'rebase-merge', 'rebase-apply', 'BISECT_LOG')):
            raise Stop('git_operation_in_progress')
        relevant = self.git('status', '--porcelain=v1', '-z', '--untracked-files=all', '--', 'run', 'manual-action', '.github/workflows/manual-action-fixtures.yml')[1]
        expected_status = b'A  ' + recovery[0].encode() + b'\0' if recovery else b''
        if relevant and relevant != expected_status:
            raise Stop('runner_or_plan_paths_dirty_preserved')
        for relative in ('run', 'manual-action', 'manual-action/plan_runner.py', 'manual-action/foo_manual.py', 'manual-action/plan.json', RETURN_DIR):
            safe_path(self.root / relative)

    def acquire(self, inherited=None):
        self.preconditions()
        path = self.gitdir / 'offmenu-run.lock'
        if inherited is None:
            fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        else:
            fd = int(inherited)
            existing = os.stat(path, follow_symlinks=False)
            actual = os.fstat(fd)
            if (existing.st_dev, existing.st_ino) != (actual.st_dev, actual.st_ino) or not stat.S_ISREG(actual.st_mode):
                raise Stop('invalid_inherited_lock')
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(fd)
            raise Stop('another_run_is_active') from None
        self.lock = fd
        self.preconditions()

    def pull(self):
        announce('[1/4] Pulling the reviewed manual-action branch (fast-forward only).')
        self.git('pull', '--ff-only', '--no-rebase', '--no-autostash', '--no-recurse-submodules', 'origin', BRANCH)
        self.remote_head = self.textgit('rev-parse', 'FETCH_HEAD')
        self.preconditions()
        self.check_outgoing()

    def reexec(self):
        os.set_inheritable(self.lock, True)
        env = dict(os.environ, OFFMENU_RUN_FD=str(self.lock), OFFMENU_RUN_HEAD=self.textgit('rev-parse', 'HEAD'), OFFMENU_RUN_REMOTE=self.remote_head)
        os.execve(sys.executable, [sys.executable, '-B', str(self.root / 'manual-action/plan_runner.py')], env)

    def check_outgoing(self):
        if not self.remote_head or not re.fullmatch(r'[0-9a-f]{40,64}', self.remote_head):
            raise Stop('missing_pulled_revision')
        if self.git('merge-base', '--is-ancestor', self.remote_head, 'HEAD', check=False)[0]:
            raise Stop('remote_diverged_local_work_preserved_no_force')
        commits = self.textgit('rev-list', self.remote_head + '..HEAD').splitlines()
        for commit in commits:
            if self.textgit('show', '-s', '--format=%B', commit) not in (COMMIT_MESSAGE,INGEST_COMMIT_MESSAGE):
                raise Stop('non_runner_commit_message_preserved')
            if len(self.textgit('rev-list', '--parents', '-n', '1', commit).split()) != 2:
                raise Stop('non_runner_commit_pending_preserved')
            changes = self.git('diff-tree', '--no-commit-id', '--name-status', '-r', '-z', commit)[1].decode().split('\0')
            changes = changes[:-1] if changes and changes[-1] == '' else changes
            if not changes or len(changes) % 2:
                raise Stop('non_runner_commit_pending_preserved')
            for status_code, path in zip(changes[::2], changes[1::2]):
                if status_code != 'A':
                    raise Stop('non_runner_commit_pending_preserved')
                validate_return_path(path)
                if not self.regular_receipt_mode(path, commit):
                    raise Stop('non_regular_receipt_commit_preserved')
                raw = self.git('show', commit + ':' + path)[1]
                value = validate_receipt(json.loads(raw))
                if receipt_relpath(value) != path or canonical(value) != raw:
                    raise Stop('non_sanitized_commit_pending_preserved')
        return bool(commits)

    def checkpoint(self, phase, job_key=None, relative=None, sha256=None):
        # A small local crash-recovery record; never staged or pushed.
        self.state = safe_path(self.state)
        self.state.mkdir(mode=0o700, exist_ok=True)
        value = {'schema': 'offmenu-run-checkpoint/1', 'phase': phase, 'job_key': job_key, 'receipt': relative, 'sha256': sha256}
        if phase not in {'checking', 'receipt_ready', 'committed', 'published', 'blocked'}:
            raise Stop('invalid_checkpoint')
        if job_key is not None and not HEX.fullmatch(job_key):
            raise Stop('invalid_checkpoint')
        if relative is not None:
            validate_return_path(relative)
        if sha256 is not None and not HEX.fullmatch(sha256):
            raise Stop('invalid_checkpoint')
        fd, temp = tempfile.mkstemp(prefix='.checkpoint-', dir=self.state)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(canonical(value)); stream.flush(); os.fsync(stream.fileno())
            os.replace(temp, self.state / 'checkpoint.json')
            directory = os.open(self.state, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)

    def owned_receipt(self, relative, raw):
        path = self.state / 'checkpoint.json'
        if path.exists():
            value = read_json(path)
            if (isinstance(value, dict) and value.get('schema') == 'offmenu-run-checkpoint/1'
                    and value.get('receipt') == relative and value.get('sha256') == digest(raw)
                    and value.get('phase') in {'receipt_ready', 'committed', 'published', 'blocked'}):
                return True
        # A v2 spool is durably written BEFORE materializing its receipt. It
        # closes the crash window between exclusive receipt creation and the
        # recovery checkpoint without accepting any unowned arbitrary file.
        validate_return_path(relative)
        spool=safe_path(self.state/'ingest-pending'/Path(relative).name)
        if not spool.exists():
            return False
        envelope=read_json(spool)
        exact_keys(envelope,{'sha256','receipt'})
        value=validate_ingest_receipt(envelope['receipt'])
        return (envelope['sha256']==digest(raw) and canonical(value)==raw
                and receipt_relpath(value)==relative)

    def recovery_receipt(self):
        path = self.state / 'checkpoint.json'
        if not path.exists():
            return None
        checkpoint = read_json(path)
        if (not isinstance(checkpoint, dict) or checkpoint.get('phase') not in {'receipt_ready', 'committed', 'published'}
                or not checkpoint.get('receipt')):
            return None
        relative = checkpoint['receipt']
        validate_return_path(relative)
        destination = safe_path(self.root / relative)
        if not destination.exists():
            raise Stop('recorded_receipt_missing_preserved')
        value = validate_receipt(read_json(destination))
        raw = canonical(value)
        if (receipt_relpath(value) != relative or destination.read_bytes() != raw
                or checkpoint.get('job_key') != value['job_key'] or not self.owned_receipt(relative, raw)):
            raise Stop('recorded_receipt_changed_preserved')
        return relative, raw, value

    def regular_receipt_mode(self, relative, commit=None):
        validate_return_path(relative)
        if commit is not None:
            raw = self.git('ls-tree', '-z', commit, '--', relative)[1]
            prefix = rb'100644 blob [0-9a-f]{40,64}\t'
        else:
            raw = self.git('ls-files', '--stage', '-z', '--', relative)[1]
            prefix = rb'100644 [0-9a-f]{40,64} 0\t'
        return bool(re.fullmatch(prefix + re.escape(relative.encode()) + b'\0', raw))

    def tracked(self, relative):
        return self.git('cat-file', '-e', 'HEAD:' + relative, check=False)[0] == 0

    def publish(self, relative=None, raw=None):
        self.preconditions()
        value = validate_receipt(json.loads(raw)) if relative is not None else None
        if relative is not None and not self.tracked(relative):
            validate_return_path(relative)
            if not self.owned_receipt(relative, raw) or (safe_path(self.root / relative)).read_bytes() != raw:
                raise Stop('receipt_ownership_or_digest_mismatch_preserved')
            value = validate_receipt(json.loads(raw))
            if receipt_relpath(value) != relative or canonical(value) != raw:
                raise Stop('invalid_receipt_preserved')
            attributes = self.git('check-attr', '-z', 'filter', '--', relative)[1].split(b'\0')
            if attributes != [relative.encode(), b'filter', b'unspecified', b''] and attributes != [relative.encode(), b'filter', b'unset', b'']:
                raise Stop('receipt_clean_filter_refused_preserved')
            staged_now = self.git('diff', '--no-ext-diff', '--no-textconv', '--cached', '--name-only', '-z')[1]
            if not staged_now:
                self.git('add', '-f', '--', relative)
            staged = self.git('diff', '--no-ext-diff', '--no-textconv', '--cached', '--name-only', '-z')[1]
            if staged != relative.encode() + b'\0' or self.git('show', ':' + relative)[1] != raw or not self.regular_receipt_mode(relative):
                raise Stop('staged_content_changed_preserved_review_index')
            self.git('commit', '-m', INGEST_COMMIT_MESSAGE if value['schema']=='offmenu-run-receipt/2' else COMMIT_MESSAGE)
            self.checkpoint('committed', value['job_key'], relative, digest(raw))
        if self.check_outgoing():
            announce('[4/4] Pushing sanitized receipts (no force).')
            self.git('push', 'origin', 'HEAD:refs/heads/' + BRANCH)
            if relative is not None:
                self.checkpoint('published', value['job_key'], relative, digest(raw))
        else:
            announce('[4/4] No unpublished receipt commits.')

    def inspector(self):
        spec = importlib.util.spec_from_file_location('offmenu_reviewed_foo_manual', self.root / 'manual-action/foo_manual.py')
        foo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(foo)
        return foo

    def ingest_engine(self):
        directory=str(self.root / 'manual-action')
        if directory not in sys.path:
            sys.path.insert(0,directory)
        import importlib
        return importlib.import_module('ingest_engine')

    def durable_local_json(self, path, value):
        path=safe_path(path)
        path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        fd,temporary=tempfile.mkstemp(prefix='.pending-',dir=path.parent)
        try:
            with os.fdopen(fd,'wb') as out:
                out.write(canonical(value));out.flush();os.fsync(out.fileno())
            os.replace(temporary,path)
            directory=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def prepare_isolated_ingest_receipt(self, value):
        from receipt_branch import ReceiptBranchPublisher
        if self.receipt_publisher is None:
            self.receipt_publisher = ReceiptBranchPublisher(self,
                validate=validate_runtime_receipt, relpath=receipt_relpath,
                canonical=canonical, fail=Stop, validate_supplement=validate_supplement,
                supplement_relpath=supplement_relpath)
        cache = safe_path(self.state / 'receipt-cache' / Path(receipt_relpath(value)).name)
        if cache.exists():
            old = validate_runtime_receipt(read_json(cache))
            if receipt_relpath(old) != receipt_relpath(value) or cache.read_bytes() != canonical(old):
                raise Stop('isolated_receipt_cache_changed_preserved')
            value = old
        else:
            self.durable_local_json(cache, value)
        supplemental = None
        if 'evidence_ref' in runtime_summary(value):
            reference = evidence_ref(runtime_summary(value)['evidence_ref'])
            path = safe_path(self.state / 'ingest-evidence' / (reference['sha256'] + '.json'))
            if not path.is_file():
                recovered = self.receipt_publisher.recover_supplement(reference)
                self.durable_local_json(path, recovered)
            supplemental = validate_supplement(read_json(path))
            if reference_for_supplement(supplemental) != reference or path.read_bytes() != canonical(supplemental):
                raise Stop('required_supplement_changed_spool_preserved')
        return value, supplemental

    def materialize_ingest_receipts(self, values):
        # Startup caller supplies a bounded batch; prepare every canonical
        # receipt and bound supplement before creating/pushing its one tree.
        if not values or len(values) > 512:
            raise Stop('startup_receipt_batch_limit_preserved')
        entries = [self.prepare_isolated_ingest_receipt(value) for value in values]
        self.receipt_publisher.publish_batch(entries)

    def materialize_ingest_receipt(self, value):
        if self.receipt_transport == 'isolated-branch-v1':
            value, supplemental = self.prepare_isolated_ingest_receipt(value)
            self.receipt_publisher.publish(value, supplemental)
            return
        relative=receipt_relpath(value)
        raw=canonical(value)
        destination=safe_path(self.root / relative)
        destination.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        if destination.exists():
            previous=validate_receipt(read_json(destination))
            if receipt_relpath(previous)!=relative:
                raise Stop('existing_receipt_identity_mismatch')
            raw=canonical(previous)
            if destination.read_bytes()!=raw:
                raise Stop('existing_receipt_noncanonical_preserved')
            if not self.tracked(relative):
                if not self.owned_receipt(relative,raw):
                    raise Stop('unowned_existing_receipt_preserved')
                self.checkpoint('receipt_ready',value['job_key'],relative,digest(raw))
        else:
            fd=os.open(destination,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
            with os.fdopen(fd,'wb') as out:
                out.write(raw);out.flush();os.fsync(out.fileno())
            self.checkpoint('receipt_ready',value['job_key'],relative,digest(raw))
        self.publish(relative,raw)

    def ingest_summary(self, report):
        domains={}
        for domain in DOMAINS:
            row=report.get('domains',{}).get(domain,{})
            status=row.get('status','pending')
            status=status if status in DOMAIN_STATUSES else 'partial'
            counts={key:row.get(key,0) for key in ('read','written','unchanged','errors','skipped','reused_rows','reused_stores')}
            for key,value in counts.items():
                if type(value) is not int or value<0 or value>10**15:
                    raise Stop('invalid_engine_counter')
            codes=row.get('error_codes',[])
            if not isinstance(codes,list):
                codes=[]
            codes=sorted(set(code if isinstance(code,str) and code in ERROR_CODES else 'source_error' for code in codes))
            domains[domain]={'status':status,**counts,'source_count':row.get('sources_total',0),'error_codes':codes}
            if 'error_telemetry' in row:
                domains[domain]['error_telemetry'] = error_telemetry(row['error_telemetry'])
        try:
            remaining=validate_pending_work(report.get('pending_work'))
        except (Stop, TypeError, ValueError):
            remaining=unknown_pending_work()
        summary={'binding':'additive_staging_not_app_bound','domains':domains,
                 'pending_work':remaining}
        supplement = build_supplement(report)
        if supplement is not None:
            summary['evidence_ref'] = reference_for_supplement(supplement)
        summary['progress_sha256']=ingest_progress_digest(summary)
        return summary

    def pending_snapshot(self, engine, prepared):
        try:
            return validate_pending_work(engine.pending_snapshot(prepared))
        except Exception:
            # This is visibility, not permission to load. Missing/broken reports
            # never gate otherwise authorized independent source ingestion.
            announce('[pending] Remaining work is unknown; ingestion continues independently.')
            return unknown_pending_work()

    def announce_remaining(self, pending, label):
        pending=validate_pending_work(pending)
        announce('[pending] '+label+': '+pending['status']+
                 '; catalog_complete='+str(pending['catalog_complete']).lower())
        if pending['status']=='unknown':
            announce('  Remaining assignments, files and records are unknown (not zero).')
            return
        announce('  App-managed at application runtime (not external ingest): user_profiles, inventory.')
        for domain,row in pending['domains'].items():
            if domain in ('user_profiles', 'inventory'):
                retained = pending.get('scope', {}).get('app_managed_assignments', {}).get(domain)
                announce('  '+domain+': app_managed; external-ingest requirement=none'+
                    ('; retained catalog assignments='+str(retained) if retained is not None else ''))
                continue
            assignments=' '.join(key+'='+str(row[key]) for key in PENDING_ASSIGNMENTS)
            announce('  '+domain+': '+assignments+' files_remaining='+str(row['files_remaining'])+
                ' records_remaining_known='+str(row['records_remaining_known'])+
                ' unknown_record_assignments='+str(row['records_remaining_unknown']))

    def prepare_household_schema(self):
        # Preparation only: no output-directory argument, deployment or runtime wiring.
        from ingest_household_preparation import run_preparation, unavailable, validate_preparation
        try:
            return validate_preparation(run_preparation(self.root))
        except Exception:
            result = unavailable('invocation_failed')
            result['status'] = 'preparation_failed'
            return result

    def run_ingest_plan(self, plan, job):
        self.preconditions()
        self.receipt_transport = plan.get('receipt_transport', 'legacy-same-branch')
        engine=self.ingest_engine()
        self.state=safe_path(self.state)
        self.state.mkdir(mode=0o700,exist_ok=True)
        pending=safe_path(self.state / 'ingest-pending')
        pending.mkdir(mode=0o700,exist_ok=True)
        transport_failed=False

        def deliver(value, spool=None):
            nonlocal transport_failed
            if transport_failed:
                return
            try:
                self.materialize_ingest_receipt(value)
                if spool is not None:
                    spool.unlink()
            except KeyboardInterrupt:
                transport_failed=True
                raise
            except Exception as exc:
                # No reset/rebase/pull mid-run. Keep data workers independent of
                # transport; exact staged receipt and private spool remain durable.
                transport_failed=True
                announce('Receipt sync paused: '+(str(exc) if isinstance(exc, Stop) else 'receipt_delivery_error')+'. Ingestion continues; local checkpoints retained.')

        recovery=self.recovery_receipt()
        if recovery:
            relative,raw,value=recovery
            if not self.tracked(relative) or self.check_outgoing():
                try:
                    announce('[2/4] Recovering exact owned receipt before the new ingest plan.')
                    self.publish(relative,raw)
                except Stop as exc:
                    transport_failed=True
                    announce('Receipt sync paused: '+str(exc)+'. New ingest is independent of the prior supplier outcome.')
        # Spool files live only in .git, contain strict sanitized payloads and
        # bind canonical bytes to a digest. Never stage arbitrary working files.
        def deliver_startup_batch(batch):
            nonlocal transport_failed
            if transport_failed or not batch:
                return
            announce('[2/4] Returning '+str(len(batch))+' preserved checkpoints in one batch; no source ingest yet.')
            try:
                self.materialize_ingest_receipts([value for value, _ in batch])
                # Only a confirmed non-force push permits removal of these
                # owned spool files. Interruption/failure leaves retry evidence.
                for _, spool in batch:
                    spool.unlink()
                announce('[2/4] Returned '+str(len(batch))+' preserved checkpoints; continuing startup.')
            except KeyboardInterrupt:
                transport_failed=True
                raise
            except Exception as exc:
                transport_failed=True
                announce('Receipt sync paused: '+(str(exc) if isinstance(exc, Stop) else 'receipt_delivery_error')+'. Ingestion continues; local checkpoints retained.')

        batch=[]
        batch_bytes=0
        for spool in sorted(pending.glob('*.json')):
            envelope=read_json(spool)
            exact_keys(envelope,{'sha256','receipt'})
            value=validate_ingest_receipt(envelope['receipt'])
            raw=canonical(value)
            if envelope['sha256']!=digest(raw) or spool.name!=Path(receipt_relpath(value)).name:
                raise Stop('pending_receipt_changed_preserved')
            if self.receipt_transport != 'isolated-branch-v1':
                deliver(value,spool)
                continue
            # Bound memory and one-commit size, including any readable evidence.
            size=len(raw)+(value['ingest'].get('evidence_ref') or {}).get('bytes',0)
            if batch and (len(batch)>=512 or batch_bytes+size>8*1024*1024):
                deliver_startup_batch(batch)
                batch=[];batch_bytes=0
            batch.append((value,spool));batch_bytes+=size
        deliver_startup_batch(batch)
        household_preparation = self.prepare_household_schema()
        announce('[2/4] Household app schema: '+household_preparation['status']+
                 ' ('+household_preparation['reason']+'); preparation only, application wiring/security activation pending.')
        # Receipt transport does not authorize a second physical database copy.
        # Derived relational snapshots remain a separate explicit API opt-in.
        options={'workers':plan['max_parallel'],'report_interval':60,'terminal_progress':True,
                 'materialize_relational_targets': False}
        announce('[2/4] Discovering retained and newly acquired inputs, then ingesting all eight domains in parallel; no downloads. Bounded acquired groups first, then retained cursor resume.')
        prepared=engine.prepare_default(self.state/'ingest',options)
        initial_pending=self.pending_snapshot(engine,prepared)
        self.announce_remaining(initial_pending, 'Before ingest')
        input_sha=prepared['catalog_sha256']
        if not isinstance(input_sha,str) or not HEX.fullmatch(input_sha):
            raise Stop('invalid_catalog_identity')
        files=['run','manual-action/plan_runner.py']+[str(p.relative_to(self.root)) for p in sorted((self.root/'manual-action').glob('receipt_*.py'))]+[str(p.relative_to(self.root)) for p in sorted((self.root/'manual-action').glob('ingest_*.py'))]
        for helper in ('manual-action/acquired_recipe_js.py', 'manual-action/relational-targets.schema.sql', 'manual-action/relational-target-mapping.json'):
            if (self.root / helper).is_file():
                files.append(helper)
        implementation=digest(b''.join((self.root/path).read_bytes() for path in files)+
            canonical({'household_preparation_sources': household_preparation['source_sha256']}))
        job_key=digest(canonical({'job':job,'implementation':implementation,'input':input_sha,
            'household_preparation':digest(canonical(household_preparation))}))
        completed=f'{RETURN_DIR}/{job_key}-completed.json'
        completed_path = (self.state / 'receipt-cache' / Path(completed).name if self.receipt_transport == 'isolated-branch-v1' else self.root / completed)
        if completed_path.exists() and engine.completed_outputs_available(prepared):
            value=validate_ingest_receipt(read_json(completed_path))
            if value['job_key']!=job_key or value['outcome']!='completed':
                raise Stop('existing_receipt_identity_mismatch')
            deliver(value)
            announce('[3/4] This unchanged completed ingest plan is already durable; no source rows replayed.')
            return 2 if transport_failed else 0
        last_signature=None

        def checkpoint_report(report):
            nonlocal last_signature
            report = {**report, 'household_schema_preparation': household_preparation}
            summary=self.ingest_summary(report)
            supplement = build_supplement(report)
            if supplement is not None:
                reference = reference_for_supplement(supplement)
                evidence_path = safe_path(self.state / 'ingest-evidence' / (reference['sha256'] + '.json'))
                if evidence_path.exists():
                    if evidence_path.read_bytes() != canonical(supplement):
                        raise Stop('evidence_content_address_conflict_preserved')
                else:
                    self.durable_local_json(evidence_path, supplement)
                if self.receipt_transport != 'isolated-branch-v1':
                    # Legacy plans predate this companion protocol. Their exact
                    # old receipts remain recoverable; new release enables it.
                    summary.pop('evidence_ref', None)
                    summary['progress_sha256'] = ingest_progress_digest(summary)
            status=report.get('status')
            outcome='completed' if status=='complete' else 'running' if status=='running' else 'partial' if status=='partial' else 'blocked'
            signature=(outcome,summary['progress_sha256'])
            if signature==last_signature:
                return
            receipt={'schema':'offmenu-run-receipt/2','job_id':job['id'],'job_version':job['version'],
                'operation':job['operation'],'job_key':job_key,'implementation_sha256':implementation,
                'input_sha256':input_sha,'observed_at':datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                'outcome':outcome,'ingest':summary}
            validate_ingest_receipt(receipt)
            spool=pending/Path(receipt_relpath(receipt)).name
            if not spool.exists():
                self.durable_local_json(spool,{'sha256':digest(canonical(receipt)),'receipt':receipt})
            else:
                envelope=read_json(spool)
                exact_keys(envelope,{'sha256','receipt'})
                prior=validate_ingest_receipt(envelope['receipt'])
                if envelope['sha256']!=digest(canonical(prior)) or receipt_relpath(prior)!=receipt_relpath(receipt):
                    raise Stop('pending_receipt_changed_preserved')
                receipt=prior
            last_signature=signature
            deliver(receipt,spool)

        report=engine.run_prepared(prepared,report_callback=checkpoint_report)
        report = {**report, 'household_schema_preparation': household_preparation}
        # Independent final handling also persists a result if an earlier engine
        # callback encountered a local reporting error. No failed source hides it.
        checkpoint_report(report)
        announce('[3/4] Final domain summary (counts are source rows, not unique entities):')
        final_summary=self.ingest_summary(report)
        for domain,row in final_summary['domains'].items():
            announce('  '+domain+': '+row['status']+'; written='+str(row['written'])+' reused_stores='+str(row['reused_stores'])+' reused_table_rows='+str(row['reused_rows'])+' errors='+str(row['errors']))
        self.announce_remaining(final_summary.get('pending_work',unknown_pending_work()), 'Final remaining work')
        if transport_failed:
            announce('[4/4] Git sync remains pending; ingestion data and sanitized checkpoints are preserved locally.')
        return 0 if report.get('status')=='complete' and not transport_failed else 2


    def normalization_engine(self):
        directory = str(self.root / 'manual-action')
        if directory not in sys.path:
            sys.path.insert(0, directory)
        import importlib
        return importlib.import_module('normalization_engine')

    def run_normalization_plan(self, plan, job):
        """Read only owned staging databases; never dispatch ingest/discovery."""
        self.preconditions()
        self.receipt_transport = 'isolated-branch-v1'
        engine = self.normalization_engine()
        from normalization_receipts import build_summary, validate_report, DOMAINS as PUBLIC_DOMAINS
        from ingest_storage_sizes import capture_storage_sizes, unknown_storage_sizes
        self.state = safe_path(self.state)
        self.state.mkdir(mode=0o700, exist_ok=True)
        pending = safe_path(self.state / 'normalization-pending')
        pending.mkdir(mode=0o700, exist_ok=True)
        transport_failed = False

        def failure(exc):
            nonlocal transport_failed
            transport_failed = True
            announce('Receipt sync paused: '+(str(exc) if isinstance(exc, Stop) else 'receipt_delivery_error')+
                     '. DB normalization continues; local checkpoints retained.')

        def deliver_batch(batch):
            if transport_failed or not batch:
                return
            announce('[2/4] Returning '+str(len(batch))+' preserved checkpoints in one batch; no database normalization yet.')
            try:
                self.materialize_ingest_receipts([value for value, _ in batch])
                for _, spool in batch:
                    spool.unlink()
            except KeyboardInterrupt:
                raise
            except Exception as exc:
                failure(exc)

        recovery = self.recovery_receipt()
        if recovery:
            relative, raw, value = recovery
            if not self.tracked(relative) or self.check_outgoing():
                try:
                    self.publish(relative, raw)
                except KeyboardInterrupt:
                    raise
                except Exception as exc:
                    failure(exc)
        # Recover both old ingest and new normalization spools, retaining every
        # canonical byte and prior timestamp. Transport never restarts ingestion.
        batch, batch_bytes = [], 0
        for directory in (safe_path(self.state/'ingest-pending'), pending):
            for spool in sorted(directory.glob('*.json')):
                envelope = read_json(spool)
                exact_keys(envelope, {'sha256', 'receipt'})
                value = validate_runtime_receipt(envelope['receipt'])
                raw = canonical(value)
                if envelope['sha256'] != digest(raw) or spool.name != Path(receipt_relpath(value)).name:
                    raise Stop('pending_receipt_changed_preserved')
                size = len(raw)+(runtime_summary(value).get('evidence_ref') or {}).get('bytes', 0)
                if batch and (len(batch) >= 512 or batch_bytes+size > 8*1024*1024):
                    deliver_batch(batch)
                    batch, batch_bytes = [], 0
                batch.append((value, spool)); batch_bytes += size
        deliver_batch(batch)
        household = self.prepare_household_schema()
        announce('[2/4] Household schema: '+household['status']+'; preparation only, not runtime deployment.')
        announce('[2/4] Normalizing retained database records only; no downloads, extraction, source-file reads or ingestion backlog.')
        announce('  All retained source versions remain distinct. Profiles and inventory are app-managed, not external-input blockers.')
        announce('  Cached rules first; actual recipe/menu AI review remains mandatory and pending an approved route. No AI calls or data export.')
        options = {'workers': plan['max_parallel'], 'report_interval': 60,
                   'disk_reserve_bytes': 2*1024*1024*1024, 'max_seconds': 6*60*60}
        prepared = engine.prepare_default(self.state/'ingest', options)
        input_sha = prepared['input_sha256']
        if not isinstance(input_sha, str) or not HEX.fullmatch(input_sha):
            raise Stop('invalid_normalization_input_identity')
        names = ['run', 'manual-action/plan_runner.py', 'manual-action/plan.json',
                 'manual-action/normalize_recipes.py']
        for pattern in ('normalization_*.py', 'receipt_*.py'):
            names += [str(p.relative_to(self.root)) for p in sorted((self.root/'manual-action').glob(pattern))]
        implementation = digest(b''.join((self.root/path).read_bytes() for path in names)+
            canonical({'household_preparation_sources': household['source_sha256']}))
        job_key = digest(canonical({'job': job, 'implementation': implementation,
                                  'input': input_sha, 'household_preparation': digest(canonical(household))}))
        last_signature = None

        def checkpoint(report):
            nonlocal last_signature
            report = validate_report(report)
            if report['input_sha256'] != input_sha:
                raise Stop('normalization_input_binding_changed')
            try:
                sizes = capture_storage_sizes(self.state/'ingest')
            except Exception:
                sizes = unknown_storage_sizes()
            supplement = build_supplement({'household_schema_preparation': household, 'storage_sizes': sizes})
            reference = reference_for_supplement(supplement)
            evidence_path = safe_path(self.state/'ingest-evidence'/(reference['sha256']+'.json'))
            if evidence_path.exists():
                if evidence_path.read_bytes() != canonical(supplement):
                    raise Stop('evidence_content_address_conflict_preserved')
            else:
                self.durable_local_json(evidence_path, supplement)
            summary = build_summary(report, reference)
            outcome = {'running': 'running', 'rules_complete': 'completed', 'partial': 'partial', 'failed': 'blocked'}[report['status']]
            signature = (outcome, summary['progress_sha256'])
            if signature == last_signature:
                return
            receipt = {'schema': 'offmenu-run-receipt/3', 'job_id': job['id'], 'job_version': job['version'],
                'operation': job['operation'], 'job_key': job_key, 'implementation_sha256': implementation,
                'input_sha256': input_sha, 'observed_at': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                'outcome': outcome, 'normalization': summary}
            validate_runtime_receipt(receipt)
            spool = pending/Path(receipt_relpath(receipt)).name
            if spool.exists():
                envelope = read_json(spool)
                exact_keys(envelope, {'sha256', 'receipt'})
                old = validate_runtime_receipt(envelope['receipt'])
                if envelope['sha256'] != digest(canonical(old)) or receipt_relpath(old) != receipt_relpath(receipt):
                    raise Stop('pending_receipt_changed_preserved')
                receipt = old
            else:
                self.durable_local_json(spool, {'sha256': digest(canonical(receipt)), 'receipt': receipt})
            last_signature = signature
            counts = {key: sum(row[key] for row in report['domains'].values())
                      for key in ('scanned', 'rules_new', 'rules_reused', 'pendingreview', 'unresolved', 'failed')}
            announce('[normalize] '+report['status']+': '+' '.join(key+'='+str(value) for key, value in counts.items())+
                     ' free_disk_bytes='+str(report['resources']['free_disk_bytes'])+
                     ' workers='+str(report['resources']['workers']))
            if not transport_failed:
                try:
                    self.materialize_ingest_receipt(receipt)
                    spool.unlink()
                except KeyboardInterrupt:
                    raise
                except Exception as exc:
                    failure(exc)

        report = engine.run_prepared(prepared, report_callback=checkpoint)
        checkpoint(report)
        announce('[3/4] Database normalization summary (source-version occurrences, not unique gold entities):')
        for domain in PUBLIC_DOMAINS:
            row = report['domains'][domain]
            announce('  '+domain+': '+row['status']+' selected='+str(row['selected_rows'])+
                ' scanned='+str(row['scanned'])+' rules_new='+str(row['rules_new'])+
                ' rules_reused='+str(row['rules_reused'])+' pendingreview='+str(row['pendingreview'])+
                ' unresolved='+str(row['unresolved'])+' failed='+str(row['failed']))
        announce('  Actual AI review: pending approved route; gold/application binding: blocked. Originals preserved for future extraction.')
        if transport_failed:
            announce('[4/4] Git sync remains pending; normalization cache and sanitized checkpoints are preserved locally.')
        return 0 if report['status'] == 'rules_complete' and not transport_failed else 2

    def run_plan(self):
        plan=read_json(self.root / 'manual-action/plan.json')
        job=validate_plan(plan)
        if job['operation']=='normalize_staged_databases':
            return self.run_normalization_plan(plan,job)
        if job['operation']=='retained_ingest_all':
            return self.run_ingest_plan(plan,job)
        self.preconditions()
        recovery = self.recovery_receipt()
        recovered = None
        if recovery:
            relative, raw, value = recovery
            pending = not self.tracked(relative) or bool(self.textgit('rev-list', self.remote_head + '..HEAD', '--', relative))
            if pending:
                announce('[2/4] Resuming the existing sanitized receipt; no inspection repeated.')
                announce('[3/4] Previous supplier outcome: ' + value['outcome'] + '. Existing data/jobs unchanged.')
                self.publish(relative, raw)
                recovered = value
        job = validate_plan(read_json(self.root / 'manual-action/plan.json'))
        foo = self.inspector()
        implementation = digest(b''.join((self.root / path).read_bytes() for path in ('run', 'manual-action/plan_runner.py', 'manual-action/foo_manual.py')))
        input_sha = None
        try:
            with foo.open_regular(foo.SUPPLIER_ARCHIVE)[0] as stream:
                before = os.fstat(stream.fileno())
                raw = stream.read(foo.MAX_COMPRESSED + 1)
                if len(raw) <= foo.MAX_COMPRESSED and len(raw) == before.st_size and foo.fingerprint(before) == foo.fingerprint(os.fstat(stream.fileno())):
                    input_sha = digest(raw)
        except (OSError, foo.Refusal):
            pass
        if recovered and job['version'] == recovered['job_version'] and input_sha == recovered['input_sha256']:
            announce('Existing receipt published; no new reviewed job version or changed input. No inspection repeated.')
            return 0 if recovered['outcome'] == 'completed' else 2
        if recovered:
            announce('Existing receipt published; evaluating new reviewed supplier job version ' + str(job['version']) + '.')
        job_key = digest(canonical({'job': job, 'implementation': implementation, 'input': input_sha}))
        completed = f'{RETURN_DIR}/{job_key}-completed.json'
        if (self.root / completed).exists():
            existing = validate_receipt(read_json(self.root / completed))
            if existing['job_key'] != job_key or existing['outcome'] != 'completed':
                raise Stop('existing_receipt_identity_mismatch')
            raw = canonical(existing)
            if not self.tracked(completed) and not self.owned_receipt(completed, raw):
                raise Stop('unowned_existing_receipt_preserved')
            announce('[2/4] This supplier check is already complete; no inspection repeated.')
            announce('[3/4] Existing sanitized receipt retained; source review remains required.')
            self.publish(completed, raw)
            return 0
        announce('[2/4] Inspecting only the fixed supplier source capsule (30-second bound).')
        # Keep a recoverable receipt_ready record until a new receipt is durable.
        if not (self.state / 'checkpoint.json').exists():
            self.checkpoint('checking', job_key)
        old_handler = signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(foo.Deadline('wall_time_limit')))
        signal.alarm(foo.MAX_SECONDS)
        try:
            result = foo.inspect_supplier()
        except foo.Deadline:
            result = {'status': 'blocked', 'reason': 'wall_time_limit'}
        except (OSError, foo.Refusal, ValueError):
            result = {'status': 'blocked', 'reason': 'inspection_error'}
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
        supplier = {key: result[key] for key in ('status', 'expected_sha256_prefix', 'observed_sha256', 'compressed_bytes', 'source_bytes') if key in result}
        supplier.update(member_count=len(result.get('manifest', [])), transfer='NOT_UPLOADED')
        if result.get('status') == 'blocked':
            supplier['reason'] = result.get('reason') if result.get('reason') in REASONS else 'inspection_error'
        if result.get('status') != 'blocked' and result.get('observed_sha256') != input_sha:
            supplier = {'status': 'blocked', 'reason': 'archive_changed', 'member_count': 0, 'transfer': 'NOT_UPLOADED'}
        outcome = 'completed' if supplier['status'] == 'inspection_pass_manual_review_required' else 'blocked'
        receipt = {'schema': RECEIPT_SCHEMA, 'job_id': job['id'], 'job_version': job['version'],
            'operation': job['operation'], 'job_key': job_key, 'implementation_sha256': implementation,
            'input_sha256': input_sha, 'observed_at': foo.stamp(), 'outcome': outcome,
            'supplier': supplier, 'data_loads': 'not_implemented', 'source_review': 'manual_review_required', 'source_upload': 'NOT_UPLOADED'}
        relative = receipt_relpath(receipt)
        raw = canonical(receipt)
        destination = safe_path(self.root / relative)
        destination.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        if destination.exists():
            prior = validate_receipt(read_json(destination))
            if receipt_relpath(prior) != relative:
                raise Stop('existing_receipt_identity_mismatch')
            raw = canonical(prior)
            if not self.tracked(relative) and not self.owned_receipt(relative, raw):
                raise Stop('unowned_existing_receipt_preserved')
        else:
            foo.write_result(destination, receipt)
            self.checkpoint('receipt_ready', job_key, relative, digest(raw))
        announce('[3/4] Sanitized supplier receipt: ' + outcome + '. No inventory, source upload or data load.')
        self.publish(relative, raw)
        return 0 if outcome == 'completed' else 2


def main():
    runner = Runner(Path(__file__).resolve().parents[1])
    try:
        if len(sys.argv) != 1:
            raise Stop('no_arguments_supported_edit_reviewed_plan_for_reruns')
        inherited = os.environ.pop('OFFMENU_RUN_FD', None)
        inherited_head = os.environ.pop('OFFMENU_RUN_HEAD', None)
        inherited_remote = os.environ.pop('OFFMENU_RUN_REMOTE', None)
        runner.acquire(inherited)
        if inherited is None:
            runner.pull()
            runner.reexec()  # Updated implementation, same exclusive lock; exactly one pull.
        if not inherited_head or runner.textgit('rev-parse', 'HEAD') != inherited_head:
            raise Stop('checkout_changed_during_reexec')
        runner.remote_head = inherited_remote
        runner.check_outgoing()
        code = runner.run_plan()
        announce('Done. Sanitized results returned; this is not AI review, gold or application acceptance.' if code == 0 else 'Partial or blocked result retained; see domain summary. Local data and receipts preserved.')
        return code
    except KeyboardInterrupt:
        announce('STOP: interrupted; local work preserved.')
        return 130
    except Exception as error:
        reason = str(error) if isinstance(error, Stop) else 'local_runner_error'
        announce('STOP: ' + reason + '. No reset, stash, clean or force-push was performed.')
        return 2
    finally:
        if runner.lock is not None:
            os.close(runner.lock)


if __name__ == '__main__':
    raise SystemExit(main())
