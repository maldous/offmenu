"""Bounded pure reconciliation validation; caller-selected evidence is authority.

No source reads, authority discovery, commits or source-rights grants occur here.
Hashes bind selected inputs; they do not prove that producer assertions are true.
All prior history and registry inputs must come from the independent caller.
"""
from copy import deepcopy
import hashlib
import json
import math
import re

VERSION = 'offmenu.entity-reconciliation/1'
MAX_BYTES, MAX_NODES, MAX_DEPTH = 8 * 1024 * 1024, 200000, 32
DOMAINS = frozenset(('barcodes', 'ingredients', 'recipes', 'dietary', 'suppliers',
                     'citations', 'user_profiles', 'inventory'))


class ReconciliationError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _require(ok, code):
    if not ok:
        raise ReconciliationError(code)


def _bounded(value):
    stack, nodes = [(value, 0)], 0
    while stack:
        item, depth = stack.pop()
        nodes += 1
        _require(nodes <= MAX_NODES and depth <= MAX_DEPTH, 'input_bounds')
        kind = type(item)
        if kind is dict:
            _require(nodes + len(stack) + len(item) <= MAX_NODES, 'input_bounds')
            _require(all(type(k) is str and len(k) <= MAX_BYTES for k in item), 'json_keys')
            stack.extend((v, depth + 1) for v in item.values())
        elif kind is list:
            _require(nodes + len(stack) + len(item) <= MAX_NODES, 'input_bounds')
            stack.extend((v, depth + 1) for v in item)
        elif kind is str:
            _require(len(item) <= MAX_BYTES, 'input_bounds')
        elif kind is float:
            _require(math.isfinite(item), 'json_number')
        else:
            _require(kind in (int, bool, type(None)), 'json_value')
    try:
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(',', ':'), allow_nan=False).encode('utf-8')
    except (ValueError, UnicodeError, OverflowError) as error:
        raise ReconciliationError('json_encoding') from error
    _require(len(raw) <= MAX_BYTES, 'input_bounds')
    return raw


def digest(value):
    return hashlib.sha256(_bounded(value)).hexdigest()


def _object(value, keys, code):
    _require(type(value) is dict and set(value) == set(keys.split()), code)
    return value


def _text(value):
    return type(value) is str and bool(value.strip()) and value.strip().casefold() not in ('none', 'null', 'unknown', 'unverified')


def _id(value, code='identifier_required'):
    _require(_text(value) and len(value) <= 2048, code)


def _sha(value):
    _require(type(value) is str and len(value) == 64 and all(c in '0123456789abcdef' for c in value), 'digest_required')


def _list(value):
    _require(type(value) is list, 'array_required')
    return value


def _unique_ids(value, code='duplicate_identifier'):
    values = _list(value)
    for v in values:
        _id(v)
    _require(len(values) == len(set(values)), code)
    return set(values)


def _index(rows, key, fields):
    result = {}
    for row in _list(rows):
        _object(row, fields, 'row_shape')
        _id(row[key])
        _require(row[key] not in result, 'duplicate_identifier')
        result[row[key]] = row
    return result


def history_digest(history):
    _bounded(history)
    _require(type(history) is dict and type(history.get('entries')) is list, 'history_shape')
    rows = history['entries']
    _require(all(type(r) is dict and _text(r.get('entry_id')) for r in rows), 'history_entry')
    return digest({**history, 'entries': sorted(rows, key=lambda r: r['entry_id'])})


def registry_digest(registry):
    _bounded(registry)
    _require(type(registry) is dict, 'registry_shape')
    _require(type(registry.get('entities')) is list and type(registry.get('memberships')) is list, 'registry_shape')
    _require(all(type(e) is dict and _text(e.get('entity_id')) for e in registry['entities']), 'registry_shape')
    _require(all(type(e) is dict and _text(e.get('entity_id')) and _text(e.get('occurrence_id')) for e in registry['memberships']), 'registry_shape')
    return digest({**registry, 'entities': sorted(registry['entities'], key=lambda e: e['entity_id']),
                   'active_entity_ids': sorted(_unique_ids(registry.get('active_entity_ids'))),
                   'memberships': sorted(registry['memberships'], key=lambda e: (e['entity_id'], e['occurrence_id']))})


ENTITY = 'entity_id domain entity_type household_scope user_scope'
DECISION = 'entry_id kind occurrence_id sequence action disposition entity_id reason identity_evidence_id supersedes'
MEMBERSHIP = 'entry_id kind decision_id occurrence_id entity_id supersedes'
ALIAS = 'entry_id kind from_entity_id to_entity_id decision_id supersedes'


def _scope(row):
    _require(type(row['domain']) is str and row['domain'] in DOMAINS, 'domain_required')
    _id(row['entity_type'])
    for key in ('household_scope', 'user_scope'):
        if row[key] is not None:
            _id(row[key], 'scope_required')
    return (row['domain'], row['entity_type'], row['household_scope'], row['user_scope'])


def _occ_scope(row):
    return _scope({**row, 'domain': row['source']['domain']})


def _identity(value):
    if type(value) is not dict or set(value) != {'namespace', 'provider', 'value_type', 'lexical_value'}:
        return False
    if not all(_text(value[k]) and len(value[k]) <= 2048 for k in ('namespace', 'provider', 'lexical_value')):
        return False
    return value['value_type'] == 'string' or (value['value_type'] == 'integer' and
        re.fullmatch(r'[+-]?[0-9]+', value['lexical_value']) is not None)


def _binding(binding, value, scope_id, hasher):
    _object(binding, 'version scope_id sha256', 'prior_binding_shape')
    _sha(binding['sha256'])
    _require(binding['scope_id'] == scope_id == value['scope_id'] and
             binding['version'] == value['version'] and binding['sha256'] == hasher(value), 'prior_binding_mismatch')


def _history(value, scope_id):
    _object(value, 'schema_version version previous_version scope_id entries', 'history_shape')
    _require(value['schema_version'] == 'offmenu.entity-history/1' and value['scope_id'] == scope_id, 'history_scope')
    _id(value['version'])
    if value['previous_version'] is not None:
        _id(value['previous_version'])
    result = {}
    for row in _list(value['entries']):
        _require(type(row) is dict and row.get('kind') in ('decision', 'membership', 'alias'), 'history_entry_kind')
        _object(row, {'decision': DECISION, 'membership': MEMBERSHIP, 'alias': ALIAS}[row['kind']], 'history_entry_shape')
        _id(row['entry_id'])
        _require(row['entry_id'] not in result, 'duplicate_history_id')
        result[row['entry_id']] = row
    return result


def validate_reconciliation(selection, proposal, *, authority, prior_history=None, prior_registry=None):
    """Validate a selected bounded cohort; never discover or self-admit evidence.

    Unknown identity/support can be preserved under reasoned held/unresolved
    dispositions. An unsupported mapped/qualified assertion is an error. Input
    objects remain unchanged. Required evidence must be independently selected
    by the calling owner; this pure function checks bindings, not source truth.
    """
    _bounded([selection, proposal, authority, prior_history, prior_registry])
    _object(selection, 'schema_version snapshot_id scope_id occurrences claims relationships citations attachments conflicts upstream', 'selection_shape')
    _require(selection['schema_version'] == VERSION, 'selection_version')
    _id(selection['snapshot_id']); _id(selection['scope_id'])
    scope_id, selected_hash = selection['scope_id'], digest(selection)
    occurrences = _index(selection['occurrences'], 'occurrence_id', 'occurrence_id source entity_type household_scope user_scope identifiers raw')
    for row in occurrences.values():
        source = _object(row['source'], 'domain source_key source_version record_id content_sha256 adapter_occurrence_id physical_representation_id', 'source_shape')
        for key in ('source_key', 'source_version', 'record_id'):
            _id(source[key])
        _sha(source['content_sha256']); _occ_scope(row)
        for key in ('adapter_occurrence_id', 'physical_representation_id'):
            if source[key] is not None:
                _id(source[key])
        _list(row['identifiers'])  # Invalid/unknown raw identifier values may stay held.
    claims = _index(selection['claims'], 'claim_id', 'claim_id occurrence_id path raw')
    relationships = _index(selection['relationships'], 'relationship_id', 'relationship_id occurrence_id target_occurrence_id raw')
    citations = _index(selection['citations'], 'citation_id', 'citation_id raw')
    attachments = _index(selection['attachments'], 'attachment_id', 'attachment_id owner_kind owner_id citation_id support_scope raw')
    conflicts = _index(selection['conflicts'], 'conflict_id', 'conflict_id claim_ids raw')
    for claim in claims.values():
        _require(claim['occurrence_id'] in occurrences and type(claim['path']) is str and (not claim['path'] or claim['path'].startswith('/')), 'claim_lineage')
    for rel in relationships.values():
        _require(rel['occurrence_id'] in occurrences, 'relationship_owner')
        if rel['target_occurrence_id'] is not None:
            _id(rel['target_occurrence_id'])
    for conflict in conflicts.values():
        _require(_unique_ids(conflict['claim_ids']) <= claims.keys(), 'conflict_claim_reference')
    _object(selection['upstream'], 'expected_occurrences reason', 'upstream_shape')
    expected = selection['upstream']['expected_occurrences']
    _require(expected is None or (type(expected) is int and expected >= 0), 'upstream_count')
    _require(selection['upstream']['reason'] is None or _text(selection['upstream']['reason']), 'upstream_reason')

    _object(authority, 'schema_version selection_sha256 policy_id policy_sha256 identity_evidence operation_evidence citation_evidence prior_history prior_registry upstream_evidence', 'authority_shape')
    _require(authority['schema_version'] == 'offmenu.entity-authority/1' and authority['selection_sha256'] == selected_hash, 'authority_selection')
    _id(authority['policy_id']); _sha(authority['policy_sha256'])
    identities = _index(authority['identity_evidence'], 'evidence_id', 'evidence_id kind selection_sha256 scope_id domain entity_type household_scope user_scope members identifier evidence_sha256 source_contract_sha256 operation_evidence_id review_receipt_sha256')
    operations = _index(authority['operation_evidence'], 'evidence_id', 'evidence_id selection_sha256 scope_id operation members evidence_sha256 source_contract_sha256')
    supports = _index(authority['citation_evidence'], 'evidence_id', 'evidence_id selection_sha256 scope_id attachment_ids support_scope evidence_sha256 source_contract_sha256')
    for evidence in [*identities.values(), *operations.values(), *supports.values()]:
        _require(evidence['selection_sha256'] == selected_hash and evidence['scope_id'] == scope_id, 'evidence_binding')
        _sha(evidence['evidence_sha256']); _sha(evidence['source_contract_sha256'])
    for evidence in operations.values():
        _require(evidence['operation'] == 'entity_reconciliation' and bool(_unique_ids(evidence['members'])) and set(evidence['members']) <= occurrences.keys(), 'operation_evidence')
    for evidence in supports.values():
        _require(bool(_unique_ids(evidence['attachment_ids'])) and set(evidence['attachment_ids']) <= attachments.keys() and evidence['support_scope'] in ('record', 'field', 'relationship'), 'citation_evidence')

    _object(proposal, 'schema_version entities history citation_resolutions unbound_citations relationship_resolutions', 'proposal_shape')
    _require(proposal['schema_version'] == 'offmenu.entity-proposal/1', 'proposal_version')
    entities = _index(proposal['entities'], 'entity_id', ENTITY)
    for entity in entities.values():
        _scope(entity)
    history = _history(proposal['history'], scope_id)
    prior_entries = {}
    if prior_history is None:
        _require(authority['prior_history'] is None and proposal['history']['previous_version'] is None, 'prior_history_required')
    else:
        prior_entries = _history(prior_history, scope_id)
        _require(authority['prior_history'] is not None, 'prior_history_authority_required')
        _binding(authority['prior_history'], prior_history, scope_id, history_digest)
        _require(all(k in history and history[k] == v for k, v in prior_entries.items()), 'prior_history_rewritten_or_deleted')
        if history.keys() == prior_entries.keys():
            _require(history_digest(proposal['history']) == history_digest(prior_history), 'prior_history_rewritten_or_deleted')
        else:
            _require(proposal['history']['previous_version'] == prior_history['version'] and proposal['history']['version'] != prior_history['version'], 'history_version_chain')

    decisions, members, aliases = {}, {}, {}
    for row in history.values():
        for key in ('supersedes',):
            if row[key] is not None:
                _id(row[key])
        if row['kind'] == 'decision':
            _id(row['occurrence_id'])
            if row['entity_id'] is not None:
                _id(row['entity_id'])
            if row['identity_evidence_id'] is not None:
                _id(row['identity_evidence_id'])
            _require(row['occurrence_id'] in occurrences and type(row['sequence']) is int and row['sequence'] > 0, 'decision_occurrence_sequence')
            _require(row['action'] in ('assign', 'revoke', 'split') and row['disposition'] in ('mapped', 'held', 'excluded'), 'decision_disposition')
            _id(row['reason'], 'decision_reason')
            if row['disposition'] == 'mapped':
                _require(row['entity_id'] in entities and _text(row['identity_evidence_id']) and (row['entry_id'] in prior_entries or row['identity_evidence_id'] in identities) and row['action'] != 'revoke', 'mapped_identity_evidence')
            else:
                _require(row['entity_id'] is None and row['identity_evidence_id'] is None, 'held_entity_forbidden')
            decisions.setdefault(row['occurrence_id'], []).append(row)
        elif row['kind'] == 'membership':
            for key in ('decision_id', 'occurrence_id', 'entity_id'):
                _id(row[key])
            _require(row['decision_id'] in history and row['decision_id'] not in members, 'membership_decision')
            members[row['decision_id']] = row
        else:
            for key in ('from_entity_id', 'to_entity_id', 'decision_id'):
                _id(row[key])
            _require(row['from_entity_id'] in entities and row['to_entity_id'] in entities and row['from_entity_id'] != row['to_entity_id'], 'alias_entity')
            aliases.setdefault(row['from_entity_id'], []).append(row)
    _require(decisions.keys() == occurrences.keys(), 'incomplete_occurrence_dispositions')
    effective = {}
    for oid, chain in decisions.items():
        chain.sort(key=lambda r: r['sequence'])
        _require([r['sequence'] for r in chain] == list(range(1, len(chain) + 1)), 'decision_sequence')
        previous, prior_member = None, None
        for row in chain:
            _require(row['supersedes'] == previous, 'invalid_supersedes')
            if previous is not None and history[previous]['disposition'] == 'mapped' and row['action'] == 'assign':
                _require(row['disposition'] == 'mapped' and row['entity_id'] == history[previous]['entity_id'], 'mapped_successor_requires_explicit_reversal')
            if row['action'] in ('split', 'revoke'):
                _require(previous is not None, 'invalid_reversal')
                _require(history[previous]['disposition'] == 'mapped', 'invalid_reversal')
                if row['action'] == 'split':
                    _require(row['disposition'] == 'mapped' and row['entity_id'] != history[previous]['entity_id'], 'invalid_split')
            if row['disposition'] == 'mapped':
                member = members.get(row['entry_id'])
                _require(member is not None and member['occurrence_id'] == oid and member['entity_id'] == row['entity_id'] and member['supersedes'] == prior_member, 'membership_lineage')
                prior_member = member['entry_id']
            else:
                _require(row['entry_id'] not in members, 'held_membership_forbidden')
            previous = row['entry_id']
        effective[oid] = chain[-1]
    _require(all(history[k]['kind'] == 'decision' and history[k]['disposition'] == 'mapped' for k in members), 'membership_decision')

    groups = {}
    for oid, decision in effective.items():
        if decision['disposition'] == 'mapped':
            groups.setdefault(decision['entity_id'], []).append(oid)
    used_proofs = set()
    for entity_id, oids in groups.items():
        proof_ids = {effective[o]['identity_evidence_id'] for o in oids}
        _require(len(proof_ids) == 1, 'mixed_transitive_evidence')
        proof_id = next(iter(proof_ids))
        _require(proof_id in identities and proof_id not in used_proofs, 'identity_component_not_selected_or_split')
        used_proofs.add(proof_id)
        evidence = identities[proof_id]
        selected_members = _unique_ids(evidence['members'])
        _require(set(oids) <= selected_members <= occurrences.keys(), 'identity_members')
        expected_scope = _scope(evidence)
        _require(expected_scope == _scope(entities[entity_id]) and all(_occ_scope(occurrences[o]) == expected_scope for o in selected_members), 'identity_scope')
        if expected_scope[0] in ('user_profiles', 'inventory'):
            _require(_text(expected_scope[2]), 'private_scope_required')
        _id(evidence['operation_evidence_id'])
        operation = operations.get(evidence['operation_evidence_id'])
        _require(operation is not None and selected_members <= set(operation['members']), 'operation_evidence_required')
        if evidence['kind'] == 'exact_identifier':
            _require(_identity(evidence['identifier']) and all(evidence['identifier'] in occurrences[o]['identifiers'] for o in selected_members), 'invalid_identity_evidence')
            _require(evidence['review_receipt_sha256'] is None, 'unexpected_review_receipt')
        else:
            _require(evidence['kind'] == 'reviewed_equivalence' and evidence['identifier'] is None, 'identity_evidence_kind')
            _sha(evidence['review_receipt_sha256'])

    owners = {'occurrence': occurrences, 'claim': claims, 'relationship': relationships}
    resolutions = _index(proposal['citation_resolutions'], 'attachment_id', 'attachment_id disposition reason evidence_id')
    _require(resolutions.keys() == attachments.keys(), 'citation_dispositions_incomplete')
    qualified_record_occurrences, attached, support_rows, relation_support = set(), set(), [], {}
    for aid, attachment in sorted(attachments.items()):
        _require(type(attachment['owner_kind']) is str and attachment['owner_kind'] in owners and attachment['support_scope'] in ('record', 'field', 'relationship'), 'citation_attachment_shape')
        _id(attachment['owner_id'])
        _require(attachment['citation_id'] is None or type(attachment['citation_id']) is str, 'citation_reference_type')
        owner = owners[attachment['owner_kind']].get(attachment['owner_id'])
        known = owner is not None and attachment['citation_id'] in citations
        resolution = resolutions[aid]
        if resolution['evidence_id'] is not None:
            _id(resolution['evidence_id'])
        _require(resolution['disposition'] in ('qualified', 'unresolved'), 'citation_disposition')
        _id(resolution['reason'], 'citation_reason')
        if known:
            attached.add(attachment['citation_id'])
        if resolution['disposition'] == 'qualified':
            proof = supports.get(resolution['evidence_id'])
            _require(known and proof is not None and aid in proof['attachment_ids'] and proof['support_scope'] == attachment['support_scope'], 'citation_support_unqualified')
            _require((attachment['owner_kind'], attachment['support_scope']) in (
                ('occurrence', 'record'), ('claim', 'record'), ('claim', 'field'),
                ('relationship', 'record'), ('relationship', 'relationship')), 'citation_support_owner_scope')
            if attachment['owner_kind'] == 'occurrence' and attachment['support_scope'] == 'record':
                qualified_record_occurrences.add(attachment['owner_id'])
        else:
            _require(resolution['evidence_id'] is None, 'unresolved_support_evidence')
        support_rows.append({**resolution, 'reference_status': 'resolved' if known else 'unresolved',
                             'support_scope': attachment['support_scope']})
        if attachment['owner_kind'] == 'relationship':
            relation_support.setdefault(attachment['owner_id'], []).append(support_rows[-1])
    _require(all(o in qualified_record_occurrences for o in effective if effective[o]['disposition'] == 'mapped'), 'mapped_occurrence_uncited')
    unbound = _index(proposal['unbound_citations'], 'citation_id', 'citation_id reason')
    _require(set(unbound) == citations.keys() - attached, 'unbound_citation_accounting')
    for row in unbound.values():
        _id(row['reason'], 'unbound_citation_reason')
    relationship_resolutions = _index(proposal['relationship_resolutions'], 'relationship_id', 'relationship_id disposition reason')
    _require(relationship_resolutions.keys() == relationships.keys(), 'relationship_dispositions_incomplete')
    relationship_rows = []
    for rid, rel in sorted(relationships.items()):
        resolution = relationship_resolutions[rid]
        _require(resolution['disposition'] in ('mapped', 'unresolved'), 'relationship_disposition')
        _id(resolution['reason'])
        endpoint = rel['target_occurrence_id'] in effective and effective[rel['occurrence_id']]['disposition'] == 'mapped' and effective[rel['target_occurrence_id']]['disposition'] == 'mapped'
        _require(resolution['disposition'] != 'mapped' or endpoint, 'relationship_endpoint_unresolved')
        rel_attachments = relation_support.get(rid, [])
        relationship_rows.append({**resolution, 'citation_support': 'qualified' if rel_attachments and all(s['disposition'] == 'qualified' and s['support_scope'] == 'relationship' for s in rel_attachments) else 'unresolved'})

    before, after, baseline_reason = None, None, 'qualified_prior_registry_unavailable'
    prior_entities, active, prior_members = {}, set(), {}
    if prior_registry is None:
        _require(authority['prior_registry'] is None, 'prior_registry_required')
    else:
        _object(prior_registry, 'schema_version version scope_id entities active_entity_ids memberships', 'registry_shape')
        _require(prior_registry['schema_version'] == 'offmenu.entity-registry/1' and prior_registry['scope_id'] == scope_id, 'registry_scope')
        _id(prior_registry['version'])
        prior_entities = _index(prior_registry['entities'], 'entity_id', ENTITY)
        for eid, entity in prior_entities.items():
            _scope(entity)
            _require(eid in entities and entities[eid] == entity, 'prior_entity_rewritten_or_deleted')
        active = _unique_ids(prior_registry['active_entity_ids'])
        _require(active <= prior_entities.keys(), 'registry_active_reference')
        pairs, assigned = set(), set()
        for member in _list(prior_registry['memberships']):
            _object(member, 'entity_id occurrence_id', 'registry_membership')
            _id(member['entity_id']); _id(member['occurrence_id'])
            pair = (member['entity_id'], member['occurrence_id'])
            _require(pair not in pairs and pair[0] in prior_entities and pair[1] in occurrences, 'registry_membership')
            _require(_scope(prior_entities[pair[0]]) == _occ_scope(occurrences[pair[1]]), 'registry_member_scope')
            if pair[0] in active:
                _require(pair[1] not in assigned, 'registry_multiple_active_membership')
                assigned.add(pair[1])
            pairs.add(pair)
            prior_members.setdefault(pair[0], set()).add(pair[1])
        _require(all(prior_members.get(eid) for eid in active), 'registry_active_members_missing')
        if authority['prior_registry'] is not None:
            _binding(authority['prior_registry'], prior_registry, scope_id, registry_digest)
            before, baseline_reason = len(active), None
    effective_aliases, new_aliases = {}, {}
    for source_id, chain in aliases.items():
        rows = {r['entry_id']: r for r in chain}
        successors = {}
        for row in chain:
            previous = row['supersedes']
            _require(previous is None or previous in rows, 'alias_supersedes')
            _require(previous not in successors, 'alias_branch')
            successors[previous] = row
            decision = history.get(row['decision_id'])
            _require(decision is not None and decision['kind'] == 'decision' and decision['disposition'] == 'mapped' and decision['entity_id'] == row['to_entity_id'], 'alias_decision')
            _require(_scope(entities[source_id]) == _scope(entities[row['to_entity_id']]), 'alias_scope')
        seen, previous = set(), None
        while previous in successors:
            row = successors[previous]
            _require(row['entry_id'] not in seen, 'alias_cycle')
            seen.add(row['entry_id']); previous = row['entry_id']
        _require(len(seen) == len(rows), 'alias_cycle_or_missing_root')
        effective_aliases[source_id] = rows[previous]['to_entity_id']
        if previous not in prior_entries:
            new_aliases[source_id] = rows[previous]['to_entity_id']
    # An inherited retirement is still effective: a split must use a fresh
    # entity (or a future explicit alias-revocation operation), not reactivate
    # the alias source while consumers still resolve it to its old target.
    _require(not (effective_aliases.keys() & groups.keys()), 'effective_alias_source_reactivated')
    _require(not (set(effective_aliases) & set(effective_aliases.values())), 'active_alias_chain')
    if new_aliases:
        _require(before is not None, 'alias_requires_qualified_registry')
        for old, target in new_aliases.items():
            _require(old in active and target in groups and all(effective[o]['disposition'] == 'mapped' and effective[o]['entity_id'] == target for o in prior_members[old]), 'alias_incomplete_membership')
    _require(set(entities) <= set(prior_entities) | {d['entity_id'] for chain in decisions.values() for d in chain if d['disposition'] == 'mapped'}, 'unreferenced_entity')
    if before is not None:
        # Preserve the registry as history, but qualify effective membership.
        # A first assignment cannot silently move an already active member.
        # Retirement aliases qualify a whole-entity merge. Otherwise the
        # occurrence's explicit decision chain must include its old mapping
        # before a validated split/revoke/reassignment can move it away.
        residual_members = {eid: set(prior_members[eid]) for eid in active - new_aliases.keys()}
        for old, remaining in residual_members.items():
            for oid in tuple(remaining):
                current = effective[oid]
                if current['disposition'] == 'mapped' and current['entity_id'] != old:
                    _require(any(row['disposition'] == 'mapped' and row['entity_id'] == old
                                 for row in decisions[oid]), 'active_membership_remap_requires_explicit_transition')
                    remaining.remove(oid)
        # Held/unselected decisions do not erase retained baseline membership;
        # partial splits retain residual members, and fully moved entities no
        # longer inflate the active count. Raw prior rows remain untouched.
        final_active = {eid for eid, remaining in residual_members.items() if remaining} | groups.keys()
        effective_owners = {}
        for eid, remaining in residual_members.items():
            for oid in remaining:
                _require(oid not in effective_owners or effective_owners[oid] == eid, 'final_multiple_active_membership')
                effective_owners[oid] = eid
        for eid, oids in groups.items():
            for oid in oids:
                _require(oid not in effective_owners or effective_owners[oid] == eid, 'final_multiple_active_membership')
                effective_owners[oid] = eid
        _require(not (effective_aliases.keys() & final_active), 'effective_alias_source_active_registry')
        _require(set(effective_aliases.values()) <= final_active, 'effective_alias_target_inactive')
        after = len(final_active)

    upstream_total, upstream_reason = None, 'upstream_occurrence_coverage_unavailable'
    if authority['upstream_evidence'] is not None:
        proof = _object(authority['upstream_evidence'], 'selection_sha256 scope_id expected_occurrences evidence_sha256', 'upstream_evidence')
        _sha(proof['evidence_sha256'])
        _require(proof['selection_sha256'] == selected_hash and proof['scope_id'] == scope_id and type(proof['expected_occurrences']) is int and proof['expected_occurrences'] == expected == len(occurrences), 'upstream_evidence_binding')
        upstream_total, upstream_reason = expected, None
    mapped = sum(r['disposition'] == 'mapped' for r in effective.values())
    known_keys = {(r['source']['domain'], r['source']['source_key'], r['source']['source_version'], r['source']['record_id'], r['source']['content_sha256']) for r in occurrences.values()}
    qualified_fields = {attachments[s['attachment_id']]['owner_id'] for s in support_rows if s['disposition'] == 'qualified' and attachments[s['attachment_id']]['owner_kind'] == 'claim' and s['support_scope'] == 'field'}
    normalized_proposal = deepcopy(proposal)
    normalized_proposal['history']['entries'].sort(key=lambda e: e['entry_id'])
    metrics = {'selected_occurrences': len(occurrences), 'distinct_source_record_keys': len(known_keys),
               'extra_representation_occurrences': len(occurrences) - len(known_keys),
               'mapped_occurrences': mapped, 'held_occurrences': sum(r['disposition'] == 'held' for r in effective.values()),
               'excluded_occurrences': sum(r['disposition'] == 'excluded' for r in effective.values()),
               'mapped_entities': len(groups), 'duplicate_mapped_occurrences': mapped - len(groups),
               'entities_before': before, 'entities_after': after, 'registry_unavailable_reason': baseline_reason,
               'upstream_occurrences': upstream_total, 'upstream_unavailable_reason': upstream_reason,
               'mapped_record_citation_coverage': {'covered': mapped, 'total': mapped},
               'all_record_citation_coverage': {'covered': len(qualified_record_occurrences), 'total': len(occurrences)},
               'claim_field_citation_coverage': {'covered': len(qualified_fields), 'total': len(claims)},
               'citation_count': len(citations), 'attachment_count': len(attachments), 'unbound_citations': len(unbound),
               'unresolved_citation_support': sum(s['disposition'] == 'unresolved' for s in support_rows),
               'dangling_citation_references': sum(s['reference_status'] == 'unresolved' for s in support_rows),
               'unresolved_conflicts': len(conflicts), 'unresolved_relationship_support': sum(r['citation_support'] == 'unresolved' for r in relationship_rows),
               'orphan_citation_loss': 0, 'unaccounted_occurrences': 0}
    result = {'schema_version': 'offmenu.entity-receipt/1', 'status': 'validated_selected_scope_not_data_admission',
              'preserved': deepcopy(selection), 'validated_proposal': normalized_proposal,
              'effective_decisions': [deepcopy(effective[k]) for k in sorted(effective)],
              'citation_support': support_rows, 'relationship_support': relationship_rows, 'metrics': metrics,
              'pins': {'selection_sha256': selected_hash, 'occurrences_sha256': digest(selection['occurrences']),
                       'citations_sha256': digest(selection['citations']), 'claims_sha256': digest(selection['claims']),
                       'policy_sha256': authority['policy_sha256'], 'authority_sha256': digest(authority),
                       'prior_history_sha256': history_digest(prior_history) if prior_history else None,
                       'prior_registry_sha256': registry_digest(prior_registry) if prior_registry else None,
                       'history_sha256': history_digest(proposal['history'])}}
    result['pins']['output_sha256'] = digest(result)
    return result
