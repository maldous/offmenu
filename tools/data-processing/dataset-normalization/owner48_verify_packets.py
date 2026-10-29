#!/usr/bin/env python3
"""Explicit read-only full AFCD packet verification; no default workstation paths.

CI fixtures test these invariants on declared bounded cases; callers supply the
actual retained packets to repeat full-data custody checks when authorized.
"""
import argparse
import hashlib
import json
from pathlib import Path


def rows(path):
    return [json.loads(x) for x in Path(path).read_bytes().splitlines()]


def verify_normalization(records, expected=1801, mass=1588, volume=213, recovered=1588):
    if len(records) != expected or len({r['original_normalized_id'] for r in records}) != expected:
        raise ValueError('Profile count/identifier mismatch')
    if sum(r['food_basis']['unit'] == 'g' for r in records) != mass or sum(r['food_basis']['unit'] == 'ml' for r in records) != volume:
        raise ValueError('Mass/volume basis count mismatch')
    if sum(len(r['recovered_source_columns']) for r in records) != recovered:
        raise ValueError('Recovered observation count mismatch')
    if any(r['semantic_gold'] or r['translated_acceptance'] for r in records):
        raise ValueError('Unexpected semantic acceptance')


def verify_conflicts(parent, successor, expected=1801, recovered=1588):
    if len(parent) != expected or len(successor) != expected:
        raise ValueError('Packet row count mismatch')
    changes = []
    for before, after in zip(parent, successor):
        if before['original_normalized_id'] != after['original_normalized_id']:
            raise ValueError('Identity/order mismatch')
        for key in before:
            if key != 'derivation' and before[key] != after[key]:
                raise ValueError('Recovered/source/unknown evidence altered: ' + key)
        if before != after:
            changes.append(after['original_food_id'])
            resolution = after['derivation_resolution']
            if (after['derivation'] is not None or resolution['status'] != 'UNRESOLVED'
                    or any(resolution[k] is not None for k in ['preferred_label', 'preferred_source', 'unified_nutrient_method_authority'])):
                raise ValueError('Conflict authority inferred')
    if sorted(changes) != ['F001972', 'F009464']:
        raise ValueError('Unexpected changed food identities')
    if sum(len(r['recovered_source_columns']) for r in successor) != recovered:
        raise ValueError('Recovered observations changed')


def check_manifest(directory):
    manifest = json.loads((directory / 'manifest.json').read_text())
    outputs = manifest.get('outputs', [manifest.get('output')])
    for output in outputs:
        path = directory / Path(output['path']).name
        if hashlib.sha256(path.read_bytes()).hexdigest() != output['sha256']:
            raise ValueError('Packet output digest mismatch')
    return manifest


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--normalization-packet', type=Path, required=True)
    cli.add_argument('--conflict-packet', type=Path, required=True)
    args = cli.parse_args()
    check_manifest(args.normalization_packet)
    check_manifest(args.conflict_packet)
    parent = rows(args.normalization_packet / 'normalization-delta.jsonl')
    successor = rows(args.conflict_packet / 'normalization-delta.jsonl')
    verify_normalization(parent)
    verify_conflicts(parent, successor)
    print('PASS full explicit packet checks; no semantic acceptance issued')
