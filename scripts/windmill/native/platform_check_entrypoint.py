"""Entrypoint appended to the reviewed incident/SSH helpers by build_native.py."""
_CHECK_PATH = 'u/admin/offmenu_platform_check'
_COUNT_KEYS = {'items_checked', 'items_skipped', 'entries_scanned', 'jobs_checked',
               'markers_checked', 'checkpoints_verified', 'artifact_manifests_verified',
               'artifact_objects_hashed'}
_FINDING_CODES = {'UNSAFE_COLLECTION', 'SYMLINK_ENTRY', 'MISSING_OR_UNSAFE_METADATA',
                  'INVALID_JOB_RECEIPT', 'STALE_ACTIVE_JOB', 'ACTIVE_INFLIGHT_JOB',
                  'UNRESOLVED_INFLIGHT_JOB', 'COMPLETED_NON_SUCCESS', 'UNKNOWN_JOB_STATE',
                  'ROOT_UNAVAILABLE', 'ROOT_OWNERSHIP_OR_MODE', 'INVALID_INFLIGHT_MARKER',
                  'CHECKPOINT_INTEGRITY_FAILED', 'CHECKPOINT_ADVANCED', 'ARTIFACT_INTEGRITY_FAILED',
                  'BUDGET_LIMIT_REACHED', 'CHECK_UNAVAILABLE', 'CHECK_REQUEST_FAILED'}
_SCOPES = {'health': 'recent job metadata and fixed in-flight markers',
           'verify': 'selected current checkpoints and artifact manifests; no history/orphan scan'}


class PlatformCheckFailure(RuntimeError):
    pass


def _check_receipt(value, mode, max_items):
    def require(ok):
        if not ok:
            raise PlatformCheckFailure('CHECK_RECEIPT_INVALID')
    require(isinstance(value, dict) and set(value) == {'schema_version','checked_at','mode','ok',
            'findings','counts','budgets','coverage','status'})
    require(type(value['schema_version']) is int and value['schema_version'] == 1
            and value['mode'] == mode and type(value['ok']) is bool
            and value['status'] in ('ok','findings','incomplete'))
    try:
        stamp = datetime.fromisoformat(value['checked_at'].replace('Z','+00:00'))
        require(stamp.tzinfo is not None)
    except (ValueError,TypeError,AttributeError):
        raise PlatformCheckFailure('CHECK_RECEIPT_INVALID') from None
    counts = value['counts']; budgets = value['budgets']; coverage = value['coverage']
    require(isinstance(counts,dict) and set(counts) == _COUNT_KEYS
            and all(type(n) is int and 0 <= n <= 1000000 for n in counts.values())
            and counts['items_checked'] <= max_items and counts['markers_checked'] <= 2)
    require(isinstance(budgets,dict) and set(budgets) == {'max_items','max_bytes','max_seconds','bytes_read'}
            and type(budgets['max_items']) is int and budgets['max_items'] == max_items
            and type(budgets['max_bytes']) is int and budgets['max_bytes'] == 67108864
            and type(budgets['max_seconds']) in (int,float) and budgets['max_seconds'] == 8
            and type(budgets['bytes_read']) is int and 0 <= budgets['bytes_read'] <= 67108864)
    require(isinstance(coverage,dict) and set(coverage) == {'full_coverage','scope','selection_truncated',
            'stopped_reason','selected_scope_complete'} and coverage['full_coverage'] is False
            and coverage['scope'] == _SCOPES[mode]
            and type(coverage['selection_truncated']) is bool
            and type(coverage['selected_scope_complete']) is bool
            and coverage['stopped_reason'] in (None,'bytes','deadline'))
    require(isinstance(value['findings'],list) and len(value['findings']) <= 110)
    for finding in value['findings']:
        require(isinstance(finding,dict) and set(finding) <= {'code','severity','job_id','status','checkpoint_hash','manifest_hash'}
                and finding.get('code') in _FINDING_CODES and finding.get('severity') in ('info','warning','error'))
        if finding['code'] == 'CHECKPOINT_ADVANCED':
            require(mode == 'verify' and finding['severity'] == 'warning' and counts['items_skipped'] > 0)
        if 'job_id' in finding:
            require(isinstance(finding['job_id'],str) and bool(_JOB.fullmatch(finding['job_id'])))
        if 'status' in finding:
            require(finding['status'] in ('failed','timed_out','supervisor_error'))
        for key in ('checkpoint_hash','manifest_hash'):
            if key in finding:
                require(isinstance(finding[key],str) and bool(_SHA.fullmatch(finding[key])))
    errors = any(f['severity'] == 'error' for f in value['findings'])
    complete = not (coverage['selection_truncated'] or coverage['stopped_reason'] or counts['items_skipped'])
    require(coverage['selected_scope_complete'] is complete)
    require(value['ok'] is (complete and not errors))
    require(value['status'] == ('incomplete' if not complete else ('findings' if errors else 'ok')))
    return value


def _check_native_state():
    client = _incident_sdk()
    response = client.get('/w/offmenu/resources/get/u/admin/offmenu_platform',raise_for_status=False)
    if response.status_code != 200:
        raise PlatformCheckFailure('CHECK_TRANSPORT_FAILED')
    meta = response.json()
    value = meta.get('value',{})
    if (meta.get('path') != 'u/admin/offmenu_platform' or meta.get('workspace_id') != 'offmenu'
            or meta.get('created_by') != 'admin' or meta.get('extra_perms') != {}
            or meta.get('resource_type') != 'state' or not isinstance(value,dict)
            or value.get('format') != 'offmenu-platform-config-v1' or value.get('schema_version') != 1):
        raise PlatformCheckFailure('CHECK_RECEIPT_INVALID')


def _remote_check(mode, max_items):
    client = channel = secret = private_key = None
    try:
        client = paramiko.SSHClient(); _pin(client)
        secret = wmill.get_variable(SECRET_PATH)
        with io.StringIO(secret) as stream:
            private_key = paramiko.Ed25519Key.from_private_key(stream)
        secret = None
        client.connect(HOST,port=PORT,username=USER,pkey=private_key,allow_agent=False,look_for_keys=False,
                       timeout=5,banner_timeout=5,auth_timeout=5,channel_timeout=5)
        private_key = None
        transport = client.get_transport()
        if transport is None or not transport.is_authenticated():
            raise PlatformCheckFailure('CHECK_TRANSPORT_FAILED')
        channel = transport.open_session(timeout=5); channel.settimeout(5)
        command = shlex.join(['python3','/offmenu/scripts/windmill/platform_check.py',
                              '--mode',mode,'--max-items',str(max_items)])
        channel.exec_command('offmenu-exec-v1')
        channel.sendall(json.dumps({'command':command},ensure_ascii=True).encode())
        channel.shutdown_write()
        receipt = _drain(channel,20)
        if any(receipt['truncated'].values()) or receipt['exit_code'] not in (0,1):
            raise PlatformCheckFailure('CHECK_RECEIPT_INVALID')
        value = _check_receipt(json.loads(receipt['stdout']),mode,max_items)
        if receipt['exit_code'] != (0 if value['ok'] else 1):
            raise PlatformCheckFailure('CHECK_RECEIPT_INVALID')
        return value
    finally:
        secret = private_key = None
        for item in (channel,client):
            if item is not None:
                try: item.close()
                except Exception: pass


def _check_incident_failure(code, mode):
    wid = os.environ.get('WM_JOB_ID','').lower()
    logical_id = 'check-' + wid if _UUID.fullmatch(wid) else 'check-without-run-id'
    try:
        receipt = record_incident(logical_id,mode,code,_CHECK_PATH)
        print(json.dumps({'code':code,'incident_resource_path':receipt['resource_path']}))
    except IncidentError:
        print(json.dumps({'code':code,'incident_recorded':False}))
    raise PlatformCheckFailure(code) from None


def main(mode: str = 'health', max_items: int = 100):
    if mode not in ('health','verify') or type(max_items) is not int or not 1 <= max_items <= 100:
        raise ValueError('CHECK_INPUT_INVALID')
    try:
        _check_native_state()
        result = _remote_check(mode,max_items)
    except PlatformCheckFailure as error:
        code = str(error) if str(error) in ('CHECK_RECEIPT_INVALID','CHECK_TRANSPORT_FAILED') else 'CHECK_TRANSPORT_FAILED'
        _check_incident_failure(code,mode)
    except Exception:
        _check_incident_failure('CHECK_TRANSPORT_FAILED',mode)
    if any(f['severity'] == 'error' for f in result['findings']):
        _check_incident_failure('HEALTH_FINDINGS' if mode == 'health' else 'VERIFY_FINDINGS',mode)
    # A bounded partial check is not an integrity failure and is never called healthy.
    # No incident/automatic replay/pruning is generated for coverage-only warnings.
    return dict(result,native_config_private=True)
