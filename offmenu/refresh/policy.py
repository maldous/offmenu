"""Offline-only planning for registered bundles; observations never alter keys."""
from datetime import datetime, timezone
from .core import RefreshError, exact_keys, safe_path, strict_json, timestamp
from .registry import fixture


def load_evidence(path):
    path = safe_path(path)
    if not path.is_file() or path.stat().st_size > 16384:
        raise RefreshError('evidence-missing-or-too-large')
    return strict_json(path.read_bytes())


def plan_fixture(name, evidence=None, *, now=None, force=False, repin_runtime=False):
    entry = fixture(name, repin_runtime=repin_runtime, with_blobs=False)
    result = {'schemaVersion': 'offmenu-refresh-policy/2',
              'sourceId': entry.source_id, 'releaseId': entry.lock['releaseId'],
              'scope': entry.lock['scope'], 'inputBundleSha256': entry.bundle_key(),
              'admission': 'reviewed-immutable-authored-fixture',
              'historicalSourceAdmission': 'not-enabled',
              'minimumReuseDays': 30, 'acquisitionAgeDays': None,
              'decision': 'acquisition-evidence-not-supplied',
              'assetBytesVerifiedByThisPlan': False, 'mtimeUsedForFreshness': False,
              'revalidationResetsAcquisitionAge': False, 'acquisitionEvidenceInBuildKey': False,
              'onlineAcquisition': 'not-implemented', 'networkRequests': 0,
              'nextOnlineStep': 'none'}
    if evidence is not None:
        exact_keys(evidence, ('schemaVersion', 'inputBundleSha256', 'originalAcquiredAt', 'revalidations'))
        if (evidence['schemaVersion'] != 'offmenu-refresh-acquisition-evidence/2'
                or evidence['inputBundleSha256'] != entry.bundle_key()):
            raise RefreshError('evidence-bundle-mismatch')
        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None:
            raise RefreshError('policy-clock-must-be-aware')
        acquired = timestamp(evidence['originalAcquiredAt'])
        age = (now - acquired).total_seconds()
        if age < 0:
            raise RefreshError('acquisition-timestamp-in-future')
        if not isinstance(evidence['revalidations'], list):
            raise RefreshError('invalid-revalidation-evidence')
        previous = acquired
        for event in evidence['revalidations']:
            exact_keys(event, ('observedAt', 'result', 'inputBundleSha256'))
            observed = timestamp(event['observedAt'])
            if (event['result'] not in ('not-modified-304', 'identical-body-200')
                    or event['inputBundleSha256'] != entry.bundle_key()
                    or not previous <= observed <= now):
                raise RefreshError('invalid-revalidation-evidence')
            previous = observed
        result.update(acquisitionAgeDays=int(age // 86400),
                      decision='reuse-verified-retained-inputs' if age < 30 * 86400
                      else 'revalidation-review-required-no-download')
    if force:
        result['decision'] = 'explicit-refresh-review-required-no-download'
    return result
