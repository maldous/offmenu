"""Private, effect-free join for the existing UIF OffMenu publication outcome.

Inputs come from the already protected publisher-owner and independent
destination reader, not a public request. The projection is neither custody
nor an attestation; only existing UIF control may independently attest it.
"""

import json

from native_publisher_invocation import (InvocationHold, association, decode, exact,
                                         fingerprint, hex64, request, require, sha,
                                         uif_attempt_id, validate_result, wire)
from offmenu.delivery.integration import Controller

HANDOFF = {'schema', 'publisher', 'issue_id', 'fence', 'binding', 'accepted_review_sha256',
           'candidate', 'tree', 'parent', 'bundle', 'bundle_sha256',
           'existing_publication_intent', 'existing_publication_receipt'}


def seal_native_publication(*, current_fence, handoff_raw, protected_owner_handoff_sha256, protected_attempt_id,
                            inner, protected_config):
    """Validate the protected owner's original input, never resolve authority."""
    require(association(protected_config, inner) == 'integration', 'owner_original_scope')
    require(type(handoff_raw) is bytes and hex64(protected_owner_handoff_sha256)
            and sha(handoff_raw) == protected_owner_handoff_sha256, 'owner_handoff_pin')
    handoff = decode(handoff_raw, 128_000)
    require(exact(handoff, HANDOFF) and handoff['schema'] == 'uif.native-owner-candidate/1'
            and handoff['publisher'] == 'offmenu-cloud' and handoff['fence'] == current_fence
            # UIF handoff_store.wire: unlike OffMenu invocation.wire, no LF.
            and handoff_raw == json.dumps(handoff, sort_keys=True, separators=(',', ':'),
                                         allow_nan=False).encode() and hex64(handoff['accepted_review_sha256'])
            and hex64(handoff['bundle_sha256']), 'owner_handoff_scope')
    b = protected_config['binding']
    hb = handoff['binding']
    try:
        fsource = current_fence['source']
        fkey = current_fence['scope']['key']
        require('source_projection' not in b and fingerprint(b) == inner['operation_id']
                and inner['issue_id'] == handoff['issue_id'] == fkey['issue_id']
                and inner['project_id'] == fkey['project_id']
                and hb['kind'] == 'git' and hb['issue_id'] == inner['issue_id']
                and hb['repo'] == b['repository'] == fsource['repository']
                and hb['base'] == fsource['branch'] == 'develop'
                and hb['branch'] == b['head_branch']
                and hb['candidate'] == handoff['candidate'] == b['head']
                and handoff['tree'] == b['tree']
                and handoff['parent'] == b['base'] == fsource['head']
                and handoff['bundle'] == b['head'] + '.bundle',
                'owner_original_handoff_mismatch')
    except (KeyError, TypeError, AttributeError):
        raise InvocationHold('owner_original_handoff_shape') from None
    require(type(current_fence['generation']) is int and current_fence['generation'] > 0
            and uif_attempt_id(protected_attempt_id), 'owner_fence_attempt')
    return {'schema': 'uif.offmenu-native-publication-original/1',
            'handoff_sha256': protected_owner_handoff_sha256, 'attempt_id': protected_attempt_id,
            'fence': json.loads(json.dumps(current_fence, allow_nan=False))}


def join_native_publication(*, current_fence, handoff_raw, protected_owner_handoff_sha256,
                            protected_attempt_id, envelope,
                            result, closure_sha256, protected_config, controller,
                            destination_snapshot):
    """Project only an exact native-owner git candidate and verified merge.

    The pin must be the original UIF producer receipt's protected pin from
    _verify_producer_handoff, not a hash learned from presented handoff bytes
    or their Linear notice. The exact raw handoff binds its accepted-review and
    bundle hashes. The OffMenu invocation wire does not independently attest
    those hashes; the existing protected producer receipt is their trust source.
    No production caller is provided by this module.
    """
    outer = request(wire(envelope))
    inner = outer['request']
    require(outer['mode'] == 'observe' and type(controller) is Controller
            and controller.binding == protected_config['binding'], 'owner_original_scope')
    expected = seal_native_publication(current_fence=current_fence, handoff_raw=handoff_raw,
        protected_owner_handoff_sha256=protected_owner_handoff_sha256,
        protected_attempt_id=protected_attempt_id, inner=inner, protected_config=protected_config)
    observed = validate_result(result, outer, closure_sha256)
    ref = observed['receipt']
    require(observed['status'] == 'complete' and ref is not None
            and ref['body']['intent']['phase'] == 'integration'
            and ref['body']['intent'].get('uif_publication') == expected
            and observed['response'] is not None and observed['response']['status'] == 'verified',
            'owner_original_not_verified')
    # GitHub-only proof is intentionally not whole-issue or tracker acceptance.
    require(type(destination_snapshot) is dict
            and not {'linear', 'full_issue_acceptance'} & destination_snapshot.keys(),
            'independent_destination_scope')
    decision = controller.decide(destination_snapshot)
    require(decision.get('status') == 'merge-verified'
            and decision.get('binding_sha256') == inner['operation_id']
            and decision.get('merge_effect') == 'verified'
            and decision.get('merge_commit_sha') == destination_snapshot.get('github', {}).get('merge_commit_sha'),
            'independent_destination_not_verified')
    return {'schema': 'uif.offmenu-publisher-outcome/1', 'publisher': 'offmenu-cloud',
            'handoff_sha256': protected_owner_handoff_sha256, 'fence': current_fence,
            'publication_original_id': inner['operation_id'], 'repository': controller.binding['repository'],
            'base': 'develop', 'publication_receipt_sha256': ref['sha256']}


class ProtectedUIFPublicationConsume:
    """Private capability supplied by the installed owner, never JSON input.

    The authenticated resolver must query current UIF control authority. Its
    attempt ID and original invocation envelope are held independently by the
    installed owner. This component supplies neither a resolver nor credentials.
    """
    def __init__(self, *, envelope, closure_sha256, seal, attempt_id, resolve_current):
        self._envelope = request(wire(envelope))
        require(self._envelope['mode'] == 'invoke' and self._envelope['request']['mode'] in ('step','publish')
                and hex64(closure_sha256) and uif_attempt_id(attempt_id)
                and type(seal) is dict and seal.get('attempt_id') == attempt_id
                and callable(resolve_current), 'protected_consume_context')
        self._closure = closure_sha256
        self._seal = json.loads(json.dumps(seal, allow_nan=False))
        self._current = resolve_current

    def check(self, controller, *, owner_uid=984):
        # Production controller always supplies its fixed protected directory;
        # owner_uid default is fixed and no wire caller passes either value.
        from native_publisher_invocation import _read, _result, LIMIT
        require(type(controller) is Controller and self._envelope['request']['operation_id'] ==
                fingerprint(controller.binding), 'protected_consume_original')
        path = controller.directory / ('native-invocation-' + self._envelope['invocation_id'] + '.json')
        raw = _read(path, owner_uid, 0o600, LIMIT)
        record = decode(raw)
        result = validate_result(_result(self._envelope, record), self._envelope, self._closure)
        require(result['status'] == 'unknown' and record['terminal'] is None
                and record['intent'].get('uif_publication') == self._seal,
                'protected_consume_original')
        fence = json.loads(json.dumps(self._seal['fence'], allow_nan=False))
        reply = self._current(fence=fence, attempt_id=self._seal['attempt_id'])
        require(type(reply) is dict and reply.keys() == {'current'} and reply['current'] is True,
                'protected_consume_fence_not_current')
        require(_read(path, owner_uid, 0o600, LIMIT) == raw, 'protected_consume_original_changed')
