"""Fixed native CIQUAL delivery identity and aggregate-only export contract."""
from __future__ import annotations

import json
import re

from offmenu_ciqual import source_native as native
from offmenu_ciqual.adapter import runtime
from . import core, survey, survey_ciqual

SCHEMA = 'offmenu-ciqual-source-native-receipt/1'
ERROR_CODES = survey.ERRORS | frozenset(('native-receipt-invalid',
    'native-cell-position', 'native-cell-shape-drift', 'native-code-changed-during-build',
    'native-contract-version', 'native-duplicate-food-id', 'native-existing-candidate-conflict',
    'native-food-id', 'native-french-name-missing', 'native-header-hash-drift',
    'native-identity-entry', 'native-identity-envelope', 'native-identity-field',
    'native-identity-field-set', 'native-identity-join-drift', 'native-identity-set-drift',
    'native-invalid-cell', 'native-invalid-style-id', 'native-nine-input-bundle-required',
    'native-output-limit', 'native-output-location', 'native-output-parent-required',
    'native-output-set-or-size', 'native-row-count-drift', 'native-row-sequence-drift',
    'native-selected-input-pin-mismatch', 'native-selected-pin-contract-drift',
    'native-sheet-count-drift', 'native-sheet-name-drift', 'native-sheet-target',
    'native-survey-contract-drift', 'native-unreviewed-structure', 'native-unsafe-workbook',
    'native-worksheet-envelope', 'writer-lock-held', 'symlink-path-rejected',
    'directory-unavailable-or-symlink', 'regular-file-required', 'asset-size-limit',
    'asset-size-mismatch', 'input-changed-during-read', 'input-unavailable-or-symlink',
    'asset-sha256-mismatch'))


def selected_output(trusted_sha):
    if not isinstance(trusted_sha, str) or not re.fullmatch('[0-9a-f]{40}', trusted_sha):
        raise core.RefreshError('trusted-code-sha-not-configured')
    # A runtime change gets a distinct immutable destination, never an overwrite.
    suffix = core.sha(core.canonical(runtime()))[:16]
    return survey.OUTPUT / ('ciqual-source-native-' + trusted_sha + '-' + suffix)


def sanitize_receipt(value):
    """No source records, paths, metadata bodies or arbitrary text can escape."""
    try:
        fixed = {'schemaVersion': SCHEMA, 'status': 'private-source-native-extracted',
            'inputPinsVerified': True, 'readOnlyViewVerified': True,
            'sourceContentsUploaded': False, 'sourceCopies': 0, 'downloads': 0,
            'sourceWrites': 0, 'acceptance': 'not-performed', 'publicExport': 'not-enabled',
            'countryCoverageComplete': False, 'freshness': 'unknown',
            'originalAcquiredAt': None, 'minimumReuseDays': 30}
        if type(value) is not dict or set(value) != set(fixed) | {'buildKey', 'inputBundleSha256', 'counts', 'created', 'artifacts'}:
            raise ValueError()
        if any(type(value[k]) is not type(v) or value[k] != v for k, v in fixed.items()):
            raise ValueError()
        if type(value['created']) is not bool:
            raise ValueError()
        for key in ('buildKey', 'inputBundleSha256'):
            if type(value[key]) is not str or not re.fullmatch('[0-9a-f]{64}', value[key]):
                raise ValueError()
        if value['inputBundleSha256'] != core.sha(core.canonical(native._pins())):
            raise ValueError()
        expected = native.contract()['survey']
        count = expected['reconciliation']['intersection']
        fixed_counts = {'raw': count, 'extracted': count, 'accepted': None,
            'sourceColumns': 84, 'sourceQuantityColumns': 74, 'infoodsRows': 75,
            'duplicates': 0, 'excluded': 0, 'quarantined': 0}
        counts = value['counts']
        if type(counts) is not dict or set(counts) != set(fixed_counts) | {'qualifiers'}:
            raise ValueError()
        if any(type(counts[k]) is not type(v) or counts[k] != v for k, v in fixed_counts.items()):
            raise ValueError()
        qualifiers = counts['qualifiers']
        if type(qualifiers) is not dict or not set(qualifiers) <= set(survey_ciqual.QUALIFIERS):
            raise ValueError()
        if any(type(v) is not int or not 0 <= v <= count * 74 for v in qualifiers.values()) or sum(qualifiers.values()) != count * 74:
            raise ValueError()
        artifacts = value['artifacts']
        if type(artifacts) is not dict or set(artifacts) != set(native.OUTPUT_FILES):
            raise ValueError()
        for pin in artifacts.values():
            if (type(pin) is not dict or set(pin) != {'bytes', 'sha256'} or
                    type(pin['bytes']) is not int or not 0 < pin['bytes'] <= native.MAX_OUTPUT or
                    type(pin['sha256']) is not str or not re.fullmatch('[0-9a-f]{64}', pin['sha256'])):
                raise ValueError()
        if sum(p['bytes'] for p in artifacts.values()) > native.MAX_OUTPUT:
            raise ValueError()
        encoded = core.canonical(value)
        if len(encoded) > 8192:
            raise ValueError()
        return json.loads(encoded)
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError):
        raise core.RefreshError('native-receipt-invalid') from None
