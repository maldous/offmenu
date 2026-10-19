"""Separately gated, exact-five owner HEAD diagnostic; no GET/custody mutations."""
from contextlib import ExitStack, contextmanager
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import stat
import time

from .core import canonical, sha, strict_json, RefreshError
from .owner_head_metadata import sanitize_response, validate_observation

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = 'docs/collection-selections/owner-head-diagnostic-proposal.json'
MANIFEST_SHA256 = '6ae3989bc83a05abb60713e595d392f26efa2682ef7d470943b92c56706f50a1'
# A parent-reviewed selection must supply an exact active selection pin separately.
# No automatic selector, environment switch or prepared manifest can activate I/O.
ACTIVATION_SHA256 = None
ACTIVATION_PATH = 'docs/collection-selections/owner-head-diagnostic-activation.json'
# Public identity-only validation requires no parent-side filesystem access.
SOURCE_IDENTITIES = ({'entry': {'sourceKey': 'so-wfp-markets', 'sourceContractSHA256': '2ce67aca77439104e8f8686a65c42642bafeb417d32a476bd7b466565a91fe4f', 'sourceURLSHA256': '604412e658534fae66a7e0bc80bc93677f9c29ff15c64a4006e6ea70c120f815', 'priorDetailSHA256': 'd17451e019e07d1faf50e67a4c091f4b6168bb0a1b1bc0f368106b5ff3526f1c', 'freshFetchDetailSHA256': '339ea2a09fec6b2d37043bd28b2f70913e7d757f2dedc17efe7dadefa6a43e97', 'priorErrorCode': 'source-response-not-permitted'}}, {'entry': {'sourceKey': 'so-wfp-metadata', 'sourceContractSHA256': '2b583a7e8ff30a5058bc964c22c7eab021b4537aed7be3a3721d705c34341ccb', 'sourceURLSHA256': '931c4fff4903d43a35cc6c11e82b24d209f2a482752515bf0cea1bb6add64b88', 'priorDetailSHA256': 'd172972195d2ebb64beb3a7a97bb2eb304e97ba61774b2191b915e0c124006a1', 'freshFetchDetailSHA256': 'a7c13840c678478b59a21ca5da1c2ca8e3aff0091578e4abd64faa4cf4c9915a', 'priorErrorCode': 'invalid-response-headers'}}, {'entry': {'sourceKey': 'so-wfp-prices', 'sourceContractSHA256': '35bf5fc4e1f40e965fafad7cf5e553468ea7db7f948bf089b5d2fb80c0c5d8c1', 'sourceURLSHA256': '34f60731ccee8e57f2a024dc83c3ac81f90f430e2b081db3a5c3d787ddf265ec', 'priorDetailSHA256': '520c0bd5cba792342f6e4e79dd72bf5bdadd2e367701e0b2363b446efb7b4a49', 'freshFetchDetailSHA256': '8b37f095e233fcca5196efd04acb38bf460afc7743c02e968b9267d2138e6004', 'priorErrorCode': 'source-response-not-permitted'}}, {'entry': {'sourceKey': 'pg58-plos-0184279-s001', 'sourceContractSHA256': '9b523baf92829b3455df3818c5e4c309ea5e41466ae17706ac00da37183b9c1d', 'sourceURLSHA256': 'eca306d9a836969228525b16ec5ca1817e62765f30ec1d936baf6a0dcd2f4c4c', 'priorDetailSHA256': 'f64d5304914f010513d5c27056cce6af7678b5bd58e6712890b1300497c36949', 'freshFetchDetailSHA256': 'b03e037ff9b12c7bfdaaf5a598ab9b77f126d35cb810ca7673c35b937932b613', 'priorErrorCode': 'invalid-response-headers'}}, {'entry': {'sourceKey': 'pg58-plos-0184279-s002', 'sourceContractSHA256': '88d17ee9814a2eab9bddee738984183d93101eb8d6d0b5ae93fda1cb04f458c6', 'sourceURLSHA256': '589e7736b7e8fe760ec490dc177e049ff0a4e1df3401d66583124586129cbbef', 'priorDetailSHA256': '3663866316e36d3fd2a7a056c2fb304cde71a979bb5debf2e711087a8c5b5e04', 'freshFetchDetailSHA256': 'c21067a3e6e15c4e3c553ea10ab7925c7209fad25ed5d21854eb2858f031ad99', 'priorErrorCode': 'invalid-response-headers'}})
MAX_REPORT = 65536
MAX_METADATA = 2 * 1024 * 1024
CODES = frozenset(('diagnostic-inactive', 'diagnostic-config-invalid', 'diagnostic-pin-mismatch',
    'diagnostic-owner-mismatch', 'diagnostic-unsafe-path', 'diagnostic-unsafe-metadata',
    'diagnostic-metadata-changed', 'diagnostic-failure-mismatch', 'diagnostic-intent-mismatch',
    'diagnostic-current-claims-blocked', 'diagnostic-custody-conflict', 'diagnostic-lease-held',
    'diagnostic-lease-changed', 'diagnostic-already-attempted', 'diagnostic-deadline',
    'diagnostic-ledger-failed', 'diagnostic-transport-failed', 'diagnostic-result-invalid',
    'diagnostic-local-failure', 'diagnostic-supervisor-failed'))
SAFETY = {'method': 'HEAD', 'maximumGETs': 0, 'sourceBodyBytesRead': 0,
    'sourceClaimsChanged': False, 'sourceCustodyChanged': False, 'originalGETRetried': False,
    'priorGETCauseEstablished': False, 'acquisitionEnabled': False, 'parsePerformed': False,
    'redirectsFollowed': 0, 'retries': 0, 'rawHeaderValuesEmitted': False,
    'queryValuesEmitted': False, 'rawPathsEmitted': False, 'downstreamHoldsPreserved': True,
    'sourceAccessAndRateHoldsPreserved': True, 'automaticPublication': False}


class HeadSource(dict):
    @property
    def exact_url(self):
        return self['url']
    def __repr__(self):
        return '<exact-pinned-head-source>'


def fail(code):
    raise ValueError(code if code in CODES else 'diagnostic-local-failure') from None


def deadline_check(deadline):
    if time.monotonic() >= deadline:
        fail('diagnostic-deadline')


def safe_code(error):
    code = error.args[0] if isinstance(error, ValueError) and error.args else None
    return code if type(code) is str and code in CODES else 'diagnostic-local-failure'


def parse(raw):
    try:
        if type(raw) is not bytes or len(raw) > 32 * 1024 * 1024:
            fail('diagnostic-config-invalid')
        return strict_json(raw)
    except (ValueError, UnicodeError, RecursionError, RefreshError):
        fail('diagnostic-config-invalid')


def identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_nlink,
            info.st_size, info.st_mtime_ns, info.st_ctime_ns)


class SafeTree:
    """Descriptor-pinned owner tree; every metadata component is no-follow."""
    def __init__(self, root, uid):
        self.root = Path(root)
        self.uid = uid
        self.stack = ExitStack()
        self.snapshots = {}
        if not self.root.is_absolute() or '..' in self.root.parts:
            fail('diagnostic-unsafe-path')
        try:
            fd = self._take(os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC))
            for part in self.root.parts[1:]:
                fd = self._take(os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd))
            self.fd = fd
            self._owned(os.fstat(fd), directory=True)
            self.root_inode = identity(os.fstat(fd))[:4]
        except BaseException:
            self.stack.close()
            raise

    def _take(self, fd):
        self.stack.callback(os.close, fd)
        return fd

    def close(self):
        self.stack.close()

    def _owned(self, info, directory=False):
        if (info.st_uid != self.uid or info.st_mode & 0o077
                or not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
                or (not directory and info.st_nlink != 1)):
            fail('diagnostic-unsafe-metadata')

    def _parts(self, relative):
        parts = Path(relative).parts
        if not parts or Path(relative).is_absolute() or any(p in ('..', '.', '') for p in parts):
            fail('diagnostic-unsafe-path')
        return parts

    @contextmanager
    def parent(self, relative):
        parts = self._parts(relative)
        with ExitStack() as stack:
            fd = self.fd
            for part in parts[:-1]:
                fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
                stack.callback(os.close, fd)
                self._owned(os.fstat(fd), directory=True)
            yield fd, parts[-1]

    def read(self, relative, expected_sha=None, *, remember=True):
        with self.parent(relative) as (parent, name):
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=parent)
            try:
                before = os.fstat(fd)
                self._owned(before)
                if before.st_size > MAX_METADATA:
                    fail('diagnostic-unsafe-metadata')
                raw = bytearray()
                while len(raw) <= before.st_size:
                    part = os.read(fd, min(65536, before.st_size + 1 - len(raw)))
                    if not part:
                        break
                    raw.extend(part)
                after = os.fstat(fd)
                named = os.stat(name, dir_fd=parent, follow_symlinks=False)
                if (len(raw) != before.st_size or identity(before) != identity(after)
                        or identity(after) != identity(named)):
                    fail('diagnostic-metadata-changed')
                raw = bytes(raw)
                if relative in self.snapshots and self.snapshots[relative] != (identity(after), sha(raw)):
                    fail('diagnostic-metadata-changed')
                if expected_sha is not None and sha(raw) != expected_sha:
                    fail('diagnostic-pin-mismatch')
                if remember:
                    previous = self.snapshots.get(relative)
                    observed = (identity(after), sha(raw))
                    if previous is not None and previous != observed:
                        fail('diagnostic-metadata-changed')
                    self.snapshots[relative] = observed
                return raw
            finally:
                os.close(fd)

    def absent(self, relative):
        try:
            with self.parent(relative) as (parent, name):
                os.stat(name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            return
        fail('diagnostic-custody-conflict')

    def unchanged(self):
        try:
            if identity(os.fstat(self.fd))[:4] != self.root_inode:
                fail('diagnostic-metadata-changed')
            # Reopen without following any ancestor symlink; no source body reads.
            other = SafeTree(self.root, self.uid)
            try:
                if other.root_inode != self.root_inode:
                    fail('diagnostic-metadata-changed')
            finally:
                other.close()
            for path, (_, digest) in tuple(self.snapshots.items()):
                self.read(path, digest)
        except (OSError, ValueError):
            fail('diagnostic-metadata-changed')

    @contextmanager
    def existing_lease(self):
        relative = 'collection/fixed-selection.lock'
        with self.parent(relative) as (parent, name):
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=parent)
            try:
                self._owned(os.fstat(fd))
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    fail('diagnostic-lease-held')
                def check():
                    try:
                        opened = os.fstat(fd)
                        self._owned(opened)
                        # Reopen from the pinned root: a cached parent descriptor
                        # could otherwise still name a detached collection tree.
                        with self.parent(relative) as (current_parent, current_name):
                            named = os.stat(current_name, dir_fd=current_parent, follow_symlinks=False)
                        if identity(opened) != identity(named):
                            fail('diagnostic-lease-changed')
                    except (OSError, ValueError):
                        fail('diagnostic-lease-changed')
                check()
                yield check
                check()
            finally:
                os.close(fd)

    def open_ledger(self):
        try:
            os.mkdir('head-observations', mode=0o700, dir_fd=self.fd)
            os.fsync(self.fd)
        except FileExistsError:
            pass
        fd = os.open('head-observations', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=self.fd)
        try:
            self._owned(os.fstat(fd), directory=True)
        except BaseException:
            os.close(fd)
            raise
        return fd

    def ledger_unchanged(self, ledger):
        opened = os.fstat(ledger)
        self._owned(opened, directory=True)
        named = os.stat('head-observations', dir_fd=self.fd, follow_symlinks=False)
        if identity(opened)[:4] != identity(named)[:4]:
            fail('diagnostic-metadata-changed')


def immutable(ledger, name, value, *, attempted=False):
    raw = canonical(value)
    if len(raw) > MAX_REPORT:
        fail('diagnostic-result-invalid')
    try:
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=ledger)
    except FileExistsError:
        fail('diagnostic-already-attempted' if attempted else 'diagnostic-ledger-failed')
    try:
        if os.write(fd, raw) != len(raw):
            fail('diagnostic-ledger-failed')
        os.fsync(fd)
    finally:
        os.close(fd)
    os.fsync(ledger)
    # Never remove an uncertain/partial attempt record: it consumes the pass.
    return sha(raw)


def repository_bytes(root, path, expected_sha):
    # No dynamic source locators: every path comes from the immutable manifest.
    if Path(path).is_absolute() or '..' in Path(path).parts:
        fail('diagnostic-config-invalid')
    with ExitStack() as stack:
        fd = os.open(str(root), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        stack.callback(os.close, fd)
        for part in Path(path).parts[:-1]:
            fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
            stack.callback(os.close, fd)
        file = os.open(Path(path).name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=fd)
        stack.callback(os.close, file)
        before = os.fstat(file)
        if not stat.S_ISREG(before.st_mode) or before.st_size > 32 * 1024 * 1024:
            fail('diagnostic-config-invalid')
        raw = bytearray()
        while len(raw) < before.st_size + 1:
            block = os.read(file, min(65536, before.st_size + 1 - len(raw)))
            if not block:
                break
            raw.extend(block)
        if identity(before) != identity(os.fstat(file)) or len(raw) != before.st_size or sha(raw) != expected_sha:
            fail('diagnostic-pin-mismatch')
        return bytes(raw)


def load_bundle(root=ROOT):
    raw = repository_bytes(root, MANIFEST_PATH, MANIFEST_SHA256)
    manifest = parse(raw)
    values = {k: repository_bytes(root, p['path'], p['sha256']) for k, p in manifest['inputs'].items()}
    selection = parse(values['selection'])
    runtime, hold = parse(values['runtime']), parse(values['hold'])
    fetch, third = parse(values['fetch-summary.json']), parse(values['third-summary.json'])
    if (fetch['handover'] != manifest['ownerHandover'] or third['handover'] != manifest['ownerHandover']
            or fetch['globalReport'].get('executionStage') != 'fetch'
            or fetch['globalReport']['networkRequests'] != 0
            or fetch['globalReport']['preparedBytes'] != 0
            or runtime['dispatchHoldPin']['sha256'] != manifest['ownerHandover']['dispatchHoldSHA256']
            or hold['overlapHold']['active'] is not True
            or hold['overlapHold']['automaticRunnerSubmissionPermitted'] is not False
            or selection['privateOriginalDownload']['diagnosticReportPin']['sha256'] != manifest['failedIntentDiagnosticReportSHA256']
            or runtime['sourceKeys'] != [s['sourceKey'] for s in selection['sources']]
            or runtime['sourceContractSHA256'] != [sha(canonical(s)) for s in selection['sources']]):
        fail('diagnostic-config-invalid')
    sources = []
    for entry in manifest['failedSources']:
        source = next(s for s in selection['sources'] if s['sourceKey'] == entry['sourceKey'])
        if sha(canonical(source)) != entry['sourceContractSHA256'] or sha(source['url'].encode()) != entry['sourceURLSHA256']:
            fail('diagnostic-pin-mismatch')
        for chunk, digest in ((entry['priorAssetChunk'], entry['priorAssetRowSHA256']),
                (entry['freshAssetChunk'], entry['freshAssetRowSHA256'])):
            rows = [r for r in parse(values[chunk])['rows'] if r['assetIndex'] == entry['assetIndex']]
            if len(rows) != 1 or sha(canonical(rows[0])) != digest:
                fail('diagnostic-failure-mismatch')
        sources.append(HeadSource(url=source['url'], contract=source, entry=entry))
    if len(sources) != 5 or len({s.exact_url for s in sources}) != 5:
        fail('diagnostic-config-invalid')
    return manifest, sources, selection, runtime


def activation(root, manifest):
    if ACTIVATION_SHA256 is None:
        fail('diagnostic-inactive')
    value = parse(repository_bytes(root, ACTIVATION_PATH, ACTIVATION_SHA256))
    expected = {'schemaVersion': 'offmenu-owner-head-activation/1', 'selected': True,
        'manifestSHA256': MANIFEST_SHA256, 'fetchResultSHA256': manifest['fetchResultSHA256'],
        'handoffId': manifest['ownerHandover']['handoffId'],
        'dispatchHoldSHA256': manifest['ownerHandover']['dispatchHoldSHA256'],
        'scope': 'exact-five-owner-no-body-HEAD-observations', 'maximumRequests': 5,
        'maximumGETs': 0, 'maximumBodyBytes': 0, 'maximumRedirects': 0, 'maximumRetries': 0,
        'maximumSeconds': 90, 'diagnosticLedgerWriteApproved': True,
        'GETRetryApproved': False, 'sourceCustodyWriteApproved': False, 'parseApproved': False}
    if canonical(value) != canonical(expected):
        fail('diagnostic-inactive')
    return value


def collector_module(root):
    spec = importlib.util.spec_from_file_location('owner_head_existing_collector', root / 'scripts/collect-fixed-global.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def current_runtime(g, manifest, selected, config):
    runtime = object.__new__(g.OwnerRuntime)
    runtime.config, runtime.selected, runtime.uid = config, selected, os.getuid()
    runtime.root = Path(manifest['outputRoot'])
    runtime.native = Path(config['nativeClaimsRoot'])
    runtime.runner_work, runtime.runner_cache = Path('/srv/offmenu-refresh/outputs/collection'), Path('/srv/offmenu-refresh/cache')
    return runtime


def guard_current_fetch(tree, manifest):
    digest = manifest['fetchResultSHA256']
    pointer = {'schemaVersion': 'offmenu-manual-result-pointer/1',
        'resultFilename': 'result-' + digest + '.json', 'resultSHA256': digest}
    tree.read('collection/manual-results/latest-fetch.json', sha(canonical(pointer)))
    tree.read('collection/manual-results/result-' + digest + '.json', digest)


def guard_source(tree, manifest, item, runtime, deadline):
    deadline_check(deadline)
    source, e = item['contract'], item['entry']
    detail = parse(tree.read('collection/private-original-result-' + e['priorDetailSHA256'] + '.json', e['priorDetailSHA256']))
    fresh = parse(tree.read('collection/private-original-result-' + e['freshFetchDetailSHA256'] + '.json', e['freshFetchDetailSHA256']))
    folder = 'collection/private-originals/' + e['sourceContractSHA256']
    intent = parse(tree.read(folder + '/successor-intent.json', e['expectedIntentSHA256']))
    expected = {'schemaVersion': 'offmenu-private-original-successor/1', 'sourceKey': e['sourceKey'],
        'url': source['url'], 'sourceContractSHA256': e['sourceContractSHA256'],
        'predecessor': None, 'diagnosticReportSHA256': manifest['failedIntentDiagnosticReportSHA256'], 'owner': manifest['ownerUID'],
        'ownerHandover': manifest['ownerHandover'], 'state': 'failed-no-retry',
        'errorCode': e['priorErrorCode'], 'network': {'requests': 1, 'bodyBytesRead': 0},
        'privateSaveState': 'none', 'localBodyBytes': 0}
    if canonical(intent) != canonical(expected):
        fail('diagnostic-intent-mismatch')
    for value, status, code, count in ((detail, 'failed', e['priorErrorCode'], 1),
            (fresh, 'blocked', 'private-save-intent-uncertain', 0)):
        fields = {'schemaVersion': 'offmenu-private-media-original-save-detail/1',
            'sourceKey': e['sourceKey'], 'selectionSHA256': e['sourceContractSHA256'],
            'status': status, 'errorCode': code, 'network': {'requests': count, 'bodyBytesRead': 0},
            'privateSaveState': 'none', 'localBodyBytes': 0, 'receiptPersistence': 'written',
            'downstreamHolds': source['downstreamHolds']}
        if canonical({k: value.get(k) for k in fields}) != canonical(fields):
            fail('diagnostic-failure-mismatch')
    if sha(canonical(detail.get('responseMetadata'))) != e['priorResponseMetadataSHA256'] or sha(canonical(detail.get('responsePolicy'))) != e['priorResponsePolicySHA256']:
        fail('diagnostic-failure-mismatch')
    for name in ('original.pdf', 'original.csv', 'original.json', 'original.docx', 'original.partial', 'provenance.json', 'reservation.bin'):
        tree.absent(folder + '/' + name)
    try:
        runtime.admit(tree.root / 'collection', source, tree.root / folder / 'successor-intent.json',
            tree.root / 'collection/intents' / (sha(source['url'].encode()) + '.json'), None, deadline)
    except (RefreshError, OSError, ValueError, KeyError, TypeError):
        fail('diagnostic-current-claims-blocked')
    deadline_check(deadline)
    return {'sourceKey': e['sourceKey'], 'intentSHA256': e['expectedIntentSHA256'],
        'priorDetailSHA256': e['priorDetailSHA256'], 'freshFetchDetailSHA256': e['freshFetchDetailSHA256']}


def report_template(code=None):
    return {'schemaVersion': 'offmenu-owner-head-result/1', 'manifestSHA256': MANIFEST_SHA256,
        'status': 'blocked' if code else 'complete', 'code': code, 'items': [],
        'sourceAttemptsConsumed': 0, 'requestAttemptedCount': 0, 'requestAttemptUnknownCount': 0,
        'sourceMetadataUnchanged': None, 'ledgerResultSHA256': None, **SAFETY}


def execute_owner(*, root=ROOT, deadline, observer=None, runtime_factory=None):
    """Owner-only entry; prepared selection always blocks before owner tree access."""
    if ACTIVATION_SHA256 is None:
        return report_template('diagnostic-inactive')
    report = report_template()
    tree = None
    ledger = None
    try:
        deadline_check(deadline)
        manifest, sources, selected, config = load_bundle(root)
        activation(root, manifest)
        if os.getuid() != manifest['ownerUID'] or os.geteuid() != manifest['ownerUID'] or os.getuid() == 0:
            fail('diagnostic-owner-mismatch')
        g = collector_module(root)
        runtime = (runtime_factory or current_runtime)(g, manifest, selected, config)
        tree = SafeTree(manifest['outputRoot'], manifest['ownerUID'])
        if observer is None:
            from .owner_head_transport import observe_head
            observer = observe_head
        with tree.existing_lease() as lease_check:
            guard_current_fetch(tree, manifest)
            states = [guard_source(tree, manifest, s, runtime, deadline) for s in sources]
            tree.unchanged()
            lease_check()
            report['sourceMetadataUnchanged'] = True
            ledger = tree.open_ledger()
            tree.ledger_unchanged(ledger)
            report['sourceAttemptsConsumed'] = 5  # Conservative before durable attempt creation.
            attempt_digest = immutable(ledger, MANIFEST_SHA256 + '.attempt.json', {
                'schemaVersion': 'offmenu-owner-head-attempt/1', 'manifestSHA256': MANIFEST_SHA256,
                'fetchResultSHA256': manifest['fetchResultSHA256'], 'handoffId': manifest['ownerHandover']['handoffId'],
                'method': 'HEAD', 'maximumRequests': 5, 'sources': states,
                'state': 'consumed-no-retry'}, attempted=True)
            tree.read('head-observations/' + MANIFEST_SHA256 + '.attempt.json', attempt_digest)
            report['sourceAttemptsConsumed'] = 5
            for source in sources:
                deadline_check(deadline)
                tree.ledger_unchanged(ledger)
                lease_check()
                tree.unchanged()
                guard_source(tree, manifest, source, runtime, deadline)
                result = observer(source, absolute_deadline=deadline - 1, sanitizer=sanitize_response)
                # Transport emits only a closed wrapper and bounded safe metadata.
                if not isinstance(result, dict) or type(result.get('ok')) is not bool or not valid_attempt(result.get('requestAttempted')):
                    fail('diagnostic-result-invalid')
                attempted = result['requestAttempted']
                report['requestAttemptedCount'] += attempted is True
                report['requestAttemptUnknownCount'] += attempted == 'unknown'
                tree.unchanged()
                tree.ledger_unchanged(ledger)
                guard_source(tree, manifest, source, runtime, deadline)
                lease_check()
                item = {'sourceKey': source['entry']['sourceKey'], 'requestAttempted': attempted,
                    'sourceMetadataUnchanged': True}
                if result['ok']:
                    if set(result) != {'ok', 'requestAttempted', 'observation'}:
                        fail('diagnostic-result-invalid')
                    if attempted is not True:
                        fail('diagnostic-result-invalid')
                    try:
                        item['observation'] = validate_observation(result['observation'], source)
                    except (ValueError, TypeError, KeyError):
                        fail('diagnostic-result-invalid')
                else:
                    if set(result) != {'ok', 'requestAttempted', 'transport_error'}:
                        fail('diagnostic-result-invalid')
                    from .owner_head_transport import ERROR_CODES
                    if type(result['transport_error']) is not str or result['transport_error'] not in ERROR_CODES:
                        fail('diagnostic-result-invalid')
                    item['transportError'] = result['transport_error']
                    report['status'] = 'complete-with-errors'
                report['items'].append(item)
                if len(canonical(report)) > MAX_REPORT:
                    fail('diagnostic-result-invalid')
            tree.unchanged()
            lease_check()
            deadline_check(deadline)
            tree.ledger_unchanged(ledger)
            validate_report(report, sources=sources)
            digest = immutable(ledger, MANIFEST_SHA256 + '.result.json', report)
            tree.ledger_unchanged(ledger)
            tree.read('head-observations/' + MANIFEST_SHA256 + '.result.json', digest, remember=False)
            report['ledgerResultSHA256'] = digest
    except (ValueError, OSError, TypeError, KeyError, RefreshError):
        import sys
        error = sys.exc_info()[1]
        report.update(status='incomplete-consumed' if report['sourceAttemptsConsumed'] else 'blocked', code=safe_code(error))
        if report['code'] in ('diagnostic-metadata-changed', 'diagnostic-intent-mismatch', 'diagnostic-custody-conflict', 'diagnostic-current-claims-blocked', 'diagnostic-lease-changed'):
            report['sourceMetadataUnchanged'] = False
    finally:
        if ledger is not None:
            os.close(ledger)
        if tree is not None:
            tree.close()
    return report


def valid_attempt(value):
    return type(value) is bool or type(value) is str and value == 'unknown'


def validate_report(value, *, sources=None):
    if type(value) is not dict or set(value) != set(report_template()) or len(canonical(value)) > MAX_REPORT:
        fail('diagnostic-result-invalid')
    fixed = {'schemaVersion': 'offmenu-owner-head-result/1', 'manifestSHA256': MANIFEST_SHA256, **SAFETY}
    if canonical({k: value[k] for k in fixed}) != canonical(fixed):
        fail('diagnostic-result-invalid')
    if value['status'] not in ('blocked', 'complete', 'complete-with-errors', 'incomplete-consumed'):
        fail('diagnostic-result-invalid')
    if value['code'] is not None and (type(value['code']) is not str or value['code'] not in CODES):
        fail('diagnostic-result-invalid')
    if value['sourceMetadataUnchanged'] is not None and type(value['sourceMetadataUnchanged']) is not bool:
        fail('diagnostic-result-invalid')
    for key in ('sourceAttemptsConsumed', 'requestAttemptedCount', 'requestAttemptUnknownCount'):
        if type(value[key]) is not int or not 0 <= value[key] <= 5:
            fail('diagnostic-result-invalid')
    digest = value['ledgerResultSHA256']
    if digest is not None and (type(digest) is not str or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest)):
        fail('diagnostic-result-invalid')
    items = value['items']
    if type(items) is not list or len(items) > 5:
        fail('diagnostic-result-invalid')
    if sources is None:
        sources = SOURCE_IDENTITIES
    for index, item in enumerate(items):
        if (type(item) is not dict or set(item) not in (
                {'sourceKey', 'requestAttempted', 'sourceMetadataUnchanged', 'observation'},
                {'sourceKey', 'requestAttempted', 'sourceMetadataUnchanged', 'transportError'})
                or item['sourceKey'] != sources[index]['entry']['sourceKey']
                or item['sourceMetadataUnchanged'] is not True or not valid_attempt(item['requestAttempted'])):
            fail('diagnostic-result-invalid')
        if 'observation' in item:
            if item['requestAttempted'] is not True:
                fail('diagnostic-result-invalid')
            validate_observation(item['observation'], sources[index])
        else:
            from .owner_head_transport import ERROR_CODES
            if type(item['transportError']) is not str or item['transportError'] not in ERROR_CODES:
                fail('diagnostic-result-invalid')
    known_attempted = sum(item['requestAttempted'] is True for item in items)
    known_unknown = sum(item['requestAttempted'] == 'unknown' for item in items)
    if (value['sourceAttemptsConsumed'] not in (0, 5) or value['requestAttemptedCount'] < known_attempted
            or value['requestAttemptUnknownCount'] < known_unknown):
        fail('diagnostic-result-invalid')
    if value['status'] in ('complete', 'complete-with-errors'):
        if (len(items) != 5 or value['code'] is not None or value['sourceAttemptsConsumed'] != 5
                or value['sourceMetadataUnchanged'] is not True
                or value['requestAttemptedCount'] != known_attempted
                or value['requestAttemptUnknownCount'] != known_unknown
                or (value['status'] == 'complete-with-errors') != any('transportError' in item for item in items)):
            fail('diagnostic-result-invalid')
    elif value['code'] is None:
        fail('diagnostic-result-invalid')
    if value['status'] == 'blocked' and (items or value['sourceAttemptsConsumed']):
        fail('diagnostic-result-invalid')
    if value['status'] == 'incomplete-consumed' and value['sourceAttemptsConsumed'] != 5:
        fail('diagnostic-result-invalid')
    if sum(value[k] for k in ('requestAttemptedCount', 'requestAttemptUnknownCount')) > value['sourceAttemptsConsumed']:
        fail('diagnostic-result-invalid')
    return value
